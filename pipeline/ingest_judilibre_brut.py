"""Pipeline d'ingestion Open Data → analyse LLM → base de données.

Télécharge les archives Judilibre/Open Data (ou lit un .tar.gz local), pré-filtre
les décisions pertinentes par regex locale (0 token), puis soumet chaque décision
au worker asynchrone GLM Flash (Zhipu AI, API OpenAI-compliant) pour extraction
JSON structurée. Les résultats sont aplanis en colonnes requêtables dans la même
base que le backend FastAPI (backend/jurisprudence.db par défaut).

Usage :
    python pipeline/ingest_judilibre_brut.py export_judilibre_cour_appel_2025.tar.gz
    python pipeline/ingest_judilibre_brut.py archives/ --db backend/jurisprudence.db

Variables d'environnement : ZHIPU_API_KEY (requis), ZHIPU_BASE_URL,
JURISDIVORCE_MODEL (défaut glm-4-flash), CONCURRENCY_LIMIT (défaut 20).

Les archives ne doivent JAMAIS être extraites dans ce répertoire (risque
d'import de code planté) : garder les données dans un dossier séparé.
"""
import argparse
import asyncio
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys
import tarfile
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL = os.getenv("JURISDIVORCE_MODEL", "glm-4-flash")
CONCURRENCY_LIMIT = int(os.getenv("CONCURRENCY_LIMIT", "20"))
MAX_TEXT_CHARS = 30_000

KEYWORDS_REGEX = re.compile(
    r"(liquidation du régime matrimonial|état liquidatif|indemnité d'occupation"
    r"|récompense|créance entre époux|prestation compensatoire)",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """Tu es un expert juriste en droit de la famille et un analyste de données judiciaires français.
Ta tâche est d'analyser l'arrêt ou le jugement fourni et d'extraire TOUTES les informations financières, factuelles et juridiques sous la forme d'un objet JSON STRICT respectant scrupuleusement le schéma demandé.

Règles de traitement :
1. Si une information est absente du texte, indique `null`. Ne devine ni n'invente jamais d'information.
2. Exprime tous les montants monétaires en nombres purs (ex: 1500.50 et non "1 500,50 €").
3. Garde une synthèse neutre, factuelle et orientée sur le raisonnement de la décision.

Schéma JSON de sortie :
{
  "metadata": {"juridiction": str|null, "chambre": str|null, "date_decision": "YYYY-MM-DD"|null, "numero_pourvoi_rg": str|null},
  "contexte_familial": {"regime_matrimonial": "COMMUNAUTE_REDUITE_AUX_ACQUETS|SEPARATION_DE_BIENS|PARTICIPATION_AUX_ACQUETS|COMMUNAUTE_UNIVERSELLE|INCONNU", "duree_mariage_annees": number|null, "nombre_enfants": number|null},
  "biens_litigieux": {"bien_immobilier_principal": boolean, "valeur_bien_principal": number|null, "entreprises_societes": boolean, "comptes_epargne": boolean},
  "indemnite_occupation": {"demandee": boolean, "accordee": boolean, "montant_mensuel_base_valeur_locative": number|null, "pourcentage_abattement_accorde": number|null, "montant_mensuel_final": number|null, "duree_mois_retenue": number|null, "montant_total_accorde": number|null, "motifs_rejet_ou_reduction": str|null},
  "recompenses_et_creances": [{"categorie": "TRAVAUX_BIEN_PROPRE|REMBOURSEMENT_EMPRUNT|APPORT_FONDS_PROPRES|AUTRE", "demandeur": "EPOUX_A|EPOUX_B", "montant_reclame": number|null, "montant_accorde": number|null, "statut": "ACCORDE_TOTALEMENT|ACCORDE_PARTIELLEMENT|REJETE", "preuve_clef_retenue": str|null, "motif_echec": str|null}],
  "prestation_compensatoire": {"demandee": boolean, "accordee": boolean, "forme": "CAPITAL_UNIQUE|RENTE_MENSUELLE|MIXTE|AUCUNE", "montant_capital_accorde": number|null, "montant_rente_mensuelle": number|null, "duree_rente_mois": number|null},
  "frais_et_depens": {"article_700_montant": number|null, "partage_depens": "DESIGNE_EPOUX_A|DESIGNE_EPOUX_B|PARTAGE_MOITIE|REJET"},
  "analyse_strategique": {"points_forts_gagnants": [str], "pieges_et_erreurs_a_eviter": [str], "resume_decision_3_lignes": str}
}
Réponds UNIQUEMENT avec l'objet JSON."""

client = AsyncOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY, source TEXT DEFAULT 'JUDILIBRE_OD', numero_rg TEXT,
    juridiction TEXT, chambre TEXT, date_decision TEXT,
    regime_matrimonial TEXT, duree_mariage_annees INTEGER, nombre_enfants INTEGER,
    bien_immobilier_principal BOOLEAN, valeur_bien_principal REAL,
    entreprises_societes BOOLEAN, comptes_epargne BOOLEAN,
    occupation_demandee BOOLEAN, occupation_accordee BOOLEAN,
    occupation_montant_mensuel_base REAL, occupation_abattement_pct REAL,
    occupation_montant_mensuel_final REAL, occupation_duree_mois INTEGER,
    occupation_montant_total REAL,
    pc_demandee BOOLEAN, pc_accordee BOOLEAN, pc_forme TEXT,
    pc_montant_capital REAL, pc_rente_mensuelle REAL, pc_duree_rente_mois INTEGER,
    article_700_montant REAL, partage_depens TEXT, resume_3_lignes TEXT,
    raw_text TEXT, extracted_json TEXT, text_md5 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS recompenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT,
    categorie TEXT, demandeur TEXT, montant_reclame REAL, montant_accorde REAL,
    statut TEXT, preuve_type TEXT, preuve_clef_retenue TEXT, motif_echec TEXT
);
CREATE INDEX IF NOT EXISTS idx_recompenses_decision ON recompenses(decision_id);
"""

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
# BASE DE DONNÉES (même schéma que backend/app/models.py)
# ---------------------------------------------------------------------------
def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    return conn


def md5_exists(conn: sqlite3.Connection, md5: str) -> bool:
    return conn.execute("SELECT 1 FROM decisions WHERE text_md5 = ? LIMIT 1", (md5,)).fetchone() is not None


def _num(v: Any) -> Optional[float]:
    return None if v is None else (None if isinstance(v, str) and not re.fullmatch(r"-?\d+(\.\d+)?", v.strip()) else v)


def _bool(v: Any) -> Optional[bool]:
    return None if v is None else bool(v)


def save_decision(conn: sqlite3.Connection, decision_id: str, md5: str, raw_text: str, ex: dict):
    """Aplanit le JSON LLM en colonnes requêtables, puis insère décision + récompenses."""
    meta = ex.get("metadata") or {}
    ctx = ex.get("contexte_familial") or {}
    biens = ex.get("biens_litigieux") or {}
    occ = ex.get("indemnite_occupation") or {}
    pc = ex.get("prestation_compensatoire") or {}
    frais = ex.get("frais_et_depens") or {}
    strat = ex.get("analyse_strategique") or {}

    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO decisions (
                id, source, numero_rg, juridiction, chambre, date_decision,
                regime_matrimonial, duree_mariage_annees, nombre_enfants,
                bien_immobilier_principal, valeur_bien_principal, entreprises_societes, comptes_epargne,
                occupation_demandee, occupation_accordee, occupation_montant_mensuel_base,
                occupation_abattement_pct, occupation_montant_mensuel_final, occupation_duree_mois,
                occupation_montant_total, pc_demandee, pc_accordee, pc_forme, pc_montant_capital,
                pc_rente_mensuelle, pc_duree_rente_mois, article_700_montant, partage_depens,
                resume_3_lignes, raw_text, extracted_json, text_md5
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decision_id, "JUDILIBRE_OD", meta.get("numero_pourvoi_rg"), meta.get("juridiction"),
                meta.get("chambre"), meta.get("date_decision"),
                ctx.get("regime_matrimonial"), _num(ctx.get("duree_mariage_annees")), _num(ctx.get("nombre_enfants")),
                _bool(biens.get("bien_immobilier_principal")), _num(biens.get("valeur_bien_principal")),
                _bool(biens.get("entreprises_societes")), _bool(biens.get("comptes_epargne")),
                _bool(occ.get("demandee")), _bool(occ.get("accordee")),
                _num(occ.get("montant_mensuel_base_valeur_locative")), _num(occ.get("pourcentage_abattement_accorde")),
                _num(occ.get("montant_mensuel_final")), _num(occ.get("duree_mois_retenue")), _num(occ.get("montant_total_accorde")),
                _bool(pc.get("demandee")), _bool(pc.get("accordee")), pc.get("forme"),
                _num(pc.get("montant_capital_accorde")), _num(pc.get("montant_rente_mensuelle")), _num(pc.get("duree_rente_mois")),
                _num(frais.get("article_700_montant")), frais.get("partage_depens"),
                strat.get("resume_decision_3_lignes"), raw_text,
                json.dumps(ex, ensure_ascii=False), md5,
            ),
        )
        conn.execute("DELETE FROM recompenses WHERE decision_id = ?", (decision_id,))
        for r in ex.get("recompenses_et_creances") or []:
            if not isinstance(r, dict):
                continue
            conn.execute(
                """INSERT INTO recompenses (decision_id, categorie, demandeur, montant_reclame,
                   montant_accorde, statut, preuve_type, preuve_clef_retenue, motif_echec)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    decision_id, r.get("categorie"), r.get("demandeur"),
                    _num(r.get("montant_reclame")), _num(r.get("montant_accorde")), r.get("statut"),
                    classify_proof(r.get("preuve_clef_retenue"), r.get("motif_echec")),
                    r.get("preuve_clef_retenue"), r.get("motif_echec"),
                ),
            )


# ---------------------------------------------------------------------------
# APPEL LLM ASYNCHRONE (GLM Flash) — backoff exponentiel + JSON forcé
# ---------------------------------------------------------------------------
@retry(wait=wait_exponential(multiplier=2, min=2, max=60), stop=stop_after_attempt(5))
async def call_llm(text: str) -> dict:
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Voici le texte de la décision de justice :\n\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.content)


async def process_decision_with_llm(conn: sqlite3.Connection, decision_id: str, text: str, md5: str):
    truncated = text[:MAX_TEXT_CHARS]
    async with semaphore:
        try:
            extracted = await call_llm(truncated)
            save_decision(conn, decision_id, md5, truncated, extracted)
            print(f"[SUCCESS] Décision {decision_id} analysée et enregistrée.")
        except Exception as e:
            print(f"[ERROR] Échec du traitement de la décision {decision_id}: {e}")


# ---------------------------------------------------------------------------
# PIPELINE : LECTURE D'ARCHIVES .TAR.GZ → FILTRE REGEX → LLM
# ---------------------------------------------------------------------------
def iter_decisions_from_archive(tar_gz_path: str):
    """Yield (decision_id, texte) pour chaque décision pertinente de l'archive."""
    with tarfile.open(tar_gz_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not (member.isfile() and member.name.endswith(".json")):
                continue
            f = tar.extractfile(member)
            if not f:
                continue
            try:
                data = json.loads(f.read().decode("utf-8", errors="ignore"))
            except Exception:
                continue
            text = data.get("text") or data.get("contenu") or ""
            if not isinstance(text, str) or not KEYWORDS_REGEX.search(text):
                continue  # filtre local, 0 token
            yield data.get("id") or member.name, text


async def run_pipeline(archive_paths: List[str], db_path: str):
    if not ZHIPU_API_KEY:
        sys.exit("ZHIPU_API_KEY non défini : exportez votre clé Zhipu AI avant de lancer le pipeline.")
    conn = connect(db_path)

    tasks = []
    total = 0
    for path in archive_paths:
        print(f"Ouverture de l'archive : {path}")
        for decision_id, text in iter_decisions_from_archive(path):
            total += 1
            md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
            if md5_exists(conn, md5):
                continue  # élimination des doublons
            tasks.append(process_decision_with_llm(conn, decision_id, text, md5))

    print(f"{total} décisions pertinentes trouvées ; {len(tasks)} à analyser après dédoublonnage.")
    await asyncio.gather(*tasks)
    conn.close()
    print(f"Terminé. Base : {db_path}")


def main():
    parser = argparse.ArgumentParser(description="Ingestion Judilibre Open Data → LLM GLM → base SQL")
    parser.add_argument("archives", help="Archive .tar.gz ou dossier contenant plusieurs archives")
    parser.add_argument("--db", default=os.path.join(os.path.dirname(__file__), "..", "backend", "jurisprudence.db"))
    args = parser.parse_args()

    if os.path.isdir(args.archives):
        paths = sorted(glob.glob(os.path.join(args.archives, "*.tar.gz")))
    elif os.path.isfile(args.archives):
        paths = [args.archives]
    else:
        sys.exit(f"Archive introuvable : {args.archives}")
    if not paths:
        sys.exit("Aucune archive .tar.gz trouvée.")

    asyncio.run(run_pipeline(paths, os.path.abspath(args.db)))


if __name__ == "__main__":
    main()
