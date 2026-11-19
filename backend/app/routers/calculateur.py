"""Calculateur juridique interactif couplant formules légales et statistiques de la base.

- Indemnité d'occupation (art. 815-9 C. civ.) : abattement médian réel de la cour
  sélectionnée + alerte prescription quinquennale + 10 arrêts les plus proches.
- Récompense / profit subsistant (art. 1469 C. civ.) : dépense faite vs profit
  subsistant + taux de rejet constatés (amélioration vs entretien).
"""
import statistics
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..schemas import (
    OccupationCalcRequest,
    OccupationCalcResult,
    RecompenseCalcRequest,
    RecompenseCalcResult,
)
from ..services.query import load_decisions

router = APIRouter(prefix="/api/calculateur", tags=["calculateur"])


def _months_between(start: str, end: str) -> Optional[int]:
    try:
        d1 = date.fromisoformat(start[:10])
        d2 = date.fromisoformat(end[:10])
    except ValueError:
        return None
    if d2 < d1:
        return None
    return max(1, round((d2 - d1).days / 30.44))


@router.post("/occupation", response_model=OccupationCalcResult)
def occupation(req: OccupationCalcRequest, db: Session = Depends(get_db)):
    mois = _months_between(req.date_debut, req.date_fin)
    if mois is None:
        mois = 0

    pool = [
        d for d in db.query(Decision).all()
        if d.juridiction == req.juridiction and d.occupation_accordee
        and d.occupation_abattement_pct is not None
    ]
    echantillon_cour = len(pool)
    if echantillon_cour < 8:  # repli national
        pool = [d for d in db.query(Decision).all()
                if d.occupation_accordee and d.occupation_abattement_pct is not None]
    abattements = sorted(d.occupation_abattement_pct for d in pool)
    abat_median = round(statistics.median(abattements), 1) if abattements else None
    abat_eff = (abat_median or 0) / 100.0

    base = req.valeur_locative_mensuelle * mois * (req.quote_part_autres_pct / 100.0)
    montant_brut = round(base)
    montant_net = round(base * (1 - abat_eff))

    # Prescription quinquennale : au-delà de 5 ans d'occupation sans acte interruptif,
    # seules les 5 dernières années sont recouvrables.
    mois_recouvrables = min(mois, 60)
    prescription = {
        "depassement_mois": max(0, mois - 60),
        "mois_recouvrables": mois_recouvrables,
        "montant_recuperable": round(
            req.valeur_locative_mensuelle * mois_recouvrables * (req.quote_part_autres_pct / 100.0)
            * (1 - abat_eff)
        ),
        "alerte": mois > 60,
    }

    comparables: List[Dict] = []
    if pool:
        vl = req.valeur_locative_mensuelle or 1.0
        comparables = sorted(
            pool,
            key=lambda d: (
                abs((d.occupation_abattement_pct or 0) - (abat_median or 0)),
                abs((d.occupation_montant_mensuel_base or vl) - vl),
            ),
        )[:10]
        comparables = [
            {
                "id": d.id,
                "juridiction": d.juridiction,
                "date_decision": d.date_decision,
                "numero_rg": d.numero_rg,
                "abattement_pct": d.occupation_abattement_pct,
                "montant_mensuel_final": d.occupation_montant_mensuel_final,
                "montant_total": d.occupation_montant_total,
                "duree_mois": d.occupation_duree_mois,
            }
            for d in comparables
        ]

    return OccupationCalcResult(
        mois=mois,
        montant_brut=montant_brut,
        abattement_median_pct=abat_median,
        montant_net=montant_net,
        prescription=prescription,
        comparables=comparables,
        echantillon=len(pool),
    )


@router.post("/recompense", response_model=RecompenseCalcResult)
def recompense(req: RecompenseCalcRequest, db: Session = Depends(get_db)):
    plus_value = max(0.0, req.valeur_bien_actuelle - req.valeur_bien_avant_travaux)
    profit_subsistant = min(req.montant_travaux, plus_value)
    regle = "Profit subsistant" if plus_value < req.montant_travaux else "Dépense faite"

    alertes = []
    if req.nature == "entretien":
        alertes.append(
            "Les travaux d'entretien courant (réparations locatives, petite maintenance) ne "
            "constituent pas une récompense : seule l'amélioration ouvre droit à remboursement."
        )
    if req.valeur_bien_actuelle <= req.valeur_bien_avant_travaux:
        alertes.append(
            "Aucune plus-value constatée : la récompense est plafonnée au profit subsistant "
            "(art. 1469 III), soit un remboursement réduit à zéro si le bien s'est déprécié."
        )

    def taux_rejet(categorie: str) -> Optional[float]:
        recs = [
            r for r in db.query(Recompense).filter(
                Recompense.categorie == categorie, Recompense.statut.isnot(None)
            ).all()
        ]
        return round(100 * sum(r.statut == "REJETE" for r in recs) / len(recs), 1) if recs else None

    return RecompenseCalcResult(
        plus_value=round(plus_value, 2),
        profit_subsistant=round(profit_subsistant, 2),
        depense_faite=round(req.montant_travaux, 2),
        regle=regle,
        taux_rejet_amelioration_pct=taux_rejet("TRAVAUX_BIEN_PROPRE"),
        taux_rejet_entretien_pct=taux_rejet("TAXES_ASSURANCE"),
        alertes=alertes,
    )
