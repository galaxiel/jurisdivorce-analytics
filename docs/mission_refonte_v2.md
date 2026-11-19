# MISSION : REFONTE MAJEURE & PASSAGE À L'ÉCHELLE DE JURISDIVORCE ANALYTICS

> Archive : deuxième prompt du projet (conversation ZCode du 19/11/2026), conservé à l'identique.
> Résultat : voir `README.md` (v2) et le commit « feat: refonte majeure… ».

---

Tu es un ingénieur Full-Stack Senior, Data Engineer et Architecte UI/UX. 
Ton objectif est d'auditer le dépôt actuel `jurisdivorce-analytics`, d'identifier pourquoi le volume de décisions ingérées est trop faible, et d'implémenter une refonte majeure (Backend d'ingestion massive + Analytics avancés + UI moderne ultra-soignée).

Ne supprime pas ce qui fonctionne : améliore, consolide et étends l'architecture existante.

---

## ÉTAPE 1 : DIAGNOSTIC & DÉBLOCAGE DU VOLUME DE DONNÉES (PRIORITÉ ABSOLUE)

Inspecte d'abord le pipeline d'ingestion actuel et corrige ces 4 goulots d'étranglement pour passer de quelques centaines à **plusieurs dizaines de milliers de décisions analysées** :

1. **Aspiration multi-fonds complète (Open Data DILA / Cour de cassation) :**
   - Configure le scraper/downloader pour récupérer **tous les flux Open Data disponibles** sur `echanges.dila.gouv.fr` / `data.gouv.fr` :
     - **`CAPP` (Cours d'appel)** : Source principale (contient les faits chiffrés détaillés, calculs de notaires, indemnités d'occupation et prestations compensatoires).
     - **`CASS` (Cour de cassation)** : Jurisprudence de principe (1ʳᵉ chambre civile).
     - **`TJ` (Tribunaux judiciaires)** : Uniquement lorsque les motifs ne sont pas intégralement occultés.
   - Ajoute un gestionnaire d'index (`ingestion_manifest.json` ou table SQL `processed_archives`) pour télécharger et parcourir **toutes les archives historiques `.tar.gz` / `.xml` / `.json`**, pas uniquement la dernière archive du mois.

2. **Filtrage Regex large et normalisé (sans faux négatifs) :**
   - Avant d'appeler le LLM, applique un pré-filtre rapide en Python (sur texte normalisé en minuscules et sans accents) qui retient toute décision contenant au moins **2 termes** du champ lexical du divorce/partage ou **1 terme fort** :
     - *Termes forts :* `etat liquidatif`, `liquidation du regime`, `liquidation et partage`, `indivision post-communautaire`, `indemnite d'occupation`, `prestation compensatoire`, `proces-verbal de difficultes`, `recel de communaute`, `creance entre epoux`, `recompense due par`, `recompense due a`.
     - *Termes secondaires (si combinés avec `divorce` ou `epoux`) :* `notaire liquidateur`, `communaute reduite aux acquets`, `separation de biens`, `soulte`, `attribution preferentielle`, `article 270`, `article 1469`, `article 815-9`.
   - **Attention à l'occultation :** Ne rejette JAMAIS une décision simplement parce qu'elle contient `[...]` ou `***` (c'est la pseudonymisation normale des noms). Rejette uniquement si la décision contient explicitement `"motifs de la decision occultes"` ou fait moins de 1 200 caractères.

3. **Worker Asynchrone Haute Cadence optimisé pour Zhipu GLM Flash :**
   - Implémente un worker `asyncio` + `httpx` avec `Semaphore` configurable (ex: `MAX_CONCURRENCY=25` à `50`) pour saturer intelligemment le quota de **300M tokens/jour** sur l'API Zhipu (`GLM-5-Flash` / `GLM-4-Flash`).
   - **Auto-réparation JSON :** Si GLM renvoie un JSON légèrement mal formé ou entouré de balises markdown, applique un parseur tolérant (`json_repair` ou nettoyage regex) avant de rejeter.
   - **Découpage intelligent des longs arrêts :** Si un arrêt dépasse 16 000 tokens, conserve l'en-tête, l'exposé du litige, les motifs sur le partage/finances et le dispositif final plutôt que de tronquer brutalement le début.
   - Ajoute un **tableau de bord d'ingestion en temps réel** dans l'UI (`/ingestion` ou widget live) : nombre d'archives parcourues, décisions filtrées, décisions analysées par GLM, tokens consommés aujourd'hui, vitesse (décisions/min), erreurs et bouton Pause/Reprise.

---

## ÉTAPE 2 : ENRICHISSEMENT DU SCHÉMA D'EXTRACTION JURIDIQUE & FINANCIÈRE

Enrichis le prompt d'extraction GLM et le schéma de base de données (SQLite avec indexation performante ou PostgreSQL) pour extraire des données exploitables statistiquement :

- **Métadonnées & Contexte :**
  - `decision_id`, `date_decision`, `juridiction` (ex: Cour d'appel de Paris, Lyon, Rennes...), `chambre`, `numero_rg`.
  - `type_procedure` : `Divorce contentieux`, `Liquidation-partage après divorce`, `Indivision hors mariage/PACS`, `Appel sur ordonnance JAF`.
  - `regime_matrimonial` : `Communauté réduite aux acquêts`, `Séparation de biens`, `Participation aux acquêts`, `Communauté universelle`, `Indivision simple / PACS`, `Non précisé`.
  - `duree_mariage_annees` (entier ou null), `nombre_enfants` (entier ou null), `age_epoux_moyen` (si mentionné).

- **Volet 1 : Indemnité d'occupation (Indivision)**
  - `indemnite_occupation_demandee` (bool)
  - `valeur_locative_mensuelle_retenue` (€)
  - `taux_abattement_precarite_pct` (ex: 15, 20, 30 %)
  - `montant_mensuel_final` (€)
  - `motif_refus_ou_modulation` (ex: *jouissance gratuite accordée au titre du devoir de secours*, *prescription quinquennale*, *absence de preuve d'occupation exclusive*).

- **Volet 2 : Récompenses, Créances entre époux & Comptes d'administration**
  - Liste structurée `reclamations_financieres` :
    - `nature` : `Financement bien propre`, `Travaux amélioration`, `Remboursement emprunt immobilier post-séparation`, `Apport fonds propres / héritage`, `Recel de communauté`, `Compte joint vidé`, `Taxes foncières / assurance`.
    - `montant_demande` (€)
    - `montant_accorde` (€)
    - `taux_succes_pct` (calculé)
    - `regle_calcul_appliquee` : `Dépense faite`, `Profit subsistant`, `Nominalisme`, `Rejeté`.
    - `preuves_determinantes` (liste : *factures nominatives*, *relevés bancaires*, *acte notarié avec clause de remploi*, *attestations*).
    - `cause_echec` (si rejeté : *pas de preuve d'origine propre des fonds*, *dépense relevant de la contribution aux charges du mariage*, *prescription*).

- **Volet 3 : Prestation Compensatoire**
  - `pc_demandee` (bool), `montant_demande_epoux_A` (€), `montant_propose_epoux_B` (€), `montant_accorde` (€), `forme` (`Capital unique`, `Capital échelonné`, `Rente`, `Attribution bien en propriété`), `ecart_revenus_mensuel` (€), `criteres_determinants` (liste).

- **Volet 4 : Coût et Issue globale du litige**
  - `article_700_accorde` (€) et `partie_condamnee_depens`
  - `delai_procedure_estime_mois`
  - `resume_pedagogique_3_lignes` (vulgarisé pour un non-juriste)
  - `conseil_pratique_extrait` (*"Ce qu'il faut retenir pour un dossier similaire"*).

---

## ÉTAPE 3 : REFONTE DE L'INTERFACE & DES OUTILS STATISTIQUES (UI/UX MODERNE)

Conçois une interface **moderne, épurée, digne d'un produit SaaS FinTech / LegalTech premium** (inspiration Linear / Stripe / Vercel), tout en gardant les composants **strictement modulaires** (Tailwind CSS + composants UI découplés dans `components/ui` et `components/analytics`) afin de pouvoir modifier facilement le thème ou le design ultérieurement.

Implémente ces **5 vues essentielles** :

### 1. Cockpit Global (`/analytics`)
- **KPIs dynamiques** (mis à jour en temps réel selon les filtres actifs) : Nombre d'arrêts analysés, Médiane de prestation compensatoire, Abattement moyen sur indemnité d'occupation, Taux de succès global des demandes de récompense, Montant moyen Article 700.
- **Graphiques interactifs (Recharts ou Tremor) :**
  - Distribution des abattements d'indemnité d'occupation (10 %, 15 %, 20 %, 25 %, 30 %).
  - Comparateur inter-Cours d'appel (ex: Paris vs Lyon vs Aix vs Rennes : montants médians et taux d'acceptation).
  - Taux de succès par type de réclamation financière (ex: *Remboursement crédit* vs *Travaux* vs *Recel de communauté*) avec montant réclamé vs montant réellement obtenu.
  - Corrélation Durée du mariage / Écart de revenus vs Prestation compensatoire accordée (nuage de points).

### 2. Barre de Filtres Croisés Universelle (Sticky / Drawer)
Permets de croiser instantanément **toutes** les dimensions :
- Cour d'appel / Juridiction, Année de décision, Régime matrimonial, Durée du mariage (slider), Type de contentieux, Nature de la réclamation, Issue (Gagné totalement / Partiellement / Rejeté), Présence de bien immobilier, Fourchette de montants.
- Bouton **"Exporter cette sélection (CSV / JSON)"**.

### 3. Simulateur "Mon Cas" (`/simulateur`)
Un parcours guidé en 4 étapes pour un particulier ou un avocat :
1. Situation (Régime matrimonial, durée du mariage, enfants, bien immobilier en indivision ou non).
2. Points de blocage chez le notaire (ex: *J'ai payé le crédit seul depuis 2 ans*, *Mon ex occupe la maison*, *J'ai mis 50 000 € d'héritage dans les travaux*).
3. **Résultat chiffré basé sur les vrais arrêts similaires de la base :**
   - Fourchette basse / médiane / haute observée dans la base pour chaque poste.
   - **Checklist des preuves indispensables** extraites des arrêts gagnants similaires.
   - **Alertes pièges** extraites des arrêts perdants similaires (ex: *"Attention : dans 68 % des cas similaires, les travaux d'embellissement ont été rejetés faute de facture nominative"*).
   - Bouton **"Générer un dossier de synthèse PDF / Markdown imprimable"** pour préparer le rendez-vous chez l'avocat ou le notaire.

### 4. Explorateur de Jurisprudence & Recherche Sémantique/Hybride (`/decisions`)
- Recherche plein texte + filtres multicritères.
- Cartes de décisions ultra-lisibles affichant d'un coup d'œil : Juridiction, Date, Badges financiers (`Demande: 45 000 €` → `Obtenu: 18 500 €`, `Abattement IO: 20 %`), Résumé vulgarisé en 3 lignes, et tiroir latéral (Drawer) pour lire l'analyse JSON complète et le texte intégral surligné.

### 5. Moniteur du Pipeline & Consommation Tokens (`/pipeline`)
- Visualisation de l'avancement du téléchargement des archives Open Data (`CAPP`, `CASS`, `TJ`), file d'attente GLM Flash, logs en direct, et statistiques de tokens consommés.

---

## CONTRAINTES TECHNIQUES & QUALITÉ
- Code propre, typé (TypeScript strict côté front, Pydantic v2 côté FastAPI).
- Prévois un fichier `theme.config.ts` / variables CSS centralisées (`--primary`, `--surface`, `--accent`, mode sombre/clair) pour que toute l'identité visuelle soit modifiable en une seule passe si besoin.
- Mets à jour le `README.md` avec les commandes exactes pour lancer le téléchargement massif des archives `CAPP` + `CASS` et démarrer l'application.

Commence par inspecter l'arborescence actuelle du dépôt, explique brièvement les causes du faible volume trouvé dans le code existant, puis implémente l'ensemble de ces améliorations étape par étape.
