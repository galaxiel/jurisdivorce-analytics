"""Export du bundle statique : lit la base SQLite et génère les JSON de secours du frontend.

Usage : python scripts/export_static_bundle.py [--db backend/jurisprudence.db]

Écrit dans frontend/public/data/ :
  health.json · stats_globales.json · stats_par_cour.json · tendances.json ·
  distribution_pc.json · abattements.json · natures.json · scatter.json ·
  motifs.json · preuves.json · pieges_top10.json · facets.json ·
  calculateur.json · decisions_index.json

Ces fichiers permettent au frontend de fonctionner sans backend (hébergement statique) :
lib/api.ts bascule automatiquement dessus si /api/* ne répond pas.
"""
import argparse
import json
import os
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DEFAULT = os.path.join(ROOT, "backend", "jurisprudence.db")
OUT_DEFAULT = os.path.join(ROOT, "frontend", "public", "data")

PC_BUCKETS = [(0, 5, "0-5 ans"), (5, 10, "5-10 ans"), (10, 15, "10-15 ans"),
              (15, 20, "15-20 ans"), (20, 30, "20-30 ans"), (30, 200, "30 ans et +")]
ABAT_BUCKETS = [(0, 10, "0-10 %"), (10, 15, "10-15 %"), (15, 20, "15-20 %"),
                (20, 25, "20-25 %"), (25, 30, "25-30 %"), (30, 101, "30 % et +")]


def mean(v):
    return round(sum(v) / len(v), 2) if v else None


def median(v):
    return round(statistics.median(v), 2) if v else None


def main(db_path: str, out_dir: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    os.makedirs(out_dir, exist_ok=True)
    files = {}

    decisions = [dict(r) for r in conn.execute("SELECT * FROM decisions")]
    recs = [dict(r) for r in conn.execute("SELECT * FROM recompenses")]
    recs_by_id = defaultdict(list)
    for r in recs:
        recs_by_id[r["decision_id"]].append(r)

    def dump(name, data):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        files[name] = os.path.getsize(path)

    # ── health (snapshot)
    dump("health.json", {"status": "snapshot", "db_ok": True, "disk_free_gb": None,
                         "decisions": len(decisions), "worker_status": "snapshot",
                         "version": "3.0", "source": "snapshot"})

    # ── decisions_index (lite + réclamations, pour filtres/fiche en mode statique)
    index = []
    for d in decisions:
        rs = recs_by_id.get(d["id"], [])
        index.append({
            "id": d["id"], "source": d["source"], "numero_rg": d["numero_rg"],
            "juridiction": d["juridiction"], "date_decision": d["date_decision"],
            "type_procedure": d["type_procedure"], "regime_matrimonial": d["regime_matrimonial"],
            "duree_mariage_annees": d["duree_mariage_annees"],
            "occupation_accordee": d["occupation_accordee"],
            "occupation_montant_total": d["occupation_montant_total"],
            "occupation_abattement_pct": d["occupation_abattement_pct"],
            "pc_accordee": d["pc_accordee"], "pc_montant_capital": d["pc_montant_capital"],
            "nb_recompenses": len(rs),
            "taux_reussite_recompenses": (
                round(100 * sum(r["statut"] != "REJETE" for r in rs if r["statut"]) / len(rs), 1)
                if any(r["statut"] for r in rs) else None),
            "total_demande": round(sum(r["montant_reclame"] or 0 for r in rs), 2) if rs else None,
            "total_accorde": round(sum(r["montant_accorde"] or 0 for r in rs), 2) if rs else None,
            "resume_3_lignes": d["resume_3_lignes"],
            "resume_pedagogique": d["resume_pedagogique"],
            "bien_immobilier_principal": d["bien_immobilier_principal"],
            "valeur_bien_principal": d["valeur_bien_principal"],
            "pc_demandee": d["pc_demandee"], "pc_forme": d["pc_forme"],
            "article_700_montant": d["article_700_montant"],
            "partage_depens": d["partage_depens"],
            "delai_procedure_mois": d["delai_procedure_mois"],
            "conseil_pratique": d["conseil_pratique"],
            "raw_excerpt": (d["raw_text"] or "")[:600],
            "pension_par_enfant": d["pension_par_enfant"],
            "revenus_debiteur_mois": d["revenus_debiteur_mois"],
            "mode_garde": d["mode_garde"],
            "ecart_ressources_totales": d["ecart_ressources_totales"],
            "nom_usage_accorde": d["nom_usage_accorde"],
            "di_accordes": d["di_accordes"],
            "divorce_faute_retenu": d["divorce_faute_retenu"],
            "statut": d["type_procedure"],
            "recompenses": [{
                "id": r["id"], "categorie": r["categorie"], "demandeur": r["demandeur"],
                "montant_reclame": r["montant_reclame"], "montant_accorde": r["montant_accorde"],
                "statut": r["statut"], "preuve_type": r["preuve_type"],
                "preuve_clef_retenue": r["preuve_clef_retenue"], "motif_echec": r["motif_echec"],
                "regle_calcul": r["regle_calcul"],
                "preuves": json.loads(r["preuves_json"] or "[]"),
            } for r in rs],
        })
    dump("decisions_index.json", index)

    # ── stats_globales (KpiOverview)
    occ_dem = [d for d in decisions if d["occupation_demandee"]]
    occ_acc = [d for d in occ_dem if d["occupation_accordee"]]
    abat = [d["occupation_abattement_pct"] for d in occ_acc if d["occupation_abattement_pct"] is not None]
    travaux = [r["montant_accorde"] for r in recs
               if r["categorie"] == "TRAVAUX_BIEN_PROPRE" and r["montant_accorde"] is not None]
    aucune = [r for r in recs if r["preuve_type"] == "AUCUNE" and r["statut"]]
    pc_dem = [d for d in decisions if d["pc_demandee"]]
    pc_acc = [d for d in pc_dem if d["pc_accordee"]]
    capitals = [d["pc_montant_capital"] for d in pc_acc if d["pc_montant_capital"] is not None]
    statutaires = [r for r in recs if r["statut"]]
    a700 = [d["article_700_montant"] for d in decisions if d["article_700_montant"] is not None]
    dates = sorted(d["date_decision"] for d in decisions if d["date_decision"])
    dump("stats_globales.json", {
        "total_decisions": len(decisions),
        "nb_juridictions": len({d["juridiction"] for d in decisions if d["juridiction"]}),
        "periode": f"{dates[0]} → {dates[-1]}" if dates else None,
        "taux_occupation_accordee": round(100 * len(occ_acc) / len(occ_dem), 1) if occ_dem else None,
        "abattement_moyen_pct": mean(abat),
        "montant_moyen_recompense_travaux": mean(travaux),
        "taux_echec_sans_factures_pct": round(100 * sum(r["statut"] == "REJETE" for r in aucune) / len(aucune), 1) if aucune else None,
        "pc_taux_accorde_pct": round(100 * len(pc_acc) / len(pc_dem), 1) if pc_dem else None,
        "pc_capital_moyen": mean(capitals),
        "pc_capital_median": median(capitals),
        "taux_succes_recompenses_pct": round(100 * sum(r["statut"] != "REJETE" for r in statutaires) / len(statutaires), 1) if statutaires else None,
        "article_700_moyen": mean(a700),
        "total_demande": round(sum(r["montant_reclame"] for r in statutaires if r["montant_reclame"])) if statutaires else None,
        "total_accorde": round(sum(r["montant_accorde"] for r in statutaires if r["montant_accorde"])) if statutaires else None,
    })

    # ── comparatif par cour
    groups = defaultdict(list)
    for d in decisions:
        if d["juridiction"]:
            groups[d["juridiction"]].append(d)
    comparatif = []
    for jur, g in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:12]:
        monthly = [d["occupation_montant_mensuel_final"] for d in g
                   if d["occupation_accordee"] and d["occupation_montant_mensuel_final"] is not None]
        ab = [d["occupation_abattement_pct"] for d in g
              if d["occupation_accordee"] and d["occupation_abattement_pct"] is not None]
        od = [d for d in g if d["occupation_demandee"]]
        oa = [d for d in od if d["occupation_accordee"]]
        comparatif.append({
            "juridiction": jur, "nb_decisions": len(g),
            "indemnite_moyenne_mensuelle": mean(monthly),
            "indemnite_mediane_mensuelle": median(monthly),
            "abattement_moyen_pct": mean(ab),
            "taux_acceptation_pct": round(100 * len(oa) / len(od), 1) if od else None,
        })
    dump("stats_par_cour.json", comparatif)

    # ── tendances par année
    by_year = defaultdict(list)
    for d in decisions:
        if d["date_decision"]:
            by_year[d["date_decision"][:4]].append(d)
    tendances = []
    for y in sorted(by_year):
        g = by_year[y]
        gids = {d["id"] for d in g}
        grecs = [r for r in recs if r["decision_id"] in gids and r["statut"]]
        ab = [d["occupation_abattement_pct"] for d in g
              if d["occupation_accordee"] and d["occupation_abattement_pct"] is not None]
        caps = [d["pc_montant_capital"] for d in g
                if d["pc_accordee"] and d["pc_montant_capital"] is not None]
        tendances.append({
            "annee": int(y), "nb_decisions": len(g), "abattement_median_pct": median(ab),
            "pc_mediane": median(caps),
            "taux_succes_pct": round(100 * sum(r["statut"] != "REJETE" for r in grecs) / len(grecs), 1) if grecs else None,
        })
    dump("tendances.json", tendances)

    # ── distributions
    def bucket_rows(pairs, key, valkey, pool):
        rows = []
        for lo, hi, label in pairs:
            grp = [d for d in pool if lo <= (d[key] or 0) < hi]
            vals = [d[valkey] for d in grp if d[valkey] is not None]
            rows.append({"bucket": label, "nb_decisions": len(grp) if valkey == "occupation_abattement_pct" else len(vals),
                         **({"moyenne_indemnite_mensuelle": mean(
                             [d["occupation_montant_mensuel_final"] for d in grp if d["occupation_montant_mensuel_final"] is not None])}
                            if valkey == "occupation_abattement_pct" else
                            {"capital_moyen": mean(vals), "capital_median": median(vals)})})
        return rows
    dump("abattements.json", bucket_rows(ABAT_BUCKETS, "occupation_abattement_pct",
                                         "occupation_abattement_pct",
                                         [d for d in decisions if d["occupation_accordee"]]))
    pc_pool = [d for d in decisions if d["pc_accordee"] and d["pc_montant_capital"] is not None
               and d["duree_mariage_annees"] is not None]
    pc_rows = []
    for lo, hi, label in PC_BUCKETS:
        caps = [d["pc_montant_capital"] for d in pc_pool if lo <= d["duree_mariage_annees"] < hi]
        pc_rows.append({"bucket": label, "nb_decisions": len(caps),
                        "capital_moyen": mean(caps), "capital_median": median(caps)})
    dump("distribution_pc.json", pc_rows)

    # ── succès par nature + par preuve
    natures = defaultdict(list)
    for r in recs:
        if r["statut"] and r["categorie"]:
            natures[r["categorie"]].append(r)
    dump("natures.json", [{
        "nature": n, "nb_reclamations": len(g),
        "taux_succes_pct": round(100 * sum(r["statut"] != "REJETE" for r in g) / len(g), 1),
        "montant_moyen_demande": mean([r["montant_reclame"] for r in g if r["montant_reclame"] is not None]),
        "montant_moyen_accorde": mean([r["montant_accorde"] for r in g if r["montant_accorde"] is not None]),
    } for n, g in sorted(natures.items(), key=lambda kv: -len(kv[1]))])

    preuves = defaultdict(list)
    for r in recs:
        if r["statut"] and r["preuve_type"]:
            preuves[r["preuve_type"]].append(r)
    dump("preuves.json", [{
        "preuve_type": p, "nb_reclamations": len(g),
        "taux_succes_pct": round(100 * sum(r["statut"] != "REJETE" for r in g) / len(g), 1),
        "montant_moyen_accorde": mean([r["montant_accorde"] for r in g if r["montant_accorde"] is not None]),
    } for p, g in sorted(preuves.items(), key=lambda kv: -len(kv[1]))])

    # ── corrélation PC (échantillon 600)
    import random
    scatter_pool = [{"duree_mariage_annees": d["duree_mariage_annees"],
                     "ecart_revenus_mensuel": d["pc_ecart_revenus_mensuel"],
                     "capital_accorde": d["pc_montant_capital"],
                     "juridiction": d["juridiction"]}
                    for d in decisions
                    if d["pc_accordee"] and d["pc_montant_capital"] is not None
                    and d["duree_mariage_annees"] is not None]
    if len(scatter_pool) > 600:
        scatter_pool = random.sample(scatter_pool, 600)
    dump("scatter.json", scatter_pool)

    # ── motifs de rejet (top 5) + pièges (top 10 avec exemples)
    rejetes = [r for r in recs if r["statut"] == "REJETE" and r["motif_echec"]]
    d_by_id = {d["id"]: d for d in decisions}
    counts = Counter(r["motif_echec"].strip(" .") for r in rejetes if r["motif_echec"].strip())
    dump("motifs.json", [{"motif": m, "nb_cas": n} for m, n in counts.most_common(5)])
    def exemples(motif, k=3):
        out = []
        for r in [r for r in rejetes if r["motif_echec"].strip(" .") == motif][:k]:
            d = d_by_id.get(r["decision_id"], {})
            out.append({"id": r["decision_id"], "juridiction": d.get("juridiction"),
                        "date_decision": d.get("date_decision"), "numero_rg": d.get("numero_rg"),
                        "montant_perdu": r["montant_reclame"],
                        "resume": (d.get("resume_3_lignes") or "")[:220]})
        return out
    dump("pieges_top10.json", [{
        "motif": m, "nb_cas": len(g),
        "pct_rejets": round(100 * len(g) / len(rejetes), 1) if rejetes else 0.0,
        "montant_moyen_perdu": mean([r["montant_reclame"] for r in g if r["montant_reclame"] is not None]),
        "exemples": exemples(m),
    } for m, g in sorted(((m, [r for r in rejetes if r["motif_echec"].strip(" .") == m])
                          for m, _ in counts.most_common(10)), key=lambda kv: -len(kv[1]))])

    # ── pension alimentaire (V5)
    pen_pool = [d for d in decisions if d["pension_par_enfant"] is not None]
    by_cour = defaultdict(list)
    by_tranche = defaultdict(list)
    TR = [(0, 1500, "< 1 500 €"), (1500, 2500, "1 500 – 2 500 €"),
          (2500, 3500, "2 500 – 3 500 €"), (3500, 99999, "≥ 3 500 €")]
    for d in pen_pool:
        if d["juridiction"]:
            by_cour[d["juridiction"]].append(d)
        if d["revenus_debiteur_mois"] is not None:
            for lo, hi, label in TR:
                if lo <= d["revenus_debiteur_mois"] < hi:
                    by_tranche[label].append(d)
                    break
    modes = Counter(d["mode_garde"] for d in pen_pool if d["mode_garde"])
    partage = [d for d in pen_pool if d["partage_frais_exceptionnels"] is not None]
    dump("pension.json", {
        "par_cour": [{"cour": c, "pension_mediane": median(
            [d["pension_par_enfant"] for d in g]), "nb": len(g)}
            for c, g in sorted(by_cour.items(), key=lambda kv: -len(kv[1]))[:10]],
        "par_tranche_revenus": [{"tranche": t, "pension_mediane": median(
            [d["pension_par_enfant"] for d in g]), "nb": len(g)}
            for t, g in sorted(by_tranche.items())],
        "pension_mediane_globale": median([d["pension_par_enfant"] for d in pen_pool]),
        "modes_garde": [{"mode": m or "Non précisé", "nb": n} for m, n in modes.most_common()],
        "partage_frais_pct": round(100 * sum(d["partage_frais_exceptionnels"] for d in partage) / len(partage), 1) if partage else None,
    })

    # ── demandes annexes (V5)
    nom_vals = [d for d in decisions if d["nom_usage_accorde"] is not None]
    di_vals = [d for d in decisions if d["di_accordes"] is not None]
    di_acc = [d for d in di_vals if d["di_accordes"] > 0]
    faute_vals = [d for d in decisions if d["divorce_faute_retenu"] is not None]
    a700 = [d["article_700_montant"] for d in decisions if d["article_700_montant"] is not None]
    pc_dem = [d for d in decisions if d["pc_demandee"] and d["ecart_ressources_totales"] is not None]
    PC_B = [(0, 1000, "< 1 000 €"), (1000, 2000, "1 000 – 2 000 €"),
            (2000, 3500, "2 000 – 3 500 €"), (3500, 999999, "≥ 3 500 €")]
    pc_rejet = []
    for lo, hi, label in PC_B:
        g = [d for d in pc_dem if lo <= d["ecart_ressources_totales"] < hi]
        if g:
            pc_rejet.append({"bucket": label, "nb": len(g),
                             "pct_rejet": round(100 * sum(not d["pc_accordee"] for d in g) / len(g), 1)})
    dump("demandes_annexes.json", {
        "items": [
            {"demande": "Conservation du nom d'usage", "nb_demandes": len(nom_vals),
             "taux_accords_pct": round(100 * sum(d["nom_usage_accorde"] for d in nom_vals) / len(nom_vals), 1) if nom_vals else None,
             "montant_moyen": None,
             "note": "Sans accord de l'autre époux ni intérêt professionnel avéré, rejet quasi systématique."},
            {"demande": "Dommages-intérêts (art. 266 / 1240)", "nb_demandes": len(di_vals),
             "taux_accords_pct": round(100 * len(di_acc) / len(di_vals), 1) if di_vals else None,
             "montant_moyen": mean([d["di_accordes"] for d in di_acc]),
             "note": "Préjudice exceptionnel à prouver — accords minoritaires."},
            {"demande": "Divorce pour faute", "nb_demandes": len(faute_vals),
             "taux_accords_pct": round(100 * sum(d["divorce_faute_retenu"] for d in faute_vals) / len(faute_vals), 1) if faute_vals else None,
             "montant_moyen": None,
             "note": "Violation grave ou renouvelée des devoirs matrimoniaux requise."},
            {"demande": "Article 700 CPC (frais d'avocat)", "nb_demandes": len(a700),
             "taux_accords_pct": 100.0 if a700 else None, "montant_moyen": mean(a700),
             "note": "Souvent accordé partiellement."},
        ],
        "pc_rejet_par_ecart": pc_rejet,
    })

    # ── facets
    # ── facets
    dump("facets.json", {
        "juridictions": sorted({d["juridiction"] for d in decisions if d["juridiction"]}),
        "annees": sorted({int(d["date_decision"][:4]) for d in decisions
                          if d["date_decision"] and len(d["date_decision"]) >= 4}, reverse=True),
        "regimes": sorted({d["regime_matrimonial"] for d in decisions if d["regime_matrimonial"]}),
        "types_procedure": sorted({d["type_procedure"] for d in decisions if d["type_procedure"]}),
        "natures": sorted({r["categorie"] for r in recs if r["categorie"]}),
    })

    # ── calculateur : abattement médian par cour + taux de rejet
    calc_cours = []
    for jur, g in groups.items():
        ab = [d["occupation_abattement_pct"] for d in g
              if d["occupation_accordee"] and d["occupation_abattement_pct"] is not None]
        if ab:
            calc_cours.append({"juridiction": jur, "abattement_median": median(ab)})
    dump("calculateur.json", {
        "cours": calc_cours,
        "abattement_median_global": median(abat) if abat else None,
        "taux_rejet_amelioration": round(100 * sum(r["statut"] == "REJETE" for r in recs
                                                   if r["categorie"] == "TRAVAUX_BIEN_PROPRE" and r["statut"])
                                         / max(1, sum(1 for r in recs if r["categorie"] == "TRAVAUX_BIEN_PROPRE" and r["statut"])), 1),
        "taux_rejet_entretien": round(100 * sum(r["statut"] == "REJETE" for r in recs
                                                if r["categorie"] == "TAXES_ASSURANCE" and r["statut"])
                                      / max(1, sum(1 for r in recs if r["categorie"] == "TAXES_ASSURANCE" and r["statut"])), 1),
    })

    conn.close()
    print("Bundle statique écrit dans", out_dir)
    for name, size in sorted(files.items()):
        print(f"  {name:28s} {size / 1024:7.1f} Ko")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("JURISDIVORCE_DB", DB_DEFAULT))
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()
    if not os.path.exists(args.db):
        sys.exit(f"Base introuvable : {args.db} (lancez python -m app.seed dans backend/)")
    main(args.db, args.out)
