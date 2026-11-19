"""Fondations du pipeline d'ingestion v2 : filtre normalisé, troncature intelligente,
réparation JSON, schéma SQL enrichi et heartbeat temps réel du moniteur.

Le script historique `ingest_judilibre_brut.py` reste fonctionnel en autonome ;
ce module en est l'évolution partagée par `pipeline/ingest.py`.
"""
import json
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# FILTRE NORMALISÉ (sans accents, casse libre) — Étape 1.2 du cahier des charges
# ---------------------------------------------------------------------------
STRONG_TERMS = [
    "etat liquidatif", "liquidation du regime", "liquidation et partage",
    "indivision post-communautaire", "indemnite d'occupation", "prestation compensatoire",
    "proces-verbal de difficultes", "recel de communaute", "creance entre epoux",
    "recompense due par", "recompense due a",
]
SECONDARY_TERMS = [
    "notaire liquidateur", "communaute reduite aux acquets", "separation de biens",
    "soulte", "attribution preferentielle", "article 270", "article 1469", "article 815-9",
    "liquidateur", "etat des recompenses", "partage des acquets",
]
MIN_CHARS = 1200
OCCULTATION_MARKERS = ["motifs de la decision occultes", "motifs occultes", "motifs occultés"]


def normalize_text(text: str) -> str:
    t = text.lower().replace("\u2019", "'")
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def decision_filter(raw_text: str) -> Tuple[bool, str]:
    """Retient 1 terme fort, ou ≥2 termes secondaires dans un contexte divorce/époux.

    La pseudonymisation (`[...]`, `***`) n'est JAMAIS un motif de rejet : on ne
    rejette que si les motifs sont explicitement occultés ou si la décision est
    trop courte pour être exploitable.
    """
    if not raw_text or len(raw_text) < MIN_CHARS:
        return False, "trop court"
    n = normalize_text(raw_text)
    if any(marker in n for marker in OCCULTATION_MARKERS):
        return False, "motifs occultes"
    for term in STRONG_TERMS:
        if term in n:
            return True, f"fort:{term}"
    if not ("divorce" in n or "epoux" in n or "epouse" in n):
        return False, "hors champ"
    secondary = [t for t in SECONDARY_TERMS if t in n]
    if len(secondary) >= 2:
        return True, f"secondaires:{len(secondary)}"
    return False, "aucun terme"


# ---------------------------------------------------------------------------
# TRONCATURE INTELLIGENTE — garde en-tête, motifs financiers et dispositif final
# ---------------------------------------------------------------------------
SECTION_MARKERS = [
    "exposé du litige", "expose du litige", "discussion", "sur l'indemnité d'occupation",
    "sur les récompenses", "sur la prestation compensatoire", "par ces motifs",
    "pour ces motifs", "décide", "statuant",
]


def smart_truncate(text: str, max_chars: int = 48_000) -> str:
    """Budget réparti : en-tête (identité de l'affaire) + cœur juridique + dispositif.

    Une troncature brute par la fin perdrait l'état liquidatif et les montants,
    qui figurent quasi toujours dans les derniers paragraphes de l'arrêt.
    """
    if len(text) <= max_chars:
        return text
    header_budget = max(1000, min(2500, max_chars // 8))
    dispositif_budget = max(1000, min(4000, max_chars // 3))
    header = text[:header_budget]
    dispositif = text[-dispositif_budget:]
    middle_budget = max_chars - len(header) - len(dispositif) - 100
    if middle_budget < 1000:
        return text[:max_chars]
    n = normalize_text(text[2500:])
    start = len(text)
    for marker in SECTION_MARKERS:
        idx = n.find(normalize_text(marker))
        if idx != -1:
            start = min(start, 2500 + idx)
    middle_start = min(start, len(text) - middle_budget)
    middle = text[middle_start:middle_start + middle_budget]
    return f"{header}\n[…]\n{middle}\n[…]\n{dispositif}"


# ---------------------------------------------------------------------------
# RÉPARATION JSON — Étape 1.3 : ne jamais perdre une décision pour un format près
# ---------------------------------------------------------------------------
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_NAN = re.compile(r"\bNaN\b|\bInfinity\b")


def repair_json(raw: str) -> Dict[str, Any]:
    s = _FENCE.sub("", str(raw).strip())
    start = s.find("{")
    if start == -1:
        raise ValueError("aucun objet JSON dans la réponse")
    depth = 0
    end = len(s)
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    s = s[start:end]
    s = _TRAILING_COMMA.sub(r"\1", s)
    s = _NAN.sub("null", s)
    return json.loads(s)


# ---------------------------------------------------------------------------
# CLASSIFICATION DE PREUVE (même heuristique que backend/app/services/classify.py)
# ---------------------------------------------------------------------------
_NEGATIVE = re.compile(r"absence de (facture|justificatif|preuve)s?|sans facture|aucun(e)? (justificatif|facture|preuve|pièce)|défaut de preuve", re.I)
_FACTURE = re.compile(r"factures?\b|devis\b", re.I)
_RELEVE = re.compile(r"relev[eé]s?\b", re.I)
_ATTESTATION = re.compile(r"attestations?\b", re.I)


def classify_proof(*texts: Optional[str]) -> str:
    t = " ".join(x for x in texts if x)
    if not t.strip():
        return "AUCUNE"
    if _NEGATIVE.search(t):
        return "AUCUNE"
    if _FACTURE.search(t):
        return "FACTURE_NOMINATIVE"
    if _RELEVE.search(t):
        return "RELEVE_BANCAIRE"
    if _ATTESTATION.search(t):
        return "ATTESTATION"
    return "AUTRE"


# ---------------------------------------------------------------------------
# SCHÉMA SQL v2 (identique à backend/app/models.py) + tables du moniteur
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY, source TEXT DEFAULT 'JUDILIBRE_OD', numero_rg TEXT,
    juridiction TEXT, chambre TEXT, date_decision TEXT,
    type_procedure TEXT, regime_matrimonial TEXT,
    duree_mariage_annees INTEGER, nombre_enfants INTEGER, age_epoux_moyen REAL,
    bien_immobilier_principal BOOLEAN, valeur_bien_principal REAL,
    entreprises_societes BOOLEAN, comptes_epargne BOOLEAN,
    occupation_demandee BOOLEAN, occupation_accordee BOOLEAN,
    occupation_montant_mensuel_base REAL, occupation_abattement_pct REAL,
    occupation_montant_mensuel_final REAL, occupation_duree_mois INTEGER,
    occupation_montant_total REAL, occupation_motif_modulation TEXT,
    pc_demandee BOOLEAN, pc_accordee BOOLEAN, pc_forme TEXT,
    pc_montant_capital REAL, pc_montant_demande REAL, pc_montant_propose REAL,
    pc_ecart_revenus_mensuel REAL, pc_criteres_json TEXT,
    pc_rente_mensuelle REAL, pc_duree_rente_mois INTEGER,
    article_700_montant REAL, partage_depens TEXT, delai_procedure_mois INTEGER,
    resume_3_lignes TEXT, resume_pedagogique TEXT, conseil_pratique TEXT,
    raw_text TEXT, extracted_json TEXT, text_md5 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_decisions_md5 ON decisions(text_md5);
CREATE INDEX IF NOT EXISTS idx_decisions_juridiction ON decisions(juridiction);
CREATE INDEX IF NOT EXISTS idx_decisions_date ON decisions(date_decision);
CREATE TABLE IF NOT EXISTS recompenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT,
    categorie TEXT, demandeur TEXT, montant_reclame REAL, montant_accorde REAL,
    statut TEXT, preuve_type TEXT, preuve_clef_retenue TEXT, motif_echec TEXT,
    regle_calcul TEXT, preuves_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_recompenses_decision ON recompenses(decision_id);
CREATE INDEX IF NOT EXISTS idx_recompenses_statut ON recompenses(statut);
"""

PIPELINE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT DEFAULT 'idle', mode TEXT, current_archive TEXT,
    archives_done INTEGER DEFAULT 0, archives_total INTEGER DEFAULT 0,
    decisions_scanned INTEGER DEFAULT 0, decisions_kept INTEGER DEFAULT 0,
    decisions_analyzed INTEGER DEFAULT 0, decisions_failed INTEGER DEFAULT 0,
    tokens_today INTEGER DEFAULT 0, day_key TEXT, queue_size INTEGER DEFAULT 0,
    started_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, level TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS processed_archives (
    url TEXT PRIMARY KEY, fonds TEXT, size_bytes INTEGER,
    status TEXT DEFAULT 'pending', decisions_found INTEGER DEFAULT 0,
    decisions_analyzed INTEGER DEFAULT 0, error TEXT, processed_at TEXT
);
"""


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.executescript(SCHEMA_SQL)
    conn.executescript(PIPELINE_TABLES_SQL)
    return conn


# ---------------------------------------------------------------------------
# EXTRACTION DE TEXTE UNIVERSSELLE (tolérante aux formats des dumps DILA)
# ---------------------------------------------------------------------------
_TEXT_KEYS = ("text", "texte", "contenu", "contenuHtml", "texte_integral", "body")


def extract_text(data: Any) -> str:
    """Trouve le texte de la décision dans un JSON DILA quel que soit son habillage."""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in _TEXT_KEYS:
            v = data.get(key)
            if isinstance(v, str) and len(v) >= MIN_CHARS:
                return v
        decision = data.get("decision") or data.get("arret") or data.get("jugement")
        if isinstance(decision, dict):
            nested = extract_text(decision)
            if nested:
                return nested
        # dernier recours : la plus longue chaîne du document
        longest = ""
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, str) and len(item) > len(longest):
                longest = item
        return longest
    return ""


def extract_id(data: Any, fallback: str) -> str:
    if isinstance(data, dict):
        for key in ("id", "id_decision", "numero_affaire", "numero_rg", "matiere"):
            v = data.get(key)
            if isinstance(v, (str, int)) and str(v).strip():
                return str(v)
    return fallback


def _num(v: Any) -> Optional[float]:
    if v is None or isinstance(v, dict) or isinstance(v, list):
        return None
    if isinstance(v, str) and not re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
        return None
    return v


def _bool(v: Any) -> Optional[bool]:
    return None if v is None else bool(v)


def save_decision(conn: sqlite3.Connection, decision_id: str, md5: str, raw_text: str, ex: dict):
    """Aplanit le JSON LLM enrichi (v2) en colonnes requêtables + réclamations."""
    meta = ex.get("metadata") or {}
    ctx = ex.get("contexte_familial") or {}
    biens = ex.get("biens_litigieux") or {}
    occ = ex.get("indemnite_occupation") or {}
    pc = ex.get("prestation_compensatoire") or {}
    cout = ex.get("cout_issue") or (ex.get("frais_et_depens") or {})
    strat = ex.get("analyse_strategique") or {}

    criteres = pc.get("criteres_determinants") or pc.get("criteres") or []
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO decisions (
                id, source, numero_rg, juridiction, chambre, date_decision,
                type_procedure, regime_matrimonial,
                duree_mariage_annees, nombre_enfants, age_epoux_moyen,
                bien_immobilier_principal, valeur_bien_principal, entreprises_societes, comptes_epargne,
                occupation_demandee, occupation_accordee, occupation_montant_mensuel_base,
                occupation_abattement_pct, occupation_montant_mensuel_final, occupation_duree_mois,
                occupation_montant_total, occupation_motif_modulation,
                pc_demandee, pc_accordee, pc_forme, pc_montant_capital, pc_montant_demande,
                pc_montant_propose, pc_ecart_revenus_mensuel, pc_criteres_json,
                pc_rente_mensuelle, pc_duree_rente_mois,
                article_700_montant, partage_depens, delai_procedure_mois,
                resume_3_lignes, resume_pedagogique, conseil_pratique,
                raw_text, extracted_json, text_md5
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decision_id, "JUDILIBRE_OD", meta.get("numero_pourvoi_rg"), meta.get("juridiction"),
                meta.get("chambre"), meta.get("date_decision"),
                ctx.get("type_procedure"), ctx.get("regime_matrimonial"),
                _num(ctx.get("duree_mariage_annees")), _num(ctx.get("nombre_enfants")), _num(ctx.get("age_epoux_moyen")),
                _bool(biens.get("bien_immobilier_principal")), _num(biens.get("valeur_bien_principal")),
                _bool(biens.get("entreprises_societes")), _bool(biens.get("comptes_epargne")),
                _bool(occ.get("demandee")), _bool(occ.get("accordee")),
                _num(occ.get("montant_mensuel_base_valeur_locative") or occ.get("valeur_locative_mensuelle_retenue")),
                _num(occ.get("pourcentage_abattement_accorde") or occ.get("taux_abattement_precarite_pct")),
                _num(occ.get("montant_mensuel_final")), _num(occ.get("duree_mois_retenue")),
                _num(occ.get("montant_total_accorde")),
                occ.get("motifs_rejet_ou_reduction") or occ.get("motif_refus_ou_modulation"),
                _bool(pc.get("demandee")), _bool(pc.get("accordee")), pc.get("forme"),
                _num(pc.get("montant_capital_accorde") or pc.get("montant_accorde")),
                _num(pc.get("montant_demande_epoux_A")), _num(pc.get("montant_propose_epoux_B")),
                _num(pc.get("ecart_revenus_mensuel")),
                json.dumps(criteres, ensure_ascii=False) if criteres else None,
                _num(pc.get("montant_rente_mensuelle")), _num(pc.get("duree_rente_mois")),
                _num(cout.get("article_700_accorde") or cout.get("article_700_montant")),
                cout.get("partie_condamnee_depens") or cout.get("partage_depens"),
                _num(cout.get("delai_procedure_estime_mois")),
                strat.get("resume_decision_3_lignes"),
                strat.get("resume_pedagogique_3_lignes"),
                strat.get("conseil_pratique_extrait"),
                raw_text, json.dumps(ex, ensure_ascii=False), md5,
            ),
        )
        conn.execute("DELETE FROM recompenses WHERE decision_id = ?", (decision_id,))
        reclamations = ex.get("reclamations_financieres") or ex.get("recompenses_et_creances") or []
        for r in reclamations:
            if not isinstance(r, dict):
                continue
            preuves = r.get("preuves_determinantes") or []
            conn.execute(
                """INSERT INTO recompenses (decision_id, categorie, demandeur, montant_reclame,
                   montant_accorde, statut, preuve_type, preuve_clef_retenue, motif_echec,
                   regle_calcul, preuves_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    decision_id, r.get("nature") or r.get("categorie"), r.get("demandeur"),
                    _num(r.get("montant_reclame") or r.get("montant_demande")),
                    _num(r.get("montant_accorde")), r.get("statut"),
                    classify_proof(r.get("preuve_clef_retenue"), r.get("cause_echec"), r.get("motif_echec")),
                    r.get("preuve_clef_retenue"),
                    r.get("cause_echec") or r.get("motif_echec"),
                    r.get("regle_calcul"),
                    json.dumps(preuves, ensure_ascii=False) if preuves else None,
                ),
            )


# ---------------------------------------------------------------------------
# HEARTBEAT TEMPS RÉEL — alimente le moniteur /pipeline et l'API de contrôle
# ---------------------------------------------------------------------------
MAX_LOGS = 5000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PipelineStateWriter:
    """Écrit l'état du pipeline dans SQLite depuis le process d'ingestion.

    L'API FastAPI (routers/pipeline.py) lit ces tables : cross-process par la base.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._last_heartbeat = 0.0
        self._log_count = 0

    def _get(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=30)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA busy_timeout = 30000")
            self._conn.executescript(PIPELINE_TABLES_SQL)
        return self._conn

    def init(self, mode: str, archives_total: int = 0) -> None:
        conn = self._get()
        now = _now()
        conn.execute(
            """INSERT OR REPLACE INTO pipeline_state
               (id, status, mode, archives_total, started_at, updated_at, day_key,
                decisions_scanned, decisions_kept, decisions_analyzed, decisions_failed,
                tokens_today, archives_done, queue_size)
               VALUES (1, 'running', ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0)""",
            (mode, archives_total, now, now, date.today().isoformat()),
        )
        conn.commit()
        self.log("INFO", f"Pipeline démarré (mode={mode}, archives={archives_total}).")

    def heartbeat(self, **fields) -> None:
        conn = self._get()
        fields.setdefault("updated_at", _now())
        day = date.today().isoformat()
        # Reset quotidien du compteur de tokens (quota 300M/jour)
        row = conn.execute("SELECT day_key, tokens_today FROM pipeline_state WHERE id = 1").fetchone()
        if row and row["day_key"] != day:
            fields["tokens_today"] = 0
            fields["day_key"] = day
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE pipeline_state SET {sets} WHERE id = 1", tuple(fields.values()))
        conn.commit()

    def bump(self, **counters) -> None:
        """Incrémente des compteurs : bump(decisions_analyzed=1, tokens_today=1200)…"""
        conn = self._get()
        sets = ", ".join(f"{k} = {k} + ?" for k in counters)
        conn.execute(
            f"UPDATE pipeline_state SET {sets}, updated_at = ? WHERE id = 1",
            (*counters.values(), _now()),
        )
        conn.commit()

    def log(self, level: str, message: str) -> None:
        conn = self._get()
        conn.execute(
            "INSERT INTO pipeline_logs (ts, level, message) VALUES (?, ?, ?)",
            (_now(), level, message[:500]),
        )
        self._log_count += 1
        if self._log_count % 100 == 0:  # purge périodique des vieux logs
            conn.execute(
                f"DELETE FROM pipeline_logs WHERE id NOT IN "
                f"(SELECT id FROM pipeline_logs ORDER BY id DESC LIMIT {MAX_LOGS})"
            )
        conn.commit()

    def mark_archive(self, url: str, fonds: str, size_bytes: int, status: str,
                     decisions_found: int = 0, decisions_analyzed: int = 0,
                     error: str = None) -> None:
        conn = self._get()
        conn.execute(
            """INSERT OR REPLACE INTO processed_archives
               (url, fonds, size_bytes, status, decisions_found, decisions_analyzed, error, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (url, fonds, size_bytes, status, decisions_found, decisions_analyzed, error, _now()),
        )
        conn.commit()

    def control_status(self) -> str:
        row = self._get().execute("SELECT status FROM pipeline_state WHERE id = 1").fetchone()
        return row["status"] if row else "idle"

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
