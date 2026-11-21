# Journal des décisions techniques — pourquoi c'est construit comme ça

*Chaque entrée : contexte → décision → raison. En ordre chronologique (v1 → v7).*

*(Entrée 26 ajoutée en V7 — régimes matrimoniaux complets.)*

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

## 15. BatchWriter : une seule file d'écriture, lots de 25 (mission V3)
**Contexte** : avec 40 workers GLM en parallèle + l'API qui lit, SQLite renvoyait des
`database is locked` potentiels et commitait une fois par décision. **Décision** : les workers
déposent leurs JSON extraits dans une `asyncio.Queue` ; un unique task consommateur écrit des
lots de 25 décisions en une transaction. **Pourquoi** : sérialise les écritures (WAL +
busy_timeout en complément), réduit le nombre de commits, aucun verrou croisé. Piège corrigé :
`task_done()` par **item** (pas par lot) sinon `queue.join()` deadloque.

## 16. DLQ `failed_decisions` + relance (mission V3)
**Contexte** : un échec GLM final (4 tentatives) perdait la décision (simple log ERROR).
**Décision** : table `failed_decisions` (id, texte tronqué, erreur, tentatives) ; bouton
« Relancer les échecs » dans `/pipeline` (drapeau `retry_failed` dans `pipeline_state`, drainé
par le worker) + CLI `retry-failed`. **Pourquoi** : aucune décision n'est perdue ; la relance
fonctionne même après crash, et sans redémarrer une campagne complète.

## 17. Normalisation juridictions/régimes à l'écriture (mission V3)
**Contexte** : le LLM peut renvoyer « CA Paris », « Cour d'appel de PARIS »… → doublons dans
le comparatif inter-cours. **Décision** : `normalize_juridiction()` (37 villes canoniques,
détection « appel »/« CA ») et `normalize_regime()` appliquées dans `save_decision` — les
données sont propres au repos, pas à la lecture. **Pourquoi** : corriger à l'écriture coûte
une fois ; à la lecture, chaque requête paierait.

## 18. null vs 0 : règle contractuelle prompt + code (mission V3)
**Contexte** : GLM pouvait répondre `0` pour un montant inconnu, polluant toutes les moyennes.
**Décision** : règle n°4 du prompt (null par défaut, `0` réservé à `montant_accorde` d'une
demande REJETE), `norm_amount()` (négatif/non-numérique → NULL) et contrainte appliquée dans
`save_decision`. **Pourquoi** : la sémantique des agrégats (montant moyen perdu vs obtenu)
dépend entièrement de cette distinction.

## 19. Calculateur légal : formules statiques couplées aux stats réelles (mission V3)
**Contexte** : demande d'un calculateur art. 815-9 et art. 1469 « couplé à la jurisprudence ».
**Décision** : les formules légales sont codées en dur (aucun LLM à l'exécution) ; les
paramètres jurisprudentiels (abattement médian de la cour, taux de rejet par nature) sont
calculés sur la base filtrée ; alerte prescription quinquennale (>60 mois). **Pourquoi** :
déterministe, 0 token, explicable ; la base apporte le « dans votre cour, c'est X % ».

## 20. Recherche plein texte FTS5 avec triggers + rebuild (V4)
**Contexte** : la recherche `q=` en LIKE ilike 4 colonnes était lente et sans pertinence.
**Décision** : table virtuelle `decisions_fts` (id UNINDEXED, resume, resume_peda) tenue par
3 triggers, reconstruite automatiquement si le compte diverge ; `q=` tente FTS (AND de phrases
quotées) puis repli LIKE. Pièges corrigés : `executescript()` absent sur connexion SQLAlchemy
et split `;` qui casse les triggers. **Pourquoi** : recherche instantanée sans service externe ;
le repli LIKE garantit zéro régression.

## 21. CI GitHub Actions backend + frontend (V4)
**Contexte** : aucune vérification automatisée entre les commits. **Décision** : workflow
`.github/workflows/ci.yml` — deps backend+pipeline → seed → pytest → dry-run pipeline inline
(archive synthétique : 3 fichiers lus, 1 conservée) ; frontend npm ci → build.
**Pourquoi** : le run rouge du premier essai (openai manquant) a montré la valeur ; la CI est
le filet qui protège la reprise par un autre agent.

## 22. API en same-origin par défaut + rewrites Next en dev (V7)
**Contexte** : déployé derrière un tunnel Cloudflare, le build statique embarquait
`API_BASE=http://127.0.0.1:8000` en dur ; l'origine `https://….trycloudflare.com` n'étant pas
autorisée par le CORS backend (regex localhost), le navigateur bloquait tous les appels API —
sauf que `/api/pipeline/*` n'a pas de repli snapshot : l'onglet Pipeline apparaissait cassé.
**Décision** : `API_BASE = ""` (fetch relatif `/api/…`) dans `lib/api.ts` ; en mode non statique,
`next.config.mjs` réécrit `/api/:path*` vers `http://127.0.0.1:8000/api/:path*` ; en déploiement,
FastAPI sert le site statique ET l'API sur la même origine. `NEXT_PUBLIC_API_URL` reste
prioritaire si défini. **Pourquoi** : une seule origine = zéro CORS, zéro divergence dev/prod ;
le repli snapshot (`/data/*.json`) n'est plus qu'un mode hors-ligne.

## 23. Pied de page unique + mention `SYNTHETIQUE_DEMO` dynamique (V7)
**Contexte** : deux footers se superposaient (`LegalDisclaimerFooter` + `Footer`), et la mention
« données marquées SYNTHETIQUE_DEMO tant que le pipeline n'a pas tourné » était en texte fixe,
peu importe le contenu réel de la base. **Décision** : `Footer` supprimé, tout est fusionné dans
`LegalDisclaimerFooter` (clause légale Règle d'Or N°5 conservée intégralement) ; la ligne de
source est calculée depuis `/api/health`, enrichi d'un champ `synth_demo_count` (count
`source='SYNTHETIQUE_DEMO'`) — la mention démo ne s'affiche que si la base en contient.
**Pourquoi** : un seul footer à maintenir, et un affichage factuel qui bascule tout seul
(`JUDILIBRE_OD`) quand la campagne réelle a tourné.

## 24. Pré-remplissage SSR depuis les snapshots `public/data/*.json` (V7)
**Contexte** : en export statique, les hooks client partent de `null` → cartes KPI vides dans le
HTML initial (clignotement + mauvais SEO). **Décision** : importer les JSON du snapshot
(`stats_globales.json`, `health.json` — `resolveJsonModule` déjà actif) comme valeur initiale
(`data ?? snapshot`) dans l'accueil et le header ; l'appel API live écrase après hydratation.
**Pourquoi** : le HTML rendu contient déjà les chiffres réels, les moteurs indexent la page,
et l'utilisateur ne voit aucun état vide.

## 25. Thème : ombres en variables CSS 3 niveaux + utilitaires de fond (V7)
**Contexte** : re-skin « en une passe » toujours limité à `theme.config.ts` + `globals.css`, mais
les ombres étaient en dur dans les classes utilitaires et il manquait des fonds décoratifs.
**Décision** : `--shadow-card` / `--shadow-card-hover` / `--shadow-elevated` définies dans
`:root` et `.dark` (miroir de `themeConfig.shadows`), utilitaires `bg-hero`, `bg-grid`,
`text-gradient`, `bg-banner` en `globals.css` ; `Card`/`KpiCard` branchés sur `shadow-card`.
**Pourquoi** : toute la profondeur visuelle (light + dark) se règle toujours dans les 2 mêmes
fichiers, sans toucher aux composants.

## 26. Énumération complète des régimes matrimoniaux, connectée de bout en bout (V7)
**Contexte** : le prompt LLM et `normalize_regime` ne connaissaient pas le « contrat avec clause
de partage » (parts inégales, préciput, attribution intégrale) → texte brut en base, invisible
aux filtres (dropdown limité aux libellés connus, « Régime inconnu » sur les cartes) ; le
simulateur n'avait que 5 statuts et ne filtrait jamais les comparables par régime.
**Décision** : nouveau code `COMMUNAUTE_AVEC_CLAUSE` ajouté au prompt d'extraction, à
`normalize_regime` (détection clause/préciput/attribution intégrale/parts inégales, avant le
« communauté » générique ; « universelle » prioritaire), au seed, aux libellés front
(`REGIME_LABELS`, CRA rebaptisé « communauté légale / réduite aux acquêts » — depuis 1966 ce
sont le même régime) ; le simulateur gagne 3 statuts (CU, participation, clause) reliés au code
régime via `STATUT_REGIME`, et le diagnostic filtre désormais les décisions comparables par
régime (repli tous-régimes + note si < 8). **Pourquoi** : un régime non reconnu ne doit jamais
devenir une donnée fantôme ; et les fourchettes doivent être calculées sur le bon régime.

## 27. Audit des autres énumérations d'extraction : `nature` en labels FR vs codes en base (V7)
**Contexte** : même défaut que le régime — le prompt LLM émettait `nature` en **labels français**
("Travaux amélioration"…) tandis que le seed, les filtres (`nature_reclamation`) et les facets
utilisaient des **codes** (`TRAVAUX_BIEN_PROPRE`…) ; `save_decision` stockait brut → sur de vraies
données, le filtre par nature aurait renvoyé 0 résultat et les facets auraient listé des valeurs
infiltrables. **Décision** : prompt passé en codes ; nouveaux normaliseurs dans `pipeline/core.py`
(`normalize_nature` — inconnu → `AUTRE` filtrable, jamais de texte brut ; `normalize_type_procedure`,
`normalize_pc_forme` — inconnu → null, `normalize_mode_garde`) appliqués dans `save_decision` ;
les autres énumérations (`statut`, `regle_calcul`, `demandeur`, `preuve_type` via `classify_proof`)
étaient déjà cohérentes. Tests unitaires ajoutés (30 tests verts). **Pourquoi** : un champ
énuméré doit avoir UN vocabulaire canonique, imposé à l'écriture — sinon les filtres et les
facettes divergent silencieusement dès la première vraie ingestion.

## 28. Filtre lexical : audit de rappel sur la vraie archive CASS (V7)
**Contexte** : question « récupère-t-on toutes les décisions utiles ? » — audit chiffré sur
`Freemium_cass_global_…tar.gz` (145 421 fichiers XML) : le filtre retenait 785 décisions sur
62 707 scannées, et parmi les rejets figuraient des familles utiles (concubinage/PACS 291,
pension alimentaire 499, art. 262-1 70, mesures provisoires 63, ONC 102, licitation 242,
séquestre 211, communauté universelle/préciput 27+27, art. 266 47, logement familial 22…).
**Décision** : élargissement des `SECONDARY_TERMS` (articles en double forme « article X » /
« art. X », pension alimentaire, 266/1240/700, nom d'usage, logement familial, mesures
provisoires, ONC, licitation, séquestre, 262-1, communauté universelle, participation aux
acquêts, clause de partage/préciput, indivision, date des effets patrimoniaux…) et du
contexte famille (`CONTEXT_TERMS` += concubin, PACS, union libre, conjoint) — le chemin
« 2 termes secondaires » exige toujours un contexte famille, donc pas de bruit de procédure
civile générale (art. 700 seul ne suffit pas). Résultat : **1 122 retenues (+43 %)** avec
précision contrôlée (échantillon CASS inspecté). Les décisions rejetées restent non stockées
(économie disque/tokens) ; les retenues conservent `raw_text` + `extracted_json` complets, donc
réexploitables plus tard même si l'UI ne les affiche pas encore. **Pourquoi** : un pré-filtre
trop étroit perd définitivement des décisions (le texte brut n'est pas gardé) — mieux vaut
un peu plus de tokens que des angles morts.

## 29. « On ne jette plus rien » : table `raw_fiches` + filtre ctx+1 secondaire (V7)
**Contexte** : seules les décisions retenues par le pré-filtre étaient stockées — une fiche
rejetée était perdue définitivement (pas de texte brut conservé) et toute statistique future
sur ce segment aurait exigé de re-télécharger. **Décision** : (1) nouvelle table `raw_fiches`
écrite à chaque décision scannée (texte intégral, fonds, archive, md5) — vérifié dry-run CASS :
62 705 fiches = 0,26 Go, négligeable ; (2) le filtre d'extraction passe à « terme fort OU
(contexte famille + ≥1 secondaire) » (CASS : 1 122 → 2 605 retenues, ~180 M tokens CASS+CAPP) ;
le « contexte seul » est écarté car pollué par le pénal (« épouse X… »). **Pourquoi** : le
disque est quasi gratuit (~2 Go pour tout CASS+CAPP), les tokens LLM sont le vrai coût —
`raw_fiches` découple les deux : on conserve tout, on n'extrait que le pertinent, et on peut
ré-extraire hors-ligne plus tard sans jamais re-télécharger.

## 30. Page admin `/pipeline` protégée par token, fail-closed (V8, 2026-11-20)
**Contexte** : la page `/pipeline` était dans la navbar publique et exposait des endpoints
sans aucune auth : `POST /api/pipeline/control` (pause/stop), `PUT /api/pipeline/config`
(changer modèle/concurrence → facture de tokens), `POST /retry-failed`, plus la fuite des
logs internes, conso tokens (quota 300 M/j) et perfs DB. **Décision** : garde
`admin_guard` sur tout `**/api/pipeline/*` — en-tête `X-Admin-Token` == env
`JURISDIVORCE_ADMIN_TOKEN`, **fail-closed** (variable absente → 404, pour ne pas révéler
l'existence des routes) ; page retirée de la navbar (`header.tsx`) et de l'accueil
(`page.tsx`) ; saisie du token sur la page (localStorage `jd_admin_token`, bouton
« Verrouiller ») ; `load_dotenv()` ajouté dans `app/main.py` pour que le backend lise
`backend/.env`. **Pourquoi fail-closed en 404 plutôt que 403** : un 403 confirme
l'existence d'une route admin à un attaquant. **Pourquoi un simple token partagé et pas
d'OAuth** : déploiement statique same-origin derrière un tunnel Cloudflare, un seul
opérateur — un header secret suffit, zéro dépendance. Voir `docs/ADMIN_PIPELINE.md`.

## 22. Multi-fournisseurs LLM + `probe` avant campagne (2026-11-21)
**Contexte** : le pipeline était câblé sur un seul endpoint (Zhipu) ; le tier gratuit z.ai plafonne
à ~1 000 req/jour ; les gratuits OpenRouter (nemotron/gemma/ling) sont saturés ou inutilisables ;
changer de modèle à l'aveugle brûle la DLQ. **Décision** : presets `PROVIDER_BASE_URLS` +
`--provider`/`JURISDIVORCE_PROVIDER` + précédence `<PROVIDER>_API_KEY` > `ZHIPU_API_KEY` ;
sous-commande `probe --n N` : N vraies décisions, validation **déterministe** (JSON strict,
montants numériques/null, juridiction normalisable), exit 0 si ≥ 80 % → GO. **Pourquoi sans LLM
juge** : la conformité de schéma est mécanique — un juge LLM coûterait des tokens et serait
lui-même faillible ; les violations réelles (ling renvoyait un objet là où un nombre est attendu)
sont attrapées par un walk typé avec chemins complets (`soulte.montant=…`).

## 23. Dédoublonnage cross-fonds (juridiction, RG, date) — md5 en secours (2026-11-21)
**Contexte** : l'upsert ne portait que sur `META_COMMUN/ID` ; une décision inédite INCA republiée
ensuite en CASS porte un autre ID → duplication garantie entre fonds. **Décision** : garde dans
`save_decision` avant INSERT : candidats `(UPPER(juridiction), date_decision)` puis comparaison
Python du RG normalisé (`[^A-Z0-9]` retiré) ; md5 en secours seulement (une republication peut
altérer le texte) ; skip → `return False`. **Pourquoi normaliser en Python et pas en SQL** : la
base stocke le RG brut avec séparateurs — normaliser côté SQL imposerait une colonne dérivée +
migration ; le candidat `(juridiction, date)` est déjà sélectif.

## 24. Coercition int des champs entiers du schéma API (2026-11-21)
**Contexte** : hy4 a produit `duree_mariage_annees: 39.4` → ValidationError Pydantic → 500 sur
`/api/stats/pc-correlation` (et fiche détail) ; les démos n'avaient jamais déclenché le cas.
**Décision** : `int()` à l'écriture pour `duree_mariage_annees` + `nombre_enfants` dans
`save_decision`, CAST SQL des lignes `typeof='real'` existantes. **Pourquoi ne pas toucher aux
schémas** : le contrat API reste strict (int) — c'est l'ingestion qui doit produire des données
conformes ; surveiller `delai_procedure_mois`, `occupation_duree_mois`, etc.
