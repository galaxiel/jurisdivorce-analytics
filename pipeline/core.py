"""Fondations du pipeline d'ingestion v2 : filtre normalisé, troncature intelligente,
réparation JSON, extraction XML DILA (TEXTE_JURI_JUDI), concurrence adaptative 429
et heartbeat temps réel du moniteur.

Le script historique `ingest_judilibre_brut.py` reste fonctionnel en autonome ;
ce module en est l'évolution partagée par `pipeline/ingest.py`.
"""
import asyncio
import json
import re
import sqlite3
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# FILTRE NORMALISÉ (sans accents, casse libre) — Étape 1.2 du cahier des charges
# ---------------------------------------------------------------------------
STRONG_TERMS = [
    "etat liquidatif", "liquidation du regime", "liquidation et partage", "liquidation-partage",
    "indivision post-communautaire", "indemnite d'occupation", "prestation compensatoire",
    "proces-verbal de difficultes", "recel de communaute", "creance entre epoux",
    "recompense due par", "recompense due a",
]
SECONDARY_TERMS = [
    "notaire liquidateur", "communaute reduite aux acquets", "separation de biens",
    "soulte", "attribution preferentielle", "article 270", "art. 270", "article 1469", "art. 1469",
    "article 815-9", "art. 815-9",
    "liquidateur", "etat des recompenses", "partage des acquets",
    # élargis après audit CASS (rejets contenant encore des termes utiles) :
    "communaute universelle", "participation aux acquets", "clause de partage", "preciput",
    "pension alimentaire", "article 266", "art. 266", "article 1240", "art. 1240",
    "nom d'usage", "article 700", "art. 700",
    "logement familial", "usage du logement", "mesure provisoire", "non-conciliation",
    "licitation", "sequestre", "262-1", "avantage matrimonial", "divorce pour faute",
    "indivision", "date des effets patrimoniaux",
]
# Contexte « famille » élargi : un arrêt de concubinage/PACS n'a ni « divorce » ni « époux »
CONTEXT_TERMS = ["divorce", "epoux", "epouse", "concubin", "pacs", "union libre", "conjoint"]
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
    if not any(c in n for c in CONTEXT_TERMS):
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
# NORMALISATION JURIDICTIONS / RÉGIMES (anti-doublons dans les comparatifs)
# ---------------------------------------------------------------------------
_APPEL_CITIES = [
    "Aix-en-Provence", "Agen", "Amiens", "Angers", "Basse-Terre", "Bastia",
    "Besançon", "Bordeaux", "Bourges", "Caen", "Cayenne", "Chambéry", "Colmar",
    "Dijon", "Douai", "Fort-de-France", "Grenoble", "Limoges", "Lyon", "Metz",
    "Montpellier", "Nancy", "Nîmes", "Nouméa", "Orléans", "Papeete", "Paris",
    "Pau", "Poitiers", "Reims", "Rennes", "Riom", "Rouen", "Saint-Denis",
    "Toulouse", "Versailles",
]
# Villes sans Cour d'appel → ressort canonique (Marseille → Aix-en-Provence, Nantes → Rennes)
_APPEL_ALIASES = {
    "marseille": "Aix-en-Provence",
    "nantes": "Rennes",
}


def normalize_juridiction(name: Optional[str]) -> Optional[str]:
    """« CA Paris », « COUR D'APPEL DE PARIS », « cour d'appel, Paris, France » →
    « Cour d'appel de Paris » (forme canonique, anti-doublons graphiques)."""
    if not name or not name.strip():
        return name
    n = normalize_text(name)
    if "appel" not in n and not re.match(r"^\s*ca\b", n):
        return name.strip()
    for city in _APPEL_CITIES:
        if normalize_text(city) in n:
            prefix = "d'" if normalize_text(city)[:1] in "aeiou" else "de "
            return f"Cour d'appel {prefix}{city}"
    for alias, city in _APPEL_ALIASES.items():
        if alias in n:
            prefix = "d'" if city[:1].lower() in "aeiou" else "de "
            return f"Cour d'appel {prefix}{city}"
    return name.strip()


def normalize_regime(name: Optional[str]) -> Optional[str]:
    """Unifie les régimes matrimoniaux vers les codes de l'énumération."""
    if not name:
        return name
    n = normalize_text(name)
    if "universelle" in n:
        return "COMMUNAUTE_UNIVERSELLE"
    # Contrat avec clause de partage : parts inégales, préciput, attribution intégrale
    if any(k in n for k in ("clause", "preciput", "attribution integrale", "parts inegales", "partage inegal")):
        return "COMMUNAUTE_AVEC_CLAUSE"
    if "participation" in n:
        return "PARTICIPATION_AUX_ACQUETS"
    if "separation" in n:
        return "SEPARATION_DE_BIENS"
    if "indivision" in n:
        return "INDIVISION"
    # Depuis 1966, la communauté légale = communauté réduite aux acquêts ;
    # une communauté conventionnelle sans clause modificatrice = idem.
    if "reduite" in n or "acquet" in n or "legale" in n or "conventionnelle" in n:
        return "COMMUNAUTE_REDUITE_AUX_ACQUETS"
    if "communaute" in n:
        return "COMMUNAUTE_REDUITE_AUX_ACQUETS"
    return name.strip()


NATURE_CODES = {
    "TRAVAUX_BIEN_PROPRE", "FINANCEMENT_ACQUISITION", "REMBOURSEMENT_EMPRUNT",
    "APPORT_FONDS_PROPRES", "RECEL_COMMUNAUTE", "COMPTE_JOINT_VIDE",
    "TAXES_ASSURANCE", "AUTRE",
}
_NATURE_ALIASES = {
    "travaux": "TRAVAUX_BIEN_PROPRE",
    "financement": "FINANCEMENT_ACQUISITION",
    "acquisition": "FINANCEMENT_ACQUISITION",
    "remboursement": "REMBOURSEMENT_EMPRUNT",
    "emprunt": "REMBOURSEMENT_EMPRUNT",
    "apport": "APPORT_FONDS_PROPRES",
    "heritage": "APPORT_FONDS_PROPRES",
    "recel": "RECEL_COMMUNAUTE",
    "compte joint": "COMPTE_JOINT_VIDE",
    "taxe": "TAXES_ASSURANCE",
    "assurance": "TAXES_ASSURANCE",
    "autre": "AUTRE",
}


def normalize_nature(v: Any) -> Optional[str]:
    """Nature de réclamation → code canonique (NATURE_FR). Inconnu → AUTRE (filtrable),
    jamais de texte brut en base."""
    if not v:
        return None
    s = str(v).strip()
    if s in NATURE_CODES:
        return s
    n = normalize_text(s)
    if n.upper() in NATURE_CODES:
        return n.upper()
    for k, code in _NATURE_ALIASES.items():
        if k in n:
            return code
    return "AUTRE"


_TYPE_PROC_ALIASES = {
    "liquidation": "Liquidation-partage après divorce",
    "partage": "Liquidation-partage après divorce",
    "divorce": "Divorce contentieux",
    "indivision": "Indivision hors mariage/PACS",
    "pacs": "Indivision hors mariage/PACS",
    "jaf": "Appel sur ordonnance JAF",
    "appel": "Appel sur ordonnance JAF",
}
_TYPE_PROC_CODES = {
    "Divorce contentieux", "Liquidation-partage après divorce",
    "Indivision hors mariage/PACS", "Appel sur ordonnance JAF",
}


def normalize_type_procedure(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip()
    if s in _TYPE_PROC_CODES:
        return s
    n = normalize_text(s)
    for k, canon in _TYPE_PROC_ALIASES.items():
        if k in n:
            return canon
    return s


_PC_FORME_CODES = {
    "CAPITAL_UNIQUE", "CAPITAL_ECHELONNE", "RENTE_MENSUELLE",
    "ATTRIBUTION_BIEN", "MIXTE", "AUCUNE",
}
_PC_FORME_ALIASES = {
    "capital unique": "CAPITAL_UNIQUE", "unique": "CAPITAL_UNIQUE",
    "echelonne": "CAPITAL_ECHELONNE", "rente": "RENTE_MENSUELLE",
    "attribution": "ATTRIBUTION_BIEN", "bien": "ATTRIBUTION_BIEN",
    "mixte": "MIXTE", "aucune": "AUCUNE",
}


def normalize_pc_forme(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip()
    if s in _PC_FORME_CODES:
        return s
    n = normalize_text(s)
    if n.upper() in _PC_FORME_CODES:
        return n.upper()
    for k, code in _PC_FORME_ALIASES.items():
        if k in n:
            return code
    return None  # inconnu → null (l'info brute reste dans extracted_json)


_MODE_GARDE_CODES = {"Résidence classique + DVH", "Garde alternée", "Non précisé"}
_MODE_GARDE_ALIASES = {
    "classique": "Résidence classique + DVH", "dvh": "Résidence classique + DVH",
    "alternee": "Garde alternée", "garde alternee": "Garde alternée",
    "non precise": "Non précisé",
}


def normalize_mode_garde(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip()
    if s in _MODE_GARDE_CODES:
        return s
    n = normalize_text(s)
    for k, canon in _MODE_GARDE_ALIASES.items():
        if k in n:
            return canon
    return None


def norm_amount(v: Any) -> Optional[float]:
    """Montant financier : nombre pur ou None. Négatif / non numérique → None.
    `0` est réservé aux demandes explicitement rejetées (appliqué dans save_decision)."""
    v = _num(v)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f < 0 else f


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
    date_effets_patrimoniaux TEXT, gestion_loyers_mois REAL, gestion_charges_mois REAL,
    gestion_solde REAL, pension_par_enfant REAL, revenus_debiteur_mois REAL,
    mode_garde TEXT, partage_frais_exceptionnels BOOLEAN, prestations_sociales_integrees BOOLEAN,
    ecart_ressources_totales REAL, nom_usage_accorde BOOLEAN, nom_usage_motif TEXT,
    di_accordes REAL, divorce_faute_retenu BOOLEAN,
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
CREATE TABLE IF NOT EXISTS failed_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT, text_truncated TEXT, error TEXT,
    attempts INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY, value TEXT
);
"""

# Colonnes ajoutées a posteriori (base créée avant ces champs)
PIPELINE_MIGRATION_COLUMNS = {
    "pipeline_state": {"files_read": "INTEGER DEFAULT 0", "retry_failed": "INTEGER DEFAULT 0"},
}


def _migrate_pipeline_columns(conn: sqlite3.Connection) -> None:
    for table, cols in PIPELINE_MIGRATION_COLUMNS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col, coltype in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(PIPELINE_TABLES_SQL)
    _migrate_pipeline_columns(conn)
    return conn


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    """WAL + busy_timeout : zéro 'database is locked' entre worker et API."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")


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


# ---------------------------------------------------------------------------
# EXTRACTION XML DILA (fonds freemium CAPP / CASS / TJ : TEXTE_JURI_JUDI)
# ---------------------------------------------------------------------------
def parse_juri_xml(data: bytes) -> Optional[Dict[str, str]]:
    """Extrait id/juridiction/date/numéro/texte d'un fichier XML DILA.

    Structure : TEXTE_JURI_JUDI > META > META_COMMUN/ID + META_SPEC/META_JURI
    (JURIDICTION, DATE_DEC) + META_JURI_JUDI/NUMEROS_AFFAIRES + TEXTE (paragraphes).
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    texte_el = root.find("TEXTE") or root.find("BLOCTEXTUEL")
    if texte_el is None:
        return None
    paragraphs = [
        "".join(el.itertext()).strip()
        for el in texte_el.iter()
        if len(el) == 0 and (el.text or "").strip()
    ]
    body = "\n".join(paragraphs)
    if len(body) < MIN_CHARS:
        return None

    juridiction = (root.findtext(".//META_SPEC/META_JURI/JURIDICTION") or "").strip()
    date_dec = (root.findtext(".//META_SPEC/META_JURI/DATE_DEC")
                or root.findtext(".//META_COMMUN/DATE_TEXTE") or "").strip()
    numero = (root.findtext(".//NUMERO_AFFAIRE") or "").strip()
    decision_id = (root.findtext(".//META_COMMUN/ID") or "").strip()
    nature = (root.findtext(".//META_COMMUN/NATURE") or "ARRET").strip()

    # En-tête : indispensable au LLM pour extraire metadata.juridiction / date_decision
    header_bits = [juridiction.upper(), f"{nature} DU {date_dec}"]
    if numero:
        header_bits.append(f"N° RG {numero}")
    header = " — ".join(b for b in header_bits if b)
    text = f"{header}\n\n{body}"
    return {"id": decision_id, "text": text}


def _num(v: Any) -> Optional[float]:
    if v is None or isinstance(v, dict) or isinstance(v, list):
        return None
    if isinstance(v, str) and not re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
        return None
    return v


def _bool(v: Any) -> Optional[bool]:
    return None if v is None else bool(v)


def save_decision(conn: sqlite3.Connection, decision_id: str, md5: str, raw_text: str, ex: dict):
    """Aplanit le JSON LLM enrichi (v2) en colonnes requêtables + réclamations.

    Règles : juridiction/régime normalisés ; montants négatifs/non numériques → NULL ;
    `montant_accorde = 0` réservé aux demandes explicitement rejetées."""
    meta = ex.get("metadata") or {}
    ctx = ex.get("contexte_familial") or {}
    biens = ex.get("biens_litigieux") or {}
    occ = ex.get("indemnite_occupation") or {}
    pc = ex.get("prestation_compensatoire") or {}
    cout = ex.get("cout_issue") or (ex.get("frais_et_depens") or {})
    strat = ex.get("analyse_strategique") or {}
    gest = ex.get("gestion_bien_locatif_indivis") or {}
    pen = ex.get("pension_alimentaire") or {}
    rev = ex.get("revenus") or {}
    annexes = ex.get("issue_demandes_annexes") or {}

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
                date_effets_patrimoniaux, gestion_loyers_mois, gestion_charges_mois, gestion_solde,
                pension_par_enfant, revenus_debiteur_mois, mode_garde, partage_frais_exceptionnels,
                prestations_sociales_integrees, ecart_ressources_totales,
                nom_usage_accorde, nom_usage_motif, di_accordes, divorce_faute_retenu,
                resume_3_lignes, resume_pedagogique, conseil_pratique,
                raw_text, extracted_json, text_md5
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decision_id, "JUDILIBRE_OD", meta.get("numero_pourvoi_rg"),
                normalize_juridiction(meta.get("juridiction")),
                meta.get("chambre"), meta.get("date_decision"),
                normalize_type_procedure(ctx.get("type_procedure")), normalize_regime(ctx.get("regime_matrimonial")),
                _num(ctx.get("duree_mariage_annees")), _num(ctx.get("nombre_enfants")), _num(ctx.get("age_epoux_moyen")),
                _bool(biens.get("bien_immobilier_principal")), norm_amount(biens.get("valeur_bien_principal")),
                _bool(biens.get("entreprises_societes")), _bool(biens.get("comptes_epargne")),
                _bool(occ.get("demandee")), _bool(occ.get("accordee")),
                norm_amount(occ.get("montant_mensuel_base_valeur_locative") or occ.get("valeur_locative_mensuelle_retenue")),
                norm_amount(occ.get("pourcentage_abattement_accorde") or occ.get("taux_abattement_precarite_pct")),
                norm_amount(occ.get("montant_mensuel_final")), _num(occ.get("duree_mois_retenue")),
                norm_amount(occ.get("montant_total_accorde")),
                occ.get("motifs_rejet_ou_reduction") or occ.get("motif_refus_ou_modulation"),
                _bool(pc.get("demandee")), _bool(pc.get("accordee")), normalize_pc_forme(pc.get("forme")),
                norm_amount(pc.get("montant_capital_accorde") or pc.get("montant_accorde")),
                norm_amount(pc.get("montant_demande_epoux_A")), norm_amount(pc.get("montant_propose_epoux_B")),
                norm_amount(pc.get("ecart_revenus_mensuel")),
                json.dumps(criteres, ensure_ascii=False) if criteres else None,
                norm_amount(pc.get("montant_rente_mensuelle")), _num(pc.get("duree_rente_mois")),
                norm_amount(cout.get("article_700_accorde") or cout.get("article_700_montant")),
                cout.get("partie_condamnee_depens") or cout.get("partage_depens"),
                _num(cout.get("delai_procedure_estime_mois")),
                ex.get("effets_patrimoniaux", {}).get("date_effets_patrimoniaux_retenue") or ex.get("effets_patrimoniaux", {}).get("date"),
                norm_amount(gest.get("loyers_encaisses_mois")),
                norm_amount(gest.get("charges_deductibles_mois")),
                norm_amount(gest.get("solde_restitue_indivision")),
                norm_amount(pen.get("pension_par_enfant")),
                norm_amount(pen.get("revenus_debiteur_mois")),
                normalize_mode_garde(pen.get("mode_garde")),
                _bool(pen.get("partage_frais_exceptionnels")),
                _bool(rev.get("prestations_sociales_integrees")),
                norm_amount(rev.get("ecart_ressources_totales")),
                _bool(annexes.get("nom_usage_accorde")),
                annexes.get("nom_usage_motif"),
                norm_amount(annexes.get("dommages_interets_accordes")),
                _bool(annexes.get("divorce_faute_retenu")),
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
            statut = r.get("statut")
            # null vs 0 : `0` réservé aux demandes explicitement rejetées
            accorde = 0.0 if statut == "REJETE" else norm_amount(
                r.get("montant_accorde")
            )
            conn.execute(
                """INSERT INTO recompenses (decision_id, categorie, demandeur, montant_reclame,
                   montant_accorde, statut, preuve_type, preuve_clef_retenue, motif_echec,
                   regle_calcul, preuves_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    decision_id, normalize_nature(r.get("nature") or r.get("categorie")), r.get("demandeur"),
                    norm_amount(r.get("montant_reclame") or r.get("montant_demande")),
                    accorde, statut,
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
            _apply_pragmas(self._conn)
            self._conn.executescript(PIPELINE_TABLES_SQL)
            _migrate_pipeline_columns(self._conn)
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


# ---------------------------------------------------------------------------
# CONCURRENCE ADAPTATIVE — sature le quota sans se faire bannir par les 429
# ---------------------------------------------------------------------------
class AdaptiveLimiter:
    """Limiteur concurrent dynamique : part de MAX_CONCURRENCY, se réduit de moitié
    à chaque 429 (rate limit Zhipu) puis remonte progressivement sans nouvelle 429.

    Usage : limiter = AdaptiveLimiter(50) ; await limiter.acquire() … await limiter.release().
    """

    def __init__(self, max_size: int):
        self.max_size = max(1, max_size)
        self.size = self.max_size
        self.active = 0
        self._cv = asyncio.Condition()
        self._paused_until = 0.0
        self._recover_delay = 60.0

    async def acquire(self) -> None:
        async with self._cv:
            while self.active >= self.size:
                await self._cv.wait()
            self.active += 1

    async def release(self) -> None:
        async with self._cv:
            self.active = max(0, self.active - 1)
            self._cv.notify()

    def on_rate_limited(self) -> int:
        """429 reçu : réduit la concurrence et impose un temps de récupération."""
        self.size = max(2, self.size // 2)
        self._paused_until = time.monotonic() + self._recover_delay
        return self.size

    async def grow_loop(self) -> None:
        """Remonte progressivement vers MAX_CONCURRENCY quand plus de 429."""
        while True:
            await asyncio.sleep(self._recover_delay)
            async with self._cv:
                if time.monotonic() > self._paused_until and self.size < self.max_size:
                    self.size = min(self.max_size, self.size + max(1, self.max_size // 10))
                    self._cv.notify_all()

    async def set_target(self, new_max: int) -> None:
        """Réglage à chaud de la concurrence cible (table app_config, depuis /pipeline)."""
        async with self._cv:
            self.max_size = max(1, new_max)
            self.size = min(self.size, self.max_size)
            self._cv.notify_all()


def read_config(conn: sqlite3.Connection, defaults: dict) -> dict:
    """Lit app_config (réglages à chaud depuis /pipeline) par-dessus les défauts .env."""
    try:
        rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    except sqlite3.OperationalError:
        return dict(defaults)
    merged = dict(defaults)
    for r in rows:
        merged[r["key"]] = r["value"]
    return merged


def record_failure(conn: sqlite3.Connection, decision_id: str, text: str, error: str, attempts: int) -> None:
    """Dead Letter Queue : la décision n'est jamais perdue, elle attend une relance."""
    with conn:
        conn.execute(
            "INSERT INTO failed_decisions (decision_id, text_truncated, error, attempts) VALUES (?,?,?,?)",
            (decision_id, (text or "")[:12000], str(error)[:300], attempts),
        )


class BatchWriter:
    """File d'écriture dédiée : les workers déposent, UN SEUL task écrit par lots de 25
    décisions (une seule transaction) → zéro contention SQLite même à 50 workers."""

    def __init__(self, conn: sqlite3.Connection, state: "PipelineStateWriter",
                 batch_size: int = 25, flush_interval: float = 2.0):
        self.conn = conn
        self.state = state
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def put(self, decision_id: str, md5: str, text: str, extracted: dict) -> None:
        await self.queue.put((decision_id, md5, text, extracted))

    async def run(self) -> None:
        while True:
            items = [await self.queue.get()]
            deadline = time.monotonic() + self.flush_interval
            while len(items) < self.batch_size and time.monotonic() < deadline:
                try:
                    items.append(await asyncio.wait_for(self.queue.get(), timeout=0.5))
                except asyncio.TimeoutError:
                    break
            try:
                with self.conn:  # une seule transaction pour tout le lot
                    for decision_id, md5, text, extracted in items:
                        save_decision(self.conn, decision_id, md5, text, extracted)
                self.state.bump(decisions_analyzed=len(items))
            except Exception as exc:
                self.state.bump(decisions_failed=len(items))
                self.state.log("ERROR", f"Écriture lot de {len(items)} refusée : {exc}")
            for _ in items:  # task_done par item (sinon queue.join() n'aboutit jamais)
                self.queue.task_done()

    async def flush_remaining(self) -> None:
        await self.queue.join()
