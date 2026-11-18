"""Connexion SQLite (développement) / PostgreSQL (production via JURISDIVORCE_DB)."""
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("JURISDIVORCE_DB", str(BACKEND_DIR / "jurisprudence.db"))

# SQLite en dev ; JURISDIVORCE_DB="postgresql://..." bascule en Postgres sans changement de code.
if DB_PATH.startswith("postgres"):
    engine = create_engine(DB_PATH, pool_pre_ping=True)
else:
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
