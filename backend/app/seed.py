"""Jeu de données de démonstration : ~1135 décisions synthétiques réalistes (schéma v2).

Toutes les lignes sont marquées source='SYNTHETIQUE_DEMO' pour ne jamais être
confondues avec de vraies décisions JUDILIBRE_OD. Rejouer le script réinitialise
la base (les colonnes v2 du schéma enrichi sont peuplées : type de procédure,
natures de réclamation étendues, montants PC demandés/proposés, écart de revenus,
délai de procédure, conseils pratiques…).

Usage : python -m app.seed   (depuis backend/)
"""
import hashlib
import json
import random
from datetime import date, timedelta

from .database import Base, SessionLocal, ensure_schema, engine
from .models import Decision, Recompense

random.seed(42)

JURIDICTIONS = [
    ("Cour d'appel de Paris", 205), ("Cour d'appel de Versailles", 160),
    ("Cour d'appel de Lyon", 130), ("Cour d'appel d'Aix-en-Provence", 120),
    ("Cour d'appel de Nîmes", 100), ("Cour d'appel de Rennes", 75),
    ("Cour d'appel de Bordeaux", 75), ("Cour d'appel de Lille", 70),
    ("Cour d'appel d'Agen", 60), ("Cour d'appel de Toulouse", 60),
    ("Cour d'appel de Montpellier", 45), ("Cour d'appel de Pau", 35),
]
REGIMES = [
    ("COMMUNAUTE_REDUITE_AUX_ACQUETS", 0.62), ("SEPARATION_DE_BIENS", 0.22),
    ("PARTICIPATION_AUX_ACQUETS", 0.10), ("COMMUNAUTE_UNIVERSELLE", 0.06),
]
REGIME_FR = {
    "COMMUNAUTE_REDUITE_AUX_ACQUETS": "communauté réduite aux acquêts",
    "SEPARATION_DE_BIENS": "séparation de biens",
    "PARTICIPATION_AUX_ACQUETS": "participation aux acquêts",
    "COMMUNAUTE_UNIVERSELLE": "communauté universelle",
}
TYPES_PROCEDURE = [
    ("Liquidation-partage après divorce", 0.60), ("Divorce contentieux", 0.20),
    ("Indivision hors mariage/PACS", 0.10), ("Appel sur ordonnance JAF", 0.10),
]
CHAMBRES = [
    "Pôle 3 Chambre 1", "Pôle 3 Chambre 2", "Pôle 2 Chambre 4",
    "Chambre familiale", "Pôle 3 Chambre 5",
]

# (type de preuve, texte, probabilité de succès de la réclamation)
PREUVES = [
    ("FACTURE_NOMINATIVE", "Factures nominatives au nom de l'époux demandeur, acquittées par chèque personnel", 0.72),
    ("RELEVE_BANCAIRE", "Relevés bancaires personnels montrant les débits correspondants", 0.45),
    ("ATTESTATION", "Attestations d'artisans et duplicatas de paiement", 0.28),
    ("AUCUNE", "Aucun justificatif probant produit aux débats", 0.06),
]
PREUVE_WEIGHTS = [0.40, 0.25, 0.20, 0.15]
PREUVE_LABEL = {
    "FACTURE_NOMINATIVE": "Factures nominatives",
    "RELEVE_BANCAIRE": "Relevés bancaires",
    "ATTESTATION": "Attestations",
    "AUCUNE": None,
}

# (nature, poids, fourchette de montant, règles de calcul plausibles)
NATURES = [
    ("TRAVAUX_BIEN_PROPRE", 0.30, (3_000, 60_000), ["Profit subsistant", "Dépense faite"]),
    ("FINANCEMENT_ACQUISITION", 0.15, (20_000, 150_000), ["Nominalisme", "Profit subsistant"]),
    ("REMBOURSEMENT_EMPRUNT", 0.25, (10_000, 120_000), ["Nominalisme", "Dépense faite"]),
    ("APPORT_FONDS_PROPRES", 0.12, (5_000, 80_000), ["Nominalisme"]),
    ("RECEL_COMMUNAUTE", 0.08, (5_000, 90_000), ["Dépense faite"]),
    ("COMPTE_JOINT_VIDE", 0.05, (1_000, 25_000), ["Nominalisme"]),
    ("TAXES_ASSURANCE", 0.05, (500, 8_000), ["Dépense faite"]),
]
NATURE_FR = {
    "TRAVAUX_BIEN_PROPRE": "Travaux amélioration",
    "FINANCEMENT_ACQUISITION": "Financement bien propre",
    "REMBOURSEMENT_EMPRUNT": "Remboursement emprunt immobilier post-séparation",
    "APPORT_FONDS_PROPRES": "Apport fonds propres / héritage",
    "RECEL_COMMUNAUTE": "Recel de communauté",
    "COMPTE_JOINT_VIDE": "Compte joint vidé",
    "TAXES_ASSURANCE": "Taxes foncières / assurance",
    "AUTRE": "Autre",
}
CAUSES_ECHEC = [
    "Pas de preuve d'origine propre des fonds",
    "Dépense relevant de la contribution aux charges du mariage",
    "Prescription de l'action en récompense",
    "Attestations non contradictoires jugées insuffisantes",
    "Absence de justificatifs produits aux débats",
    "Factures au nom du conjoint : paiement personnel non établi",
    "Relevés bancaires sans corrélation avérée avec les travaux litigieux",
]

PC_CRITERES = [
    "Écart de revenus", "Durée du mariage", "Âge des époux",
    "Perte de chances professionnelles", "État de santé", "Éducation des enfants",
]

POINTS_FORTS = [
    "Factures nominatives acquittées par deniers personnels traçables",
    "Cohérence chronologique entre relevés bancaires et travaux",
    "État liquidatif médian chiffré convergent des deux parties",
    "Occupation exclusive avérée par constat de commissaire de justice",
    "Clause de remploi mentionnée dans l'acte notarié",
    "Valeur locative étayée par estimation d'agence immobilière",
]
PIEGES = [
    "Produire des attestations tardives sans débat contradictoire",
    "Mélanger fonds communs et deniers propres sans traçabilité",
    "Négliger de chiffrer précisément l'indemnité d'occupation",
    "Ignorer la prescription de l'action en récompense",
    "Cumuler des demandes redondantes entre récompenses et créances",
]
CONSEILS = [
    "Constituer un dossier chronologique : chaque facture rapprochée d'un débit bancaire personnel.",
    "Faire établir par le notaire un calcul de récompense opposable dès la convocation.",
    "Chiffrer la valeur locative par une estimation d'agence datée de la séparation.",
    "Réclamer le recel par rapprochements bancaires des mouvements atypiques de l'année du divorce.",
    "Surveiller la prescription : agir dans les cinq ans de la connaissance du fait générateur.",
]


def _wchoice(pairs, weights):
    return random.choices(pairs, weights=weights)[0]


def gen_decision(i: int, jur: str):
    regime = _wchoice([r for r, _ in REGIMES], [w for _, w in REGIMES])
    type_procedure = _wchoice([t for t, _ in TYPES_PROCEDURE], [w for _, w in TYPES_PROCEDURE])
    duree = max(1, int(random.gauss(14, 8)))
    enfants = random.choices([0, 1, 2, 3, 4], weights=[0.28, 0.30, 0.26, 0.10, 0.06])[0]
    age_moyen = round(random.uniform(32, 64))
    d = date(2018, 1, 1) + timedelta(days=random.randint(0, 2500))
    chambre = random.choice(CHAMBRES)
    num_rg = random.randint(1000, 9999)
    delai_mois = random.randint(8, 42)

    immo = random.random() < 0.85
    valeur_bien = round(random.uniform(150_000, 900_000), -3) if immo else None
    vl_base = round(valeur_bien * random.uniform(0.0028, 0.0042), 2) if immo else None
    entreprises = random.random() < 0.18
    epargne = random.random() < 0.65

    occ_demandee = immo and random.random() < 0.55
    occ_accordee = occ_demandee and random.random() < 0.78
    occ_mens_base = occ_abat = occ_mens_final = occ_total = occ_mois = None
    occ_motif = None
    if occ_accordee:
        occ_mens_base = vl_base
        occ_abat = round(min(50.0, max(0.0, random.gauss(20, 9))), 1)
        occ_mens_final = round(vl_base * (1 - occ_abat / 100), 2)
        occ_mois = random.randint(4, 48)
        occ_total = round(occ_mens_final * occ_mois, 2)
        occ_motif = random.choice([
            "Abattement pour précarité de l'occupation",
            "Jouissance gratuite partielle au titre du devoir de secours",
            "Prise en charge de l'entretien et des charges par l'occupant",
        ])

    pc_demandee = random.random() < 0.45
    pc_accordee = pc_demandee and random.random() < 0.68
    pc_forme = pc_capital = pc_rente = pc_rente_mois = None
    pc_demande = pc_propose = pc_ecart = None
    pc_criteres = []
    if pc_demandee:
        pc_demande = round(random.uniform(15_000, 180_000), -2)
        pc_propose = round(pc_demande * random.uniform(0.15, 0.70), -2)
        pc_ecart = round(random.uniform(400, 6500), 2)
        pc_criteres = random.sample(PC_CRITERES, 2)
    if pc_accordee:
        roll = random.random()
        if roll < 0.75:
            pc_forme = "CAPITAL_UNIQUE"
            pc_capital = round(min(180_000, max(8_000, random.uniform(1200, 2600) * duree * random.uniform(0.8, 1.4))), -2)
        elif roll < 0.90:
            pc_forme = "RENTE_MENSUELLE"
            pc_rente = round(random.uniform(700, 1600), 2)
            pc_rente_mois = random.choice([36, 48, 60, 84, 120])
        else:
            pc_forme = "MIXTE"
            pc_capital = round(min(120_000, max(8_000, random.uniform(1000, 1800) * duree)), -2)
            pc_rente = round(random.uniform(500, 900), 2)
            pc_rente_mois = random.choice([24, 36, 48])

    a700 = round(random.uniform(500, 3000), 2) if random.random() < 0.6 else None
    depens = _wchoice(["DESIGNE_EPOUX_A", "DESIGNE_EPOUX_B", "PARTAGE_MOITIE", "REJET"], [0.35, 0.30, 0.30, 0.05])

    # --- Récompenses / créances entre époux (natures étendues)
    n_rec = 0 if random.random() < 0.30 else random.randint(1, 3)
    recompenses = []
    recompenses_json = []
    for _ in range(n_rec):
        nature, _, (lo, hi), regles = _wchoice(NATURES, [n[1] for n in NATURES])
        montant_reclame = round(random.uniform(lo, hi), 2)
        ptype, ptext, pprob = _wchoice(PREUVES, PREUVE_WEIGHTS)
        demandeur = random.choice(["EPOUX_A", "EPOUX_B"])
        if random.random() < pprob:
            if random.random() < 0.55:
                statut, accorde = "ACCORDE_TOTALEMENT", montant_reclame
            else:
                statut = "ACCORDE_PARTIELLEMENT"
                accorde = round(montant_reclame * random.uniform(0.4, 0.8), 2)
            preuve, motif = ptext, None
            regle = random.choice(regles)
            preuves = [l for l in (PREUVE_LABEL[ptype],) if l]
            if ptype != "AUCUNE" and random.random() < 0.3:
                preuves.append("Constats de commissaire de justice")
        else:
            statut, accorde = "REJETE", None
            preuve, preuves = None, []
            motif = random.choice(CAUSES_ECHEC)
            regle = "Rejeté"
        rec = Recompense(
            categorie=nature, demandeur=demandeur, montant_reclame=montant_reclame,
            montant_accorde=accorde, statut=statut, preuve_type=ptype,
            preuve_clef_retenue=preuve, motif_echec=motif,
            regle_calcul=regle, preuves_json=json.dumps(preuves, ensure_ascii=False),
        )
        recompenses.append(rec)
        recompenses_json.append({
            "nature": nature, "demandeur": demandeur,
            "montant_reclame": montant_reclame, "montant_accorde": accorde,
            "statut": statut, "regle_calcul": regle,
            "preuves_determinantes": preuves, "preuve_clef_retenue": preuve,
            "cause_echec": motif,
        })

    # --- Résumés
    pieces = [f"Liquidation du régime matrimonial après {duree} ans de mariage ({REGIME_FR[regime]})."]
    if occ_accordee:
        pieces.append(f"Indemnité d'occupation de {occ_mens_final:.0f} €/mois pendant {occ_mois} mois, avec abattement de {occ_abat:.0f} %.")
    elif occ_demandee:
        pieces.append("Indemnité d'occupation demandée et rejetée.")
    if pc_accordee:
        if pc_forme == "CAPITAL_UNIQUE":
            pieces.append(f"Prestation compensatoire de {pc_capital:.0f} € en capital.")
        elif pc_forme == "RENTE_MENSUELLE":
            pieces.append(f"Prestation compensatoire en rente de {pc_rente:.0f} €/mois pendant {pc_rente_mois} mois.")
        else:
            pieces.append(f"Prestation compensatoire mixte : {pc_capital:.0f} € en capital plus rente de {pc_rente:.0f} €/mois.")
    elif pc_demandee:
        pieces.append("Prestation compensatoire rejetée.")
    n_ok = sum(r.statut != "REJETE" for r in recompenses)
    if n_rec:
        pieces.append(f"{n_ok} récompense(s) ou créance(s) au moins partiellement accordée(s) sur {n_rec}.")
    resume = " ".join(pieces)
    resume_peda = (
        f"Après {duree} ans de mariage, la cour a arbitré le partage : "
        + (f"indemnité d'occupation de {occ_mens_final:.0f} €/mois " if occ_accordee else "")
        + (f"prestation compensatoire de {pc_capital or pc_rente:.0f} € " if pc_accordee else "")
        + (f"{n_ok} demande(s) financière(s) sur {n_rec} retenue(s)." if n_rec else "aucune créance entre époux.")
    ).strip()

    valeur_txt = f"{valeur_bien:.0f}" if valeur_bien is not None else "non estimé"
    raw_text = (
        f"COUR D'APPEL — ARRET DU {d.strftime('%d/%m/%Y')} — N° RG {d.year}/{num_rg}\n\n"
        f"AFFAIRE : ÉPOUX X c/ ÉPOUSE Y — DIVORCE — LIQUIDATION DU RÉGIME MATRIMONIAL — ÉTAT LIQUIDATIF ({type_procedure.upper()}).\n\n"
        "EXPOSÉ DU LITIGE : Les époux, divorcés par jugement définitif, demeurent en désaccord sur la liquidation "
        f"de leur régime matrimonial. Le domicile conjugal, immeuble estimé à {valeur_txt} €, est demeuré "
        "occupé par l'un des époux depuis la résidence séparée. Des travaux ont été réalisés sur le bien pendant "
        "le mariage ; des récompenses et créances entre époux sont sollicitées, ainsi qu'une indemnité d'occupation "
        "et une prestation compensatoire. Le notaire liquidateur propose un état liquidatif contesté sur les "
        "récompenses dues et sur la valorisation de l'indivision post-communautaire.\n\n"
        "MOYENS ET DISCUSSION : Sur l'indemnité d'occupation, la valeur locative est déterminée au vu de "
        "l'estimation produite ; l'abattement réservé tient à l'usage partiel du bien et à l'entretien assumé. "
        "Sur les récompenses, seules les dépenses établies par factures nominatives acquittées par deniers "
        "personnels, ou tracées par relevés bancaires corroborés, ouvrent droit à remboursement ; le profit "
        "subsistant est apprécié au jour du partage. Sur la prestation compensatoire, la Cour apprécie la "
        "disparité créée par la rupture au regard de la durée du mariage, de l'âge et des ressources respectives "
        "des époux, fixée en capital ou convertie en rente viagère ou temporaire.\n\n"
        "PAR CES MOTIFS : Statuant publiquement, contradictoirement et en premier ressort avec voix prépondérante, "
        "la Cour prononce l'état liquidatif annexé au présent arrêt, alloue les sommes visées ci-dessus et "
        "condamne aux dépens selon répartition en tête."
    )

    extracted = {
        "metadata": {
            "juridiction": jur, "chambre": chambre,
            "date_decision": d.isoformat(), "numero_pourvoi_rg": f"{d.year}/{num_rg}",
        },
        "contexte_familial": {
            "type_procedure": type_procedure, "regime_matrimonial": regime,
            "duree_mariage_annees": duree, "nombre_enfants": enfants, "age_epoux_moyen": age_moyen,
        },
        "biens_litigieux": {
            "bien_immobilier_principal": immo, "valeur_bien_principal": valeur_bien,
            "entreprises_societes": entreprises, "comptes_epargne": epargne,
        },
        "indemnite_occupation": {
            "demandee": occ_demandee, "accordee": bool(occ_accordee),
            "valeur_locative_mensuelle_retenue": occ_mens_base,
            "taux_abattement_precarite_pct": occ_abat,
            "montant_mensuel_final": occ_mens_final,
            "duree_mois_retenue": occ_mois,
            "montant_total_accorde": occ_total,
            "motif_refus_ou_modulation": occ_motif,
        },
        "reclamations_financieres": recompenses_json,
        "prestation_compensatoire": {
            "demandee": pc_demandee, "accordee": bool(pc_accordee), "forme": pc_forme,
            "montant_demande_epoux_A": pc_demande, "montant_propose_epoux_B": pc_propose,
            "montant_accorde": pc_capital, "montant_rente_mensuelle": pc_rente,
            "duree_rente_mois": pc_rente_mois, "ecart_revenus_mensuel": pc_ecart,
            "criteres_determinants": pc_criteres,
        },
        "cout_issue": {
            "article_700_accorde": a700, "partie_condamnee_depens": depens,
            "delai_procedure_estime_mois": delai_mois,
        },
        "analyse_strategique": {
            "points_forts_gagnants": random.sample(POINTS_FORTS, 2),
            "pieges_et_erreurs_a_eviter": random.sample(PIEGES, 2),
            "resume_decision_3_lignes": resume,
            "resume_pedagogique_3_lignes": resume_peda,
            "conseil_pratique_extrait": random.choice(CONSEILS),
        },
    }

    dec = Decision(
        id=f"demo-{i:05d}", source="SYNTHETIQUE_DEMO",
        numero_rg=f"{d.year}/{num_rg}", juridiction=jur, chambre=chambre,
        date_decision=d.isoformat(), type_procedure=type_procedure,
        regime_matrimonial=regime, duree_mariage_annees=duree, nombre_enfants=enfants,
        age_epoux_moyen=age_moyen,
        bien_immobilier_principal=immo, valeur_bien_principal=valeur_bien,
        entreprises_societes=entreprises, comptes_epargne=epargne,
        occupation_demandee=occ_demandee, occupation_accordee=occ_accordee,
        occupation_montant_mensuel_base=occ_mens_base, occupation_abattement_pct=occ_abat,
        occupation_montant_mensuel_final=occ_mens_final, occupation_duree_mois=occ_mois,
        occupation_montant_total=occ_total, occupation_motif_modulation=occ_motif,
        pc_demandee=pc_demandee, pc_accordee=pc_accordee, pc_forme=pc_forme,
        pc_montant_capital=pc_capital, pc_montant_demande=pc_demande,
        pc_montant_propose=pc_propose, pc_ecart_revenus_mensuel=pc_ecart,
        pc_criteres_json=json.dumps(pc_criteres, ensure_ascii=False),
        pc_rente_mensuelle=pc_rente, pc_duree_rente_mois=pc_rente_mois,
        article_700_montant=a700, partage_depens=depens,
        delai_procedure_mois=delai_mois,
        resume_3_lignes=resume, resume_pedagogique=resume_peda,
        conseil_pratique=extracted["analyse_strategique"]["conseil_pratique_extrait"],
        raw_text=raw_text,
        extracted_json=json.dumps(extracted, ensure_ascii=False),
        text_md5=hashlib.md5(raw_text.encode("utf-8")).hexdigest(),
    )
    for r in recompenses:
        r.decision = dec
    return dec, recompenses


def main():
    ensure_schema()  # ajoute les colonnes v2 sans perdre les données existantes
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(Recompense).delete()
    db.query(Decision).delete()
    db.commit()

    idx = 0
    for jur, n in JURIDICTIONS:
        for _ in range(n):
            idx += 1
            dec, recs = gen_decision(idx, jur)
            db.add(dec)
            db.add_all(recs)
    db.commit()
    print(f"Seed v2 terminé : {db.query(Decision).count()} décisions, "
          f"{db.query(Recompense).count()} réclamations financières (source=SYNTHETIQUE_DEMO).")


if __name__ == "__main__":
    main()
