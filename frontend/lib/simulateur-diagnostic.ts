/* Diagnostic « Mon Cas » côté client : mêmes règles que le backend
   (routers/simulateur.py), exécutées sur le snapshot decisions_index.json
   lorsque l'API n'est pas joignable (mode statique autonome). */
import type { SimFormState, SimBien } from "./simulateur-types";

interface IndexDecision {
  id: string;
  juridiction: string | null;
  date_decision: string | null;
  pc_demandee: boolean | null;
  pc_accordee: boolean | null;
  pc_montant_capital: number | null;
  ecart_ressources_totales: number | null;
  pension_par_enfant: number | null;
  revenus_debiteur_mois: number | null;
  mode_garde: string | null;
  nom_usage_accorde: boolean | null;
  di_accordes: number | null;
  divorce_faute_retenu: boolean | null;
  article_700_montant: number | null;
  occupation_abattement_pct: number | null;
  occupation_accordee: boolean | null;
  occupation_montant_mensuel_final: number | null;
}

export interface SimDiagnostic {
  chronologie: Record<string, unknown>;
  ressources: Record<string, unknown>;
  pc: Record<string, unknown> | null;
  pension: Record<string, unknown> | null;
  bilan: Record<string, unknown>;
  radar: { demande: string; nb: number; taux_accords_pct: number | null; montant_moyen: number | null; note: string }[];
  notes: string[];
  source: "live" | "snapshot";
}

function median(v: number[]): number | null {
  if (!v.length) return null;
  const s = [...v].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return Math.round((s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2) * 100) / 100;
}
function percentile(v: number[], p: number): number | null {
  if (!v.length) return null;
  const s = [...v].sort((a, b) => a - b);
  const k = ((s.length - 1) * p) / 100;
  const f = Math.floor(k);
  const c = Math.min(f + 1, s.length - 1);
  return Math.round((s[f] + (s[c] - s[f]) * (k - f)) * 100) / 100;
}
function months(a: string, b: string): number {
  const d1 = new Date(a);
  const d2 = new Date(b);
  if (Number.isNaN(d1.getTime()) || Number.isNaN(d2.getTime()) || d2 < d1) return 0;
  return Math.round((d2.getTime() - d1.getTime()) / (30.44 * 24 * 3600 * 1000));
}

export function computeDiagnosticLocal(
  form: SimFormState,
  index: IndexDecision[],
): SimDiagnostic {
  const notes: string[] = [];
  const cour = form.juridiction;
  const courPool = index.filter((d) => d.juridiction === cour);
  const pool = courPool.length >= 8 ? courPool : index;
  if (courPool.length < 8) {
    notes.push("Échantillon trop faible pour votre cour : estimations calculées au plan national.");
  }

  // ── Chronologie
  const moisMariage = months(form.date_mariage, form.date_separation);
  const vieCommune = Math.round((moisMariage / 12) * 10) / 10;
  const sepAssign = months(form.date_separation, form.date_assignation);
  const chronologie = {
    date_mariage: form.date_mariage,
    date_separation: form.date_separation,
    date_assignation: form.date_assignation,
    duree_vie_commune_mariage_annees: vieCommune,
    mois_entre_separation_et_assignation: sepAssign,
    statut: form.statut,
  };
  if (form.statut === "CONCUBINAGE") {
    notes.push("Concubinage : pas de prestation compensatoire ni de pension entre concubins ; seules les règles de l'indivision et les créances de type art. 1240 s'appliquent.");
  } else if (form.statut === "PACS") {
    notes.push("PACS : pas de prestation compensatoire à la rupture ; partage selon les biens propres de chacun.");
  } else {
    notes.push("Art. 262-1 du Code civil : les biens acquis après la date d'assignation (mais avant le divorce) tombent en indivision pour les mariés sous communauté.");
    notes.push("La vie commune ANTÉRIEURE au mariage n'est pas retenue par les juges pour le calcul de la prestation compensatoire.");
  }
  if (sepAssign > 18) {
    notes.push(`Procédure longue : ${sepAssign} mois entre séparation et assignation — effets patrimoniaux mécaniquement augmentés.`);
  }

  // ── Ressources
  const aTotal = Math.round((form.rev_a_net + form.rev_a_compl + form.rev_a_presta) * 100) / 100;
  const bTotal = Math.round((form.rev_b_net + form.rev_b_compl + form.rev_b_presta) * 100) / 100;
  const ecart = Math.round(Math.abs(aTotal - bTotal) * 100) / 100;
  const ressources = {
    a_total: aTotal,
    b_total: bTotal,
    ecart,
    a_charges: form.rev_a_charges,
    b_charges: form.rev_b_charges,
    prestations_integrees: Boolean(form.rev_a_presta || form.rev_b_presta),
    taux_effort_a: aTotal ? Math.round((100 * form.rev_a_charges) / aTotal * 10) / 10 : null,
    taux_effort_b: bTotal ? Math.round((100 * form.rev_b_charges) / bTotal * 10) / 10 : null,
  };

  // ── PC (mariés uniquement)
  let pc: Record<string, unknown> | null = null;
  if (form.statut.startsWith("MARIAGE")) {
    const poolPC = pool.filter(
      (d) => d.pc_accordee && d.pc_montant_capital != null && d.ecart_ressources_totales != null,
    );
    const proches = poolPC.filter(
      (d) => Math.abs((d.ecart_ressources_totales ?? 0) - ecart) <= Math.max(ecart * 0.6, 800),
    );
    const base = proches.length >= 8 ? proches : poolPC;
    const caps = base.map((d) => d.pc_montant_capital as number);
    const demandees = pool.filter((d) => d.pc_demandee);
    pc = {
      demandee: form.demandes.pc,
      montant_envisage: form.demandes.pcMontant || null,
      ecart_utilisateur: ecart,
      fourchette: {
        min: percentile(caps, 25),
        mediane: percentile(caps, 50),
        max: percentile(caps, 75),
      },
      echantillon: base.length,
      taux_accordes_pct: demandees.length
        ? Math.round((100 * demandees.filter((d) => d.pc_accordee).length) / demandees.length * 10) / 10
        : null,
    };
    notes.push("Prestation compensatoire : l'art. 271 apprécie la disparité au-delà des seuls revenus (âge, santé, carrière interrompue). Estimation indicatrice.");
  } else {
    notes.push("Pas de prestation compensatoire hors mariage (voir notes chronologie).");
  }

  // ── Pension alimentaire (barème + base)
  let pension: Record<string, unknown> | null = null;
  if (form.enfants > 0 && form.mode_garde !== "na") {
    const debiteurNet = Math.max(aTotal, bTotal);
    const pourcent = form.mode_garde === "alternee"
      ? (BAREME(form.enfants) / 2)
      : BAREME(form.enfants);
    const baremeTotal = Math.round(debiteurNet * pourcent * 100) / 100;
    const parCour: Record<string, number[]> = {};
    const parTranche: Record<string, number[]> = {};
    index.forEach((d) => {
      if (d.pension_par_enfant == null) return;
      if (d.juridiction) (parCour[d.juridiction] ??= []).push(d.pension_par_enfant);
      const r = d.revenus_debiteur_mois ?? 0;
      const t = r < 1500 ? "< 1 500 €" : r < 2500 ? "1 500 – 2 500 €" : r < 3500 ? "2 500 – 3 500 €" : "≥ 3 500 €";
      (parTranche[t] ??= []).push(d.pension_par_enfant);
    });
    const allPen = index.map((d) => d.pension_par_enfant).filter((x): x is number => x != null);
    pension = {
      enfants: form.enfants,
      mode_garde: form.mode_garde,
      bareme_total_mensuel: baremeTotal,
      bareme_par_enfant: Math.round((baremeTotal / form.enfants) * 100) / 100,
      par_cour: Object.entries(parCour)
        .sort((a, b) => b[1].length - a[1].length)
        .slice(0, 8)
        .map(([c, v]) => ({ cour: c, pension_mediane: median(v), nb: v.length })),
      par_tranche_revenus: Object.entries(parTranche)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([t, v]) => ({ tranche: t, pension_mediane: median(v), nb: v.length })),
      pension_mediane_globale: median(allPen),
      partage_frais_exceptionnels_moitie: true,
    };
    if (form.mode_garde === "alternee") {
      notes.push("Garde alternée : le barème indicatif est divisé par deux ; les juges ajustent selon les revenus réels de chacun.");
    }
    notes.push("Frais exceptionnels (santé non remboursée, scolarité, activités) : partagés par moitié entre les parents, hors pension alimentaire.");
  }

  // ── Bilan patrimonial (multi-biens)
  const bilanBiens: Record<string, unknown>[] = [];
  let indemnitesTotal = 0;
  let soldeGestionTotal = 0;
  let creancesTotal = 0;
  const abatPool = pool
    .filter((d) => d.occupation_accordee && d.occupation_abattement_pct != null)
    .map((d) => d.occupation_abattement_pct as number);
  const abatMedian = median(abatPool);
  for (const b of form.biens) {
    if (b.type === "occupation") {
      const abatEff = (abatMedian ?? 0) / 100;
      const net = Math.round(b.valeur_locative * b.mois_occupation * (b.quote_part_occupant / 100) * (1 - abatEff));
      indemnitesTotal += net;
      bilanBiens.push({
        type: "occupation",
        description: b.description || "Résidence principale",
        detail: `${b.valeur_locative}/mois × ${b.mois_occupation} mois — abattement médian ${abatMedian} %`,
        montant_net: net,
        beneficiaire: b.occupant === "B" ? "A" : "B",
      });
    } else if (b.type === "locatif") {
      const solde = Math.round((b.loyers - b.charges) * Math.max(1, b.mois_gestion));
      soldeGestionTotal += solde;
      bilanBiens.push({
        type: "locatif",
        description: b.description || "Bien locatif indivis",
        detail: `${b.loyers} € de loyers − ${b.charges} de charges/mois × ${b.mois_gestion} mois (géré par ${b.gestionnaire})`,
        montant_net: solde,
        beneficiaire: solde >= 0 ? "indivision" : b.gestionnaire,
      });
    } else if (b.type === "vehicule") {
      const net = Math.max(0, b.valeur - b.credit);
      bilanBiens.push({
        type: "vehicule",
        description: b.description || "Véhicule",
        detail: `Argus ${b.valeur} − crédit ${b.credit} ; jouissance : époux ${b.jouissance}`,
        montant_net: net,
        beneficiaire: "indivision",
      });
    } else if (b.type === "creance") {
      creancesTotal += b.montant;
      bilanBiens.push({
        type: "creance",
        description: b.description || "Créance / récompense",
        detail: `Créance au profit de l'époux ${b.debiteur}`,
        montant_net: b.montant,
        beneficiaire: b.debiteur,
      });
    }
  }
  const bilan = {
    biens: bilanBiens,
    indemnites_occupation_total: Math.round(indemnitesTotal),
    solde_gestion_total: Math.round(soldeGestionTotal),
    creances_total: Math.round(creancesTotal),
  };

  // ── Radar demandes annexes
  function annexe(vals: IndexDecision[], acc: (d: IndexDecision) => boolean, label: string, noteAccord: string, noteRejet: string, montant?: (d: IndexDecision) => number | null) {
    if (!vals.length) {
      return { demande: label, nb: 0, taux_accords_pct: null, montant_moyen: null, note: "Données insuffisantes." };
    }
    const nbAcc = vals.filter(acc).length;
    const taux = Math.round((100 * nbAcc) / vals.length * 10) / 10;
    return {
      demande: label,
      nb: vals.length,
      taux_accords_pct: taux,
      montant_moyen: montant ? median(vals.map(montant).filter((x): x is number => x != null)) : null,
      note: nbAcc / vals.length >= 0.5 ? noteAccord : noteRejet,
    };
  }
  const nomVals = index.filter((d) => d.nom_usage_accorde != null);
  const diVals = index.filter((d) => d.di_accordes != null);
  const fauteVals = index.filter((d) => d.divorce_faute_retenu != null);
  const a700Vals = index.map((d) => d.article_700_montant).filter((x): x is number => x != null);
  const radar = [
    annexe(nomVals, (d) => Boolean(d.nom_usage_accorde), "Conservation du nom d'usage",
      "accord lorsque l'intérêt de l'enfant ou l'origine du nom le justifie",
      "sans accord de l'autre époux ni intérêt avéré, rejet quasi systématique"),
    annexe(diVals, (d) => (d.di_accordes ?? 0) > 0, "Dommages-intérêts (art. 266 / 1240)",
      "préjudice exceptionnel caractérisé",
      "accords rares : préjudice exceptionnel à prouver",
      (d) => d.di_accordes),
    annexe(fauteVals, (d) => Boolean(d.divorce_faute_retenu), "Divorce pour faute",
      "fautes caractérisées retenues par les juges",
      "rejets fréquents : la faute doit être une violation grave ou renouvelée des devoirs"),
    {
      demande: "Article 700 CPC (frais d'avocat)",
      nb: a700Vals.length,
      taux_accords_pct: a700Vals.length ? 100 : null,
      montant_moyen: median(a700Vals),
      note: "souvent accordé partiellement : le juge module entre les sommes demandées",
    },
  ];

  return {
    chronologie,
    ressources,
    pc,
    pension,
    bilan,
    radar,
    notes,
    source: "snapshot",
  };
}

function BAREME(enfants: number): number {
  return ({ 1: 0.18, 2: 0.155, 3: 0.135, 4: 0.12, 5: 0.105 } as Record<number, number>)[Math.min(enfants, 5)] ?? 0.095;
}

export type { SimBien };