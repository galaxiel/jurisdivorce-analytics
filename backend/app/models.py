"""Modèles SQLAlchemy : décision aplanie (colonnes requêtables) + JSON brut conservé.

Le JSON extrait par le LLM est dénormalisé en colonnes à l'ingestion pour permettre
les filtres/agrégations SQL ; `extracted_json` conserve la sortie LLM complète.
"""
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, default="JUDILIBRE_OD", index=True)
    numero_rg: Mapped[Optional[str]] = mapped_column(String)
    juridiction: Mapped[Optional[str]] = mapped_column(String, index=True)
    chambre: Mapped[Optional[str]] = mapped_column(String)
    date_decision: Mapped[Optional[str]] = mapped_column(String, index=True)

    # Contexte familial & procédural (schéma enrichi v2)
    type_procedure: Mapped[Optional[str]] = mapped_column(String, index=True)
    regime_matrimonial: Mapped[Optional[str]] = mapped_column(String, index=True)
    duree_mariage_annees: Mapped[Optional[int]] = mapped_column(Integer)
    nombre_enfants: Mapped[Optional[int]] = mapped_column(Integer)
    age_epoux_moyen: Mapped[Optional[float]] = mapped_column(Float)

    # Biens
    bien_immobilier_principal: Mapped[Optional[bool]] = mapped_column(Boolean)
    valeur_bien_principal: Mapped[Optional[float]] = mapped_column(Float)
    entreprises_societes: Mapped[Optional[bool]] = mapped_column(Boolean)
    comptes_epargne: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Indemnité d'occupation
    occupation_demandee: Mapped[Optional[bool]] = mapped_column(Boolean)
    occupation_accordee: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    occupation_montant_mensuel_base: Mapped[Optional[float]] = mapped_column(Float)
    occupation_abattement_pct: Mapped[Optional[float]] = mapped_column(Float)
    occupation_montant_mensuel_final: Mapped[Optional[float]] = mapped_column(Float)
    occupation_duree_mois: Mapped[Optional[int]] = mapped_column(Integer)
    occupation_montant_total: Mapped[Optional[float]] = mapped_column(Float)
    occupation_motif_modulation: Mapped[Optional[str]] = mapped_column(Text)

    # Prestation compensatoire
    pc_demandee: Mapped[Optional[bool]] = mapped_column(Boolean)
    pc_accordee: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    pc_forme: Mapped[Optional[str]] = mapped_column(String)
    pc_montant_capital: Mapped[Optional[float]] = mapped_column(Float)
    pc_montant_demande: Mapped[Optional[float]] = mapped_column(Float)
    pc_montant_propose: Mapped[Optional[float]] = mapped_column(Float)
    pc_ecart_revenus_mensuel: Mapped[Optional[float]] = mapped_column(Float)
    pc_criteres_json: Mapped[Optional[str]] = mapped_column(Text)
    pc_rente_mensuelle: Mapped[Optional[float]] = mapped_column(Float)
    pc_duree_rente_mois: Mapped[Optional[int]] = mapped_column(Integer)

    # Coût & issue globale du litige
    article_700_montant: Mapped[Optional[float]] = mapped_column(Float)
    partage_depens: Mapped[Optional[str]] = mapped_column(String)
    delai_procedure_mois: Mapped[Optional[int]] = mapped_column(Integer)

    # V5 — effets patrimoniaux, gestion locative, pension & demandes annexes
    date_effets_patrimoniaux: Mapped[Optional[str]] = mapped_column(String)
    gestion_loyers_mois: Mapped[Optional[float]] = mapped_column(Float)
    gestion_charges_mois: Mapped[Optional[float]] = mapped_column(Float)
    gestion_solde: Mapped[Optional[float]] = mapped_column(Float)
    pension_par_enfant: Mapped[Optional[float]] = mapped_column(Float)
    revenus_debiteur_mois: Mapped[Optional[float]] = mapped_column(Float)
    mode_garde: Mapped[Optional[str]] = mapped_column(String)
    partage_frais_exceptionnels: Mapped[Optional[bool]] = mapped_column(Boolean)
    prestations_sociales_integrees: Mapped[Optional[bool]] = mapped_column(Boolean)
    ecart_ressources_totales: Mapped[Optional[float]] = mapped_column(Float)
    nom_usage_accorde: Mapped[Optional[bool]] = mapped_column(Boolean)
    nom_usage_motif: Mapped[Optional[str]] = mapped_column(Text)
    di_accordes: Mapped[Optional[float]] = mapped_column(Float)
    divorce_faute_retenu: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Analyse stratégique (aplanie pour filtres/affichage rapides)
    resume_3_lignes: Mapped[Optional[str]] = mapped_column(Text)
    resume_pedagogique: Mapped[Optional[str]] = mapped_column(Text)
    conseil_pratique: Mapped[Optional[str]] = mapped_column(Text)

    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_json: Mapped[Optional[str]] = mapped_column(Text)
    text_md5: Mapped[Optional[str]] = mapped_column(String)
    is_demo: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    recompenses: Mapped[List["Recompense"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )


class Recompense(Base):
    __tablename__ = "recompenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    # Nature de la réclamation financière (enum étendu v2, surcharge l'ancienne « categorie »)
    categorie: Mapped[Optional[str]] = mapped_column(String, index=True)
    demandeur: Mapped[Optional[str]] = mapped_column(String)
    montant_reclame: Mapped[Optional[float]] = mapped_column(Float)
    montant_accorde: Mapped[Optional[float]] = mapped_column(Float)
    statut: Mapped[Optional[str]] = mapped_column(String, index=True)
    # Type de preuve dérivé du texte par classifieur mots-clés (voir services/classify.py)
    preuve_type: Mapped[Optional[str]] = mapped_column(String, index=True)
    preuve_clef_retenue: Mapped[Optional[str]] = mapped_column(Text)
    motif_echec: Mapped[Optional[str]] = mapped_column(Text)
    # Enrichissements v2
    regle_calcul: Mapped[Optional[str]] = mapped_column(String)
    preuves_json: Mapped[Optional[str]] = mapped_column(Text)

    decision: Mapped["Decision"] = relationship(back_populates="recompenses")

