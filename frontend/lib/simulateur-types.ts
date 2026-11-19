/* Types & état du Simulateur « Mon Cas » V5 — multi-situations et multi-biens. */

export type SimStatut =
  | "MARIAGE_CRA" | "MARIAGE_SEP" | "MARIAGE_AUTRE"
  | "MARIAGE_CU" | "MARIAGE_PA" | "MARIAGE_CLAUSE"
  | "PACS" | "CONCUBINAGE";

export interface SimBien {
  type: "occupation" | "locatif" | "vehicule" | "creance";
  description: string;
  valeur: number;
  credit: number;
  quote_part_occupant: number;
  occupant: "A" | "B";
  valeur_locative: number;
  mois_occupation: number;
  loyers: number;
  charges: number;
  mois_gestion: number;
  gestionnaire: "A" | "B";
  jouissance: "A" | "B";
  montant: number;
  debiteur: "A" | "B";
}

export interface SimFormState {
  juridiction: string;
  statut: SimStatut;
  date_mariage: string;
  date_separation: string;
  date_assignation: string;
  enfants: number;
  mode_garde: "classique" | "alternee" | "na";
  rev_a_net: number;
  rev_a_compl: number;
  rev_a_presta: number;
  rev_a_charges: number;
  rev_b_net: number;
  rev_b_compl: number;
  rev_b_presta: number;
  rev_b_charges: number;
  biens: SimBien[];
  demandes: {
    pc: boolean;
    pcMontant: number;
    pension: boolean;
    nomUsage: boolean;
    di: boolean;
    faute: boolean;
    art700: boolean;
  };
}

export const STATUT_LABELS: Record<SimStatut, string> = {
  MARIAGE_CRA: "Mariés — communauté légale / réduite aux acquêts (sans contrat ou contrat d'acquêts)",
  MARIAGE_CLAUSE: "Mariés — contrat avec clause de partage (parts inégales, préciput, attribution intégrale)",
  MARIAGE_CU: "Mariés — communauté universelle",
  MARIAGE_PA: "Mariés — participation aux acquêts",
  MARIAGE_SEP: "Mariés — séparation de biens",
  MARIAGE_AUTRE: "Mariés — autre régime (non précisé)",
  PACS: "PACS",
  CONCUBINAGE: "Concubinage (indivision)",
};

/** Code régime (colonne decisions.regime_matrimonial) déduit du statut choisi. */
export function statutToRegime(s: SimStatut): string | null {
  switch (s) {
    case "MARIAGE_CRA": return "COMMUNAUTE_REDUITE_AUX_ACQUETS";
    case "MARIAGE_CLAUSE": return "COMMUNAUTE_AVEC_CLAUSE";
    case "MARIAGE_CU": return "COMMUNAUTE_UNIVERSELLE";
    case "MARIAGE_PA": return "PARTICIPATION_AUX_ACQUETS";
    case "MARIAGE_SEP": return "SEPARATION_DE_BIENS";
    case "PACS": case "CONCUBINAGE": return "INDIVISION";
    default: return null;
  }
}

export const BIEN_TYPE_LABELS: Record<SimBien["type"], string> = {
  occupation: "Résidence occupée par un seul",
  locatif: "Bien locatif / secondaire (indivision)",
  vehicule: "Véhicule commun ou indivis",
  creance: "Créance / récompense / apport",
};

export const MODE_GARDE_LABELS: Record<string, string> = {
  classique: "Résidence classique + DVH (1 week-end sur 2)",
  alternee: "Garde alternée",
  na: "Non applicable",
};

export function newBien(type: SimBien["type"]): SimBien {
  return {
    type,
    description: "",
    valeur: 0,
    credit: 0,
    quote_part_occupant: 50,
    occupant: "A",
    valeur_locative: 0,
    mois_occupation: 0,
    loyers: 0,
    charges: 0,
    mois_gestion: 0,
    gestionnaire: "A",
    jouissance: "A",
    montant: 0,
    debiteur: "A",
  };
}

export function defaultSimForm(juridiction: string): SimFormState {
  return {
    juridiction,
    statut: "MARIAGE_CRA",
    date_mariage: "2014-06-01",
    date_separation: "2024-03-01",
    date_assignation: "2024-06-01",
    enfants: 1,
    mode_garde: "classique",
    rev_a_net: 2200,
    rev_a_compl: 0,
    rev_a_presta: 0,
    rev_a_charges: 800,
    rev_b_net: 1400,
    rev_b_compl: 0,
    rev_b_presta: 0,
    rev_b_charges: 650,
    biens: [],
    demandes: {
      pc: false, pcMontant: 0, pension: false,
      nomUsage: false, di: false, faute: false, art700: true,
    },
  };
}

/* Barème de référence indicatif du Ministère de la Justice (% du revenu net débiteur) */
export const BAREME_PENSION: Record<number, number> = {
  1: 0.18, 2: 0.155, 3: 0.135, 4: 0.12, 5: 0.105,
};
