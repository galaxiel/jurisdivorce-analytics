"""Moteur statistique de la Boussole : estimation « Mon Cas » à partir des décisions comparables.

Aucun LLM à l'exécution : les fourchettes sont des percentiles calculés sur la
jurisprudence en base (rapide, déterministe, 0 token). La logique est volontairement
isolée de l'API pour être testable et remplaçable.
"""
import statistics
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Decision, Recompense
from .classify import PROOF_LABELS, PROOF_RANK

REGIME_LABELS = {
    "COMMUNAUTE_REDUITE_AUX_ACQUETS": "communauté réduite aux acquêts",
    "SEPARATION_DE_BIENS": "séparation de biens",
    "PARTICIPATION_AUX_ACQUETS": "participation aux acquêts",
    "COMMUNAUTE_UNIVERSELLE": "communauté universelle",
    "INCONNU": "régime inconnu",
}


def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    """Percentile par interpolation linéaire ; la liste doit être triée."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return round(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f), 2)


def _filter_comparables(pool: list, attr: str, value, min_n: int) -> list:
    """Restreint au sous-ensemble correspondant, sinon retombe sur le pool (national)."""
    filtered = [x for x in pool if getattr(x, attr) == value]
    return filtered if len(filtered) >= min_n else pool


def compute_report(db: Session, req) -> Dict:
    decisions = db.query(Decision).all()
    recs_by_decision: Dict[str, List[Recompense]] = defaultdict(list)
    for r in db.query(Recompense).all():
        recs_by_decision[r.decision_id].append(r)

    notes: List[str] = []

    # ------------------------------------------------ 1) Indemnité d'occupation
    occ = [d for d in decisions if d.occupation_accordee and d.occupation_montant_mensuel_final]
    occ_comp = _filter_comparables(occ, "juridiction", req.juridiction, 8)
    if occ_comp is occ:
        notes.append(
            "Échantillon trop faible pour cette cour : la fourchette d'indemnité d'occupation est calculée au plan national."
        )
    else:
        notes.append(f"Indemnité d'occupation fondée sur {len(occ_comp)} décisions d'occupation accordée de {req.juridiction}.")
    pool_cour = occ_comp
    occ_comp = _filter_comparables(occ_comp, "regime_matrimonial", req.regime_matrimonial, 8)
    if occ_comp is pool_cour:
        notes.append("Trop peu de décisions avec ce régime matrimonial : calcul élargi à tous les régimes.")

    abattements = sorted(d.occupation_abattement_pct for d in occ_comp if d.occupation_abattement_pct is not None)
    durees_occ = [d.occupation_duree_mois for d in occ_comp if d.occupation_duree_mois]
    mois = req.mois_occupation if req.mois_occupation > 0 else (int(statistics.median(durees_occ)) if durees_occ else 12)

    indemnite_fourchette = None
    if not occ_comp:
        notes.append("Aucune décision d'occupation en base : estimation indisponible.")
    elif req.valeur_locative_mensuelle > 0:
        base_total = req.valeur_locative_mensuelle * mois
        abat_p10 = _percentile(abattements, 10)
        abat_p50 = _percentile(abattements, 50)
        abat_p90 = _percentile(abattements, 90)
        indemnite_fourchette = {
            "min": round(base_total * (1 - (abat_p90 or 0) / 100.0)),
            "mediane": round(base_total * (1 - (abat_p50 or 0) / 100.0)),
            "max": round(base_total * (1 - (abat_p10 or 0) / 100.0)),
            "mois": mois,
            "abattement_median_pct": abat_p50,
            "valeur_locative_utilisee": req.valeur_locative_mensuelle,
        }
    else:
        monthly = sorted(d.occupation_montant_mensuel_final for d in occ_comp)
        indemnite_fourchette = {
            "min": round((_percentile(monthly, 25) or 0) * mois),
            "mediane": round((_percentile(monthly, 50) or 0) * mois),
            "max": round((_percentile(monthly, 90) or 0) * mois),
            "mois": mois,
            "abattement_median_pct": _percentile(abattements, 50),
            "valeur_locative_utilisee": None,
        }
    if indemnite_fourchette:
        direction = (
            "Vous pourriez percevoir cette indemnité (votre conjoint occupe seul le bien)."
            if req.occupant == "CONJOINT"
            else "Vous pourriez devoir cette indemnité (vous occupez seul le bien)."
        )
        notes.append(f"Indemnité d'occupation pour {mois} mois d'occupation — {direction}")

    # ------------------------------------------------ 2) Chances de succès des travaux
    chances_travaux = None
    if req.travaux != "NA":
        recs = [r for r in db.query(Recompense).all() if r.statut]
        travaux = [r for r in recs if r.categorie == "TRAVAUX_BIEN_PROPRE"]
        pool = travaux if len(travaux) >= 30 else recs
        if pool is recs:
            notes.append("Statistiques de succès calculées sur toutes les créances entre époux (échantillon travaux trop faible).")

        rates = {}
        for r in pool:
            if not r.preuve_type:
                continue
            bucket = rates.setdefault(r.preuve_type, {"n": 0, "succes": 0})
            bucket["n"] += 1
            bucket["succes"] += 1 if r.statut != "REJETE" else 0
        taux_by_type = {
            t: round(100 * b["succes"] / b["n"], 1) for t, b in rates.items() if b["n"] >= 3
        }
        taux_global = round(100 * sum(r.statut != "REJETE" for r in pool) / len(pool), 1) if pool else None

        user_types = [p for p in dict.fromkeys(req.preuves) if p in PROOF_RANK]
        best = max(user_types, key=lambda t: PROOF_RANK[t], default="AUCUNE")
        best_taux = taux_by_type.get(best, taux_global)
        detail = [
            {
                "preuve_type": t,
                "label": PROOF_LABELS.get(t, t),
                "taux_pct": taux_by_type.get(t, taux_global),
            }
            for t in user_types
        ]
        chances_travaux = {
            "taux_pct": best_taux,
            "preuve_retenue": PROOF_LABELS.get(best, best),
            "taux_global_pct": taux_global,
            "echantillon": len(pool),
            "detail": detail,
        }
        aucune = taux_by_type.get("AUCUNE")
        if aucune is not None and best not in ("FACTURE_NOMINATIVE",):
            notes.append(f"Sans factures nominatives, le taux de succès observé des réclamations chute à {aucune} %.")

    # ------------------------------------------------ 3) Prestation compensatoire
    prestation_compensatoire = None
    pc_pool = [d for d in decisions if d.pc_accordee and d.pc_montant_capital]
    pc_comp = _filter_comparables(pc_pool, "regime_matrimonial", req.regime_matrimonial, 10)
    proches = [d for d in pc_comp if d.duree_mariage_annees is not None and abs(d.duree_mariage_annees - req.duree_mariage_annees) <= 6]
    if len(proches) >= 10:
        pc_comp = proches
    else:
        notes.append("Prestation compensatoire : durée de mariage proche insuffisante, calcul élargi aux décisions similaires.")
    if pc_comp:
        capitals = sorted(d.pc_montant_capital for d in pc_comp)
        prestation_compensatoire = {
            "capital_min": _percentile(capitals, 10),
            "capital_mediane": _percentile(capitals, 50),
            "capital_max": _percentile(capitals, 90),
            "echantillon": len(pc_comp),
        }
        notes.append("Prestation compensatoire : estimation indicative (art. 270-271 du Code civil ; la disparité, l'âge et les besoins comptent davantage).")

    # ------------------------------------------------ 4) Décisions « jumelles »
    def score(d: Decision) -> float:
        s = 0.0
        if d.juridiction == req.juridiction:
            s += 3.0
        if d.regime_matrimonial == req.regime_matrimonial:
            s += 2.0
        if req.mois_occupation > 0 and d.occupation_accordee:
            s += 2.0
        if d.bien_immobilier_principal:
            s += 0.5
        if d.duree_mariage_annees is not None:
            s += max(0.0, 2.0 - abs(d.duree_mariage_annees - req.duree_mariage_annees) / 4.0)
        if req.travaux != "NA" and any(r.statut and r.statut != "REJETE" for r in recs_by_decision.get(d.id, [])):
            s += 1.0
        if d.pc_accordee:
            s += 0.5
        return round(s, 1)

    jumelles = sorted(decisions, key=score, reverse=True)[:5]
    jumelles_out = [
        {
            "id": d.id,
            "juridiction": d.juridiction,
            "date_decision": d.date_decision,
            "regime_matrimonial": d.regime_matrimonial,
            "duree_mariage_annees": d.duree_mariage_annees,
            "score": score(d),
            "occupation_montant_total": d.occupation_montant_total,
            "pc_montant_capital": d.pc_montant_capital,
            "resume_3_lignes": d.resume_3_lignes,
        }
        for d in jumelles
    ]

    notes.append("Rapport statistique indicatif : il ne constitue pas un avis juridique et ne remplace pas votre avocat ou notaire.")

    return {
        "indemnite_fourchette": indemnite_fourchette,
        "indemnite_echantillon": len(occ_comp) if occ_comp else 0,
        "chances_travaux": chances_travaux,
        "prestation_compensatoire": prestation_compensatoire,
        "jumelles": jumelles_out,
        "notes": notes,
    }
