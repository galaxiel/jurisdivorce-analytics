"""Schémas Pydantic v2 (contrats API exposés dans Swagger /docs)."""
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------- Filtres universels
class DecisionFiltersQuery(BaseModel):
    """Filtres croisés partagés par /decisions, /stats/* et /export (via Depends())."""

    model_config = ConfigDict(extra="ignore")

    juridiction: Optional[str] = None
    annee: Optional[int] = None
    regime: Optional[str] = None
    type_procedure: Optional[str] = None
    nature_reclamation: Optional[str] = None
    issue: Optional[str] = None
    has_immo: Optional[bool] = None
    montant_min: Optional[float] = None
    montant_max: Optional[float] = None
    q: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


# ---------------------------------------------------------------- Stats
class KpiOverview(BaseModel):
    total_decisions: int
    nb_juridictions: int
    periode: Optional[str]
    taux_occupation_accordee: Optional[float]
    abattement_moyen_pct: Optional[float]
    montant_moyen_recompense_travaux: Optional[float]
    taux_echec_sans_factures_pct: Optional[float]
    pc_taux_accorde_pct: Optional[float]
    pc_capital_moyen: Optional[float]
    pc_capital_median: Optional[float] = None
    taux_succes_recompenses_pct: Optional[float] = None
    article_700_moyen: Optional[float] = None
    total_demande: Optional[float] = None
    total_accorde: Optional[float] = None


class CourComparatif(BaseModel):
    juridiction: str
    nb_decisions: int
    indemnite_moyenne_mensuelle: Optional[float]
    indemnite_mediane_mensuelle: Optional[float] = None
    abattement_moyen_pct: Optional[float]
    taux_acceptation_pct: Optional[float] = None


class PCDistribution(BaseModel):
    bucket: str
    nb_decisions: int
    capital_moyen: Optional[float]
    capital_median: Optional[float]


class MotifRejet(BaseModel):
    motif: str
    nb_cas: int


class PreuveSucces(BaseModel):
    preuve_type: str
    nb_reclamations: int
    taux_succes_pct: float
    montant_moyen_accorde: Optional[float]


class AbattementBucket(BaseModel):
    bucket: str
    nb_decisions: int
    moyenne_indemnite_mensuelle: Optional[float]


class NatureSucces(BaseModel):
    nature: str
    nb_reclamations: int
    taux_succes_pct: float
    montant_moyen_demande: Optional[float]
    montant_moyen_accorde: Optional[float]


class PCCorrelationPoint(BaseModel):
    duree_mariage_annees: Optional[int]
    ecart_revenus_mensuel: Optional[float]
    capital_accorde: Optional[float]
    juridiction: Optional[str]


class Facets(BaseModel):
    juridictions: List[str]
    annees: List[int]
    regimes: List[str]
    types_procedure: List[str]
    natures: List[str]


# ---------------------------------------------------------------- Décisions
class RecompenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categorie: Optional[str]
    demandeur: Optional[str]
    montant_reclame: Optional[float]
    montant_accorde: Optional[float]
    statut: Optional[str]
    preuve_type: Optional[str]
    preuve_clef_retenue: Optional[str]
    motif_echec: Optional[str]
    regle_calcul: Optional[str] = None
    preuves: List[str] = []


class DecisionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    numero_rg: Optional[str]
    juridiction: Optional[str]
    date_decision: Optional[str]
    type_procedure: Optional[str] = None
    regime_matrimonial: Optional[str]
    duree_mariage_annees: Optional[int]
    occupation_accordee: Optional[bool]
    occupation_montant_total: Optional[float]
    occupation_abattement_pct: Optional[float] = None
    pc_accordee: Optional[bool]
    pc_montant_capital: Optional[float]
    nb_recompenses: int = 0
    taux_reussite_recompenses: Optional[float] = None
    total_demande: Optional[float] = None
    total_accorde: Optional[float] = None
    resume_3_lignes: Optional[str]


class DecisionList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DecisionListItem]


class DecisionDetail(DecisionListItem):
    chambre: Optional[str]
    nombre_enfants: Optional[int]
    age_epoux_moyen: Optional[float] = None
    bien_immobilier_principal: Optional[bool]
    valeur_bien_principal: Optional[float]
    pc_demandee: Optional[bool]
    pc_forme: Optional[str]
    pc_montant_demande: Optional[float] = None
    pc_montant_propose: Optional[float] = None
    pc_ecart_revenus_mensuel: Optional[float] = None
    pc_criteres: List[str] = []
    occupation_motif_modulation: Optional[str] = None
    article_700_montant: Optional[float]
    partage_depens: Optional[str]
    delai_procedure_mois: Optional[int] = None
    recompenses: List[RecompenseOut] = []
    points_forts_gagnants: List[str] = []
    pieges_et_erreurs: List[str] = []
    resume_pedagogique: Optional[str] = None
    conseil_pratique: Optional[str] = None
    raw_excerpt: Optional[str] = None


# ---------------------------------------------------------------- Boussole / Simulateur
class BoussoleRequest(BaseModel):
    juridiction: str
    regime_matrimonial: str
    duree_mariage_annees: int = Field(ge=0, le=70)
    nombre_enfants: int = Field(ge=0, le=12)
    valeur_locative_mensuelle: float = Field(ge=0, le=10000)
    occupant: str = Field(pattern="^(MOI|CONJOINT)$")
    mois_occupation: int = Field(ge=0, le=240)
    paye_credit: str = Field(pattern="^(MOI|CONJOINT|COMMUN|NA)$")
    travaux: str = Field(pattern="^(MOI|CONJOINT|NA)$")
    heritage_injecte: Optional[float] = None
    preuves: List[str] = []


class BoussoleReport(BaseModel):
    indemnite_fourchette: Optional[Dict]
    indemnite_echantillon: int
    chances_travaux: Optional[Dict]
    prestation_compensatoire: Optional[Dict]
    jumelles: List[Dict]
    checklist_preuves: List[Dict] = []
    alertes_pieges: List[Dict] = []
    notes: List[str]


# ---------------------------------------------------------------- Moniteur du pipeline
class PipelineState(BaseModel):
    status: str
    mode: Optional[str]
    current_archive: Optional[str]
    archives_done: int
    archives_total: int
    decisions_scanned: int
    decisions_kept: int
    decisions_analyzed: int
    decisions_failed: int
    tokens_today: int
    queue_size: int
    started_at: Optional[str]
    updated_at: Optional[str]
    vitesse_par_minute: Optional[float] = None


class PipelineLog(BaseModel):
    id: int
    ts: str
    level: str
    message: str


class ArchiveInfo(BaseModel):
    url: str
    fonds: Optional[str]
    size_bytes: Optional[int]
    status: str
    decisions_found: int
    decisions_analyzed: int
    error: Optional[str]
    processed_at: Optional[str]


class PipelineControl(BaseModel):
    action: str = Field(pattern="^(pause|resume|stop)$")
