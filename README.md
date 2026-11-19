# JurisDivorce Analytics

> **📘 Guide d'utilisation complet** : [`GUIDE_UTILISATION.md`](GUIDE_UTILISATION.md) (pas à pas, avec exemples chiffrés) — version PDF : [`GUIDE_UTILISATION.pdf`](GUIDE_UTILISATION.pdf)

Plateforme d'analyse statistique et décisionnelle de la jurisprudence française en droit de la
famille (divorce, liquidation de régime matrimonial & partage) — **v4** : ingestion massive
multi-fonds, recherche plein texte FTS5, calculateur juridique, radar des pièges, moniteur du
pipeline, suite de tests et CI.

```
DILA Open Data (CAPP · CASS · TJ — toutes les archives historiques, XML + JSON)
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
Frontend Next.js          — 7 vues : Accueil · Cockpit · Mon Cas · Calculateur · Jurisprudence ·
                            Pièges · Pipeline (thème centralisé, mode sombre/clair)
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
pytest tests -q                         # 26 tests (pipeline + API)
# La CI GitHub (.github/workflows/ci.yml) exécute seed + pytest + dry-run + build à chaque push.
```

## 🚀 Ingestion massive CAPP + CASS + TJ

```bash
pip install -r pipeline/requirements.txt
export ZHIPU_API_KEY="votre_clé_zhipu"          # quota 300 M tokens/jour sur GLM Flash

python -m pipeline.ingest run --download --fonds CAPP,CASS,TJ --dry-run   # comptage, 0 token
python -m pipeline.ingest run --download --fonds CAPP,CASS,TJ --analyze   # campagne complète
python -m pipeline.ingest status                                          # état
python -m pipeline.ingest control pause|resume|stop                       # pilotage
python -m pipeline.ingest retry-failed                                    # relancer la DLQ
```

Ce que fait la campagne : aspiration récursive des **archives historiques** DILA (manifest
`processed_archives` → reprise), filtre sans faux négatifs (pseudonymisation acceptée, seuls
les motifs explicitement occultés ou textes < 1 200 caractères sont écartés), worker haute
cadence avec **réparation JSON** et **troncature par sections** (en-tête + motifs + dispositif),
**DLQ** des échecs, heartbeat temps réel → moniteur `/pipeline`.

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
- Réglages modifiables **à chaud** depuis `/pipeline` (table `app_config` relue à chaque décision)
  ou `.env` (`ZHIPU_API_KEY`, `MAX_CONCURRENCY`, `MAX_CHARS`, `JURISDIVORCE_MODEL`).

## Les 7 vues

| Vue | Route | Contenu |
|---|---|---|
| Accueil | `/` | Hero + KPIs nationaux + accès modules + bandeau démo |
| **Cockpit Global** | `/analytics` | KPIs réactifs aux filtres croisés + 8 graphiques (comparateur inter-cours, **tendances par année**, distribution des abattements, succès par nature réclamé/obtenu, corrélation PC, distribution PC, motifs de rejet, succès par preuve) |
| **Simulateur « Mon Cas »** | `/simulateur` | 4 étapes → fourchettes observées, chances par preuve, checklist des preuves gagnantes, alertes pièges, 5 décisions jumelles, **Dire à Notaire** (Word/Markdown/PDF) |
| **Calculateur juridique** | `/calculateur` | Art. 815-9 : indemnité d'occupation (abattement médian de la cour, **alerte prescription quinquennale**, 10 arrêts comparables) · Art. 1469 : profit subsistant vs dépense faite + taux de rejet constatés |
| **Explorateur** | `/decisions` | Recherche plein texte **FTS5** + filtres multicritères, cartes avec badges financiers, fiche détaillée (IA vs texte intégral) |
| **Radar des Pièges** | `/pieges` | 10 motifs de rejet : % des échecs, montant moyen perdu, arrêts illustratifs liés |
| **Moniteur Pipeline** | `/pipeline` | Archives, compteurs (fichiers lus / parcourues / conservées / analysées), tokens, vitesse, logs, **config à chaud**, **relancer les échecs**, benchmark |

**Filtres croisés universels** (Cockpit + Explorateur) : cour, année, régime, contentieux,
nature de réclamation, issue, immobilier, fourchette de montants, plein texte — +
**Export CSV/JSON** de la sélection.

## Tests & CI

- `tests/` : **26 tests pytest** (filtre normalisé, null vs 0, réparation JSON, troncature,
  XML DILA, limiteur adaptatif, BatchWriter, 20 routes API, calculateur, pièges, tendances,
  FTS, démo, config, export). Lancer : `pytest tests -q`.
- CI : `.github/workflows/ci.yml` — à chaque push : deps → seed → pytest → dry-run pipeline
  (backend) et npm ci → build (frontend).

## Architecture (re-skin en une passe)

- `frontend/theme.config.ts` + `app/globals.css` : toute l'identité visuelle (HSL, radius,
  polices, ombres) est centralisée — changer les valeurs = nouvelle charte, rien d'autre.
- Aucun `fetch` dans les composants d'affichage : tout passe par `lib/api.ts`.
- Types TypeScript alignés manuellement sur `backend/app/schemas.py`.
- Migration légère : `ensure_schema()` ajoute les colonnes en `ALTER TABLE` sans perte ;
  `ensure_fts()` maintient l'index plein texte (triggers + rebuild).

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
