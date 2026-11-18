# JurisDivorce Analytics

Plateforme d'analyse statistique et décisionnelle de la jurisprudence française en droit de la
famille (divorce, liquidation de régime matrimonial & partage) — conformément au cahier des charges.

```
pipeline/ingest_judilibre_brut.py   →  backend/jurisprudence.db (SQLite)  →  API FastAPI  →  Frontend Next.js
      (regex 0 token + GLM Flash async)         (colonnes aplanies + JSON brut)     (REST /docs)    (Tailwind, Recharts)
```

## Arborescence

```
jurisdivorce/
├── backend/                 # API FastAPI (SQLAlchemy, SQLite/Postgres)
│   ├── app/
│   │   ├── main.py          # point d'entrée + CORS + /docs
│   │   ├── models.py        # Decision (aplanie) + Recompense
│   │   ├── schemas.py       # contrats Pydantic = OpenAPI
│   │   ├── routers/         # stats.py · decisions.py · boussole.py
│   │   ├── services/        # predictor.py (moteur statistique) · classify.py (preuves)
│   │   ├── seed.py          # jeu de démonstration SYNTHETIQUE_DEMO (665 décisions)
│   │   └── database.py
│   └── jurisprudence.db     # base (créée par seed ou pipeline)
├── pipeline/
│   └── ingest_judilibre_brut.py   # archives Open Data → GLM Flash → base
└── frontend/                # Next.js 14 App Router + Tailwind + shadcn-style + Recharts
    ├── app/                 # page (landing) · analytics · boussole · jurisprudence
    ├── components/          # ui/ · charts/ · boussole/ · jurisprudence/ · layout/
    └── lib/                 # api.ts (hooks) · types.ts · utils.ts
```

## Démarrage

### 1. Backend (port 8000)

```bash
cd backend
pip install -r requirements.txt
python -m app.seed          # données de démonstration (réinitialise la base)
python -m uvicorn app.main:app --reload --port 8000
# Swagger : http://127.0.0.1:8000/docs
```

### 2. Frontend (port 3000, sinon `-p 3100`)

```bash
cd frontend
npm install
npm run dev                 # ou : npm run dev -- -p 3100 si le 3000 est occupé
# http://localhost:3000
```

Variables : `NEXT_PUBLIC_API_URL` (défaut `http://127.0.0.1:8000`), `JURISDIVORCE_DB` (défaut
`backend/jurisprudence.db`).

### 3. Ingestion réelle (Phase 1 du plan)

```bash
pip install -r pipeline/requirements.txt
export ZHIPU_API_KEY="votre_clé"
python pipeline/ingest_judilibre_brut.py export_judilibre_cour_appel_2025.tar.gz --db backend/jurisprudence.db
```

Filtre regex local (0 token) → dédoublonnage MD5 → GLM Flash asynchrone (semaphore 20, backoff
`tenacity`, `response_format=json_object`) → aplanissement en colonnes requêtables. Les archives
restent dans un dossier séparé du code. La bascule API PISTE/Judilibre reste un point d'évolution
(abstraction `JudilibreClient` à ajouter dans `pipeline/`).

## Modules livrés

| Module | Route | Contenu |
|---|---|---|
| Landing | `/` | Hero + KPI nationaux + accès modules |
| Dashboard Analytics | `/analytics` | 6 KPI + comparatif des cours (barres+courbe), distribution PC par durée de mariage, top 5 motifs de rejet, taux de succès par type de preuve |
| La Boussole « Mon Cas » | `/boussole` | Questionnaire 4 étapes → fourchette min/médiane/max, chances de succès selon les preuves, estimation PC, 5 décisions jumelles (lien profond vers la fiche) |
| Explorer la Jurisprudence | `/jurisprudence` | Filtres combinés (cour, régime, statut récompense, PC, texte) + fiche détaillée : résumé IA vs extrait brut, badge de fiabilité de la source |

## Points d'architecture (re-skin facilité)

- Thème 100 % variables CSS HSL dans `frontend/app/globals.css` (bloc `:root`/`.dark`).
- Aucun `fetch` dans les composants d'affichage : tout passe par `lib/api.ts` (`useAnalytics`,
  `useJurisprudence`, `useDecision`, `postBoussole`).
- Composants `ui/` atomiques sans dépendance radicale (pas de Radix), remplaçables un à un.
- Types TypeScript générés à la main depuis `backend/app/schemas.py` — à synchroniser si le schéma
  d'extraction évolue.

## Avertissement

Outil statistique **indicatif** : il ne constitue pas un avis juridique. Les données livrées sont
synthétiques (`source = SYNTHETIQUE_DEMO`) afin que l'interface soit démontrable sans consommer de
tokens ; exécuter le pipeline sur les archives Judilibre Open Data remplace ces lignes par de
vraies décisions (`source = JUDILIBRE_OD`).
