/* Types miroirs de l'API (backend/app/schemas.py) + constantes d'affichage. */

export const REGIME_LABELS: Record<string, string> = {
  COMMUNAUTE_REDUITE_AUX_ACQUETS: "Communauté réduite aux acquêts",
  SEPARATION_DE_BIENS: "Séparation de biens",
  PARTICIPATION_AUX_ACQUETS: "Participation aux acquêts",
  COMMUNAUTE_UNIVERSELLE: "Communauté universelle",
  INCONNU: "Inconnu",
};

export const JURIDICTIONS = [
  "Cour d'appel de Paris",
  "Cour d'appel de Versailles",
  "Cour d'appel de Lyon",
  "Cour d'appel d'Aix-en-Provence",
  "Cour d'appel de Marseille",
  "Cour d'appel de Rennes",
  "Cour d'appel de Bordeaux",
  "Cour d'appel de Lille",
  "Cour d'appel de Nantes",
  "Cour d'appel de Toulouse",
  "Cour d'appel de Montpellier",
  "Cour d'appel de Pau",
];

export const PROOF_OPTIONS = [
  { value: "FACTURE_NOMINATIVE", label: "Factures nominatives" },
  { value: "RELEVE_BANCAIRE", label: "Relevés bancaires personnels" },
  { value: "ATTESTATION", label: "Attestations d'artisans" },
  { value: "AUCUNE", label: "Aucune preuve" },
] as const;

export const PROOF_LABELS: Record<string, string> = Object.fromEntries(
  PROOF_OPTIONS.map((o) => [o.value, o.label]),
);

export const STATUT_LABELS: Record<string, string> = {
  ACCORDE_TOTALEMENT: "Accordée",
  ACCORDE_PARTIELLEMENT: "Partiellement accordée",
  REJETE: "Rejetée",
};

export interface KpiOverview {
  total_decisions: number;
  nb_juridictions: number;
  periode: string | null;
  taux_occupation_accordee: number | null;
  abattement_moyen_pct: number | null;
  montant_moyen_recompense_travaux: number | null;
  taux_echec_sans_factures_pct: number | null;
  pc_taux_accorde_pct: number | null;
  pc_capital_moyen: number | null;
}

export interface CourComparatif {
  juridiction: string;
  nb_decisions: number;
  indemnite_moyenne_mensuelle: number | null;
  abattement_moyen_pct: number | null;
}

export interface PCDistribution {
  bucket: string;
  nb_decisions: number;
  capital_moyen: number | null;
  capital_median: number | null;
}

export interface MotifRejet {
  motif: string;
  nb_cas: number;
}

export interface PreuveSucces {
  preuve_type: string;
  nb_reclamations: number;
  taux_succes_pct: number;
  montant_moyen_accorde: number | null;
}

export interface RecompenseOut {
  id: number;
  categorie: string | null;
  demandeur: string | null;
  montant_reclame: number | null;
  montant_accorde: number | null;
  statut: string | null;
  preuve_type: string | null;
  preuve_clef_retenue: string | null;
  motif_echec: string | null;
}

export interface DecisionListItem {
  id: string;
  source: string;
  numero_rg: string | null;
  juridiction: string | null;
  date_decision: string | null;
  regime_matrimonial: string | null;
  duree_mariage_annees: number | null;
  occupation_accordee: boolean | null;
  occupation_montant_total: number | null;
  pc_accordee: boolean | null;
  pc_montant_capital: number | null;
  nb_recompenses: number;
  taux_reussite_recompenses: number | null;
  resume_3_lignes: string | null;
}

export interface DecisionList {
  total: number;
  page: number;
  page_size: number;
  items: DecisionListItem[];
}

export interface DecisionDetail extends DecisionListItem {
  chambre: string | null;
  nombre_enfants: number | null;
  bien_immobilier_principal: boolean | null;
  valeur_bien_principal: number | null;
  pc_demandee: boolean | null;
  pc_forme: string | null;
  article_700_montant: number | null;
  partage_depens: string | null;
  recompenses: RecompenseOut[];
  points_forts_gagnants: string[];
  pieges_et_erreurs: string[];
  raw_excerpt: string | null;
}

export interface BoussoleRequest {
  juridiction: string;
  regime_matrimonial: string;
  duree_mariage_annees: number;
  nombre_enfants: number;
  valeur_locative_mensuelle: number;
  occupant: "MOI" | "CONJOINT";
  mois_occupation: number;
  paye_credit: "MOI" | "CONJOINT" | "COMMUN" | "NA";
  travaux: "MOI" | "CONJOINT" | "NA";
  preuves: string[];
}

export interface BoussoleFourchette {
  min: number;
  mediane: number;
  max: number;
  mois: number;
  abattement_median_pct: number | null;
  valeur_locative_utilisee: number | null;
}

export interface BoussoleFormState {
  juridiction: string;
  regime_matrimonial: string;
  duree_mariage_annees: number;
  nombre_enfants: number;
  valeur_locative_mensuelle: number;
  occupant: "MOI" | "CONJOINT";
  mois_occupation: number;
  paye_credit: "MOI" | "CONJOINT" | "COMMUN" | "NA";
  travaux: "MOI" | "CONJOINT" | "NA";
  preuves: string[];
}

export interface BoussoleReport {
  indemnite_fourchette: BoussoleFourchette | null;
  indemnite_echantillon: number;
  chances_travaux: {
    taux_pct: number | null;
    preuve_retenue: string;
    taux_global_pct: number | null;
    echantillon: number;
    detail: { preuve_type: string; label: string; taux_pct: number | null }[];
  } | null;
  prestation_compensatoire: {
    capital_min: number | null;
    capital_mediane: number | null;
    capital_max: number | null;
    echantillon: number;
  } | null;
  jumelles: {
    id: string;
    juridiction: string | null;
    date_decision: string | null;
    regime_matrimonial: string | null;
    duree_mariage_annees: number | null;
    score: number;
    occupation_montant_total: number | null;
    pc_montant_capital: number | null;
    resume_3_lignes: string | null;
  }[];
  notes: string[];
}

export interface DecisionFilters {
  juridiction?: string;
  regime?: string;
  statut_recompense?: string;
  presence_pc?: string;
  q?: string;
}
