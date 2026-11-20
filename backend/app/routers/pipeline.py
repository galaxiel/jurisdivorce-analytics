"""Moniteur du pipeline d'ingestion : état temps réel, logs, contrôle pause/reprise/stop,
configuration à chaud, DLQ « relancer les échecs » et benchmark de performance.

Le pipeline écrit son heartbeat dans pipeline_state / pipeline_logs / processed_archives
(voir pipeline/ingest.py) ; ces endpoints lisent ces tables et permettent le contrôle.
"""
import os
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import DB_PATH, get_db
from ..models import Decision
from ..schemas import (
    ArchiveInfo,
    Benchmark,
    PipelineConfig,
    PipelineControl,
    PipelineLog,
    PipelineState,
)
from ..schemas import DecisionFiltersQuery

def admin_guard(x_admin_token: str | None = Header(default=None)) -> None:
    """Garde admin : toutes les routes /api/pipeline/* exigent l'en-tête
    X-Admin-Token égal à la variable d'environnement JURISDIVORCE_ADMIN_TOKEN.
    Fail-closed : si la variable n'est pas définie, tout est refusé (404 pour
    ne pas révéler l'existence de la route)."""
    expected = os.getenv("JURISDIVORCE_ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(prefix="/api/pipeline", tags=["pipeline"], dependencies=[Depends(admin_guard)])

DEFAULTS = dict(
    status="idle", mode=None, current_archive=None, archives_done=0, archives_total=0,
    decisions_scanned=0, decisions_kept=0, decisions_analyzed=0, decisions_failed=0,
    tokens_today=0, day_key=None, queue_size=0, started_at=None, updated_at=None,
    files_read=0, retry_failed=0,
)

CONFIG_DEFAULTS = {
    "max_concurrency": os.getenv("MAX_CONCURRENCY", "25"),
    "model": os.getenv("JURISDIVORCE_MODEL", "glm-4-flash"),
    "max_chars": os.getenv("MAX_CHARS", "48000"),
}


def _state_row(db: Session) -> dict:
    row = db.execute(text("SELECT * FROM pipeline_state WHERE id = 1")).mappings().first()
    return {**DEFAULTS, **dict(row)} if row else dict(DEFAULTS)


@router.get("/state", response_model=PipelineState)
def state(db: Session = Depends(get_db)):
    s = _state_row(db)
    vitesse = None
    if s["status"] == "running" and s["started_at"]:
        try:
            started = datetime.fromisoformat(s["started_at"])
            minutes = max((datetime.utcnow() - started).total_seconds() / 60.0, 0.1)
            vitesse = round(s["decisions_analyzed"] / minutes, 1)
        except ValueError:
            pass
    return PipelineState(vitesse_par_minute=vitesse, **s)


@router.get("/logs", response_model=List[PipelineLog])
def logs(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, ts, level, message FROM pipeline_logs ORDER BY id DESC LIMIT :n"),
        {"n": limit},
    ).mappings().all()
    return [PipelineLog(**dict(r)) for r in rows]


@router.get("/archives", response_model=List[ArchiveInfo])
def archives(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT * FROM processed_archives ORDER BY processed_at DESC LIMIT :n"),
        {"n": limit},
    ).mappings().all()
    return [ArchiveInfo(**dict(r)) for r in rows]


@router.post("/control", response_model=PipelineState)
def control(cmd: PipelineControl, db: Session = Depends(get_db)):
    s = _state_row(db)
    if s["status"] == "idle":
        raise HTTPException(status_code=409, detail="Aucun pipeline en cours (état idle).")
    s["status"] = {"pause": "paused", "resume": "running", "stop": "stopped"}[cmd.action]
    now = datetime.utcnow().isoformat(timespec="seconds")
    db.execute(
        text("""INSERT INTO pipeline_state (id, status, updated_at) VALUES (1, :status, :now)
                ON CONFLICT(id) DO UPDATE SET status = :status, updated_at = :now"""),
        {"status": s["status"], "now": now},
    )
    db.execute(
        text("INSERT INTO pipeline_logs (ts, level, message) VALUES (:ts, :level, :msg)"),
        {"ts": now, "level": "INFO", "msg": f"Contrôle opérateur : {cmd.action}"},
    )
    db.commit()
    return state(db)


# ------------------------------------------------ Configuration à chaud
@router.get("/config", response_model=PipelineConfig)
def get_config(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT key, value FROM app_config")).all()
    overrides = {k: v for k, v in rows}
    merged = {k: overrides.get(k, v) for k, v in CONFIG_DEFAULTS.items()}
    return PipelineConfig(
        max_concurrency=int(merged["max_concurrency"]),
        model=merged["model"],
        max_chars=int(merged["max_chars"]),
    )


@router.put("/config", response_model=PipelineConfig)
def put_config(cfg: PipelineConfig, db: Session = Depends(get_db)):
    """Écrit dans app_config : le worker relit cette table à chaque décision (à chaud)."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    for key, value in (
        ("max_concurrency", cfg.max_concurrency),
        ("model", cfg.model),
        ("max_chars", cfg.max_chars),
    ):
        if value is None:
            continue
        db.execute(
            text("INSERT OR REPLACE INTO app_config (key, value) VALUES (:k, :v)"),
            {"k": key, "v": str(value)},
        )
    db.execute(
        text("INSERT INTO pipeline_logs (ts, level, message) VALUES (:ts, :level, :msg)"),
        {"ts": now, "level": "INFO", "msg": f"Configuration à chaud : {cfg.model_dump(exclude_none=True)}"},
    )
    db.commit()
    return get_config(db)


# ------------------------------------------------ DLQ : relancer les échecs
@router.post("/retry-failed")
def retry_failed(db: Session = Depends(get_db)):
    """Pose le drapeau retry_failed : le worker (s'il tourne) redraine failed_decisions
    à sa prochaine itération. Sinon, utiliser `python -m pipeline.ingest retry-failed`."""
    n = db.execute(text("SELECT COUNT(*) FROM failed_decisions")).scalar() or 0
    db.execute(text("UPDATE pipeline_state SET retry_failed = 1, updated_at = :now WHERE id = 1"),
               {"now": datetime.utcnow().isoformat(timespec="seconds")})
    db.commit()
    return {"failed_decisions": n, "flag_posed": True,
            "note": "Le worker redraine les échecs s'il tourne ; sinon lancez : python -m pipeline.ingest retry-failed"}


# ------------------------------------------------ Benchmark de performance
@router.get("/benchmark", response_model=Benchmark)
def benchmark(db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    db.query(Decision).limit(100).all()
    t1 = time.perf_counter()
    from ..routers.stats import overview as stats_overview

    stats_overview(DecisionFiltersQuery(), db)
    t2 = time.perf_counter()

    s = _state_row(db)
    try:
        db_size_mb = round(os.path.getsize(DB_PATH) / 1e6, 2)
    except OSError:
        db_size_mb = 0.0

    started = s["started_at"]
    vitesse = None
    if s["status"] == "running" and started:
        try:
            minutes = max((datetime.utcnow() - datetime.fromisoformat(started)).total_seconds() / 60.0, 0.1)
            vitesse = round(s["decisions_analyzed"] / minutes, 1)
        except ValueError:
            pass

    try:
        raw_count = db.execute(text("SELECT COUNT(*) FROM raw_fiches")).scalar() or 0
        raw_mb = round(db.execute(text("SELECT COALESCE(SUM(LENGTH(raw_text)),0) FROM raw_fiches")).scalar() / 1e6, 1)
    except Exception:
        raw_count, raw_mb = 0, 0.0

    return Benchmark(
        decisions=db.query(Decision).count(),
        db_list_100_ms=round((t1 - t0) * 1000, 1),
        stats_overview_ms=round((t2 - t1) * 1000, 1),
        db_size_mb=db_size_mb,
        vitesse_par_minute=vitesse,
        tokens_today=s["tokens_today"],
        raw_fiches=raw_count,
        raw_fiches_mb=raw_mb,
    )
