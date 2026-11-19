"""Diagnostic « Mon Cas » V5 : multi-situations (mariage/PACS/concubinage), multi-biens,
revenus & charges réels, demandes annexes — calculs couplés aux décisions de la base."""
import statistics
from collections import defaultdict
from datetime import date
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Decision
from ..schemas import SimulateurReport, SimulateurRequest

router = APIRouter(prefix="/api/simulateur", tags=["simulateur"])

BAREME_PENSION = {1: 0.18, 2: 0.155, 3: 0.135, 4: 0.12, 5: 0.105}  # barème de référence indicatif


def _median(v):
    return round(statistics.median(v), 2) if v else None


def _percentile(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 2)


def _months(a: str, b: str) -> int:
    try:
        d1 = date.fromisoformat(a[:10])
        d2 = date.fromisoformat(b[:10])
    except ValueError:
        return 0
    if d2 < d1:
        return 0
    return round((d2 - d1).days / 30.44)


@router.post("/diagnostic", response_model=SimulateurReport)
def diagnostic(req: SimulateurRequest, db: Session = Depends(get_db)):
    notes: List[str] = []
    decisions = db.query(Decision).all()
    decisions = [d for d in decisions if d.juridiction == req.juridiction] or [
        d for d in decisions if d.juridiction
    ]
    if decisions and decisions[0].juridiction != req.juridiction:
        notes.append("Échantillon trop faible pour votre cour : estimations calculées au plan national.")

    # ── Chronologie (art. 262-1 : effets patrimoniaux entre assignation et divorce)
    mois_mariage = _months(req.date_mariage, req.date_separation)
    vie_commune = round(mois_mariage / 12, 1)
    separe_assign = _months(req.date_separation, req.date_assignation)
    chronologie = {
        "date_mariage": req.date_mariage,
        "date_separation": req.date_separation,
        "date_assignation": req.date_assignation,
        "duree_vie_commune_mariage_annees": vie_commune,
        "mois_entre_separation_et_assignation": separe_assign,
        "statut": req.statut,
    }
    if req.statut == "CONCUBINAGE":
        notes.append("Concubinage : pas de prestation compensatoire ni de pension entre concubins ; "
                     "seules les règles de l'indivision (art. 815 et suivants) et les créances de "
                     "type 1240 s'appliquent sur les biens communs de fait.")
    elif req.statut == "PACS":
        notes.append("PACS : pas de prestation compensatoire à la rupture ; le patrimoine se "
                     "partage selon les biens propres de chacun et l'indivision éventuelle.")
    else:
        notes.append("Art. 262-1 du Code civil : les biens acquis après la date d'assignation "
                     "(mais avant le divorce) tombent en indivision pour les mariés sous communauté.")
        notes.append("La vie commune ANTÉRIEURE au mariage n'est pas retenue par les juges pour "
                     "le calcul de la prestation compensatoire.")
    if separe_assign > 18:
        notes.append(f"Procédure longue : {separe_assign} mois entre séparation et assignation — "
                     "les effets patrimoniaux et l'indemnité d'occupation s'en trouvent mécaniquement augmentés.")

    # ── Ressources (prestations sociales intégrées dans l'appréciation globale)
    a_total = round(req.rev_a_net + req.rev_a_compl + req.rev_a_presta, 2)
    b_total = round(req.rev_b_net + req.rev_b_compl + req.rev_b_presta, 2)
    ecart = round(abs(a_total - b_total), 2)
    ressources = {
        "a_total": a_total, "b_total": b_total, "ecart": ecart,
        "a_charges": req.rev_a_charges, "b_charges": req.rev_b_charges,
        "prestations_integrees": bool(req.rev_a_presta or req.rev_b_presta),
        "taux_effort_a": round(100 * req.rev_a_charges / a_total, 1) if a_total else None,
        "taux_effort_b": round(100 * req.rev_b_charges / b_total, 1) if b_total else None,
    }

    # ── Prestation compensatoire (mariés uniquement)
    pc = None
    if req.statut.startswith("MARIAGE"):
        pool = [d for d in decisions if d.pc_accordee and d.pc_montant_capital is not None
                and d.ecart_ressources_totales is not None]
        proches = [d for d in pool if abs(d.ecart_ressources_totales - ecart) <= max(0.6 * ecart, 800)]
        base = proches if len(proches) >= 8 else pool
        caps = [d.pc_montant_capital for d in base]
        taux_accorde = [d for d in decisions if d.pc_demandee]
        pc = {
            "demandee": bool(req.demandes.get("pc")),
            "montant_envisage": req.demandes.get("pcMontant"),
            "ecart_utilisateur": ecart,
            "fourchette": {"min": _percentile(caps, 25), "mediane": _percentile(caps, 50), "max": _percentile(caps, 75)},
            "echantillon": len(base),
            "taux_accordes_pct": round(100 * sum(d.pc_accordee for d in taux_accorde) / len(taux_accorde), 1) if taux_accorde else None,
        }
        notes.append("Prestation compensatoire : l'art. 271 apprécie la disparité au-delà des "
                     "seuls revenus (âge, santé, carrière interrompue). Estimation indicatrice.")
    else:
        notes.append("Pas de prestation compensatoire hors mariage (voir notes chronologie).")

    # ── Pension alimentaire (CEE) — barème de référence + base
    pension = None
    if req.enfants > 0 and req.mode_garde != "na":
        debiteur_net = max(a_total, b_total)
        pourcent = BAREME_PENSION.get(min(req.enfants, 5), 0.095)
        total_bareme = round(debiteur_net * pourcent, 2)
        if req.mode_garde == "alternee":
            total_bareme = round(total_bareme / 2, 2)
        par_cour = defaultdict(list)
        for d in decisions:
            if d.pension_par_enfant is not None and d.juridiction:
                par_cour[d.juridiction].append(d.pension_par_enfant)
        par_tranche = defaultdict(list)
        for d in decisions:
            if d.pension_par_enfant is not None and d.revenus_debiteur_mois:
                t = "< 1 500 €" if d.revenus_debiteur_mois < 1500 else \
                    "1 500 – 2 500 €" if d.revenus_debiteur_mois < 2500 else \
                    "2 500 – 3 500 €" if d.revenus_debiteur_mois < 3500 else "≥ 3 500 €"
                par_tranche[t].append(d.pension_par_enfant)
        all_pen = [d.pension_par_enfant for d in decisions if d.pension_par_enfant is not None]
        pension = {
            "enfants": req.enfants,
            "mode_garde": req.mode_garde,
            "bareme_total_mensuel": total_bareme,
            "bareme_par_enfant": round(total_bareme / req.enfants, 2),
            "par_cour": [{"cour": c, "pension_mediane": _median(v), "nb": len(v)}
                         for c, v in sorted(par_cour.items(), key=lambda kv: -len(kv[1]))[:8]],
            "par_tranche_revenus": [{"tranche": t, "pension_mediane": _median(v), "nb": len(v)}
                                    for t, v in sorted(par_tranche.items())],
            "pension_mediane_globale": _median(all_pen),
            "partage_frais_exceptionnels_moitie": True,
        }
        if req.mode_garde == "alternee":
            notes.append("Garde alternée : le barème indicatif est divisé par deux ; les juges "
                         "ajustent selon les revenus réels de chacun.")
        notes.append("Frais exceptionnels (santé non remboursée, scolarité, activités) : "
                     "partagés par moitié entre les parents, hors pension alimentaire.")

    # ── Bilan patrimonial (multi-biens)
    bilan_biens: List[Dict] = []
    indemnites_total = 0.0
    solde_gestion_total = 0.0
    creances_total = 0.0
    abat_pool = [d.occupation_abattement_pct for d in decisions
                 if d.occupation_accordee and d.occupation_abattement_pct is not None]
    abat_median = _median(abat_pool)
    for b in req.biens:
        if b.type == "occupation":
            abat = (abat_median or 0) / 100
            net = round(b.valeur_locative * b.mois_occupation * (b.quote_part_occupant / 100.0) * (1 - abat), 2)
            indemnites_total += net
            bilan_biens.append({
                "type": "occupation", "description": b.description or "Résidence principale",
                "detail": f"{format_vl(b.valeur_locative)}/mois × {b.mois_occupation} mois — abattement médian {abat_median} %",
                "montant_net": net,
                "beneficiaire": "A" if b.occupant == "B" else "B",
            })
        elif b.type == "locatif":
            solde_mois = b.loyers - b.charges
            solde = round(solde_mois * max(1, b.mois_gestion), 2)
            solde_gestion_total += solde
            bilan_biens.append({
                "type": "locatif", "description": b.description or "Bien locatif indivis",
                "detail": f"{format_vl(b.loyers)} € de loyers − {format_vl(b.charges)} de charges/mois × {b.mois_gestion} mois (géré par {b.gestionnaire})",
                "montant_net": solde,
                "beneficiaire": "indivision" if solde >= 0 else b.gestionnaire,
            })
        elif b.type == "vehicule":
            net = round(max(0.0, b.valeur - b.credit), 2)
            bilan_biens.append({
                "type": "vehicule", "description": b.description or "Véhicule",
                "detail": f"Argus {format_vl(b.valeur)} − crédit {format_vl(b.credit)} ; jouissance pendant la procédure : époux {b.jouissance}",
                "montant_net": net,
                "beneficiaire": "indivision",
            })
        elif b.type == "creance":
            creances_total += b.montant
            bilan_biens.append({
                "type": "creance", "description": b.description or "Créance / récompense",
                "detail": f"Créance au profit de l'époux {b.debiteur}",
                "montant_net": round(b.montant, 2),
                "beneficiaire": b.debiteur,
            })
    bilan = {
        "biens": bilan_biens,
        "indemnites_occupation_total": round(indemnites_total, 2),
        "solde_gestion_total": round(solde_gestion_total, 2),
        "creances_total": round(creances_total, 2),
    }

    # ── Radar des demandes annexes (taux réels de la base)
    def _annexe(vals, acc_fn, label, note_accord, note_rejet, moyen_fn=None):
        if not vals:
            return {"demande": label, "nb": 0, "taux_accords_pct": None,
                    "montant_moyen": None, "note": "Données insuffisantes."}
        acc = sum(1 for d in vals if acc_fn(d))
        taux = round(100 * acc / len(vals), 1)
        moyen = moyen_fn(vals) if moyen_fn else None
        note = note_accord if acc / len(vals) >= 0.5 else note_rejet
        return {"demande": label, "nb": len(vals), "taux_accords_pct": taux,
                "montant_moyen": moyen, "note": note}

    nom_vals = [d for d in decisions if d.nom_usage_accorde is not None]
    di_vals = [d for d in decisions if d.di_accordes is not None]
    faute_vals = [d for d in decisions if d.divorce_faute_retenu is not None]
    a700_vals = [d.article_700_montant for d in decisions if d.article_700_montant is not None]

    radar = [
        _annexe(nom_vals, lambda d: d.nom_usage_accorde, "Conservation du nom d'usage",
                "accord lorsque l'intérêt de l'enfant ou l'origine du nom le justifie",
                "sans accord de l'autre époux ni intérêt avéré, rejet quasi systématique"),
        _annexe(di_vals, lambda d: d.di_accordes > 0, "Dommages-intérêts (art. 266 / 1240)",
                "préjudice exceptionnel caractérisé",
                "accords rares : préjudice exceptionnel à prouver",
                moyen_fn=lambda vs: _median([d.di_accordes for d in vs if d.di_accordes])),
        _annexe(faute_vals, lambda d: d.divorce_faute_retenu, "Divorce pour faute",
                "fautes caractérisées retenues par les juges",
                "rejets fréquents : la faute doit être une violation grave ou renouvelée des devoirs"),
        {
            "demande": "Article 700 CPC (frais d'avocat)", "nb": len(a700_vals),
            "taux_accords_pct": 100.0 if a700_vals else None,
            "montant_moyen": _mean_list(a700_vals),
            "note": "souvent accordé partiellement : le juge module entre les sommes demandées",
        },
    ]

    return SimulateurReport(
        chronologie=chronologie, ressources=ressources, pc=pc, pension=pension,
        bilan=bilan, radar=radar, notes=notes,
    )


def _mean_list(v):
    return round(sum(v) / len(v), 2) if v else None


def format_vl(x):
    return f"{x:,.0f}".replace(",", " ")
