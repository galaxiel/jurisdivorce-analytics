"""Schémas Pydantic (contrats API exposés dans Swagger /docs)."""
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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


class CourComparatif(BaseModel):
    juridiction: str
    nb_decisions: int
    indemnite_moyenne_mensuelle: Optional[float]
    abattement_moyen_pct: Optional[float]


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


class DecisionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    numero_rg: Optional[str]
    juridiction: Optional[str]
    date_decision: Optional[str]
    regime_matrimonial: Optional[str]
    duree_mariage_annees: Optional[int]
    occupation_accordee: Optional[bool]
    occupation_montant_total: Optional[float]
    pc_accordee: Optional[bool]
    pc_montant_capital: Optional[float]
    nb_recompenses: int = 0
    taux_reussite_recompenses: Optional[float] = None
    resume_3_lignes: Optional[str]


class DecisionList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DecisionListItem]


class DecisionDetail(DecisionListItem):
    chambre: Optional[str]
    nombre_enfants: Optional[int]
    bien_immobilier_principal: Optional[bool]
    valeur_bien_principal: Optional[float]
    pc_demandee: Optional[bool]
    pc_forme: Optional[str]
    article_700_montant: Optional[float]
    partage_depens: Optional[str]
    recompenses: List[RecompenseOut] = []
    points_forts_gagnants: List[str] = []
    pieges_et_erreurs: List[str] = []
    raw_excerpt: Optional[str] = None


# ---------------------------------------------------------------- Boussole
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
    preuves: List[str] = []


class BoussoleReport(BaseModel):
    indemnite_fourchette: Optional[Dict]
    indemnite_echantillon: int
    chances_travaux: Optional[Dict]
    prestation_compensatoire: Optional[Dict]
    jumelles: List[Dict]
    notes: List[str]
