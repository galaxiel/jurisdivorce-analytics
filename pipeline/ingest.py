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
from openai import APIStatusError, AsyncOpenAI, RateLimitError

try:  # config .env optionnelle (ZHIPU_API_KEY, MAX_CONCURRENCY, MODEL…)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .core import (
    AdaptiveLimiter,
    BatchWriter,
    PipelineStateWriter,
    connect_db,
    decision_filter,
    extract_id,
    extract_text,
    parse_juri_xml,
    read_config,
    record_failure,
    repair_json,
    save_decision,
    smart_truncate,
)
from .dila import DEFAULT_OPENDATA_URL

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL = os.getenv("JURISDIVORCE_MODEL", "glm-4-flash")
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "25"))
MAX_CHARS = int(os.getenv("MAX_CHARS", "48000"))
OPENDATA_BASE_URL = os.getenv("JUDILIBRE_OPENDATA_URL", DEFAULT_OPENDATA_URL)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(REPO_ROOT, "backend", "jurisprudence.db")
ARCHIVES_DIR = os.path.join(REPO_ROOT, "archives")  # données non fiables : jamais dans le code

SYSTEM_PROMPT = """Tu es un expert juriste en droit de la famille et un analyste de données judiciaires français.
Ta tâche est d'analyser l'arrêt ou le jugement fourni et d'extraire TOUTES les informations financières, factuelles et juridiques sous la forme d'un objet JSON STRICT respectant scrupuleusement le schéma demandé.

Règles de traitement :
1. Si une information est absente du texte, indique `null`. Ne devine ni n'invente jamais d'information.
2. Exprime tous les montants monétaires en nombres purs (ex: 1500.50 et non "1 500,50 €").
3. Garde une synthèse neutre, factuelle et orientée sur le raisonnement de la décision.
4. N'utilise JAMAIS 0 par défaut : tout montant non explicitement chiffré dans la décision est `null`. `0` est strictement réservé au champ `montant_accorde` d'une demande explicitement rejetée.

Schéma JSON de sortie :
{
  "metadata": {"juridiction": str|null, "chambre": str|null, "date_decision": "YYYY-MM-DD"|null, "numero_pourvoi_rg": str|null},
  "contexte_familial": {"type_procedure": "Divorce contentieux|Liquidation-partage après divorce|Indivision hors mariage/PACS|Appel sur ordonnance JAF", "regime_matrimonial": "COMMUNAUTE_REDUITE_AUX_ACQUETS|COMMUNAUTE_AVEC_CLAUSE|SEPARATION_DE_BIENS|PARTICIPATION_AUX_ACQUETS|COMMUNAUTE_UNIVERSELLE|INDIVISION|INCONNU", "duree_mariage_annees": number|null, "nombre_enfants": number|null, "age_epoux_moyen": number|null},
  "biens_litigieux": {"bien_immobilier_principal": boolean, "valeur_bien_principal": number|null, "entreprises_societes": boolean, "comptes_epargne": boolean},
  "indemnite_occupation": {"demandee": boolean, "accordee": boolean, "valeur_locative_mensuelle_retenue": number|null, "taux_abattement_precarite_pct": number|null, "montant_mensuel_final": number|null, "duree_mois_retenue": number|null, "montant_total_accorde": number|null, "motif_refus_ou_modulation": str|null},
  "reclamations_financieres": [{"nature": "Financement bien propre|Travaux amélioration|Remboursement emprunt immobilier post-séparation|Apport fonds propres / héritage|Recel de communauté|Compte joint vidé|Taxes foncières / assurance|Autre", "demandeur": "EPOUX_A|EPOUX_B", "montant_reclame": number|null, "montant_accorde": number|null, "statut": "ACCORDE_TOTALEMENT|ACCORDE_PARTIELLEMENT|REJETE", "regle_calcul": "Dépense faite|Profit subsistant|Nominalisme|Rejeté", "preuves_determinantes": [str], "cause_echec": str|null, "preuve_clef_retenue": str|null}],
  "prestation_compensatoire": {"demandee": boolean, "accordee": boolean, "forme": "CAPITAL_UNIQUE|CAPITAL_ECHELONNE|RENTE_MENSUELLE|ATTRIBUTION_BIEN|MIXTE|AUCUNE", "montant_demande_epoux_A": number|null, "montant_propose_epoux_B": number|null, "montant_accorde": number|null, "montant_rente_mensuelle": number|null, "duree_rente_mois": number|null, "ecart_revenus_mensuel": number|null, "criteres_determinants": [str]},
  "cout_issue": {"article_700_accorde": number|null, "partie_condamnee_depens": str|null, "delai_procedure_estime_mois": number|null},
  "effets_patrimoniaux": {"date_effets_patrimoniaux_retenue": "YYYY-MM-DD"|null, "duree_vie_commune_annees": number|null},
  "gestion_bien_locatif_indivis": {"loyers_encaisses_mois": number|null, "charges_deductibles_mois": number|null, "solde_restitue_indivision": number|null},
  "pension_alimentaire": {"pension_par_enfant": number|null, "mode_garde": "Résidence classique + DVH|Garde alternée|Non précisé", "partage_frais_exceptionnels": boolean|null, "revenus_debiteur_mois": number|null},
  "revenus": {"prestations_sociales_integrees": boolean|null, "ecart_ressources_totales": number|null},
  "issue_demandes_annexes": {"nom_usage_accorde": boolean|null, "nom_usage_motif": str|null, "dommages_interets_accordes": number|null, "divorce_faute_retenu": boolean|null},
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


def iter_decisions_from_archive(path: str, counters: Optional[dict] = None) -> Iterable[Tuple[str, str]]:
    """Archive .tar.gz / .zip / .json (XML DILA ou JSON) — STREAMING `r|*` : l'archive
    n'est jamais chargée entièrement en RAM. counters['files_read'] compte le nombre
    EXACT de fichiers XML/JSON lus (vs decisions_scanned = textes exploitables)."""
    def mark() -> None:
        if counters is not None:
            counters["files_read"] += 1

    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if member.endswith("/"):
                    continue
                mark()
                yield from _decisions_from_member(archive.read(member), member)
        return
    if path.endswith(".json"):
        mark()
        with open(path, "rb") as file:
            yield from _decisions_from_member(file.read(), os.path.basename(path))
        return
    with tarfile.open(path, mode="r|*") as archive:
        for member in archive:
            if not member.isfile():
                continue
            file = archive.extractfile(member)
            if file is None:
                continue
            mark()
            yield from _decisions_from_member(file.read(), member.name)


def _decisions_from_member(content: bytes, name: str) -> Iterable[Tuple[str, str]]:
    """Un membre d'archive = XML DILA (fonds freemium CAPP/CASS/TJ) ou JSON."""
    stripped = content.lstrip()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<TEXTE"):
        parsed = parse_juri_xml(content)
        if parsed:
            yield parsed["id"], parsed["text"]
        return
    for payload in _json_payloads(content):
        text = extract_text(payload)
        if text:
            yield extract_id(payload, name), text


# ---------------------------------------------------------------------------
# WORKER ASYNCHRONE HAUTE CADENCE (httpx + Semaphore + réparation JSON)
# ---------------------------------------------------------------------------
client = AsyncOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL) if ZHIPU_API_KEY else None

MAX_ATTEMPTS = 5


async def call_llm(text: str, model: str) -> Tuple[dict, int]:
    response = await client.chat.completions.create(
        model=model,
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


async def analyze_decision(conn, state: PipelineStateWriter, limiter: AdaptiveLimiter,
                           writer: BatchWriter, decision_id: str, text: str, md5: str,
                           defaults: dict) -> bool:
    """Analyse une décision : config à chaud + backoff 429/503 + DLQ sur échec final.

    L'écriture ne se fait PAS ici : la décision réussie part dans la BatchWriter
    (un seul task d'écriture, lots de 25) → zéro 'database is locked'."""
    if not await wait_if_paused(state):
        state.log("WARN", f"Arrêt demandé : {decision_id} abandonnée.")
        return False

    cfg = read_config(conn, defaults)  # réglages à chaud (table app_config, /pipeline)
    target = int(cfg.get("max_concurrency") or MAX_CONCURRENCY)
    if target != limiter.max_size:
        await limiter.set_target(target)
        state.log("INFO", f"Concurrence ajustée à chaud : {target} requêtes simultanées.")
    model = cfg.get("model") or MODEL
    max_chars = int(cfg.get("max_chars") or MAX_CHARS)

    truncated = smart_truncate(text, max_chars)
    last_exc: Optional[Exception] = None
    attempt = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            extracted, tokens = await call_llm(truncated, model)
            await writer.put(decision_id, md5, truncated, extracted)
            state.bump(tokens_today=tokens)
            return True
        except (RateLimitError, APIStatusError) as exc:
            status = getattr(exc, "status_code", None)
            if isinstance(exc, RateLimitError) or status in (429, 503):
                new_size = limiter.on_rate_limited()
                state.log("WARN", f"{status or 429} Zhipu : concurrence → {new_size} ; "
                                  f"backoff {min(90, 2 ** attempt * 2):.0f} s (tentative {attempt}/{MAX_ATTEMPTS})")
                await asyncio.sleep(min(90.0, 2.0 * (2 ** attempt)))
                last_exc = exc
            else:
                last_exc = exc
                break  # erreur non transitoire (400…) : DLQ direct
        except Exception as exc:  # timeout, réseau, JSON invalide…
            await asyncio.sleep(min(20.0, 2.0 * attempt))
            last_exc = exc

    if last_exc is not None:
        record_failure(conn, decision_id, truncated, last_exc, attempt=attempt)
        state.bump(decisions_failed=1)
        state.log("ERROR", f"Décision {decision_id} en file d'échecs (DLQ) : {last_exc}")
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

    # 2) Parcours des archives → filtre → file de travail (concurrence adaptative + writer dédié)
    limiter = AdaptiveLimiter(args.concurrency or MAX_CONCURRENCY)
    defaults = {
        "max_concurrency": args.concurrency or MAX_CONCURRENCY,
        "model": MODEL,
        "max_chars": args.max_chars or MAX_CHARS,
    }
    grow_task = asyncio.create_task(limiter.grow_loop())
    writer = BatchWriter(conn, state)
    writer_task = asyncio.create_task(writer.run())

    async def bounded(decision_id: str, text: str, md5: str) -> bool:
        await limiter.acquire()
        try:
            return await analyze_decision(conn, state, limiter, writer, decision_id, text, md5, defaults)
        finally:
            await limiter.release()

    async def drain_failed() -> int:
        """Redraine la DLQ : relance les décisions en échec (bouton /pipeline ou CLI)."""
        rows = conn.execute(
            "SELECT id, decision_id, text_truncated FROM failed_decisions ORDER BY id LIMIT 200"
        ).fetchall()
        ok = 0
        for row in rows:
            md5 = hashlib.md5(row["text_truncated"].encode("utf-8")).hexdigest()
            if await analyze_decision(conn, state, limiter, writer, row["decision_id"], row["text_truncated"], md5, defaults):
                with conn:
                    conn.execute("DELETE FROM failed_decisions WHERE id = ?", (row["id"],))
                ok += 1
            else:
                with conn:
                    conn.execute("UPDATE failed_decisions SET attempts = attempts + 1 WHERE id = ?", (row["id"],))
        if rows:
            state.log("INFO", f"DLQ drainée : {ok}/{len(rows)} décision(s) relancée(s) avec succès.")
        with conn:
            conn.execute("UPDATE pipeline_state SET retry_failed = 0 WHERE id = 1")
        return ok

    total_analyzed = 0
    try:
        for index, archive in enumerate(pending):
            if state.control_status() == "stopped":
                state.log("WARN", "Arrêt demandé : campagne interrompue.")
                break
            state.heartbeat(current_archive=archive["url"], queue_size=len(pending) - index)

            # Drapeau posé par le bouton « Relancer les échecs » de /pipeline
            flag = conn.execute("SELECT retry_failed FROM pipeline_state WHERE id = 1").fetchone()
            if flag and flag["retry_failed"]:
                await drain_failed()

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
            counters = {"files_read": 0}
            try:
                for decision_id, text in iter_decisions_from_archive(path, counters):
                    scanned += 1
                    keep, reason = decision_filter(text)
                    if not keep:
                        continue
                    md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
                    if conn.execute("SELECT 1 FROM decisions WHERE text_md5 = ? LIMIT 1", (md5,)).fetchone():
                        continue  # élimination des doublons
                    if conn.execute("SELECT 1 FROM decisions WHERE id = ? LIMIT 1", (decision_id,)).fetchone():
                        continue
                    kept.append((decision_id, text, md5))
            except Exception as exc:
                state.mark_archive(archive["url"], archive["fonds"], size, "error",
                                   error=f"extraction: {exc}"[:300])
                state.bump(archives_done=1)
                continue

            state.bump(decisions_scanned=scanned, decisions_kept=len(kept),
                       files_read=counters["files_read"])
            state.log("INFO", f"{os.path.basename(path)} : {counters['files_read']} fichiers XML/JSON lus, "
                              f"{scanned} décisions exploitables, {len(kept)} retenues par le pré-filtre.")

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
        grow_task.cancel()
        try:
            await writer.flush_remaining()  # écrit le dernier lot incomplet
        except Exception as exc:
            state.log("ERROR", f"Flush final de la file d'écriture : {exc}")
        writer_task.cancel()
        final = state.control_status()
        state.heartbeat(status="idle" if final != "stopped" else "stopped", queue_size=0)
        state.log("INFO", f"Campagne terminée : {total_analyzed} décisions analysées au total.")
        conn.close()
        state.close()

    print(f"Terminé — {total_analyzed} décisions analysées. Base : {db_path}")


async def retry_failed_cli(db_path: str) -> None:
    """Sub-command `retry-failed` : redraine la DLQ sans campagne complète."""
    if not ZHIPU_API_KEY:
        sys.exit("ZHIPU_API_KEY requis pour relancer les échecs.")
    conn = connect_db(os.path.abspath(db_path))
    state = PipelineStateWriter(os.path.abspath(db_path))
    limiter = AdaptiveLimiter(MAX_CONCURRENCY)
    defaults = {"max_concurrency": MAX_CONCURRENCY, "model": MODEL, "max_chars": MAX_CHARS}
    writer = BatchWriter(conn, state)
    writer_task = asyncio.create_task(writer.run())
    try:
        rows = conn.execute("SELECT COUNT(*) n FROM failed_decisions").fetchone()
        print(f"{rows['n']} décision(s) en échec dans la DLQ.")
        drained = await _drain_standalone(conn, state, limiter, writer, defaults)
        print(f"{drained} décision(s) relancée(s) avec succès.")
    finally:
        await writer.flush_remaining()
        writer_task.cancel()
        conn.close()
        state.close()


async def _drain_standalone(conn, state, limiter, writer, defaults) -> int:
    rows = conn.execute(
        "SELECT id, decision_id, text_truncated FROM failed_decisions ORDER BY id LIMIT 500"
    ).fetchall()
    ok = 0
    for row in rows:
        md5 = hashlib.md5(row["text_truncated"].encode("utf-8")).hexdigest()
        if await analyze_decision(conn, state, limiter, writer, row["decision_id"], row["text_truncated"], md5, defaults):
            with conn:
                conn.execute("DELETE FROM failed_decisions WHERE id = ?", (row["id"],))
            ok += 1
        else:
            with conn:
                conn.execute("UPDATE failed_decisions SET attempts = attempts + 1 WHERE id = ?", (row["id"],))
    if rows:
        state.log("INFO", f"DLQ drainée (CLI) : {ok}/{len(rows)} relancée(s).")
    with conn:
        conn.execute("UPDATE pipeline_state SET retry_failed = 0 WHERE id = 1")
    return ok


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
    run_p.add_argument("--concurrency", type=int, default=None,
                       help=f"Requêtes simultanées GLM (défaut MAX_CONCURRENCY={MAX_CONCURRENCY} ; 30-50 si aucune 429)")
    run_p.add_argument("--max-chars", type=int, default=None,
                       help=f"Budget de troncature par décision (défaut {MAX_CHARS} ; ~16000 pour viser 40-50k décisions/jour)")
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

    retry_p = sub.add_parser("retry-failed", help="Relancer les décisions en échec (DLQ)")
    retry_p.add_argument("--db", default=DEFAULT_DB)

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(args.func(args))
    elif args.command == "retry-failed":
        asyncio.run(retry_failed_cli(args.db))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
