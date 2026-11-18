"""Classifieur de preuves par mots-clés (dérivé du texte libre produit par le LLM).

Le schéma d'extraction (cahier des charges §3) ne contient pas d'énumération de
type de preuve : `preuve_clef_retenue` et `motif_echec` sont du texte libre. Ce
classifieur heuristique déduit le type pour permettre les statistiques du
Module 1 ("taux d'échec des réclamations sans factures nominatives").
"""
import re
from typing import Optional

_NEGATIVE = re.compile(
    r"absence de (facture|justificatif|preuve)s?"
    r"|sans facture"
    r"|aucun(e)? (justificatif|facture|preuve|pièce)"
    r"|défaut de preuve",
    re.IGNORECASE,
)
_FACTURE = re.compile(r"factures?\b|devis\b", re.IGNORECASE)
_RELEVE = re.compile(r"relev[eé]s?\b|relev[eé]s? bancaires?", re.IGNORECASE)
_ATTESTATION = re.compile(r"attestations?\b", re.IGNORECASE)


def classify_proof(*texts: Optional[str]) -> str:
    """Retourne FACTURE_NOMINATIVE | RELEVE_BANCAIRE | ATTESTATION | AUCUNE | AUTRE."""
    t = " ".join(x for x in texts if x)
    if not t.strip():
        return "AUCUNE"
    if _NEGATIVE.search(t):
        return "AUCUNE"
    if _FACTURE.search(t):
        return "FACTURE_NOMINATIVE"
    if _RELEVE.search(t):
        return "RELEVE_BANCAIRE"
    if _ATTESTATION.search(t):
        return "ATTESTATION"
    return "AUTRE"


PROOF_LABELS = {
    "FACTURE_NOMINATIVE": "Factures nominatives",
    "RELEVE_BANCAIRE": "Relevés bancaires personnels",
    "ATTESTATION": "Attestations d'artisans",
    "AUCUNE": "Aucune preuve",
    "AUTRE": "Autres justificatifs",
}

# Force relative de chaque type de preuve (meilleure preuve retenue pour la Boussole)
PROOF_RANK = {
    "FACTURE_NOMINATIVE": 4,
    "RELEVE_BANCAIRE": 3,
    "ATTESTATION": 2,
    "AUTRE": 1,
    "AUCUNE": 0,
}
