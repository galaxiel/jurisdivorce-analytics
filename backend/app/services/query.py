"""Constructeur de requête partagé : filtres croisés pour /decisions, /stats/* et /export."""
import re
import time
from typing import List, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Query, Session, defer

from ..models import Decision, Recompense
from ..schemas import DecisionFiltersQuery

_DECISIONS_CACHE_TTL = 300  # secondes — les ~9 appels stats du Cockpit partagent une lecture
_decisions_cache: dict = {}


def _fts_search_ids(db: Session, query: str) -> Optional[List[str]]:
    """Recherche plein texte FTS5 (AND sur les mots, index tenu par triggers).

    Retourne None si FTS indisponible → repli LIKE par l'appelant."""
    words = [w for w in re.findall(r"\w+", query, re.UNICODE) if len(w) > 1]
    if not words:
        return None
    match = " ".join(f'"{w}"' for w in words)  # AND de phrases → sans erreur de syntaxe FTS
    try:
        rows = db.execute(
            text("SELECT id FROM decisions_fts WHERE decisions_fts MATCH :m LIMIT 1000"),
            {"m": match},
        ).all()
        return [r[0] for r in rows]
    except Exception:
        return None


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
        fts_ids = _fts_search_ids(db, f.q)
        if fts_ids:
            q = q.filter(Decision.id.in_(fts_ids))
        else:
            # Repli LIKE (FTS indisponible ou aucun résultat FTS)
            like = f"%{f.q}%"
            q = q.filter(
                Decision.resume_3_lignes.ilike(like)
                | Decision.resume_pedagogique.ilike(like)
                | Decision.juridiction.ilike(like)
                | Decision.numero_rg.ilike(like)
            )
    return q.order_by(Decision.date_decision.desc().nullslast())


def load_decisions(db: Session, f: DecisionFiltersQuery) -> List[Decision]:
    """Charge les décisions pour les agrégations stats — SANS raw_text/extracted_json
    (defer) : à 14 486 lignes ces colonnes ~7 Ko représentaient ~100 Mo d'ORM par appel
    et 58 s sur /api/stats/overview. Cache TTL partagé entre les appels stats (les
    entités renvoyées ne sont utilisées qu'en lecture)."""
    key = (str(db.bind.url) if db.bind else None, f.juridiction, f.annee, f.regime,
           f.type_procedure, f.nature_reclamation, f.issue, f.has_immo,
           f.montant_min, f.montant_max, f.q)
    now = time.monotonic()
    hit = _decisions_cache.get(key)
    if hit and now - hit[0] < _DECISIONS_CACHE_TTL:
        return hit[1]
    rows = filtered_query(db, f).options(
        defer(Decision.raw_text), defer(Decision.extracted_json)
    ).all()
    if len(_decisions_cache) > 16:
        for k in [k for k, v in _decisions_cache.items() if now - v[0] >= _DECISIONS_CACHE_TTL]:
            _decisions_cache.pop(k, None)
    _decisions_cache[key] = (now, rows)
    return rows


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
