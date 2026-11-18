"""Endpoints du moteur de recherche de jurisprudence (Module 3 du cahier des charges)."""
import json
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..schemas import DecisionDetail, DecisionList, DecisionListItem, RecompenseOut

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("", response_model=DecisionList)
def list_decisions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    juridiction: Optional[str] = None,
    regime: Optional[str] = None,
    statut_recompense: Optional[str] = None,
    presence_pc: Optional[bool] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Decision)
    if juridiction:
        query = query.filter(Decision.juridiction == juridiction)
    if regime:
        query = query.filter(Decision.regime_matrimonial == regime)
    if presence_pc is not None:
        query = query.filter(Decision.pc_demandee == presence_pc)
    if statut_recompense:
        query = query.filter(Decision.recompenses.any(Recompense.statut == statut_recompense))
    if q:
        like = f"%{q}%"
        query = query.filter(
            Decision.resume_3_lignes.ilike(like)
            | Decision.juridiction.ilike(like)
            | Decision.numero_rg.ilike(like)
        )

    total = query.count()
    items = (
        query.order_by(Decision.date_decision.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    ids = [d.id for d in items]
    by_decision: dict[str, list] = defaultdict(list)
    if ids:
        for r in db.query(Recompense).filter(Recompense.decision_id.in_(ids)).all():
            by_decision[r.decision_id].append(r)

    def taux_reussite(recs: list) -> Optional[float]:
        done = [r for r in recs if r.statut]
        if not done:
            return None
        return round(100 * sum(r.statut != "REJETE" for r in done) / len(done), 1)

    items_out = []
    for d in items:
        item = DecisionListItem.model_validate(d)
        recs = by_decision.get(d.id, [])
        item.nb_recompenses = len(recs)
        item.taux_reussite_recompenses = taux_reussite(recs)
        items_out.append(item)
    return DecisionList(total=total, page=page, page_size=page_size, items=items_out)


@router.get("/{decision_id}", response_model=DecisionDetail)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(status_code=404, detail="Décision introuvable")

    try:
        parsed = json.loads(d.extracted_json or "{}")
    except json.JSONDecodeError:
        parsed = {}
    strategie = parsed.get("analyse_strategique", {}) if isinstance(parsed, dict) else {}

    detail = DecisionDetail.model_validate(d)
    detail.nb_recompenses = len(d.recompenses)
    done = [r for r in d.recompenses if r.statut]
    if done:
        detail.taux_reussite_recompenses = round(100 * sum(r.statut != "REJETE" for r in done) / len(done), 1)
    detail.recompenses = [RecompenseOut.model_validate(r) for r in d.recompenses]
    detail.points_forts_gagnants = strategie.get("points_forts_gagnants", [])
    detail.pieges_et_erreurs = strategie.get("pieges_et_erreurs_a_eviter", [])
    detail.raw_excerpt = (d.raw_text or "")[:4000]
    return detail
