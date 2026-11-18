"""Endpoints statistiques du Dashboard Analytics (Module 1 du cahier des charges)."""
import statistics
from collections import Counter, defaultdict
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..schemas import CourComparatif, KpiOverview, MotifRejet, PCDistribution, PreuveSucces

router = APIRouter(prefix="/api/stats", tags=["stats"])

PC_BUCKETS = [
    (0, 5, "0-5 ans"),
    (5, 10, "5-10 ans"),
    (10, 15, "10-15 ans"),
    (15, 20, "15-20 ans"),
    (20, 30, "20-30 ans"),
    (30, 200, "30 ans et +"),
]


def _mean(values) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _median(values) -> float | None:
    return round(statistics.median(values), 2) if values else None


@router.get("/overview", response_model=KpiOverview)
def overview(db: Session = Depends(get_db)):
    decisions = db.query(Decision).all()  # dataset léger : agrégation Python ; passer en SQL/JSONB à l'échelle
    dates = sorted(d.date_decision for d in decisions if d.date_decision)

    occ_demandees = [d for d in decisions if d.occupation_demandee]
    occ_accordees = [d for d in occ_demandees if d.occupation_accordee]
    abattements = [d.occupation_abattement_pct for d in occ_accordees if d.occupation_abattement_pct is not None]

    travaux_accordes = [
        r.montant_accorde
        for r in db.query(Recompense)
        .filter(Recompense.categorie == "TRAVAUX_BIEN_PROPRE", Recompense.montant_accorde.isnot(None))
        .all()
    ]

    aucune = [
        r for r in db.query(Recompense)
        .filter(Recompense.preuve_type == "AUCUNE", Recompense.statut.isnot(None))
        .all()
    ]
    echec_sans_factures = round(100 * sum(r.statut == "REJETE" for r in aucune) / len(aucune), 1) if aucune else None

    pc_demandees = [d for d in decisions if d.pc_demandee]
    pc_accordees = [d for d in pc_demandees if d.pc_accordee]
    capitals = [d.pc_montant_capital for d in pc_accordees if d.pc_montant_capital is not None]

    return KpiOverview(
        total_decisions=len(decisions),
        nb_juridictions=len({d.juridiction for d in decisions if d.juridiction}),
        periode=f"{dates[0]} → {dates[-1]}" if dates else None,
        taux_occupation_accordee=round(100 * len(occ_accordees) / len(occ_demandees), 1) if occ_demandees else None,
        abattement_moyen_pct=_mean(abattements),
        montant_moyen_recompense_travaux=_mean(travaux_accordes),
        taux_echec_sans_factures_pct=echec_sans_factures,
        pc_taux_accorde_pct=round(100 * len(pc_accordees) / len(pc_demandees), 1) if pc_demandees else None,
        pc_capital_moyen=_mean(capitals),
    )


@router.get("/comparatif-cours", response_model=List[CourComparatif])
def comparatif_cours(db: Session = Depends(get_db)):
    groups: dict[str, list] = defaultdict(list)
    for d in db.query(Decision).all():
        if d.juridiction:
            groups[d.juridiction].append(d)
    items = []
    for jur, g in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:10]:
        monthly = [d.occupation_montant_mensuel_final for d in g if d.occupation_accordee and d.occupation_montant_mensuel_final is not None]
        abat = [d.occupation_abattement_pct for d in g if d.occupation_accordee and d.occupation_abattement_pct is not None]
        items.append(
            CourComparatif(
                juridiction=jur,
                nb_decisions=len(g),
                indemnite_moyenne_mensuelle=_mean(monthly),
                abattement_moyen_pct=_mean(abat),
            )
        )
    return items


@router.get("/distribution-pc", response_model=List[PCDistribution])
def distribution_pc(db: Session = Depends(get_db)):
    decisions = [
        d for d in db.query(Decision).all()
        if d.pc_accordee and d.pc_montant_capital is not None and d.duree_mariage_annees is not None
    ]
    out = []
    for lo, hi, label in PC_BUCKETS:
        capitals = [d.pc_montant_capital for d in decisions if lo <= d.duree_mariage_annees < hi]
        out.append(
            PCDistribution(
                bucket=label,
                nb_decisions=len(capitals),
                capital_moyen=_mean(capitals),
                capital_median=_median(capitals),
            )
        )
    return out


@router.get("/top-motifs-rejet", response_model=List[MotifRejet])
def top_motifs_rejet(db: Session = Depends(get_db)):
    motifs = (
        db.query(Recompense.motif_echec)
        .filter(Recompense.statut == "REJETE", Recompense.motif_echec.isnot(None))
        .all()
    )
    counts = Counter(m.strip(" .") for (m,) in motifs if m.strip())
    return [MotifRejet(motif=m, nb_cas=n) for m, n in counts.most_common(5)]


@router.get("/recompenses-par-preuve", response_model=List[PreuveSucces])
def recompenses_par_preuve(db: Session = Depends(get_db)):
    recs = (
        db.query(Recompense)
        .filter(Recompense.statut.isnot(None), Recompense.preuve_type.isnot(None))
        .all()
    )
    buckets: dict[str, list] = defaultdict(list)
    for r in recs:
        buckets[r.preuve_type].append(r)
    out = []
    for ptype, group in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        accordees = [r.montant_accorde for r in group if r.montant_accorde is not None]
        out.append(
            PreuveSucces(
                preuve_type=ptype,
                nb_reclamations=len(group),
                taux_succes_pct=round(100 * sum(r.statut != "REJETE" for r in group) / len(group), 1),
                montant_moyen_accorde=_mean(accordees),
            )
        )
    return out
