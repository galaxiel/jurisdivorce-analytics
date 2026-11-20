# JurisDivorce Analytics

> **📘 Guide d'utilisation complet** : [`GUIDE_UTILISATION.md`](GUIDE_UTILISATION.md) (pas à pas, avec exemples chiffrés) — version PDF : [`GUIDE_UTILISATION.pdf`](GUIDE_UTILISATION.pdf)

Plateforme d'analyse statistique et décisionnelle de la jurisprudence française en droit de la
famille (divorce, liquidation de régime matrimonial & partage) — **v7** : ingestion massive
multi-fonds, recherche plein texte FTS5, calculateur juridique, radar des pièges, moniteur du
pipeline, simulateur multi-situations, conformité juridique (Règle d'Or N°5) + freemium,
suite de tests et CI, refonte UI et déploiement web same-origin (tunnel Cloudflare).

```
DILA Open Data (CAPP · CASS — seules juridictions publiées, le fonds TJ renvoie 404 côté DILA)
        │  pipeline/dila.py    — aspirateur récursif, tri taille/date, manifest processed_archives
        ▼
pipeline/core.py          — filtre normalisé (1 terme fort OU 2 secondaires), dédoublonnage MD5,
                            troncature par sections (dispositif conservé), réparation JSON,
                            normalisation juridictions/régimes, extraction XML TEXTE_JURI_JUDI
        ▼
pipeline/ingest.py        — worker httpx + concurrence adaptative 429/503, BatchWriter (lots de 25),
                            DLQ failed_decisions, tokens trackés, config à chaud (app_config)
        ▼
backend/jurisprudence.db  — SQLite/Postgres, colonnes aplanies v2+, index FTS5, migration auto
        ▼
API FastAPI               — filtres croisés partagés (/decisions · /stats/* · /export),
                            calculateur 815-9/1469, pièges, tendances, pipeline monitor, /api/health
        ▼
Frontend Next.js          — 6 vues publiques : Accueil · Cockpit · Mon Cas · Calculateur ·
                            Jurisprudence · Pièges + 1 vue admin `/pipeline` (protégée par token,
                            Règle d'Or N°7) ; thème centralisé, mode sombre/clair
```

## Démarrage rapide

### Option A — double-clic (Windows) 👍

| Fichier | Effet |
|---|---|
| **`start.cmd`** | Double-cliquez : installe les dépendances si nécessaire, génère les données de démo si la base est vide, ouvre l'API + le site dans deux fenêtres, attend qu'ils soient prêts puis ouvre le navigateur sur **http://localhost:3100** |
| **`stop.cmd`** | Arrête l'API (8000) et le site (3100) d'un coup |

### Option B — ligne de commande

```bash
# 1. Backend
cd backend && pip install -r requirements.txt
python -m app.seed                      # 1 135 décisions de démonstration (0 token)
python -m uvicorn app.main:app --reload --port 8000   # Swagger : http://127.0.0.1:8000/docs

# 2. Frontend
cd frontend && npm install
npm run dev                             # http://localhost:3000 (ou -- -p 3100 si le 3000 est occupé)

# 3. Tests & CI
pytest tests -q                         # 27 tests (pipeline + API)
# La CI GitHub (.github/workflows/ci.yml) exécute seed + pytest + dry-run + build à chaque push.
```

## 🚀 Ingestion massive CAPP + CASS + TJ

```bash
pip install -r pipeline/requirements.txt
export ZHIPU_API_KEY="votre_clé_zhipu"          # quota 300 M tokens/jour sur GLM Flash

python -m pipeline.ingest run --download --fonds CAPP,CASS --dry-run   # comptage, 0 token
python -m pipeline.ingest run --download --fonds CAPP,CASS --analyze   # campagne complète
# (fonds TJ inexistant côté DILA : /OPENDATA/TJ/ → 404 ; seuls CAPP et CASS sont publiés)
python -m pipeline.ingest status                                          # état
python -m pipeline.ingest control pause|resume|stop                       # pilotage
python -m pipeline.ingest retry-failed                                    # relancer la DLQ
```

Ce que fait la campagne : aspiration récursive des **archives historiques** DILA (manifest
`processed_archives` → reprise), filtre sans faux négatifs (pseudonymisation acceptée, seuls
les motifs explicitement occultés ou textes < 1 200 caractères sont écartés), worker haute
cadence avec **réparation JSON** et **troncature par sections** (en-tête + motifs + dispositif),
**DLQ** des échecs, heartbeat temps réel → moniteur `/pipeline` (**admin** : page retirée de la
navbar, toutes les routes `/api/pipeline/*` exigent `X-Admin-Token` = `JURISDIVORCE_ADMIN_TOKEN`, voir
[`docs/ADMIN_PIPELINE.md`](docs/ADMIN_PIPELINE.md)).

**Preuves réelles** (dry-run, 2026-11-19) : CAPP 292 Mo → 25 999 décisions parcourues,
**2 001 conservées** ; CASS 264 Mo → 145 421 fichiers XML lus, **785 conservées**.

### ⚡ Débit : la vraie contrainte est l'enveloppe de tokens, pas la concurrence

| Réglage | Tokens/décision (approx.) | Décisions/jour sur 300 M |
|---|---|---|
| `MAX_CHARS=48000` (qualité max) | ~14 k entrée + 2,5 k sortie ≈ **16,5 k** | **~18 000** |
| `MAX_CHARS=16000` (équilibré) | ~4,7 k + 2,5 k ≈ **7 k** | **~42 000** |
| `MAX_CHARS=12000` (débit max) | ~3,5 k + 2,5 k ≈ **6 k** | **~50 000** |

- **Concurrence** : démarrez `--concurrency 50` — le limiteur adaptatif divise par 2 à chaque
  429 (50 → 25 → 12…), retente en backoff exponentiel, remonte de +10 % toutes les 90 s sans erreur.
- Réglages modifiables **à chaud** depuis `/pipeline` (admin, token requis — table `app_config`
  relue à chaque décision) ou `.env` (`ZHIPU_API_KEY`, `MAX_CONCURRENCY`, `MAX_CHARS`,
  `JURISDIVORCE_MODEL`, `JURISDIVORCE_ADMIN_TOKEN`). Le backend lit `backend/.env` au démarrage
  (`load_dotenv()` dans `app/main.py`).

## Les 6 vues publiques + 1 vue admin

| Vue | Route | Contenu |
|---|---|---|
| Accueil | `/` | Hero (badge chiffré, dégradé) + 4 KPIs nationaux **pré-remplis en SSR** + « Comment ça marche » + 5 cartes modules + CTA + bandeau démo |
| **Cockpit Global** | `/analytics` | KPIs réactifs aux filtres croisés + 8 graphiques (comparateur inter-cours, **tendances par année**, distribution des abattements, succès par nature réclamé/obtenu, corrélation PC, distribution PC, motifs de rejet, succès par preuve) |
| **Simulateur « Mon Cas »** | `/simulateur` | 4 étapes → fourchettes observées, chances par preuve, checklist des preuves gagnantes, alertes pièges, 5 décisions jumelles, **Dire à Notaire** (Word/Markdown/PDF) |
| **Calculateur juridique** | `/calculateur` | Art. 815-9 : indemnité d'occupation (abattement médian de la cour, **alerte prescription quinquennale**, 10 arrêts comparables) · Art. 1469 : profit subsistant vs dépense faite + taux de rejet constatés |
| **Explorateur** | `/decisions` | Recherche plein texte **FTS5** + filtres multicritères, cartes avec badges financiers, fiche détaillée (IA vs texte intégral) |
| **Radar des Pièges** | `/pieges` | 10 motifs de rejet : % des échecs, montant moyen perdu, arrêts illustratifs liés |
| **Moniteur Pipeline** *(admin)* | `/pipeline` | 🔒 Protégé par `X-Admin-Token` (Règle d'Or N°7, plus dans la navbar) : archives, compteurs (fichiers lus / parcourues / conservées / analysées), tokens, vitesse, logs, **config à chaud**, **relancer les échecs**, benchmark |

**Filtres croisés universels** (Cockpit + Explorateur) : cour, année, régime, contentieux,
nature de réclamation, issue, immobilier, fourchette de montants, plein texte — +
**Export CSV/JSON** de la sélection.

## Tests & CI

- `tests/` : **37 tests pytest** (filtre normalisé, null vs 0, réparation JSON, troncature,
  XML DILA, limiteur adaptatif, BatchWriter, routes API publiques + **garde admin 404/200**,
  calculateur, pièges, tendances, FTS, démo, config, export). Lancer : `pytest tests -q`.
- CI : `.github/workflows/ci.yml` — à chaque push : deps → seed → pytest → dry-run pipeline
  (backend) et npm ci → build (frontend).

## Architecture (re-skin en une passe)

- `frontend/theme.config.ts` + `app/globals.css` : toute l'identité visuelle (HSL, radius,
  polices, ombres 3 niveaux en variables CSS, utilitaires `bg-hero`/`bg-grid`/`text-gradient`)
  est centralisée — changer les valeurs = nouvelle charte, rien d'autre.
- Aucun `fetch` dans les composants d'affichage : tout passe par `lib/api.ts`, en **same-origin**
  (`API_BASE=""` → `/api/…`) ; en dev, `next.config.mjs` réécrit `/api/*` vers `127.0.0.1:8000`.
  Repli hors-ligne : snapshots `frontend/public/data/*.json` (aussi utilisés comme valeurs
  SSR initiales de l'accueil/header).
- Un seul pied de page : `components/legal-disclaimer-footer.tsx` (clause légale obligatoire +
  source des données dynamique via `/api/health.synth_demo_count`).
- Types TypeScript alignés manuellement sur `backend/app/schemas.py`.
- Migration légère : `ensure_schema()` ajoute les colonnes en `ALTER TABLE` sans perte ;
  `ensure_fts()` maintient l'index plein texte (triggers + rebuild).

## Déploiement web (statique + API same-origin)

```bash
cd frontend && BUILD_STATIC=1 npm run build        # export statique → frontend/out/
rm -rf ../backend/static_site && cp -r out ../backend/static_site
# FastAPI sert alors le site sur / ET l'API sur /api/* (même process, même origine)
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8100
# tunnel Cloudflare : cloudflared tunnel --url http://127.0.0.1:8100
```

⚠️ Tout changement **backend** (`main.py`, `schemas.py`, routers) exige de **redémarrer** le
process uvicorn (pas de rechargement à chaud en production) ; le site statique, lui, est servi
à la volée depuis `backend/static_site/`.

## Kit de reprise par un agent

- [`AGENTS.md`](AGENTS.md) — règles d'architecture non négociables + commandes de vérification.
- [`docs/STATE.md`](docs/STATE.md) — état vérifié (avec preuves chiffrées) + roadmap.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — journal des choix techniques (contexte → décision → pourquoi).
- [`docs/cahier_des_charges_v1.md`](docs/cahier_des_charges_v1.md) et
  [`docs/mission_refonte_v2.md`](docs/mission_refonte_v2.md) — prompts fondateurs archivés.

## Avertissement

Outil statistique **indicatif** : il ne constitue pas un avis juridique. Les données livrées
sont synthétiques (`source = SYNTHETIQUE_DEMO`) ; exécuter la campagne d'ingestion remplace
ces lignes par de vraies décisions (`source = JUDILIBRE_OD`). Les archives téléchargées vont
dans `archives/` (jamais dans le code, jamais dans git) et sont supprimées après traitement
(`--keep-archives` pour les conserver).
