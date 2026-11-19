/* Types miroirs de l'API v2 (backend/app/schemas.py) + constantes d'affichage. */

export const REGIME_LABELS: Record<string, string> = {
  COMMUNAUTE_REDUITE_AUX_ACQUETS: "Communauté légale / réduite aux acquêts (contrat d'acquêts inclus)",
  COMMUNAUTE_AVEC_CLAUSE: "Contrat avec clause de partage (parts inégales, préciput, attribution intégrale)",
  SEPARATION_DE_BIENS: "Séparation de biens",
  PARTICIPATION_AUX_ACQUETS: "Participation aux acquêts",
  COMMUNAUTE_UNIVERSELLE: "Communauté universelle",
  INDIVISION: "Indivision simple / PACS",
  INCONNU: "Inconnu",
};

export const TYPE_PROCEDURE_LABELS: Record<string, string> = {
  "Divorce contentieux": "Divorce contentieux",
  "Liquidation-partage après divorce": "Liquidation-partage",
  "Indivision hors mariage/PACS": "Indivision hors mariage",
  "Appel sur ordonnance JAF": "Appel ordonnance JAF",
};

export const NATURE_FR: Record<string, string> = {
  TRAVAUX_BIEN_PROPRE: "Travaux amélioration",
  FINANCEMENT_ACQUISITION: "Financement bien propre",
  REMBOURSEMENT_EMPRUNT: "Remboursement emprunt",
  APPORT_FONDS_PROPRES: "Apport fonds propres / héritage",
  RECEL_COMMUNAUTE: "Recel de communauté",
  COMPTE_JOINT_VIDE: "Compte joint vidé",
  TAXES_ASSURANCE: "Taxes foncières / assurance",
  AUTRE: "Autre",
};

export const REGLE_LABELS: Record<string, string> = {
  "Dépense faite": "Dépense faite",
  "Profit subsistant": "Profit subsistant",
  Nominalisme: "Nominalisme",
  "Rejeté": "Rejeté",
};

/* Les 36 Cours d'appel officielles françaises (Marseille relève d'Aix-en-Provence,
   Nantes de Rennes — ces deux « cours » n'existent pas). */
export const COURS_APPEL_OFFICIELLES = [
  "Cour d'appel d'Aix-en-Provence", "Cour d'appel d'Agen", "Cour d'appel d'Amiens",
  "Cour d'appel d'Angers", "Cour d'appel de Basse-Terre", "Cour d'appel de Bastia",
  "Cour d'appel de Besançon", "Cour d'appel de Bordeaux", "Cour d'appel de Bourges",
  "Cour d'appel de Caen", "Cour d'appel de Cayenne", "Cour d'appel de Chambéry",
  "Cour d'appel de Colmar", "Cour d'appel de Dijon", "Cour d'appel de Douai",
  "Cour d'appel de Fort-de-France", "Cour d'appel de Grenoble", "Cour d'appel de Limoges",
  "Cour d'appel de Lyon", "Cour d'appel de Metz", "Cour d'appel de Montpellier",
  "Cour d'appel de Nancy", "Cour d'appel de Nîmes", "Cour d'appel de Nouméa",
  "Cour d'appel d'Orléans", "Cour d'appel de Papeete", "Cour d'appel de Paris",
  "Cour d'appel de Pau", "Cour d'appel de Poitiers", "Cour d'appel de Reims",
  "Cour d'appel de Rennes", "Cour d'appel de Riom", "Cour d'appel de Rouen",
  "Cour d'appel de Saint-Denis", "Cour d'appel de Toulouse", "Cour d'appel de Versailles",
] as const;

export const JURIDICTIONS: readonly string[] = COURS_APPEL_OFFICIELLES;

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
  pc_capital_median: number | null;
  taux_succes_recompenses_pct: number | null;
  article_700_moyen: number | null;
  total_demande: number | null;
  total_accorde: number | null;
}

export interface CourComparatif {
  juridiction: string;
  nb_decisions: number;
  indemnite_moyenne_mensuelle: number | null;
  indemnite_mediane_mensuelle: number | null;
  abattement_moyen_pct: number | null;
  taux_acceptation_pct: number | null;
}

export interface PCDistribution {
  bucket: string;
  nb_decisions: number;
  capital_moyen: number | null;
  capital_median: number | null;
}

export interface AbattementBucket {
  bucket: string;
  nb_decisions: number;
  moyenne_indemnite_mensuelle: number | null;
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

export interface NatureSucces {
  nature: string;
  nb_reclamations: number;
  taux_succes_pct: number;
  montant_moyen_demande: number | null;
  montant_moyen_accorde: number | null;
}

export interface PCCorrelationPoint {
  duree_mariage_annees: number | null;
  ecart_revenus_mensuel: number | null;
  capital_accorde: number | null;
  juridiction: string | null;
}

export interface Facets {
  juridictions: string[];
  annees: number[];
  regimes: string[];
  types_procedure: string[];
  natures: string[];
}

export interface TendancePoint {
  annee: number;
  nb_decisions: number;
  abattement_median_pct: number | null;
  pc_mediane: number | null;
  taux_succes_pct: number | null;
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
  regle_calcul: string | null;
  preuves: string[];
}

export interface DecisionListItem {
  id: string;
  source: string;
  numero_rg: string | null;
  juridiction: string | null;
  date_decision: string | null;
  type_procedure: string | null;
  regime_matrimonial: string | null;
  duree_mariage_annees: number | null;
  occupation_accordee: boolean | null;
  occupation_montant_total: number | null;
  occupation_abattement_pct: number | null;
  pc_accordee: boolean | null;
  pc_montant_capital: number | null;
  nb_recompenses: number;
  taux_reussite_recompenses: number | null;
  total_demande: number | null;
  total_accorde: number | null;
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
  age_epoux_moyen: number | null;
  bien_immobilier_principal: boolean | null;
  valeur_bien_principal: number | null;
  pc_demandee: boolean | null;
  pc_forme: string | null;
  pc_montant_demande: number | null;
  pc_montant_propose: number | null;
  pc_ecart_revenus_mensuel: number | null;
  pc_criteres: string[];
  occupation_motif_modulation: string | null;
  article_700_montant: number | null;
  partage_depens: string | null;
  delai_procedure_mois: number | null;
  recompenses: RecompenseOut[];
  points_forts_gagnants: string[];
  pieges_et_erreurs: string[];
  resume_pedagogique: string | null;
  conseil_pratique: string | null;
  raw_excerpt: string | null;
}

export interface DecisionFilters {
  juridiction?: string;
  annee?: string;
  regime?: string;
  type_procedure?: string;
  nature_reclamation?: string;
  issue?: string;
  has_immo?: string;
  montant_min?: string;
  montant_max?: string;
  q?: string;
  page?: number;
  page_size?: number;
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
  heritage_injecte?: number;
  preuves: string[];
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
  heritage_injecte: number;
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

export interface ChecklistPreuve {
  preuve: string;
  frequence_pct: number;
}

export interface AlertePiege {
  piege: string;
  frequence_pct: number;
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
  checklist_preuves: ChecklistPreuve[];
  alertes_pieges: AlertePiege[];
  notes: string[];
}

/* ------------------------------------------------ Moniteur du pipeline */
export interface PipelineState {
  status: "idle" | "running" | "paused" | "stopped";
  mode: string | null;
  current_archive: string | null;
  archives_done: number;
  archives_total: number;
  decisions_scanned: number;
  decisions_kept: number;
  decisions_analyzed: number;
  decisions_failed: number;
  files_read: number;
  tokens_today: number;
  queue_size: number;
  started_at: string | null;
  updated_at: string | null;
  vitesse_par_minute: number | null;
}

export interface PipelineConfig {
  max_concurrency: number;
  model: string;
  max_chars: number;
}

export interface Benchmark {
  decisions: number;
  db_list_100_ms: number;
  stats_overview_ms: number;
  db_size_mb: number;
  vitesse_par_minute: number | null;
  tokens_today: number;
}

export interface HealthStatus {
  status: string;
  db_ok: boolean;
  disk_free_gb: number | null;
  decisions: number;
  worker_status: string;
  version: string;
  source?: "live" | "snapshot";
  /** Nb de décisions encore marquées SYNTHETIQUE_DEMO (jeu de démo seed). */
  synth_demo_count?: number;
}

/* ------------------------------------------------ Chantier 2 : métier */
export interface Piege {
  motif: string;
  nb_cas: number;
  pct_rejets: number;
  montant_moyen_perdu: number | null;
  exemples: {
    id: string;
    juridiction: string | null;
    date_decision: string | null;
    numero_rg: string | null;
    montant_perdu: number | null;
    resume: string;
  }[];
}

export interface OccupationCalcResult {
  mois: number;
  montant_brut: number;
  abattement_median_pct: number | null;
  montant_net: number;
  prescription: {
    depassement_mois: number;
    mois_recouvrables: number;
    montant_recuperable: number;
    alerte: boolean;
  };
  comparables: {
    id: string;
    juridiction: string | null;
    date_decision: string | null;
    numero_rg: string | null;
    abattement_pct: number | null;
    montant_mensuel_final: number | null;
    montant_total: number | null;
    duree_mois: number | null;
  }[];
  echantillon: number;
}

export interface RecompenseCalcResult {
  plus_value: number;
  profit_subsistant: number;
  depense_faite: number;
  regle: string;
  taux_rejet_amelioration_pct: number | null;
  taux_rejet_entretien_pct: number | null;
  alertes: string[];
}

export interface PipelineLog {
  id: number;
  ts: string;
  level: string;
  message: string;
}

export interface ArchiveInfo {
  url: string;
  fonds: string | null;
  size_bytes: number | null;
  status: string;
  decisions_found: number;
  decisions_analyzed: number;
  error: string | null;
  processed_at: string | null;
}

export interface PensionCour {
  cour: string;
  pension_mediane: number | null;
  nb: number;
}
export interface PensionTranche {
  tranche: string;
  pension_mediane: number | null;
  nb: number;
}
export interface PensionStats {
  par_cour: PensionCour[];
  par_tranche_revenus: PensionTranche[];
  pension_mediane_globale: number | null;
  modes_garde: { mode: string; nb: number }[];
  partage_frais_pct: number | null;
}
export interface DemandeAnnexeStat {
  demande: string;
  nb_demandes: number;
  taux_accords_pct: number | null;
  montant_moyen: number | null;
  note: string | null;
}
export interface DemandesAnnexesStats {
  items: DemandeAnnexeStat[];
  pc_rejet_par_ecart: { bucket: string; nb: number; pct_rejet: number }[];
}
