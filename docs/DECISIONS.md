# Journal des décisions techniques — pourquoi c'est construit comme ça

*Chaque entrée : contexte → décision → raison. En ordre chronologique (v1 → v2 → fixes).*

## 1. SQLite par défaut, Postgres par variable d'environnement
**Contexte** : cahier des charges « PostgreSQL / SQLite ». **Décision** : SQLite en dev
(`backend/jurisprudence.db`), `JURISDIVORCE_DB=postgresql://…` bascule sans changer une ligne
(`database.py` choisit le moteur). **Pourquoi** : zéro friction pour tester sur la machine
utilisateur ; le code métier n'utilise que l'ORM.

## 2. Décisions aplanies en colonnes + `extracted_json` conservé
**Contexte** : filtrer/agréger sur du JSON imbriqué est fragile en SQLite.
**Décision** : le JSON LLM est dénormalisé en colonnes typées à l'écriture (`save_decision`),
et la sortie LLM complète est conservée telle quelle dans `extracted_json` (audit + évolution
du schéma sans ré-ingestion). **Pourquoi** : filtres SQL indexés + traçabilité complète.

## 3. Migration par `ALTER TABLE ADD COLUMN` (`ensure_schema`)
**Contexte** : le schéma v2 est arrivé après la création de la base v1.
**Décision** : comparaison PRAGMA ↔ modèles, ajout des colonnes manquantes au démarrage.
**Pourquoi** : aucune perte de données, pas de dépendance Alembic, marche sur SQLite et Postgres.

## 4. Filtre lexical normalisé (1 fort OU ≥2 secondaires) plutôt qu'une regex unique
**Contexte** : la regex v1 (6 termes accentués) générait des faux négatifs massifs.
**Décision** : normalisation NFD sans accents + casse libre, 2 niveaux de termes, contexte
divorce/époux requis pour les termes secondaires ; jamais de rejet pour pseudonymisation ;
seuls « motifs occultés » explicites ou < 1 200 caractères sont écartés.
**Pourquoi** : exigence anti-faux-négatifs de la mission v2, validée sur des vrais XML CAPP.

## 5. Extraction XML DILA `TEXTE_JURI_JUDI` (découverte en testant le réel)
**Contexte** : l'URL `OPENDATA/Judilibre/` documentée par la mission v1 renvoie 404 ; la
vraie structure est `/OPENDATA/CAPP/` (fonds racine) et les dumps sont des XML JURI, pas du JSON.
**Décision** : BFS sur `/OPENDATA/` (dossiers fonds, élagués par filtre), fonds détecté par
segment OU nom de fichier, `parse_juri_xml` extrait ID/juridiction/date/RG + texte (feuilles
de `TEXTE`) recollé en en-tête + corps. **Pourquoi** : sans cela, CAPP = 0 décision ; l'en-tête
reconstruit donne au LLM les metadata qu'il doit extraire.

## 6. Troncature par sections (`smart_truncate`) au lieu d'une coupe brutale
**Contexte** : la v1 tronquait à 30 000 chars par la fin → l'état liquidatif et les montants
(dispositif) étaient perdus. **Décision** : budget réparti en-tête / cœur (recherche des
marqueurs de sections) / dispositif (fin de l'arrêt), proportionnel à `MAX_CHARS`.
**Pourquoi** : les montants à extraire sont quasi toujours dans les derniers paragraphes.

## 7. Réparation JSON systématique (`repair_json`)
**Décision** : strip des fences ```json, extraction de l'objet équilibré, virgules finales,
NaN → null, avant `json.loads`. **Pourquoi** : chaque parse échoué = une décision perdue
(comptée ERROR) ; coût nul, gain direct de volume ingéré.

## 8. Concurrence adaptative (`AdaptiveLimiter`) au lieu d'un Sémaphore fixe
**Contexte** : la mission demande de vérifier 30-50 requêtes simultanées sans 429 ; pas de
clé API disponible sur la machine de dev pour tester en live. **Décision** : limiter dynamique
— ÷2 à chaque 429, remontée de +10 % toutes les 90 s sans erreur ; `--concurrency` et
`--max-chars` en CLI. **Pourquoi** : le pipeline s'auto-cale sur la limite réelle de Zhipu,
qu'il vaut mieux découvrir en production que subir ; le plafond de débit est l'enveloppe de
tokens (math dans README), pas la concurrence.

## 9. Monitoring cross-process par tables SQLite (`pipeline_state`/`pipeline_logs`/`processed_archives`)
**Contexte** : l'UI doit afficher/piloter un pipeline qui tourne dans un autre process.
**Décision** : heartbeat du writer dans la base partagée, l'API FastAPI lit ces tables,
contrôle = UPDATE du champ `status`, la boucle du worker vérifie avant chaque décision.
**Pourquoi** : pas de WebSocket/redis à opérer, reprise garantie (manifest), pause/resume
fonctionnent même après crash du worker.

## 10. Données de démonstration synthétiques marquées `SYNTHETIQUE_DEMO`
**Contexte** : l'UI doit être démontrable sans consommer de tokens ni attendre la campagne.
**Décision** : `backend/app/seed.py` génère ~1 135 décisions aux ordres de grandeur
réalistes, colonne `source` distingue démo et `JUDILIBRE_OD`. **Pourquoi** : UI/analytics
immédiatement exploitables, aucune confusion possible avec de vraies décisions ; la campagne
réelle complète la base sans conflit (dédoublonnage MD5 + id).

## 11. Frontend : 5 vues avec routes renommées et redirections
**Contexte** : mission v2 impose `/simulateur` et `/decisions` (v1 : `/boussole`,
`/jurisprudence`). **Décision** : nouvelles routes + `redirect()` sur les anciennes
(307 vérifiés). **Pourquoi** : rien ne casse chez un utilisateur qui aurait bookmarké.

## 12. Thème centralisé `theme.config.ts` + variables HSL `globals.css`
**Contexte** : exigence « identité visuelle modifiable en une seule passe / re-skin par LLM ».
**Décision** : triplets HSL dans `globals.css` (`:root`/`.dark`), tokens référencés par
Tailwind et le JS via `theme.config.ts` ; composants `ui/` sans Radix (forwardRef + cva +
Slot maison dans Button). **Pourquoi** : changer la charte = éditer 2 fichiers, aucune
vue à toucher ; moins de dépendances = moins de rupture d'API de lib.

## 13. UI sans dépendance de composants lourds (pas de shadcn CLI ni Radix)
**Décision** : kit `components/ui/` écrit à la main (Button asChild maison, Dialog,
Select natif stylé). **Pourquoi** : versions Next/React stables et auditables, contrôle
total du re-skin, aucun conflit de peer deps sous Node 26.

## 14. CORS en regex `localhost:<tout port>`
**Contexte** : le port du frontend a bougé (3000 occupé par une autre app utilisateur → 3100),
le CORS v1 fixé sur :3000 bloquait les fetch. **Décision** :
`allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+"`. **Pourquoi** : tolère tout port
local, refuse le reste (dépôt public à terme).
