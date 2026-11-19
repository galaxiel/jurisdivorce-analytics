"""Connexion SQLite (développement) / PostgreSQL (production via JURISDIVORCE_DB)."""
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("JURISDIVORCE_DB", str(BACKEND_DIR / "jurisprudence.db"))

# SQLite en dev ; JURISDIVORCE_DB="postgresql://..." bascule en Postgres sans changement de code.
if DB_PATH.startswith("postgres"):
    engine = create_engine(DB_PATH, pool_pre_ping=True)
else:
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL + busy_timeout : élimine les 'database is locked' entre worker et API."""
    if not DB_PATH.startswith("postgres"):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=10000")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Migration automatique légère : ajoute en ALTER TABLE les colonnes v2 manquantes.

    Préserve les données existantes (SQLite comme PostgreSQL) : aucune suppression,
    uniquement des ajouts de colonnes nullables.
    """
    from sqlalchemy import inspect, text

    from . import models  # import tardif : models importe Base de ce module

    inspector = inspect(engine)
    for table in (models.Decision.__table__, models.Recompense.__table__):
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            coltype = col.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}"))


PIPELINE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status TEXT DEFAULT 'idle',
    mode TEXT,
    current_archive TEXT,
    archives_done INTEGER DEFAULT 0,
    archives_total INTEGER DEFAULT 0,
    decisions_scanned INTEGER DEFAULT 0,
    decisions_kept INTEGER DEFAULT 0,
    decisions_analyzed INTEGER DEFAULT 0,
    decisions_failed INTEGER DEFAULT 0,
    tokens_today INTEGER DEFAULT 0,
    day_key TEXT,
    queue_size INTEGER DEFAULT 0,
    started_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS pipeline_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    level TEXT,
    message TEXT
);
CREATE TABLE IF NOT EXISTS processed_archives (
    url TEXT PRIMARY KEY,
    fonds TEXT,
    size_bytes INTEGER,
    status TEXT DEFAULT 'pending',
    decisions_found INTEGER DEFAULT 0,
    decisions_analyzed INTEGER DEFAULT 0,
    error TEXT,
    processed_at TEXT
);
CREATE TABLE IF NOT EXISTS failed_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT,
    text_truncated TEXT,
    error TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_id ON pipeline_logs(id DESC);
"""

# Colonnes ajoutées a posteriori sur les tables pipeline (migrations légères)
PIPELINE_MIGRATION_COLUMNS = {
    "pipeline_state": {"files_read": "INTEGER DEFAULT 0", "retry_failed": "INTEGER DEFAULT 0"},
}


def ensure_pipeline_tables() -> None:
    """Crée/migre les tables du moniteur (état, logs, manifest, DLQ, config à chaud)."""
    from sqlalchemy import text

    with engine.begin() as conn:
        for stmt in filter(None, (s.strip() for s in PIPELINE_SCHEMA_SQL.split(";"))):
            conn.execute(text(stmt))
        for table, cols in PIPELINE_MIGRATION_COLUMNS.items():
            existing = {r[1] for r in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            for col, coltype in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
