"""Point d'entrée FastAPI — JurisDivorce Analytics.

Docs interactive : http://127.0.0.1:8000/docs
Lancer : uvicorn app.main:app --reload --port 8000  (depuis backend/)
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, get_db
from .models import Decision  # noqa: F401 — importé pour create_all
from .routers import boussole, decisions, stats

Base.metadata.create_all(bind=engine)

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


@app.get("/api/health", tags=["health"])
def health(db=Depends(get_db)):
    return {"status": "ok", "decisions": db.query(Decision).count()}
