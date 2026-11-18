"""Jeu de données de démonstration : ~665 décisions synthétiques réalistes.

Toutes les lignes sont marquées source='SYNTHETIQUE_DEMO' pour ne jamais être
confondues avec de vraies décisions JUDILIBRE_OD. Rejouer le script réinitialise
la base. Les distributions (abattement ~20 %, succès selon la preuve, capital PC
proportionnel à la durée de mariage) calquent les ordres de grandeur usuels afin
que les statistiques du dashboard soient plausibles.

Usage : python -m app.seed   (depuis backend/)
"""
import hashlib
import json
import random
from datetime import date, timedelta

from .database import Base, SessionLocal, engine
from .models import Decision, Recompense

random.seed(42)

JURIDICTIONS = [
    ("Cour d'appel de Paris", 120), ("Cour d'appel de Versailles", 95),
    ("Cour d'appel de Lyon", 75), ("Cour d'appel d'Aix-en-Provence", 70),
    ("Cour d'appel de Marseille", 60), ("Cour d'appel de Rennes", 45),
    ("Cour d'appel de Bordeaux", 45), ("Cour d'appel de Lille", 40),
    ("Cour d'appel de Nantes", 35), ("Cour d'appel de Toulouse", 35),
    ("Cour d'appel de Montpellier", 25), ("Cour d'appel de Pau", 20),
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

MOTIFS_REJET = {
    "FACTURE_NOMINATIVE": [
        "Factures au nom du conjoint : paiement par deniers personnels non établi",
        "Factures sans mention du mode de règlement ni rapprochement bancaire",
    ],
    "RELEVE_BANCAIRE": [
        "Absence de preuve du paiement par deniers propres : fonds communs présumés",
        "Relevés bancaires sans corrélation avérée avec les travaux litigieux",
    ],
    "ATTESTATION": [
        "Attestations non contradictoires jugées insuffisantes",
        "Devis non datés et non chiffrés jugés insuffisants",
    ],
    "AUCUNE": [
        "Absence de justificatifs produits aux débats",
        "Dépenses non justifiées par aucun document",
    ],
}
MOTIFS_NEUTRES = [
    "Dépenses non nécessaires à la conservation du bien",
    "Prescription de l'action en récompense",
    "Dépenses engagées sans accord de l'autre époux",
    "Double comptabilisation avec l'indemnité d'occupation déjà allouée",
    "Montants non chiffrés avec précision aux débats",
]

POINTS_FORTS = [
    "Factures nominatives acquittées par deniers personnels traçables",
    "Cohérence chronologique entre relevés bancaires et travaux",
    "État liquidatif médian chiffré convergent des deux parties",
    "Occupation exclusive avérée par constat de commissaire de justice",
    "Valeur locative étayée par estimation d'agence immobilière",
]
PIEGES = [
    "Produire des attestations tardives sans débat contradictoire",
    "Mélanger fonds communs et deniers propres sans traçabilité",
    "Négliger de chiffrer précisément l'indemnité d'occupation",
    "Ignorer la prescription de l'action en récompense",
    "Cumuler des demandes redondantes entre récompenses et créances",
]


def _wchoice(pairs, weights):
    return random.choices(pairs, weights=weights)[0]


def gen_decision(i: int, jur: str):
    regime = _wchoice([r for r, _ in REGIMES], [w for _, w in REGIMES])
    duree = max(1, int(random.gauss(14, 8)))
    enfants = random.choices([0, 1, 2, 3, 4], weights=[0.28, 0.30, 0.26, 0.10, 0.06])[0]
    d = date(2018, 1, 1) + timedelta(days=random.randint(0, 2500))
    chambre = random.choice(CHAMBRES)
    num_rg = random.randint(1000, 9999)

    immo = random.random() < 0.85
    valeur_bien = round(random.uniform(150_000, 900_000), -3) if immo else None
    vl_base = round(valeur_bien * random.uniform(0.0028, 0.0042), 2) if immo else None
    entreprises = random.random() < 0.18
    epargne = random.random() < 0.65

    occ_demandee = immo and random.random() < 0.55
    occ_accordee = occ_demandee and random.random() < 0.78
    occ_mens_base = occ_abat = occ_mens_final = occ_total = occ_mois = None
    if occ_accordee:
        occ_mens_base = vl_base
        occ_abat = round(min(50.0, max(0.0, random.gauss(20, 9))), 1)
        occ_mens_final = round(vl_base * (1 - occ_abat / 100), 2)
        occ_mois = random.randint(4, 48)
        occ_total = round(occ_mens_final * occ_mois, 2)

    pc_demandee = random.random() < 0.45
    pc_accordee = pc_demandee and random.random() < 0.68
    pc_forme = pc_capital = pc_rente = pc_rente_mois = None
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

    # --- Récompenses / créances entre époux
    n_rec = 0 if random.random() < 0.35 else random.randint(1, 3)
    recompenses = []
    recompenses_json = []
    for _ in range(n_rec):
        cat = _wchoice(
            ["TRAVAUX_BIEN_PROPRE", "REMBOURSEMENT_EMPRUNT", "APPORT_FONDS_PROPRES", "AUTRE"],
            [0.40, 0.30, 0.20, 0.10],
        )
        montant_reclame = round({
            "TRAVAUX_BIEN_PROPRE": random.uniform(3_000, 60_000),
            "REMBOURSEMENT_EMPRUNT": random.uniform(10_000, 120_000),
            "APPORT_FONDS_PROPRES": random.uniform(5_000, 80_000),
            "AUTRE": random.uniform(1_000, 20_000),
        }[cat], 2)
        ptype, ptext, pprob = _wchoice(PREUVES, PREUVE_WEIGHTS)
        demandeur = random.choice(["EPOUX_A", "EPOUX_B"])
        if random.random() < pprob:
            if random.random() < 0.55:
                statut, accorde = "ACCORDE_TOTALEMENT", montant_reclame
            else:
                statut = "ACCORDE_PARTIELLEMENT"
                accorde = round(montant_reclame * random.uniform(0.4, 0.8), 2)
            preuve, motif = ptext, None
        else:
            statut, accorde = "REJETE", None
            preuve = None
            motif = random.choice(MOTIFS_REJET[ptype] + MOTIFS_NEUTRES)
        rec = Recompense(
            categorie=cat, demandeur=demandeur, montant_reclame=montant_reclame,
            montant_accorde=accorde, statut=statut, preuve_type=ptype,
            preuve_clef_retenue=preuve, motif_echec=motif,
        )
        recompenses.append(rec)
        recompenses_json.append({
            "categorie": cat, "demandeur": demandeur,
            "montant_reclame": montant_reclame, "montant_accorde": accorde,
            "statut": statut, "preuve_clef_retenue": preuve, "motif_echec": motif,
        })

    # --- Résumé 3 lignes
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

    valeur_txt = f"{valeur_bien:.0f}" if valeur_bien is not None else "non estimé"
    raw_text = (
        f"COUR D'APPEL — ARRET DU {d.strftime('%d/%m/%Y')} — N° RG {d.year}/{num_rg}\n\n"
        "AFFAIRE : ÉPOUX X c/ ÉPOUSE Y — DIVORCE — LIQUIDATION DU RÉGIME MATRIMONIAL — ÉTAT LIQUIDATIF.\n\n"
        "EXPOSÉ DU LITIGE : Les époux, divorcés par jugement définitif, demeurent en désaccord sur la liquidation "
        f"de leur régime matrimonial. Le domicile conjugal, immeuble estimé à {valeur_txt} €, est demeuré "
        "occupé par l'un des époux depuis la résidence séparée. Des travaux ont été réalisés sur le bien pendant "
        "le mariage ; des récompenses et créances entre époux sont sollicitées, ainsi qu'une indemnité d'occupation "
        "et une prestation compensatoire.\n\n"
        "MOYENS ET DISCUSSION : Sur l'indemnité d'occupation, la valeur locative est déterminée au vu de "
        "l'estimation produite ; l'abattement réservé tient à l'usage partiel du bien et à l'entretien assumé. "
        "Sur les récompenses, seules les dépenses établies par factures nominatives acquittées par deniers "
        "personnels, ou tracées par relevés bancaires corroborés, ouvrent droit à remboursement. Sur la prestation "
        "compensatoire, la Cour apprécie la disparité créée par la rupture au regard de la durée du mariage, de "
        "l'âge et des ressources respectives des époux.\n\n"
        "PAR CES MOTIFS : Statuant publiquement, contradictoirement et en premier ressort avec voix prépondérante, "
        "la Cour prononce l'état liquidatif annexé au présent arrêt, alloue les sommes visées ci-dessus et "
        "condamne aux dépens selon répartition en tête."
    )

    extracted = {
        "metadata": {
            "juridiction": jur, "chambre": chambre,
            "date_decision": d.isoformat(), "numero_pourvoi_rg": f"{d.year}/{num_rg}",
        },
        "contexte_familial": {"regime_matrimonial": regime, "duree_mariage_annees": duree, "nombre_enfants": enfants},
        "biens_litigieux": {
            "bien_immobilier_principal": immo, "valeur_bien_principal": valeur_bien,
            "entreprises_societes": entreprises, "comptes_epargne": epargne,
        },
        "indemnite_occupation": {
            "demandee": occ_demandee, "accordee": bool(occ_accordee),
            "montant_mensuel_base_valeur_locative": occ_mens_base,
            "pourcentage_abattement_accorde": occ_abat,
            "montant_mensuel_final": occ_mens_final,
            "duree_mois_retenue": occ_mois,
            "montant_total_accorde": occ_total,
            "motifs_rejet_ou_reduction": (
                f"Abattement de {occ_abat:.0f} % tenant à l'usage partiel du bien et à l'entretien assumé"
                if occ_accordee and occ_abat else
                ("Indemnité refusée : occupation exclusive non établie" if occ_demandee else None)
            ),
        },
        "recompenses_et_creances": recompenses_json,
        "prestation_compensatoire": {
            "demandee": pc_demandee, "accordee": bool(pc_accordee), "forme": pc_forme,
            "montant_capital_accorde": pc_capital,
            "montant_rente_mensuelle": pc_rente, "duree_rente_mois": pc_rente_mois,
        },
        "frais_et_depens": {"article_700_montant": a700, "partage_depens": depens},
        "analyse_strategique": {
            "points_forts_gagnants": random.sample(POINTS_FORTS, 2),
            "pieges_et_erreurs_a_eviter": random.sample(PIEGES, 2),
            "resume_decision_3_lignes": resume,
        },
    }

    dec = Decision(
        id=f"demo-{i:05d}", source="SYNTHETIQUE_DEMO",
        numero_rg=f"{d.year}/{num_rg}", juridiction=jur, chambre=chambre,
        date_decision=d.isoformat(),
        regime_matrimonial=regime, duree_mariage_annees=duree, nombre_enfants=enfants,
        bien_immobilier_principal=immo, valeur_bien_principal=valeur_bien,
        entreprises_societes=entreprises, comptes_epargne=epargne,
        occupation_demandee=occ_demandee, occupation_accordee=occ_accordee,
        occupation_montant_mensuel_base=occ_mens_base, occupation_abattement_pct=occ_abat,
        occupation_montant_mensuel_final=occ_mens_final, occupation_duree_mois=occ_mois,
        occupation_montant_total=occ_total,
        pc_demandee=pc_demandee, pc_accordee=pc_accordee, pc_forme=pc_forme,
        pc_montant_capital=pc_capital, pc_rente_mensuelle=pc_rente, pc_duree_rente_mois=pc_rente_mois,
        article_700_montant=a700, partage_depens=depens,
        resume_3_lignes=resume, raw_text=raw_text,
        extracted_json=json.dumps(extracted, ensure_ascii=False),
        text_md5=hashlib.md5(raw_text.encode("utf-8")).hexdigest(),
    )
    for r in recompenses:
        r.decision = dec
    return dec, recompenses


def main():
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
    print(f"Seed terminé : {db.query(Decision).count()} décisions, "
          f"{db.query(Recompense).count()} récompenses (source=SYNTHETIQUE_DEMO).")


if __name__ == "__main__":
    main()
