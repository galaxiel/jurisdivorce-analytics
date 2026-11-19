# Monétisation & Stratégie — JurisDivorce Analytics

*Document de réflexion business — stratégie de monétisation retenue et implémentée dans le code.*

---

## Partie 1 — Analyse comparative des 3 modèles étudiés

### Modèle 1 : B2C Freemium à déblocage (Paiement unique)

**Cible** : particuliers en instance de divorce ou de liquidation-partage.

**Analyse** : le besoin est **ponctuel** (l'utilisateur traverse une procédure qui dure
12 à 36 mois, il n'a pas besoin d'un abonnement récurrent). Le moment de la conversion
est **l'urgence avant le rendez-vous chez l'avocat ou le notaire**. Le refus de
l'abonnement est majoritaire sur ce segment (étude sectorielle LegalTech : < 5 % des
particuliers acceptent un abonnement mensualisé pour un besoin unique).

**Avantages** : friction minimale (un seul clic de paiement), prix psychologique < 50 €,
pas de gestion de rétention.
**Inconvénients** : revenu par utilisateur faible, nécessite un fort volume de trafic SEO.

**Verdict** : ✅ **Retenu pour le lancement** — segment le plus large, friction minimale.

---

### Modèle 2 : B2B Abonnement Cabinet (JurisDivorce Pro — 59 € HT/mois)

**Cible** : avocats en droit de la famille, notaires, cliquetiers spécialisés.

**Analyse** : les professionnels ont un besoin **récurrent** (plusieurs dossiers par mois),
et valorisent le **comparateur inter-cours** et la **génération de trames de dires en
marque blanche**. Le panier moyen est 10× supérieur au B2C et la rétention est
naturelle (l'abonnement s'arrête quand le cabinet arrête de l'utiliser).

**Avantages** : revenu récurrent prévisible, panier élevé, bouche-à-oreille professionnel.
**Inconvénients** : cycle de vente plus long, exigences de fiabilité et de mise à jour des
données plus élevées, nécessite une authentification par cabinet.

**Verdict** : ⏳ **Reporté au second semestre** — à implémenter après validation du
product-market fit sur le B2C.

---

### Modèle 3 : Apport d'affaires & Partenariats connexes

**Cible** : avocats partenaires (annuaire territorial), courtiers en rachat de soulte,
estimation immobilière.

**Analyse** : l'utilisateur qui a simulé son cas a **un besoin immédiat** d'un professionnel
pour concrétiser. Un annuaire d'avocats partenaires par département (abonnement visibilité
sans partage d'honoraires — interdit par la déontologie) génère un revenu récurrent sans
interférer avec l'indépendance professionnelle. Les partenaires connexes (rachat de
soulte, estimation immobilière) touchent le même segment avec des offres complémentaires.

**Avantages** : revenu récurrent sans effort après mise en place, synergie naturelle.
**Inconvénients** : risque de perte de confiance si les partenaires sont mal choisis,
nécessite une charte de sélection.

**Verdict** : ⏳ **Reporté à maturité** (≥ 10 000 utilisateurs actifs mensuels).

---

## Partie 2 — Stratégie retenue pour le lancement (implémentée dans le code)

### 100 % Gratuit — Acquisition SEO & Confiance

| Page | Contenu | Objectif SEO |
|---|---|---|
| `/analytics` | Cockpit global (8 graphiques, KPIs réactifs aux filtres) | Trafic organique "jurisprudence pension alimentaire" |
| `/calculateur` | 3 calculateurs (occupation 815-9, récompense 1469, balance finale soulte) | "calculer indemnité occupation indivision" |
| `/pieges` | Radar des 10 motifs de rejet | "pourquoi demande récompense rejetée divorce" |
| `/simulateur` étapes 1-4 | Questionnaire complet + aperçu diagnostic global (nombre d'arrêts similaires, niveau de risque) | Tunnel de conversion |
| `/decisions` | Recherche + filtres + titres + résumés 3 lignes | Indexation des juridictions |

### Paywall de déblocage B2C (Paiement unique, sans abonnement)

| Offre | Prix | Contenu débloqué | Durée |
|---|---|---|---|
| **Diagnostic Complet « Mon Cas »** | **29 € TTC** | Fourchettes chiffrées (basse/médiane/haute), détail du compte de gestion des biens, checklist des preuves déterminantes, 5 arrêts similaires complets (Juridiction, Date, N° RG, extraits) | 30 jours |
| **Pack Préparation Avocat / Dire à Notaire** | **49 € TTC** | Diagnostic Complet + générateur de dossier exportable structuré (.pdf / .docx / .md) prêt à remettre à son avocat ou notaire | 30 jours |
| **Pass Exploration Jurisprudence** | **19 € TTC / 7 jours** | Accès illimité à la recherche plein texte, aux fiches détaillées et aux résumés complets dans `/decisions` | 7 jours |

**Inclus mutuellement** : l'offre 49 € inclut les droits de l'offre 29 € et du Pass 19 €.
L'offre 29 € inclut le Pass 19 €.

### Implémentation technique

- État de déblocage : `localStorage` (clé `jd_entitlements`) + synchronisable par token URL
  après redirection Stripe (`/checkout/success?tier=…&session_id=…`).
- Backend : `POST /api/checkout/create-session` — crée une session Stripe Checkout en mode
  `payment` si `STRIPE_SECRET_KEY` est configurée ; sinon, bascule sur la page de simulation
  `/checkout/simulation` (démo 1 clic).
- Floutage : composant `<PaywallOverlay />` — contenu réel rendu sous le flou
  (`blur-md select-none`), carte de déblocage centrée au premier plan.
- Mode test : discret dans `/pipeline`, permet de basculer entre les niveaux d'accès pour
  tester l'expérience utilisateur sans payer.
