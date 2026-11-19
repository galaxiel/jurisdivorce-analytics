"""Endpoints de l'explorateur de jurisprudence + export CSV/JSON (Module 3 v2)."""
import csv
import io
import json
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..schemas import DecisionDetail, DecisionFiltersQuery, DecisionList, DecisionListItem, RecompenseOut
from ..services.query import filtered_query, load_recompenses

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("", response_model=DecisionList)
def list_decisions(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    query = filtered_query(db, filters)
    page, page_size = filters.page, filters.page_size
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    by_decision: dict[str, list] = defaultdict(list)
    for r in load_recompenses(db, items):
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
        if recs:
            item.total_demande = round(sum(r.montant_reclame or 0 for r in recs), 2)
            item.total_accorde = round(sum(r.montant_accorde or 0 for r in recs), 2)
        items_out.append(item)

    return DecisionList(total=total, page=page, page_size=page_size, items=items_out)


@router.get("/export")
def export(filters: DecisionFiltersQuery = Depends(), format: str = Query("csv", pattern="^(csv|json)$"),
           db: Session = Depends(get_db)):
    """Export de la sélection courante (mêmes filtres que la liste)."""
    decisions = filtered_query(db, filters).limit(10_000).all()
    recs_by_decision: dict[str, list] = defaultdict(list)
    for r in load_recompenses(db, decisions):
        recs_by_decision[r.decision_id].append(r)

    if format == "json":
        payload = []
        for d in decisions:
            payload.append({
                "id": d.id, "date_decision": d.date_decision, "juridiction": d.juridiction,
                "type_procedure": d.type_procedure, "regime_matrimonial": d.regime_matrimonial,
                "duree_mariage_annees": d.duree_mariage_annees,
                "occupation_montant_total": d.occupation_montant_total,
                "occupation_abattement_pct": d.occupation_abattement_pct,
                "pc_montant_capital": d.pc_montant_capital,
                "article_700_montant": d.article_700_montant,
                "delai_procedure_mois": d.delai_procedure_mois,
                "resume_3_lignes": d.resume_3_lignes,
                "reclamations": [
                    {"nature": r.categorie, "montant_reclame": r.montant_reclame,
                     "montant_accorde": r.montant_accorde, "statut": r.statut,
                     "regle_calcul": r.regle_calcul}
                    for r in recs_by_decision.get(d.id, [])
                ],
            })
        blob = json.dumps(payload, ensure_ascii=False, indent=1)
        return StreamingResponse(
            iter([blob]),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="jurisdivorce-selection.json"'},
        )

    # CSV (séparateur ; pour Excel FR)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "id", "date", "juridiction", "type_procedure", "regime", "duree_mariage_ans",
        "occupation_accordee", "occupation_total_eur", "abattement_pct",
        "pc_accordee", "pc_capital_eur", "article_700_eur", "delai_mois",
        "nb_reclamations", "total_demande_eur", "total_accorde_eur", "resume",
    ])
    for d in decisions:
        recs = recs_by_decision.get(d.id, [])
        writer.writerow([
            d.id, d.date_decision, d.juridiction, d.type_procedure, d.regime_matrimonial,
            d.duree_mariage_annees, d.occupation_accordee, d.occupation_montant_total,
            d.occupation_abattement_pct, d.pc_accordee, d.pc_montant_capital,
            d.article_700_montant, d.delai_procedure_mois, len(recs),
            round(sum(r.montant_reclame or 0 for r in recs), 2),
            round(sum(r.montant_accorde or 0 for r in recs), 2),
            (d.resume_3_lignes or "").replace("\n", " "),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="jurisdivorce-selection.csv"'},
    )


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
    if d.recompenses:
        detail.total_demande = round(sum(r.montant_reclame or 0 for r in d.recompenses), 2)
        detail.total_accorde = round(sum(r.montant_accorde or 0 for r in d.recompenses), 2)
    detail.recompenses = []
    for r in d.recompenses:
        rec = RecompenseOut.model_validate(r)
        try:
            rec.preuves = json.loads(r.preuves_json or "[]")
        except json.JSONDecodeError:
            rec.preuves = []
        detail.recompenses.append(rec)
    detail.points_forts_gagnants = strategie.get("points_forts_gagnants", [])
    detail.pieges_et_erreurs = strategie.get("pieges_et_erreurs_a_eviter", [])
    detail.pc_criteres = json.loads(d.pc_criteres_json or "[]")
    detail.raw_excerpt = (d.raw_text or "")[:6000]
    return detail
