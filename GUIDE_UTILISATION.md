# Guide d'utilisation — JurisDivorce Analytics

*Manuel utilisateur complet — version 4, novembre 2026.*

> **⚠️ Avertissement important** : JurisDivorce Analytics est un outil **statistique indicatif**
> fondé sur la jurisprudence publiée. Il ne constitue **pas un avis juridique** et ne remplace
> ni votre avocat, ni votre notaire. Les fourchettes affichées sont des tendances observées,
> pas des promesses de résultat.

---

## Sommaire

1. [Démarrer l'application](#1-démarrer-lapplication)
2. [L'accueil](#2-laccueil)
3. [Le Cockpit Global — /analytics](#3-le-cockpit-global--analytics)
4. [Le Simulateur « Mon Cas » — /simulateur](#4-le-simulateur-mon-cas--simulateur)
5. [Le Calculateur juridique — /calculateur](#5-le-calculateur-juridique--calculateur)
6. [L'Explorateur de jurisprudence — /decisions](#6-lexplorateur-de-jurisprudence--decisions)
7. [Le Radar des Pièges — /pieges](#7-le-radar-des-pièges--pieges)
8. [Le Moniteur du Pipeline — /pipeline](#8-le-moniteur-du-pipeline--pipeline)
9. [Les exports (CSV, JSON, Word, Markdown, PDF)](#9-les-exports)
10. [Le mode sombre / clair](#10-le-mode-sombre--clair)
11. [Questions fréquentes](#11-questions-fréquentes)

---

## 1. Démarrer l'application

**Option simple (Windows) — double-cliquez sur `start.cmd`** à la racine du projet : il
installe les dépendances si nécessaire, génère les données de démonstration si la base est
vide, ouvre l'API et le site dans deux fenêtres, puis ouvre votre navigateur sur
**http://localhost:3100**. Pour tout arrêter : `stop.cmd` (ou fermez les deux fenêtres).

**Option ligne de commande :**

```bash
# Terminal 1 — l'API (backend)
cd backend
pip install -r requirements.txt
python -m app.seed                   # 1 135 décisions de démonstration
python -m uvicorn app.main:app --port 8000

# Terminal 2 — le site (frontend)
cd frontend
npm install
npm run dev                          # http://localhost:3000
```

Ouvrez **http://localhost:3100** (ou 3000) dans votre navigateur. La documentation technique
de l'API est disponible sur **http://127.0.0.1:8000/docs**.

**Première visite ?** Si la base contient moins de 50 décisions, un bandeau ambre apparaît en
haut de l'écran : cliquez sur **« Charger 50 arrêts de démonstration »** pour que tous les
graphiques se remplissent immédiatement. Un bouton **« Purger les données de démo »** permet
de les retirer en un clic avant l'ingestion de vraies décisions.

---

## 2. L'accueil

La page d'accueil présente :

- Un **hero** avec badge chiffré (ex. « 1 135 décisions de 12 juridictions · 2018 → 2024 »),
  deux boutons d'action (Simuler mon cas / Voir les statistiques) et la mention « statistiques
  indicatives — ne constituent pas un avis juridique ».
- **4 indicateurs nationaux** : nombre de décisions analysées, abattement médian sur
  l'indemnité d'occupation, taux de rejet sans factures nominatives, capital médian de
  prestation compensatoire. Ils sont **pré-remplis dès le chargement** (snapshot intégré au
  HTML) puis rafraîchis en live par l'API.
- Une section **« Comment ça marche ? »** en 3 étapes (décrire sa situation → observer les
  fourchettes constatées → préparer son rendez-vous avec son avocat/notaire).
- **6 cartes d'accès** : Cockpit, Simulateur, Calculateur, Jurisprudence, Pièges, Pipeline.
- Un **bandeau CTA** final renvoyant au simulateur.
- Un **point de santé** dans la barre de navigation (vert = base et disque OK ; infobulle avec
  le détail au survol) et un **pied de page unique** : clause légale (loi du 31/12/1971) +
  source des données en direct (live/snapshot, mention `SYNTHETIQUE_DEMO` uniquement si la
  base contient réellement des décisions de démonstration).

---

## 3. Le Cockpit Global — /analytics

C'est le tableau de bord statistique. **Tout réagit en temps réel aux filtres.**

### Les filtres croisés (bandeau sticky en haut)

Croisez autant de dimensions que vous voulez :

| Filtre | Exemple d'usage |
|---|---|
| Cour d'appel | « Montre-moi uniquement Paris » |
| Année | « Uniquement 2023 » |
| Régime matrimonial | Communauté réduite aux acquêts, Séparation de biens… |
| Contentieux | Liquidation-partage, Divorce contentieux, Indivision hors mariage… |
| Nature de réclamation | Travaux, Recel de communauté, Compte joint vidé… |
| Issue | Accordée / Partiellement accordée / Rejetée |
| Immobilier | Avec ou sans bien immobilier |
| Montant du litige | min / max en euros |
| Recherche plein texte | mots-clés dans les résumés (index FTS) |

Le bouton **Réinitialiser** remet tout à zéro ; les boutons **CSV** et **JSON** exportent
exactement la sélection affichée (voir [§9 Les exports](#9-les-exports)).

### Les 6 indicateurs (KPIs)

Recalculés sur la sélection : arrêts analysés, taux de succès global des réclamations
financières, médiane de prestation compensatoire, abattement moyen sur l'indemnité
d'occupation, montant moyen de l'article 700, taux de rejet sans factures.

### Les 8 graphiques

1. **Comparateur inter-Cours d'appel** — barres = indemnité mensuelle moyenne, courbe =
   abattement moyen. *Lecture utile : « À Lyon, l'abattement médian est plus faible qu'à
   Marseille ».*
2. **Tendances par année** — PC médiane, abattement médian et taux de succès dans le temps.
3. **Distribution des abattements** — combien de décisions à 10-15 %, 15-20 %, 20-25 %…
4. **Succès par nature de réclamation** — montant réclamé vs obtenu + taux d'acceptation.
5. **Corrélation PC** — nuage de points : durée du mariage × écart de revenus vs capital accordé.
6. **Distribution des PC** — capital moyen et médian par tranche de durée de mariage.
7. **Top 5 des motifs de rejet** — les raisons d'échec les plus fréquentes.
8. **Taux de succès selon la preuve** — la facture nominative change tout (vert) ; aucune
   preuve = rejet quasi systématique (rouge).

---

## 4. Le Simulateur « Mon Cas » — /simulateur

**Le parcours en 4 étapes** pour obtenir un rapport prédictif fondé sur les décisions
comparables de la base.

### Étape 1 — Situation
Juridiction (votre cour d'appel régionale), statut matrimonial complet : communauté légale /
réduite aux acquêts (sans contrat ou contrat d'acquêts), **contrat avec clause de partage**
(parts inégales, préciput, attribution intégrale), communauté universelle, participation aux
acquêts, séparation de biens, PACS, concubinage. Le diagnostic ne retient que les décisions
**du même régime** (avec repli tous-régimes si l'échantillon est < 8) ; durée du mariage,
nombre d'enfants.

### Étape 2 — Le bien et l'occupation
Valeur locative mensuelle estimée (une estimation d'agence suffit), durée d'occupation
exclusive en mois, et **qui occupe** (vous ou votre conjoint) — cela détermine si vous
pourriez **recevoir** ou **devoir** l'indemnité.

### Étape 3 — Travaux et blocages
Qui a payé le crédit, qui a financé les travaux, **héritage injecté dans le bien** (optionnel —
déclenche un avertissement sur la clause de remploi), et surtout **les justificatifs que vous
possédez** (factures nominatives, relevés bancaires, attestations, rien).

### Étape 4 — Le rapport prédictif

- **Indemnité d'occupation** : fourchette minimum / médiane / maximum pour votre durée
  d'occupation, avec l'abattement médian observé dans votre cour.
- **Remboursement des travaux** : vos chances de succès en % avec votre meilleure preuve,
  comparées à la moyenne toutes preuves confondues.
- **Prestation compensatoire** : 10ᵉ percentile / médiane / 90ᵉ percentile selon votre durée
  de mariage.
- **Checklist des preuves indispensables** : barres de fréquence issues des dossiers
  **gagnants** comparables (ex. « Factures nominatives — présentes dans 48 % des dossiers gagnants »).
- **Alertes pièges** : les causes d'échec les plus fréquentes des dossiers **perdants**
  (ex. « Dépense relevant de la contribution aux charges du mariage — 19 % des échecs »).
- **5 décisions « jumelles »** : les arrêts les plus proches de votre situation, chacun avec
  un lien vers sa fiche décisionnelle complète.

### Les exports (boutons en haut du rapport)

- **Dire à Notaire (Word)** : un document structuré prêt à remettre — exposé de la situation,
  prétentions chiffrées, références d'arrêts, pièces à annexer. Ouvre dans Microsoft Word.
- **Dossier (Markdown)** : même contenu en texte brut.
- **Imprimer / PDF** : ouvre la boîte d'impression du navigateur → « Enregistrer en PDF ».

---

## 5. Le Calculateur juridique — /calculateur

Deux calculateurs couplant **les formules légales** et **les statistiques réelles de la base**.

### Indemnité d'occupation (art. 815-9 du Code civil)

Saisissez : votre cour d'appel, la valeur locative mensuelle, la **date de début**
(ordonnance de non-conciliation ou assignation), la **date prévue du partage**, et la
**quote-part** revenant aux non-occupants (curseur 0-100 %).

L'outil calcule :

1. Le **montant brut** = valeur locative × mois × quote-part.
2. Le **montant net** après l'**abattement de précarité médian constaté dans votre cour**
   (ex. −19,8 % à Paris).
3. L'**alerte prescription quinquennale** : au-delà de 5 ans d'occupation sans acte
   interruptif (mise en demeure, assignation), seules les 5 dernières années sont
   recouvrables — le montant plafonné s'affiche automatiquement.
4. **Les 10 arrêts les plus proches** de votre cour (abattement et montant comparables).

**Exemple** : 900 €/mois × 71 mois × 50 % = **31 950 € bruts** ; après abattement médian de
19,8 % → **25 624 € nets** ; prescription dépassée de 11 mois → recouvrable plafonné à
environ **20 000 €**.

Les boutons **Dire à Notaire (Word)**, **Markdown** et **Imprimer / PDF** génèrent le dossier
complet (situation, prétentions, 5 références d'arrêts, pièces à annexer).

### Récompense / profit subsistant (art. 1469 du Code civil)

Saisissez : valeur du bien **avant** travaux, valeur **actuelle**, montant des travaux
financés, nature (amélioration ou entretien courant).

L'outil calcule : la **plus-value**, la **dépense faite**, la **récompense plafonnée au
profit subsistant** (art. 1469 III) et affiche les **taux de rejet constatés** dans la base
pour les travaux d'amélioration vs entretien. Des alertes apparaissent si le bien s'est
déprécié (récompense ramenée à zéro) ou pour l'entretien courant (non remboursable).

---

## 6. L'Explorateur de jurisprudence — /decisions

- **Recherche plein texte** (index FTS) : tapez « indemnité », « recel », un numéro RG…
- **Filtres multicritères** identiques à ceux du Cockpit.
- **Cartes de décisions** lisibles d'un coup d'œil : juridiction, date, RG, badges financiers
  (« Demande 130 903 € → Obtenu 0 € », « IO 15 647 € · abattement 20 % », « PC 18 300 € »),
  résumé en 3 lignes.
- **Cliquez sur une carte** : la fiche détaillée s'ouvre en deux colonnes —
  à gauche le **résumé structuré IA** (points forts gagnants, pièges, réclamations détaillées
  avec règle de calcul et preuves déterminantes, conseil pratique), à droite l'**extrait brut
  de l'arrêt**.
- **Pagination** en bas de page ; **Export CSV/JSON** de la sélection dans la barre de filtres.

---

## 7. Le Radar des Pièges — /pieges

La vue consacrée aux **échecs** : le classement des raisons pour lesquelles les demandes
financières sont rejetées.

Pour chaque piège (ex. « Dépense relevant de la contribution aux charges du mariage ») :

- le **% des rejets** qu'il représente (badge rouge/ambre selon la gravité),
- le **montant moyen perdu** par les demandeurs,
- **3 arrêts illustratifs** avec le montant réclamé et un lien vers la fiche complète.

*Usage concret : avant de rédiger votre demande, parcourez cette page — chaque piège vous
dit quel justificatif apporter pour ne pas le rencontrer.*

---

## 8. Le Moniteur du Pipeline — /pipeline

La vue réservée à **l'exploitation** (remplissage de la base avec de vraies décisions).

### Lancer une campagne d'ingestion

```bash
export ZHIPU_API_KEY="votre_clé"
python -m pipeline.ingest run --download --fonds CAPP,CASS --analyze --concurrency 50 --max-chars 16000
```

### Lire le moniteur

- **Badge de statut** (Inactif / En cours / En pause / Arrêté) + boutons
  Pause / Reprise / Stop / **Relancer les échecs**.
- **8 compteurs** : archives traitées, **fichiers XML/JSON lus**, décisions parcourues,
  conservées par le filtre, analysées par GLM, échecs (DLQ), **tokens du jour** (quota Zhipu
  300 M/jour), vitesse en décisions/minute.
- **Table des archives** : statut (Terminée/Erreur), décisions conservées et analysées.
- **Logs en direct** : chaque archive, chaque erreur, chaque ajustement de concurrence.

### Configurer à chaud (sans redémarrer)

Le cadre **« Configuration du worker »** permet de changer la **concurrence max**, le **modèle
GLM** et le **budget de caractères par décision** — appliqués dès la décision suivante
(« Appliquer sans redémarrer »).

### Benchmark

Liste 100 décisions en X ms, agrégats du cockpit en Y ms, taille de la base, vitesse
d'ingestion — utile pour vérifier que tout reste réactif à mesure que la base grossit.

---

## 9. Les exports

| Où | Quoi | Format |
|---|---|---|
| Cockpit & Explorateur (barre de filtres) | La sélection filtrée | **CSV** (Excel FR, `;`) et **JSON** |
| Simulateur — rapport | Dossier de synthèse | **Markdown**, **Word (.doc)**, **PDF (impression)** |
| Calculateur | Dire à Notaire | **Word (.doc)**, **Markdown**, **PDF (impression)** |

---

## 10. Le mode sombre / clair

### Monétisation Freemium

La plateforme fonctionne en modèle freemium :

- **Gratuit** : Cockpit Global, Calculateur, Radar des Pièges, recherche et résumés dans l'Explorateur, aperçu du diagnostic (nombre d'arrêts similaires, niveau de risque).
- **Diagnostic Complet (29 €, 30 jours)** : débloque les fourchettes chiffrées, le compte de gestion détaillé, la checklist des preuves et les 5 arrêts similaires complets.
- **Pack Préparation Avocat (49 €, 30 jours)** : Diagnostic Complet + générateur de dossier exportable (Word/Markdown/PDF) prêt à remettre à votre avocat ou notaire.
- **Pass Exploration (19 € / 7 jours)** : accès illimité aux fiches décisionnelles complètes dans /decisions.

Le paiement est unique (sans abonnement). En mode démo (sans clé Stripe), la page `/checkout/simulation` permet de tester le déblocage en 1 clic.

## 10. Le mode sombre / clair

Le bouton lune/soleil dans la barre de navigation bascule le thème. Le choix suit d'abord les
préférences de votre système, puis mémorise votre sélection. Toute la charte est centralisée
dans `frontend/theme.config.ts` + `app/globals.css` (une seule passe pour la modifier).

---

## 11. Questions fréquentes

**Les données sont-elles de vraies décisions ?**
Au premier lancement, non : ce sont 1 135 décisions de **démonstration** marquées
`SYNTHETIQUE_DEMO`. Après une campagne d'ingestion (voir `/pipeline`), ce sont de **vraies
décisions** Judilibre marquées `JUDILIBRE_OD`. Chaque fiche affiche son badge de source, et le
pied de page indique en direct combien de décisions `SYNTHETIQUE_DEMO` restent en base
(`synth_demo_count` via `/api/health`).

**Le site est-il accessible depuis Internet (tunnel) ?**
Oui : déployé en statique, le frontend appelle l'API en **same-origin** (`/api/…` relatifs) —
aucun souci de CORS derrière le tunnel Cloudflare. En local, `npm run dev` (port 3100) réécrit
automatiquement `/api/*` vers le backend sur le port 8000.

**Pourquoi le filtre conserve-t-il « seulement » 7-8 % des décisions des archives ?**
Les dumps DILA couvrent **toutes les matières** (1995-2026) : le pré-filtre retient ce qui
relève du divorce/liquidation-partage — c'est voulu, pour ne pas brûler de tokens sur des
arrêts hors sujet.

**Pourquoi ma fourchette est-elle « nationale » et non celle de ma cour ?**
Si votre cour compte moins de 8 décisions comparables, l'estimation bascule automatiquement
au plan national (mentionné dans les notes du rapport). Charger plus de décisions de votre
cour augmente la précision.

**Que signifie « montant moyen perdu » sur /pieges ?**
La moyenne des montants **réclamés** par les demandeurs dont la réclamation a été rejetée
pour ce motif — c'est ce que ce piège coûte en moyenne.

**Le simulateur est-il fiable à 100 % ?**
Non — et aucun outil ne l'est. Il donne des **tendances observées** dans la base ; deux
dossiers identiques peuvent avoir des issues différentes selon leur rédaction et leurs
pièces. Utilisez le rapport comme **base de discussion** avec votre avocat ou notaire.

**Comment mettre à jour les données ?**
Relancez la campagne : le manifest `processed_archives` retélécharge uniquement les
**nouveaux dumps** publiés par la DILA (les archives déjà traitées sont ignorées).
