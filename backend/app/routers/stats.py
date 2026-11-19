"""Endpoints statistiques du Cockpit (Module 1 v2) — tous sensibles aux filtres croisés."""
import random
import statistics
from collections import Counter, defaultdict
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision, Recompense
from ..schemas import (
    AbattementBucket,
    CourComparatif,
    DecisionFiltersQuery,
    Facets,
    KpiOverview,
    MotifRejet,
    NatureSucces,
    PCCorrelationPoint,
    PCDistribution,
    Piege,
    PreuveSucces,
    TendancePoint,
)
from ..services.query import load_decisions, load_recompenses

router = APIRouter(prefix="/api/stats", tags=["stats"])

PC_BUCKETS = [
    (0, 5, "0-5 ans"), (5, 10, "5-10 ans"), (10, 15, "10-15 ans"),
    (15, 20, "15-20 ans"), (20, 30, "20-30 ans"), (30, 200, "30 ans et +"),
]
ABATTEMENT_BUCKETS = [
    (0, 10, "0-10 %"), (10, 15, "10-15 %"), (15, 20, "15-20 %"),
    (20, 25, "20-25 %"), (25, 30, "25-30 %"), (30, 101, "30 % et +"),
]


def _mean(values) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _median(values) -> float | None:
    return round(statistics.median(values), 2) if values else None


@router.get("/overview", response_model=KpiOverview)
def overview(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    decisions = load_decisions(db, filters)
    recs = load_recompenses(db, decisions)

    dates = sorted(d.date_decision for d in decisions if d.date_decision)
    occ_demandees = [d for d in decisions if d.occupation_demandee]
    occ_accordees = [d for d in occ_demandees if d.occupation_accordee]
    abattements = [d.occupation_abattement_pct for d in occ_accordees if d.occupation_abattement_pct is not None]

    travaux_accordes = [
        r.montant_accorde for r in recs
        if r.categorie == "TRAVAUX_BIEN_PROPRE" and r.montant_accorde is not None
    ]
    aucune = [r for r in recs if r.preuve_type == "AUCUNE" and r.statut]
    echec_sans_factures = round(100 * sum(r.statut == "REJETE" for r in aucune) / len(aucune), 1) if aucune else None

    pc_demandees = [d for d in decisions if d.pc_demandee]
    pc_accordees = [d for d in pc_demandees if d.pc_accordee]
    capitals = [d.pc_montant_capital for d in pc_accordees if d.pc_montant_capital is not None]

    statutaires = [r for r in recs if r.statut]
    demandes = [r.montant_reclame for r in statutaires if r.montant_reclame is not None]
    accordes = [r.montant_accorde for r in statutaires if r.montant_accorde is not None]
    a700 = [d.article_700_montant for d in decisions if d.article_700_montant is not None]

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
        pc_capital_median=_median(capitals),
        taux_succes_recompenses_pct=round(100 * sum(r.statut != "REJETE" for r in statutaires) / len(statutaires), 1) if statutaires else None,
        article_700_moyen=_mean(a700),
        total_demande=round(sum(demandes)) if demandes else None,
        total_accorde=round(sum(accordes)) if accordes else None,
    )


@router.get("/comparatif-cours", response_model=List[CourComparatif])
def comparatif_cours(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    groups: dict[str, list] = defaultdict(list)
    for d in load_decisions(db, filters):
        if d.juridiction:
            groups[d.juridiction].append(d)
    items = []
    for jur, g in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:12]:
        monthly = [d.occupation_montant_mensuel_final for d in g if d.occupation_accordee and d.occupation_montant_mensuel_final is not None]
        abat = [d.occupation_abattement_pct for d in g if d.occupation_accordee and d.occupation_abattement_pct is not None]
        occ_demandees = [d for d in g if d.occupation_demandee]
        occ_accordees = [d for d in occ_demandees if d.occupation_accordee]
        items.append(
            CourComparatif(
                juridiction=jur,
                nb_decisions=len(g),
                indemnite_moyenne_mensuelle=_mean(monthly),
                indemnite_mediane_mensuelle=_median(monthly),
                abattement_moyen_pct=_mean(abat),
                taux_acceptation_pct=round(100 * len(occ_accordees) / len(occ_demandees), 1) if occ_demandees else None,
            )
        )
    return items


@router.get("/distribution-pc", response_model=List[PCDistribution])
def distribution_pc(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    decisions = [
        d for d in load_decisions(db, filters)
        if d.pc_accordee and d.pc_montant_capital is not None and d.duree_mariage_annees is not None
    ]
    out = []
    for lo, hi, label in PC_BUCKETS:
        capitals = [d.pc_montant_capital for d in decisions if lo <= d.duree_mariage_annees < hi]
        out.append(
            PCDistribution(bucket=label, nb_decisions=len(capitals),
                           capital_moyen=_mean(capitals), capital_median=_median(capitals))
        )
    return out


@router.get("/abattement-distribution", response_model=List[AbattementBucket])
def abattement_distribution(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    decisions = [
        d for d in load_decisions(db, filters)
        if d.occupation_accordee and d.occupation_abattement_pct is not None
    ]
    out = []
    for lo, hi, label in ABATTEMENT_BUCKETS:
        group = [d for d in decisions if lo <= d.occupation_abattement_pct < hi]
        monthly = [d.occupation_montant_mensuel_final for d in group if d.occupation_montant_mensuel_final is not None]
        out.append(AbattementBucket(bucket=label, nb_decisions=len(group), moyenne_indemnite_mensuelle=_mean(monthly)))
    return out


@router.get("/succes-par-nature", response_model=List[NatureSucces])
def succes_par_nature(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    recs = load_recompenses(db, load_decisions(db, filters))
    buckets: dict[str, list] = defaultdict(list)
    for r in recs:
        if r.statut and r.categorie:
            buckets[r.categorie].append(r)
    out = []
    for nature, group in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        demandes = [r.montant_reclame for r in group if r.montant_reclame is not None]
        accordes = [r.montant_accorde for r in group if r.montant_accorde is not None]
        out.append(
            NatureSucces(
                nature=nature,
                nb_reclamations=len(group),
                taux_succes_pct=round(100 * sum(r.statut != "REJETE" for r in group) / len(group), 1),
                montant_moyen_demande=_mean(demandes),
                montant_moyen_accorde=_mean(accordes),
            )
        )
    return out


@router.get("/pc-correlation", response_model=List[PCCorrelationPoint])
def pc_correlation(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    points = [
        PCCorrelationPoint(
            duree_mariage_annees=d.duree_mariage_annees,
            ecart_revenus_mensuel=d.pc_ecart_revenus_mensuel,
            capital_accorde=d.pc_montant_capital,
            juridiction=d.juridiction,
        )
        for d in load_decisions(db, filters)
        if d.pc_accordee and d.pc_montant_capital is not None and d.duree_mariage_annees is not None
    ]
    if len(points) > 600:
        points = random.sample(points, 600)
    return points


@router.get("/top-motifs-rejet", response_model=List[MotifRejet])
def top_motifs_rejet(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    motifs = [r.motif_echec for r in load_recompenses(db, load_decisions(db, filters))
              if r.statut == "REJETE" and r.motif_echec]
    counts = Counter(m.strip(" .") for m in motifs if m.strip())
    return [MotifRejet(motif=m, nb_cas=n) for m, n in counts.most_common(5)]


@router.get("/pieges", response_model=List[Piege])
def pieges(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    """Radar des pièges : 10 principaux motifs de rejet, % des échecs, montant moyen
    perdu et 3 arrêts illustratifs chacun."""
    recs = load_recompenses(db, load_decisions(db, filters))
    rejected = [r for r in recs if r.statut == "REJETE" and r.motif_echec]
    total_rejets = len(rejected)

    # Détail décisionnel pour les arrêts illustratifs
    ids = {r.decision_id for r in rejected}
    decisions_by_id = {}
    for chunk_start in range(0, len(ids), 500):
        chunk = list(ids)[chunk_start:chunk_start + 500]
        for d in db.query(Decision).filter(Decision.id.in_(chunk)).all():
            decisions_by_id[d.id] = d

    groups: dict[str, list] = defaultdict(list)
    for r in rejected:
        groups[r.motif_echec.strip(" .")].append(r)

    out = []
    for motif, group in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:10]:
        perdus = [r.montant_reclame for r in group if r.montant_reclame is not None]
        exemples = []
        for r in group[:3]:
            d = decisions_by_id.get(r.decision_id)
            if d:
                exemples.append({
                    "id": d.id,
                    "juridiction": d.juridiction,
                    "date_decision": d.date_decision,
                    "numero_rg": d.numero_rg,
                    "montant_perdu": r.montant_reclame,
                    "resume": (d.resume_3_lignes or "")[:220],
                })
        out.append(Piege(
            motif=motif,
            nb_cas=len(group),
            pct_rejets=round(100 * len(group) / total_rejets, 1) if total_rejets else 0.0,
            montant_moyen_perdu=_mean(perdus),
            exemples=exemples,
        ))
    return out


@router.get("/recompenses-par-preuve", response_model=List[PreuveSucces])
def recompenses_par_preuve(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    recs = [r for r in load_recompenses(db, load_decisions(db, filters))
            if r.statut and r.preuve_type]
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


@router.get("/tendances", response_model=List[TendancePoint])
def tendances(filters: DecisionFiltersQuery = Depends(), db: Session = Depends(get_db)):
    """Analytics temporelles : volume, abattement médian, PC médiane et taux de succès
    par année de décision (réactif aux filtres croisés)."""
    decisions = load_decisions(db, filters)
    recs = load_recompenses(db, decisions)
    recs_by_decision: dict[str, list] = defaultdict(list)
    for r in recs:
        recs_by_decision[r.decision_id].append(r)

    by_year: dict[str, list] = defaultdict(list)
    for d in decisions:
        if d.date_decision and len(d.date_decision) >= 4:
            by_year[d.date_decision[:4]].append(d)

    out = []
    for year in sorted(by_year):
        group = by_year[year]
        abat = [d.occupation_abattement_pct for d in group
                if d.occupation_accordee and d.occupation_abattement_pct is not None]
        capitals = [d.pc_montant_capital for d in group
                    if d.pc_accordee and d.pc_montant_capital is not None]
        statutaires = [r for d in group for r in recs_by_decision.get(d.id, []) if r.statut]
        out.append(TendancePoint(
            annee=int(year),
            nb_decisions=len(group),
            abattement_median_pct=_median(abat),
            pc_mediane=_median(capitals),
            taux_succes_pct=round(100 * sum(r.statut != "REJETE" for r in statutaires) / len(statutaires), 1) if statutaires else None,
        ))
    return out


@router.get("/facets", response_model=Facets)
def facets(db: Session = Depends(get_db)):
    """Valeurs distinctes pour alimenter la barre de filtres universelle."""
    decisions = db.query(Decision).all()
    annees = sorted({d.date_decision[:4] for d in decisions if d.date_decision and len(d.date_decision) >= 4}, reverse=True)
    natures = [row[0] for row in db.query(Recompense.categorie).filter(Recompense.categorie.isnot(None)).distinct().all()]
    return Facets(
        juridictions=sorted({d.juridiction for d in decisions if d.juridiction}),
        annees=[int(a) for a in annees],
        regimes=sorted({d.regime_matrimonial for d in decisions if d.regime_matrimonial}),
        types_procedure=sorted({d.type_procedure for d in decisions if d.type_procedure}),
        natures=sorted(natures),
    )
