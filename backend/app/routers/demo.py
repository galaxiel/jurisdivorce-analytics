"""Mode démo : charge 50 arrêts de démonstration réalistes (is_demo=true) et purge en 1 clic.

Utilisé par le bandeau affiché quand la base est encore vide (< 50 décisions) : permet de
tester immédiatement tous les graphiques et simulateurs, puis de purger avant l'ingestion réelle.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..seed import JURIDICTIONS, gen_decision

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_COUNT = 50


def _count(db: Session) -> int:
    return db.query(Decision).filter(Decision.is_demo == True).count()  # noqa: E712


@router.get("/count")
def demo_count(db: Session = Depends(get_db)):
    return {"demo_decisions": _count(db)}


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """Insère DEMO_COUNT décisions synthétiques marquées is_demo (ne touche pas le reste)."""
    created = 0
    token = uuid.uuid4().hex[:6]
    for i in range(1, DEMO_COUNT + 1):
        jur = JURIDICTIONS[(i * 7) % len(JURIDICTIONS)][0]
        dec, recs = gen_decision(i, jur)
        dec.id = f"demo50-{token}-{i:03d}"
        dec.is_demo = True
        db.add(dec)
        db.add_all(recs)
        created += 1
    db.commit()
    return {"created": created, "demo_decisions": _count(db)}


@router.delete("")
def purge_demo(db: Session = Depends(get_db)):
    """Purge 1 clic de toutes les décisions marquées is_demo (et leurs réclamations)."""
    ids = [d.id for d in db.query(Decision).filter(Decision.is_demo == True).all()]  # noqa: E712
    if ids:
        db.query(Recompense).filter(Recompense.decision_id.in_(ids)).delete(synchronize_session=False)
        db.query(Decision).filter(Decision.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return {"purged": len(ids), "demo_decisions": _count(db)}
