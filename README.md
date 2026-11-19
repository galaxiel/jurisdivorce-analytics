# JurisDivorce Analytics

Plateforme d'analyse statistique et décisionnelle de la jurisprudence française en droit de la
famille (divorce, liquidation de régime matrimonial & partage) — **v2 : ingestion massive,
schéma enrichi, cockpit à filtres croisés, moniteur du pipeline**.

> **🤖 Reprise par un agent IA** : lire d'abord [`AGENTS.md`](AGENTS.md) (règles + commandes
> de vérification), puis [`docs/STATE.md`](docs/STATE.md) (état vérifié + roadmap) et
> [`docs/DECISIONS.md`](docs/DECISIONS.md) (journal des choix techniques). Les prompts
> fondateurs sont archivés dans [`docs/`](docs/).

```
DILA Open Data (CAPP · CASS · TJ, toutes les archives historiques)
        │  pipeline/dila.py       — aspirateur récursif + manifest processed_archives
        ▼
pipeline/core.py            — filtre normalisé (1 terme fort OU 2 secondaires), dédoublonnage MD5,
                              troncature par sections (dispositif conservé), réparation JSON
        ▼
pipeline/ingest.py          — worker httpx + Semaphore(25-50), tokens trackés, pause/reprise,
                              heartbeat temps réel (pipeline_state / pipeline_logs)
        ▼
backend/jurisprudence.db    — SQLite/Postgres, colonnes aplanies v2 (type_procedure, natures
                              étendues, montants PC demandés/proposés, écart de revenus, délai…)
        ▼
API FastAPI  (filtres croisés partagés /decisions · /stats/* · /export, export CSV/JSON)
        ▼
Frontend Next.js  — Cockpit Global · Simulateur « Mon Cas » · Explorateur · Moniteur Pipeline
```

## Arborescence

```
jurisdivorce/
├── backend/                 # API FastAPI v2 (SQLAlchemy, migration auto des colonnes v2)
│   ├── app/
│   │   ├── main.py          # + ensure_schema() & tables pipeline au démarrage
│   │   ├── models.py        # Decision v2 + Recompense v2 (nature, règle de calcul, preuves)
│   │   ├── schemas.py       # contrats Pydantic v2 (filtres croisés, moniteur, cockpit)
│   │   ├── routers/         # stats.py (8 endpoints filtrés) · decisions.py (+ /export)
│   │   │                    # boussole.py · pipeline.py (state/logs/control/archives)
│   │   ├── services/        # query.py (filtres partagés) · predictor.py (checklist/alertes)
│   │   └── seed.py          # démonstration SYNTHETIQUE_DEMO (1135 décisions)
├── pipeline/
│   ├── core.py              # filtre, troncature, réparation JSON, heartbeat, schéma SQL
│   ├── dila.py              # aspirateur Open Data multi-fonds (CAPP/CASS/TJ…)
│   ├── ingest.py            # orchestrateur CLI + worker GLM haute cadence
│   └── ingest_judilibre_brut.py  # script v1 conservé (autonome)
└── frontend/                # Next.js 14 — 5 vues, thème centralisé (theme.config.ts)
    ├── app/                 # page · analytics · simulateur · decisions · pipeline
    │                        # (/boussole et /jurisprudence redirigent vers les nouvelles)
    ├── components/          # ui/ · analytics/ (FilterBar, KpiCard, DecisionCard) · charts/
    │                        # boussole/ (étapes + résultat avec checklist/alertes/export)
    └── lib/                 # api.ts (hooks + polling pipeline) · types.ts · utils.ts
```

## Démarrage rapide

```bash
# 1. Backend
cd backend && pip install -r requirements.txt
python -m app.seed                      # jeu de démonstration (0 token)
python -m uvicorn app.main:app --reload --port 8000   # Swagger : /docs

# 2. Frontend
cd frontend && npm install
npm run dev                             # http://localhost:3000 (ou -- -p 3100)
```

## 🚀 Ingestion massive CAPP + CASS + TJ (passage à l'échelle)

```bash
pip install -r pipeline/requirements.txt
export ZHIPU_API_KEY="votre_clé_zhipu"          # quota 300 M tokens/jour sur GLM Flash

# 0) Comptage complet SANS consommer de tokens (recommandé en premier) :
python -m pipeline.ingest run --download --fonds CAPP,CASS,TJ --dry-run

# 1) Campagne complète : TOUTES les archives historiques des 3 fonds :
python -m pipeline.ingest run --download --fonds CAPP,CASS,TJ --analyze

# 2) Pilotage pendant la campagne (CLI ou UI /pipeline) :
python -m pipeline.ingest status
python -m pipeline.ingest control pause|resume|stop
```

Variables : `MAX_CONCURRENCY` (défaut 25, montez à 50 pour saturer le quota),
`MAX_CHARS` (défaut 48000 — troncature intelligente : en-tête + motifs financiers +
dispositif), `JURILIBRE_OPENDATA_URL`, `JURISDIVORCE_MODEL` (défaut `glm-4-flash`).
Flags équivalents : `--concurrency 50 --max-chars 16000`.

### ⚡ Débit : la vraie contrainte est l'enveloppe de tokens, pas la concurrence

| Réglage | Tokens/décision (approx.) | Décisions/jour sur 300 M |
|---|---|---|
| `MAX_CHARS=48000` (qualité max) | ~14 k entrée + 2,5 k sortie ≈ **16,5 k** | **~18 000** |
| `MAX_CHARS=16000` (équilibré) | ~4,7 k + 2,5 k ≈ **7 k** | **~42 000** |
| `MAX_CHARS=12000` (débit max) | ~3,5 k + 2,5 k ≈ **6 k** | **~50 000** |

- **Concurrence** : démarrez `--concurrency 50`. Le limiteur **adaptatif** divise la
  concurrence par 2 à chaque 429 (50 → 25 → 12…), retente chaque décision en backoff
  exponentiel, puis remonte de +10 % toutes les 90 s sans erreur — le pipeline s'auto-règle
  à la limite réelle de Zhipu sans intervention.
- **50 000–100 000 décisions/jour** n'est atteignable que si le budget de troncature suit :
  à `MAX_CHARS=12000`, chaque décision coûte ~6 k tokens et la vitesse réseau/GLM (≈2-4
  décisions/s à 30-50 requêtes simultanées) laisse l'enveloppe 300 M comme seul plafond.
- Sources réelles (vérifiées en ligne le 2026-11-19) : `/OPENDATA/CAPP/Freemium_capp_global_…tar.gz`
  (**292 Mo, XML DILA `TEXTE_JURI_JUDI` — 85 % des décisions chiffrées de liquidation-partage**)
  et `/OPENDATA/CASS/Freemium_cass_global_…tar.gz`. L'extracteur XML + JSON est intégré ;
  les nouveaux dumps du jour sont repris automatiquement au prochain lancement (manifest).

Ce que fait la campagne :

1. **Aspiration multi-fonds** — parcours récursif de l'index public DILA ; **toutes** les
   archives `.tar.gz`/`.zip` historiques sont découvertes (pas seulement le dernier mois) ;
   le manifest `processed_archives` permet la **reprise** (les archives `done` sont ignorées,
   `--force` pour retraiter).
2. **Filtre sans faux négatifs** — texte normalisé (minuscules, sans accents) : 1 terme fort
   (`état liquidatif`, `prestation compensatoire`, `recel de communauté`…) OU ≥2 termes
   secondaires dans un contexte divorce/époux. La pseudonymisation (`[…]`, `***`) n'est
   **jamais** un motif de rejet ; seuls les motifs explicitement occultés ou les textes
   < 1 200 caractères sont écartés.
3. **Worker haute cadence** — `httpx` + `Semaphore(MAX_CONCURRENCY)`, réparation JSON
   (balises markdown, virgules finales), dédoublonnage MD5, comptage des tokens/jour.
4. **Monitoring** — `pipeline_state` (heartbeat temps réel) + `pipeline_logs` alimentent
   l'UI `/pipeline` : archives parcourues, décisions conservées/analysées, vitesse, tokens,
   erreurs, boutons Pause/Reprise/Stop.

## Modules livrés

| Vue | Route | Contenu |
|---|---|---|
| Accueil | `/` | Hero + KPIs nationaux + accès modules |
| **Cockpit Global** | `/analytics` | KPIs réactifs aux filtres croisés + 7 graphiques (comparateur inter-cours, distribution des abattements, succès par nature de réclamation réclamé/obtenu, corrélation durée/écart revenus vs PC, distribution PC, motifs de rejet, succès par preuve) |
| **Filtres croisés** | sticky, partagé | Cour, année, régime, contentieux, nature de réclamation, issue, immobilier, fourchette de montants, plein texte + **Export CSV/JSON** de la sélection |
| **Simulateur « Mon Cas »** | `/simulateur` | 4 étapes → fourchettes observées, chances par preuve, **checklist des preuves indispensables** (fréquences issues des arrêts gagnants), **alertes pièges** (fréquences des causes d'échec), 5 décisions jumelles, **dossier de synthèse Markdown + impression PDF** |
| **Explorateur** | `/decisions` | Cartes avec badges financiers (`Demande X → Obtenu Y`, `IO … abattement Z %`), fiche détaillée (résumé IA vs texte intégral, règles de calcul, preuves déterminantes, conseil pratique) |
| **Moniteur Pipeline** | `/pipeline` | Statut, archives, compteurs, tokens du jour, vitesse, logs en direct, contrôle pause/reprise/stop |

## Architecture (re-skin en une passe)

- `frontend/theme.config.ts` + `app/globals.css` : toute l'identité visuelle (HSL, radius,
  polices, ombres) est centralisée — changer les valeurs = nouvelle charte, rien d'autre.
- Aucun `fetch` dans les composants d'affichage : tout passe par `lib/api.ts`.
- Types TypeScript alignés manuellement sur `backend/app/schemas.py`.
- Migration légère : `ensure_schema()` ajoute les colonnes v2 en `ALTER TABLE` sans perte.

## Avertissement

Outil statistique **indicatif** : ne constitue pas un avis juridique. Les données livrées sont
synthétiques (`source = SYNTHETIQUE_DEMO`) ; exécuter la campagne d'ingestion remplace ces
lignes par de vraies décisions (`source = JUDILIBRE_OD`). Les archives téléchargées vont dans
`archives/` (jamais dans le code) et sont supprimées après traitement (`--keep-archives` pour
les conserver).
