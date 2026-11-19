"""Constructeur de requête partagé : filtres croisés pour /decisions, /stats/* et /export."""
from typing import List

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from ..models import Decision, Recompense
from ..schemas import DecisionFiltersQuery


def filtered_query(db: Session, f: DecisionFiltersQuery) -> Query:
    q = db.query(Decision)
    if f.juridiction:
        q = q.filter(Decision.juridiction == f.juridiction)
    if f.annee:
        q = q.filter(Decision.date_decision.like(f"{f.annee}-%"))
    if f.regime:
        q = q.filter(Decision.regime_matrimonial == f.regime)
    if f.type_procedure:
        q = q.filter(Decision.type_procedure == f.type_procedure)
    if f.has_immo is not None:
        q = q.filter(Decision.bien_immobilier_principal == f.has_immo)
    if f.nature_reclamation:
        q = q.filter(Decision.recompenses.any(Recompense.categorie == f.nature_reclamation))
    if f.issue:
        q = q.filter(Decision.recompenses.any(Recompense.statut == f.issue))
    if f.montant_min is not None or f.montant_max is not None:
        # Montant du litige : indemnité d'occupation totale, sinon capital de PC
        montant = func.coalesce(Decision.occupation_montant_total, Decision.pc_montant_capital)
        if f.montant_min is not None:
            q = q.filter(montant >= f.montant_min)
        if f.montant_max is not None:
            q = q.filter(montant <= f.montant_max)
    if f.q:
        like = f"%{f.q}%"
        q = q.filter(
            Decision.resume_3_lignes.ilike(like)
            | Decision.resume_pedagogique.ilike(like)
            | Decision.juridiction.ilike(like)
            | Decision.numero_rg.ilike(like)
        )
    return q.order_by(Decision.date_decision.desc().nullslast())


def load_decisions(db: Session, f: DecisionFiltersQuery) -> List[Decision]:
    return filtered_query(db, f).all()


def load_recompenses(db: Session, decisions: List[Decision]) -> List[Recompense]:
    ids = [d.id for d in decisions]
    if not ids:
        return []
    out: List[Recompense] = []
    chunk = 500
    for i in range(0, len(ids), chunk):
        out.extend(
            db.query(Recompense).filter(Recompense.decision_id.in_(ids[i:i + chunk])).all()
        )
    return out
