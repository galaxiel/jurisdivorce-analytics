"""Point d'entrée FastAPI — JurisDivorce Analytics.

Docs interactive : http://127.0.0.1:8000/docs
Lancer : uvicorn app.main:app --reload --port 8000  (depuis backend/)
"""
import os
import shutil

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import DB_PATH, Base, ensure_pipeline_tables, ensure_schema, engine, get_db
from .models import Decision  # noqa: F401 — importé pour create_all
from .routers import boussole, calculateur, checkout, decisions, demo, pipeline, simulateur, stats

Base.metadata.create_all(bind=engine)
ensure_schema()  # migration légère : colonnes v2 ajoutées sans perte de données
ensure_pipeline_tables()  # tables du moniteur (état, logs, manifest, DLQ, config)

app = FastAPI(
    title="JurisDivorce Analytics API",
    version="0.1.0",
    description=(
        "API d'analyse statistique et décisionnelle de la jurisprudence en droit "
        "de la famille (divorce, liquidation de régime matrimonial & partage)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stats.router)
app.include_router(decisions.router)
app.include_router(boussole.router)
app.include_router(pipeline.router)
app.include_router(calculateur.router)
app.include_router(demo.router)
app.include_router(simulateur.router)
app.include_router(checkout.router)


@app.get("/api/health", tags=["health"])
def health(db=Depends(get_db)):
    """Test de santé : DB, espace disque, état du worker d'ingestion."""
    from .routers.pipeline import _state_row
    from .schemas import HealthStatus

    db_ok = True
    try:
        db.execute(text("SELECT 1")).fetchone()
    except Exception:
        db_ok = False
    try:
        disk_free_gb = round(shutil.disk_usage(DB_PATH).free / 1e9, 2)
    except OSError:
        disk_free_gb = 0.0
    worker = _state_row(db)["status"]
    result = {
        "status": "ok" if db_ok else "degraded",
        "db_ok": db_ok,
        "disk_free_gb": disk_free_gb,
        "decisions": db.query(Decision).count(),
        "worker_status": worker,
        "version": "3.0.1",
        "source": "live",
    }
    return HealthStatus(**result)


# Déploiement web : si un export statique du frontend est présent à côté de app/,
# FastAPI le sert sur / (un seul process : API + site). Le mount est déclaré EN DERNIER :
# dans Starlette, un mount "/" placé avant une route la masque.
STATIC_SITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static_site")
if os.path.isdir(STATIC_SITE_DIR):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=STATIC_SITE_DIR, html=True), name="site")
