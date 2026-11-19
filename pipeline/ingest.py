"""Orchestrateur d'ingestion massive v2 : téléchargement multi-fonds → filtre
normalisé → worker httpx haute cadence (GLM Flash) → base SQLite du backend.

Usage (depuis la racine du dépôt) :
  # Campagne complète CAPP + CASS + TJ (toutes les archives historiques) :
  python -m pipeline.ingest run --download --fonds CAPP,CASS,TJ --analyze

  # Comptage sans consommer de tokens (recommandé avant la première campagne) :
  python -m pipeline.ingest run --download --fonds CAPP,CASS --dry-run

  # Archives locales déjà téléchargées :
  python -m pipeline.ingest run --local archives/2023-01-CAPP.tar.gz --analyze

  # Pilotage (l'UI /pipeline appelle la même chose via l'API) :
  python -m pipeline.ingest status
  python -m pipeline.ingest control pause|resume|stop

Variables d'environnement : ZHIPU_API_KEY (requis avec --analyze),
JURISDIVORCE_MODEL (défaut glm-4-flash), MAX_CONCURRENCY (défaut 25),
MAX_CHARS (défaut 48000), JUDILIBRE_OPENDATA_URL (défaut echanges.dila.gouv.fr).
"""
import argparse
import asyncio
import glob
import hashlib
import io
import json
import os
import sys
import tarfile
import time
import zipfile
from typing import Iterable, List, Optional, Tuple

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .core import (
    PipelineStateWriter,
    connect_db,
    decision_filter,
    extract_id,
    extract_text,
    repair_json,
    save_decision,
    smart_truncate,
)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL = os.getenv("JURISDIVORCE_MODEL", "glm-4-flash")
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "25"))
MAX_CHARS = int(os.getenv("MAX_CHARS", "48000"))
OPENDATA_BASE_URL = os.getenv(
    "JUDILIBRE_OPENDATA_URL",
    "https://echanges.dila.gouv.fr/OPENDATA/Judilibre/",
)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(REPO_ROOT, "backend", "jurisprudence.db")
ARCHIVES_DIR = os.path.join(REPO_ROOT, "archives")  # données non fiables : jamais dans le code

SYSTEM_PROMPT = """Tu es un expert juriste en droit de la famille et un analyste de données judiciaires français.
Ta tâche est d'analyser l'arrêt ou le jugement fourni et d'extraire TOUTES les informations financières, factuelles et juridiques sous la forme d'un objet JSON STRICT respectant scrupuleusement le schéma demandé.

Règles de traitement :
1. Si une information est absente du texte, indique `null`. Ne devine ni n'invente jamais d'information.
2. Exprime tous les montants monétaires en nombres purs (ex: 1500.50 et non "1 500,50 €").
3. Garde une synthèse neutre, factuelle et orientée sur le raisonnement de la décision.

Schéma JSON de sortie :
{
  "metadata": {"juridiction": str|null, "chambre": str|null, "date_decision": "YYYY-MM-DD"|null, "numero_pourvoi_rg": str|null},
  "contexte_familial": {"type_procedure": "Divorce contentieux|Liquidation-partage après divorce|Indivision hors mariage/PACS|Appel sur ordonnance JAF", "regime_matrimonial": "COMMUNAUTE_REDUITE_AUX_ACQUETS|SEPARATION_DE_BIENS|PARTICIPATION_AUX_ACQUETS|COMMUNAUTE_UNIVERSELLE|INDIVISION|INCONNU", "duree_mariage_annees": number|null, "nombre_enfants": number|null, "age_epoux_moyen": number|null},
  "biens_litigieux": {"bien_immobilier_principal": boolean, "valeur_bien_principal": number|null, "entreprises_societes": boolean, "comptes_epargne": boolean},
  "indemnite_occupation": {"demandee": boolean, "accordee": boolean, "valeur_locative_mensuelle_retenue": number|null, "taux_abattement_precarite_pct": number|null, "montant_mensuel_final": number|null, "duree_mois_retenue": number|null, "montant_total_accorde": number|null, "motif_refus_ou_modulation": str|null},
  "reclamations_financieres": [{"nature": "Financement bien propre|Travaux amélioration|Remboursement emprunt immobilier post-séparation|Apport fonds propres / héritage|Recel de communauté|Compte joint vidé|Taxes foncières / assurance|Autre", "demandeur": "EPOUX_A|EPOUX_B", "montant_reclame": number|null, "montant_accorde": number|null, "statut": "ACCORDE_TOTALEMENT|ACCORDE_PARTIELLEMENT|REJETE", "regle_calcul": "Dépense faite|Profit subsistant|Nominalisme|Rejeté", "preuves_determinantes": [str], "cause_echec": str|null, "preuve_clef_retenue": str|null}],
  "prestation_compensatoire": {"demandee": boolean, "accordee": boolean, "forme": "CAPITAL_UNIQUE|CAPITAL_ECHELONNE|RENTE_MENSUELLE|ATTRIBUTION_BIEN|MIXTE|AUCUNE", "montant_demande_epoux_A": number|null, "montant_propose_epoux_B": number|null, "montant_accorde": number|null, "montant_rente_mensuelle": number|null, "duree_rente_mois": number|null, "ecart_revenus_mensuel": number|null, "criteres_determinants": [str]},
  "cout_issue": {"article_700_accorde": number|null, "partie_condamnee_depens": str|null, "delai_procedure_estime_mois": number|null},
  "analyse_strategique": {"points_forts_gagnants": [str], "pieges_et_erreurs_a_eviter": [str], "resume_decision_3_lignes": str, "resume_pedagogique_3_lignes": str, "conseil_pratique_extrait": str}
}
Réponds UNIQUEMENT avec l'objet JSON."""


# ---------------------------------------------------------------------------
# EXTRACTION DES DÉCISIONS DEPUIS ARCHIVES .tar.gz / .zip / .json
# ---------------------------------------------------------------------------
def _json_payloads(content: bytes) -> Iterable[dict]:
    """Tolère : objet JSON, tableau JSON, JSON Lines."""
    text = content.decode("utf-8", errors="ignore")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item
        return
    if isinstance(data, dict):
        yield data
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item


def iter_decisions_from_archive(path: str) -> Iterable[Tuple[str, str]]:
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if member.endswith("/"):
                    continue
                for payload in _json_payloads(archive.read(member)):
                    text = extract_text(payload)
                    if text:
                        yield extract_id(payload, member), text
        return
    if path.endswith(".json"):
        with open(path, "rb") as file:
            for payload in _json_payloads(file.read()):
                text = extract_text(payload)
                if text:
                    yield extract_id(payload, os.path.basename(path)), text
        return
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            file = archive.extractfile(member)
            if file is None:
                continue
            for payload in _json_payloads(file.read()):
                text = extract_text(payload)
                if text:
                    yield extract_id(payload, member.name), text


# ---------------------------------------------------------------------------
# WORKER ASYNCHRONE HAUTE CADENCE (httpx + Semaphore + réparation JSON)
# ---------------------------------------------------------------------------
client = AsyncOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL) if ZHIPU_API_KEY else None


@retry(wait=wait_exponential(multiplier=2, min=2, max=60), stop=stop_after_attempt(4), reraise=True)
async def call_llm(text: str) -> Tuple[dict, int]:
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Voici le texte de la décision de justice :\n\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    usage = getattr(response, "usage", None)
    tokens = int(getattr(usage, "total_tokens", 0) or 0)
    return json.loads(response.choices[0].message.content), tokens


async def wait_if_paused(state: PipelineStateWriter) -> bool:
    """Boucle de contrôle : renvoie False si le pipeline doit s'arrêter."""
    while True:
        status = state.control_status()
        if status in ("paused", "idle"):
            if status == "idle":  # jamais démarré : ne rien faire
                return False
            await asyncio.sleep(2)
            continue
        return status != "stopped"


async def analyze_decision(conn, state: PipelineStateWriter, decision_id: str, text: str, md5: str) -> bool:
    if not await wait_if_paused(state):
        state.log("WARN", f"Arrêt demandé : {decision_id} abandonnée.")
        return False
    truncated = smart_truncate(text, MAX_CHARS)
    try:
        extracted, tokens = await call_llm(truncated)
        save_decision(conn, decision_id, md5, truncated, extracted)
        state.bump(decisions_analyzed=1, tokens_today=tokens)
        return True
    except Exception as exc:
        state.bump(decisions_failed=1)
        state.log("ERROR", f"Échec GLM {decision_id} : {exc}")
        return False


# ---------------------------------------------------------------------------
# ORCHESTRATEUR
# ---------------------------------------------------------------------------
async def run_campaign(args) -> None:
    from . import dila

    db_path = os.path.abspath(args.db)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = connect_db(db_path)
    state = PipelineStateWriter(db_path)

    if args.analyze and not client and not args.dry_run:
        sys.exit("ZHIPU_API_KEY non défini : requis avec --analyze (ou utilisez --dry-run).")

    # 1) Inventaire des archives (manifest + skip des déjà traitées)
    if args.local:
        paths: List[str] = []
        for pattern in args.local:
            paths.extend(sorted(glob.glob(pattern)) or [pattern])
        archives = [{"url": os.path.abspath(p), "fonds": "LOCAL"} for p in paths if os.path.exists(p)]
        missing = [p for p in paths if not os.path.exists(p)]
        for m in missing:
            state.log("WARN", f"Archive locale introuvable : {m}")
    else:
        async with httpx.AsyncClient(follow_redirects=True) as http:
            fonds = [f.strip().upper() for f in args.fonds.split(",")] if args.fonds else None
            archives = await dila.list_archives(
                http, OPENDATA_BASE_URL, fonds_filter=fonds,
                max_archives=args.max_archives, log=state.log,
            )

    pending = []
    for a in archives:
        row = conn.execute("SELECT status FROM processed_archives WHERE url = ?", (a["url"],)).fetchone()
        if row and row["status"] == "done" and not args.force:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO processed_archives (url, fonds, status) VALUES (?, ?, 'pending')",
            (a["url"], a["fonds"]),
        )
        conn.commit()
        pending.append(a)
    state.init(mode="dry-run" if args.dry_run else ("download+analyze" if not args.local else "local+analyze"),
               archives_total=len(pending))
    print(f"{len(pending)} archive(s) à traiter ({len(archives) - len(pending)} déjà en manifest).")

    # 2) Parcours des archives → filtre → file de travail
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def bounded(decision_id: str, text: str, md5: str) -> bool:
        async with semaphore:
            return await analyze_decision(conn, state, decision_id, text, md5)

    total_analyzed = 0
    try:
        for index, archive in enumerate(pending):
            if state.control_status() == "stopped":
                state.log("WARN", "Arrêt demandé : campagne interrompue.")
                break
            state.heartbeat(current_archive=archive["url"], queue_size=len(pending) - index)

            try:
                if args.local:
                    path, size = archive["url"], os.path.getsize(archive["url"])
                else:
                    async with httpx.AsyncClient(follow_redirects=True) as http:
                        path, size = await dila.download_archive(http, archive["url"], ARCHIVES_DIR, log=state.log)
            except Exception as exc:
                state.mark_archive(archive["url"], archive["fonds"], 0, "error", error=str(exc)[:300])
                state.bump(archives_done=1)
                continue

            kept: List[Tuple[str, str, str]] = []
            scanned = 0
            try:
                for decision_id, text in iter_decisions_from_archive(path):
                    scanned += 1
                    keep, reason = decision_filter(text)
                    if not keep:
                        continue
                    md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
                    if conn.execute("SELECT 1 FROM decisions WHERE text_md5 = ? LIMIT 1", (md5,)).fetchone():
                        continue  # dédoublonnage
                    if conn.execute("SELECT 1 FROM decisions WHERE id = ? LIMIT 1", (decision_id,)).fetchone():
                        continue
                    kept.append((decision_id, text, md5))
            except Exception as exc:
                state.mark_archive(archive["url"], archive["fonds"], size, "error",
                                   error=f"extraction: {exc}"[:300])
                state.bump(archives_done=1)
                continue

            state.bump(decisions_scanned=scanned, decisions_kept=len(kept))
            state.log("INFO", f"{os.path.basename(path)} : {scanned} décisions parcourues, {len(kept)} conservées.")

            if args.analyze and not args.dry_run:
                results = await asyncio.gather(*(bounded(d, t, m) for d, t, m in kept))
                done = sum(1 for r in results if r)
            else:
                done = 0
            total_analyzed += done
            state.mark_archive(archive["url"], archive["fonds"], size, "done",
                               decisions_found=len(kept), decisions_analyzed=done)
            state.bump(archives_done=1)
            if not args.keep_archives and not args.local and os.path.exists(path):
                os.remove(path)  # économise le disque une fois l'archive traitée
    finally:
        final = state.control_status()
        state.heartbeat(status="idle" if final != "stopped" else "stopped", queue_size=0)
        state.log("INFO", f"Campagne terminée : {total_analyzed} décisions analysées au total.")
        conn.close()
        state.close()

    print(f"Terminé — {total_analyzed} décisions analysées. Base : {db_path}")


def show_status(db_path: str) -> None:
    conn = connect_db(db_path)
    state = conn.execute("SELECT * FROM pipeline_state WHERE id = 1").fetchone()
    if state:
        for key in state.keys():
            print(f"{key:22s}: {state[key]}")
    for row in conn.execute(
        "SELECT fonds, status, COUNT(*) n, SUM(decisions_analyzed) analyzed FROM processed_archives GROUP BY fonds, status"
    ):
        print(f"archive[{row['fonds']}/{row['status']}] = {row['n']} (analysées: {row['analyzed']})")
    conn.close()


def set_control(db_path: str, action: str) -> None:
    conn = connect_db(db_path)
    status = {"pause": "paused", "resume": "running", "stop": "stopped"}[action]
    conn.execute(
        "UPDATE pipeline_state SET status = ?, updated_at = datetime('now') WHERE id = 1", (status,)
    )
    conn.execute(
        "INSERT INTO pipeline_logs (ts, level, message) VALUES (datetime('now'), 'INFO', ?)",
        (f"Contrôle opérateur (CLI) : {action}",),
    )
    conn.commit()
    print(f"Statut pipeline → {status}")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion massive Judilibre → GLM Flash → base SQL")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Campagne d'ingestion")
    run_p.add_argument("--download", action="store_true", help="Aspirer les archives Open Data DILA")
    run_p.add_argument("--fonds", default="CAPP,CASS,TJ", help="Fonds à aspirer (CAPP,CASS,TJ,TGE…)")
    run_p.add_argument("--local", nargs="+", metavar="CHEMIN", help="Archives/fichiers locaux (tar.gz, zip, json, glob)")
    run_p.add_argument("--analyze", action="store_true", help="Envoyer les décisions au LLM (sinon comptage seul)")
    run_p.add_argument("--dry-run", action="store_true", help="Comptage uniquement : 0 token, 0 écriture LLM")
    run_p.add_argument("--max-archives", type=int, default=None, help="Limiter le nombre d'archives (test)")
    run_p.add_argument("--force", action="store_true", help="Retraiter les archives déjà 'done'")
    run_p.add_argument("--keep-archives", action="store_true", help="Conserver les archives téléchargées sur disque")
    run_p.add_argument("--db", default=DEFAULT_DB)
    run_p.set_defaults(func=run_campaign)

    status_p = sub.add_parser("status", help="Afficher l'état du pipeline")
    status_p.add_argument("--db", default=DEFAULT_DB)
    status_p.set_defaults(func=lambda a: show_status(a.db))

    ctrl_p = sub.add_parser("control", help="pause|resume|stop")
    ctrl_p.add_argument("action", choices=["pause", "resume", "stop"])
    ctrl_p.add_argument("--db", default=DEFAULT_DB)
    ctrl_p.set_defaults(func=lambda a: set_control(a.db, a.action))

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
