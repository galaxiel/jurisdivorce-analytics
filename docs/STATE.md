# ÉTAT DU PROJET — snapshot pour reprise par un agent

*Dernière mise à jour : 2026-11-19 (missions V3→V7 : robustesse, métier, conformité, freemium, refonte UI + correctifs déploiement) · dépôt `galaxiel/jurisdivorce-analytics` (public, `main`)*
*Lire aussi : `AGENTS.md` (règles + commandes), `docs/DECISIONS.md` (pourquoi des choix) et [`GUIDE_UTILISATION.md`](../GUIDE_UTILISATION.md) (+ PDF) pour le manuel utilisateur.*

## Stack

Python 3.11 (FastAPI 0.133, SQLAlchemy 2, Pydantic 2) · Next.js 14.2.15 (React 18,
Tailwind 3, Recharts, next-themes) · SQLite (Postgres-ready via `JURISDIVORCE_DB`) ·
GLM Flash Zhipu (API openai-compliant) pour l'extraction.

## ✅ Ce qui est fait ET vérifié (ne pas refaire)

| Capacité | Preuve de vérification |
|---|---|
| Backend : 14+ endpoints (stats filtrées, décisions, export CSV/JSON, boussole, pipeline) | TestClient : tous 200 ; filtre croisé Lyon → KPI 130 |
| Boussole/Simulateur : fourchettes %, chances travaux, PC, checklist préuves, alertes pièges | 75 % succès avec factures vs 47,6 % global ; checklist « Factures nominatives 48 % » |
| Frontend : 5 vues buildées + 2 redirections | `next build` 10/10 pages ; vérifié navigateur (Cockpit, Pipeline, Décisions, Simulateur) |
| Filtre pipeline normalisé (accents, 1 fort OU 2 secondaires, occultation, 1 200 chars min) | 6 tests unitaires ; vrai arrêt hors-champ (crédit conso) correctement rejeté |
| Extraction XML DILA `TEXTE_JURI_JUDI` + JSON + JSONL + zip | `parse_juri_xml` validé sur un vrai JURITEXT de CAPP |
| Discovery DILA réelle | listing live : `CAPP/Freemium_capp_global_…` (292 Mo) + `CASS/Freemium_cass_global_…` découverts |
| **Campagne réelle CAPP (dry-run)** | **25 999 décisions parcourues, 2 001 conservées** (manifest `done`, heartbeat /pipeline) |
| Réparation JSON + troncature par sections (en-tête/motifs/dispositif) | tests unitaires ; dispositif conservé à 48 k |
| Concurrence adaptative 429 (`AdaptiveLimiter` 50→25→12, remonte +10 %/90 s) | test unitaire |
| Moniteur temps réel (état, logs, archives, pause/reprise/stop) | vu dans le navigateur pendant la campagne CAPP |
| Export CSV/JSON de la sélection filtrée | CSV 244 lignes ; JSON vérifié |
| Migration colonnes v2 sans perte (`ensure_schema` ALTER TABLE) | exécutée sur la base pré-v2 |
| Git/GitHub | commits `cbecc53` v1, `dea6f59` v2, `ccdb09c` fixes CAPP, `bf0d5fd` docs prompts |
| **V3 — Chantier 1 (robustesse)** | SQLite **WAL + busy_timeout** (backend & pipeline) · **BatchWriter** (file d'écriture dédiée, lots de 25, 60/60 écrits en test) · règle **null vs 0** (prompt + `norm_amount` + `REJETE → 0`) · **DLQ `failed_decisions`** + bouton « Relancer les échecs » (+ CLI `retry-failed`) + backoff 429/**503** · **normalisation juridictions/régimes** (`normalize_juridiction` : « CA PARIS » → « Cour d'appel de Paris ») · `.env` lu (python-dotenv) · **config à chaud** (`app_config` relecture à chaque décision : concurrence/modèle/max_chars) · streaming `tarfile r|*` + tri archives par date/taille + compteur **fichiers XML/JSON lus vs retenus** |
| **V3 — Chantier 2 (métier)** | `/api/calculateur/occupation` (art. 815-9 : abattement médian de la cour, **alerte prescription quinquennale**, 10 arrêts comparables — vérifié : 71 mois → dépassement 11 mois) · `/api/calculateur/recompense` (art. 1469 : profit subsistant vs dépense faite + taux rejet amélioration/entretien) · **`/calculateur`** (2 onglets + export) · **`/pieges`** (10 motifs, %, montant moyen perdu, arrêts illustratifs — 842 rejets analysés) · **« Dire à Notaire »** Markdown/Word(.doc)/PDF depuis Simulateur & Calculateur (`lib/dossier.ts`) · **mode démo** : `/api/demo/seed` (50 arrêts `is_demo`) + purge 1 clic + bandeau auto si base < 50 · **benchmark** `/api/pipeline/benchmark` |
| **V3 — Chantier 3 (qualité)** | `/api/health` enrichi (DB, disque, worker, version 3.0) + **dot de santé dans la navbar** · badge `warning` ambre ajouté au thème · build 10/10 routes · routes `/calculateur`, `/pieges` vérifiées navigateur |
| **V4 (autonome) — Recherche FTS5** | Index `decisions_fts` + triggers INSERT/UPDATE/DELETE + rebuild auto si désync (`ensure_fts`) ; `q=` passe par FTS (AND de phrases, repli LIKE) | pytest `test_recherche_fts` ✓ |
| **V4 — Analytics temporelles** | `/api/stats/tendances` (par année : volume, abattement médian, PC médiane, taux succès) + graphique `TendancesChart` dans le Cockpit | pytest + vérifié navigateur |
| **V4 — Suite pytest formelle** | `tests/` (conftest sys.path) : **27 tests verts** — filtre, normalisation, null/0, repair_json, troncature, XML DILA, limiteur, BatchWriter, 20 routes API, calculateur, pièges, tendances, FTS, démo, config, export | `pytest tests -q` → 27 passed |
| **V4 — CI GitHub Actions** | `.github/workflows/ci.yml` : backend (deps → seed → pytest → dry-run pipeline) + frontend (npm ci → build) sur chaque push | run à vérifier sur le push |
| **V4 — Multi-fonds réels** | **CAPP 2 001 conservées** (26 k parcourues) + **CASS 785 conservées (145 421 fichiers XML lus)** — deux fonds traités en autonomie, manifest `done` ×2 | `/api/pipeline/archives` |

**Données actuelles** : `backend/jurisprudence.db` = 1 135 décisions `SYNTHETIQUE_DEMO`
(seed v2) + tables pipeline (`pipeline_state`, `pipeline_logs`, `processed_archives` avec
l'archive CAPP réelle).

**Conservation d'une fiche (réponse « garde-t-on tout ?»)** : chaque décision retenue stocke
`raw_text` (texte intégral de l'arrêt) + `extracted_json` (sortie LLM **complète**, non aplatie) +
les colonnes requêtables + `text_md5`. Donc ajouter une stat demain = calcul depuis
`extracted_json`/colonnes (**0 token, pas de ré-extraction**) ; un champ absent du prompt actuel
= ré-extraction depuis `raw_text` (hors-ligne, sans re-télécharger — **0 téléchargement**,
seulement des tokens). Jamais besoin de reprendre les archives DILA.
**Taille mesurée** : fiche démo ~4,7 Ko (raw 1,6 Ko + JSON 3,0 Ko) ; fiche réelle CASS ~4,1 Ko raw
+ ~3 Ko JSON ≈ ~10 Ko avec index/FTS. Dump **complet sans filtre** (CASS 145 421 + CAPP 25 999
fichiers) ≈ **0,7–0,9 Go de texte brut → ~1,5–2 Go de DB SQLite** (disque : 139 Go libres, donc
négligeable). La vraie contrainte du « dump tout » n'est pas le disque mais les **tokens LLM**
(~16,5 k/décision × ~171 k décisions ≈ 2,8 T tokens ≈ ~9 500 jours de quota 300 M/j) — d'où le
pré-filtre.

## ❌ Ce qui n'existe PAS encore (roadmap priorisée)

1. **Campagne `--analyze` réelle avec ZHIPU_API_KEY** — tout est prêt (worker, DLQ, reprise,
   config à chaud, monitor) ; il manque la clé + le lancement :
   `python -m pipeline.ingest run --download --fonds CAPP,CASS --analyze --concurrency 50 --max-chars 16000`.
2. **API PISTE / Judilibre officielle** (Phase 4) : abstraction `JudilibreClient` à créer
   dans `pipeline/` pour dépasser le périmètre freemium (26 k décisions CAPP publiques).
3. **Recherche sémantique à vecteurs** (embeddings) — le plein texte FTS5 est en place ;
   la couche embeddings se brancherait dans `services/query.py`.
4. **Postgres + agrégats SQL** — voir piège « stats agrégées en Python » dans `AGENTS.md`.
5. **Monétisation / auth** (Phase 4) — aucune authentification aujourd'hui.
6. Tests frontend (vitest) — le backend est couvert par `tests/` (27 tests verts).

## Limitations connues (assumées, à ne pas considérer comme des bugs)

- Dump freemium CAPP : 26 k décisions (toutes matières, 1995-2026) ; TJ : pas de dump
  `.tar.gz` public constaté au 2026-11-19 (le crawler le prendra automatiquement si DILA
  en publie un — manifest + nouveaux fichiers).
- Taux de conservation du filtre sur CAPP réel : ~7,7 % (2 001/25 999) — attendu sur un
  dump toutes matières ; à re-évaluer après l'extraction LLM réelle.
- `Fond TJ` absent ≠ bug : vérifier de temps en temps `python -m pipeline.ingest status`.
- L'archive CAPP traitée est supprimée du disque après campagne (re-téléchargeable ;
  `--keep-archives` pour conserver).

## Reprendre en 5 commandes

```bash
cd backend && pip install -r requirements.txt && python -m app.seed
python -m uvicorn app.main:app --port 8000          # terminal 1
cd frontend && npm install && npm run dev -- -p 3100 # terminal 2
# campagne d'analyse (terminal 3, clé Zhipu requise)
python -m pipeline.ingest run --download --fonds CAPP,CASS --analyze --concurrency 50 --max-chars 16000
# pilotage : UI /pipeline ou python -m pipeline.ingest status|control pause|resume|stop
```

**Mission V5 (commits `631a78c` + `fix(ui)`+`test: suivre 3.0.1`, 2026-11-20) — Simulateur multi-situations & pipeline étendu** :
- **Simulateur /simulateur refondu** : configurateur modulaire en 5 étapes — ① statut (Mariés CRA/SEP/Autre, PACS, Concubinage) + chronologie (mariage, séparation réelle, assignation, note art. 262-1 bascule communauté→indivision, vie commune avant mariage non retenue), ② revenus & charges des deux époux (prestations sociales intégrées), ③ **multi-biens à la carte** (occupation 815-9, locatif → compte de gestion, véhicule argus−crédit, créances/récompenses), ④ demandes annexes cochées (PC, pension CEE, nom d'usage, DI 266/1240, faute, art. 700), ⑤ diagnostic 4 blocs + export Word/Markdown/PDF. Diagnostic POST `/api/simulateur/diagnostic` avec **fallback client** sur decisions_index.json (mode statique autonome).
- **Pipeline V5** : prompt GLM + save_decision + colonnes (effets_patrimoniaux, gestion locative loyers/charges/solde, pension_par_enfant + revenus débiteur, mode_garde, partage_frais, prestations_sociales, ecart_ressources_totales, nom_usage, DI, faute) ; `ensure_schema` migre automatiquement ; `seed_version.txt` dans le stage force le re-seed cloud si le jeu change.
- **Cockpit** : onglet « Pension & demandes annexes » (médiane par cour, par tranche de revenus du débiteur, modes de garde, rejet PC par écart, taux d'échec des demandes annexes).
- 27 tests verts ; déployé après recyclage (piège `cp -r` imbriqué + limite 10 déplois/heure → delete/redeploy si besoin).

**Mission V6 (commits `35e29d1` + `9199186`, 2026-11-20) — conformité juridique + monétisation freemium** :
- `AGENTS.md` : Règle d'Or N°5 ajoutée (bouclier juridique — interdiction de formulations prescriptives, obligations statistiques, titre exports, LegalDisclaimerFooter).
- **Freemium** : `lib/entitlements.tsx` (Context + localStorage, 4 tiers free/diagnostic_29/pack_avocat_49/pass_decisions_19, sync par token URL), `components/paywall-overlay.tsx` (blur-md + carte déblocage), `components/legal-disclaimer-footer.tsx` (toutes routes), backend `routers/checkout.py` (Stripe si clé sinon simulation), `/checkout/simulation` page, badge source navbar.
- **Intégration paywall** : simulateur (tier=free → PaywallOverlay blur fourchettes), /decisions (Pass 19€ pour fiche complète), toggle démo dans /pipeline.
- `lib/dossier.ts` : titre export conforme Règle d'Or N°5.
- Déploiement : recyclé (jurisdivorce-ea02), vérifié en ligne ✓.

**Déploiement web — pièges découverts et documentés (V4→V6)** :
- ZCode Sites ne redémarre PAS le process Python entre les déploiements (hot-swap fichiers seulement) → les correctifs backend ne prennent effet qu'après un recyclage complet (delete + redeploy --new).
- `$DATA_DIR` persiste par instance → mécanisme `seed_version.txt` dans start.sh pour forcer le re-seed si le jeu de données change.
- `cp -r src dest` avec dest existant crée un DOSSIER IMBRIQUÉ → toujours `rm -rf dest && cp -r src dest`.
- La limite ZCode Sites est 10 déplois/hour → planifier les redéploiements en conséquence.

**Mission V7 (2026-11-19, refonte UI + correctifs déploiement — non commité au moment du snapshot)** :
- **Refonte UI** : thème enrichi (ombres 3 niveaux `card`/`card-hover`/`elevated` en variables CSS light+dark, radius 0,875 rem, utilitaires `bg-hero`/`bg-grid`/`text-gradient`/`bg-banner`, focus-visible, scrollbar discrète — toujours confinés à `theme.config.ts` + `globals.css`) ; landing redesign (hero halo dégradé + badge chiffré, KPIs avec icônes, section « Comment ça marche » 3 étapes, cartes modules avec flèche au hover, bandeau CTA) ; header : pilule active `bg-primary/10 text-primary` + `aria-current` ; `Card`/`KpiCard` sur `shadow-card`, `Button` micro-lift.
- **Un seul pied de page** : l'ancien `components/layout/footer.tsx` est supprimé, fusionné dans `LegalDisclaimerFooter` (texte légal Règle d'Or N°5 **intégral**) + ligne de source dynamique via `/api/health` (`source` live/snapshot + nouveau champ **`synth_demo_count`** : la mention `SYNTHETIQUE_DEMO` ne s'affiche que si la base en contient réellement).
- **Pré-remplissage SSR** : accueil et header lisent les snapshots `frontend/public/data/*.json` (`stats_globales.json`, `health.json`) comme valeurs initiales → HTML rendu contient déjà les KPIs (SEO, zéro skeleton au chargement) ; l'API live écrase ensuite côté client.
- **Fix déploiement / CORS (bug onglet Pipeline via le tunnel)** : `API_BASE` vaut désormais `""` (appels `/api/*` **same-origin**) dans `lib/api.ts` ; en dev (`npm run dev`/`start` sur 3100), `next.config.mjs` réécrit `/api/:path*` → `http://127.0.0.1:8000/api/:path*`. Avant, le build statique embarquait `http://127.0.0.1:8000` en dur → depuis l'origine Cloudflare, le CORS backend (regex localhost) bloquait tout → repli snapshot partout sauf `/api/pipeline/*` (pas de fallback) = onglet cassé. `DemoBanner` passe désormais par `lib/api.ts` (`postDemoSeed`/`deleteDemo`), plus de `fetch` en dur.
- **Fix page /pipeline** : formulaire de config initialisé depuis la config courante (ne écrase plus les champs non touchés), nom d'archive tronqué sur `/` **et** `\`, badge de statut avec fallback si valeur inconnue.
- **Déploiement local (constaté le 2026-11-19)** : le tunnel Cloudflare (`https://….trycloudflare.com`) pointe sur **127.0.0.1:8100** (uvicorn `app.main:app` qui sert `backend/static_site/` + `/api/*` en same-origin) ; le dev local reste 8000 (API) + 3100 (frontend). Procédure de mise à jour : `cd frontend && BUILD_STATIC=1 npm run build` puis `rm -rf backend/static_site && cp -r frontend/out backend/static_site` (servi à la volée, sans redémarrer) ; **tout changement backend (`main.py`, `schemas.py`, routers) exige un redémarrage du process uvicorn** (tuer via `Get-NetTCPConnection -LocalPort <port> | Stop-Process -Id …`).
- **Vérifications V7** : `pytest tests -q` → 27 passed · `npm run build` (dev + `BUILD_STATIC=1`) → 13 pages OK · routes 200 sur le tunnel · HTML SSR contient « 1 135 décisions » et le footer unique · aucun chunk JS ne contient `127.0.0.1:8000`.
- **V7 — régimes matrimoniaux complets** : nouveau code `COMMUNAUTE_AVEC_CLAUSE` (contrat avec clause de partage : parts inégales, préciput, attribution intégrale) ajouté au prompt LLM (`pipeline/ingest.py`), à `normalize_regime` (`pipeline/core.py`, test unitaire étendu) et au seed ; libellé CRA renommé « communauté légale / réduite aux acquêts » ; simulateur : 3 nouveaux statuts (MARIAGE_CU/PA/CLAUSE) mappés vers le code régime (`STATUT_REGIME` dans `routers/simulateur.py`) et **filtrage des comparables par régime** (repli + note si < 8) ; filtres : le régime clause apparaît dans le dropdown. Base re-seedée : 1 135 décisions réparties sur les 5 régimes (vérifié via `/api/stats/facets` et POST `/api/simulateur/diagnostic` avec `MARIAGE_CLAUSE`).
- **V7 — audit des énumérations d'extraction** : `nature` du prompt LLM passé en codes + normaliseurs
  `normalize_nature` / `normalize_type_procedure` / `normalize_pc_forme` / `normalize_mode_garde`
  dans `pipeline/core.py` (appliqués dans `save_decision`) — un champ énuméré n'a plus qu'un
  vocabulaire canonique, inconnu → `AUTRE`/`null` au lieu de texte brut infiltrable. 30 tests verts.
- **V7 — audit de rappel du pré-filtre (archive CASS réelle, 145 421 XML)** : 785 → **1 122 décisions
  retenues (+43 %)** après élargissement des termes secondaires (art. 266/700/1240/270/1469/815-9 en
  « article » et « art. », pension alimentaire, nom d'usage, logement familial, mesures provisoires,
  ONC, licitation, séquestre, 262-1, communauté universelle, participation aux acquêts, clause de
  partage/préciput, indivision…) et du contexte famille (concubin, PACS, union libre, conjoint).
  Le chemin « 2 secondaires » exige toujours un contexte famille → pas de bruit de procédure civile.
  31 tests verts. Note : 82 714 fichiers CASS < 1 200 chars ne sont jamais scannés (parse) — court
  délibéré (décisions de pure procédure), à réévaluer si un dump TJ voit le jour.
- **V7 — conservation intégrale des fiches + filtre élargi à ctx+1 secondaire** : nouvelle table
  `raw_fiches` (id, md5, fonds, archive, `raw_text` intégral) — **toutes** les décisions scannées y
  sont écrites, même celles que le pré-filtre rejette pour l'extraction LLM (vérifié dry-run CASS :
  62 705 fiches brutes = 0,26 Go). Le filtre d'extraction passe de « ctx + ≥2 secondaires » à
  « ctx + ≥1 secondaire » : CASS 1 122 → **2 605 retenues** (~180 M tokens pour CASS+CAPP, < 1 jour
  de quota). « contexte seul » écarté volontairement (bruit pénal « épouse X… »). Compteur
  `raw_saved` dans `pipeline_state`, exposé via `/api/pipeline/benchmark` (`raw_fiches`,
  `raw_fiches_mb`) et affiché dans le moniteur /pipeline. 32 tests verts. **Tunnel : l'URL
  quick-tunnel est éphémère** (l'ancienne `dot-rebel-…trycloudflare.com` est en NXDOMAIN après
  mort du process) — relancer `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8100`,
  URL actuelle : `https://conduct-accept-kijiji-glasgow.trycloudflare.com`.
