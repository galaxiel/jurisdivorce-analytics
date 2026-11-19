"""Moniteur du pipeline d'ingestion : état temps réel, logs, contrôle pause/reprise/stop.

Le pipeline écrit son heartbeat dans pipeline_state / pipeline_logs / processed_archives
(voir pipeline/ingest.py) ; ces endpoints lisent ces tables et permettent le contrôle.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ArchiveInfo, PipelineControl, PipelineLog, PipelineState

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

DEFAULTS = dict(
    status="idle", mode=None, current_archive=None, archives_done=0, archives_total=0,
    decisions_scanned=0, decisions_kept=0, decisions_analyzed=0, decisions_failed=0,
    tokens_today=0, day_key=None, queue_size=0, started_at=None, updated_at=None,
)


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
