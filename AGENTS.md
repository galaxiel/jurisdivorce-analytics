# AGENTS.md — Instructions pour tout agent IA travaillant sur ce dépôt

*Lis ce fichier en premier. Contexte détaillé : `docs/STATE.md` (état vérifié) et
`docs/DECISIONS.md` (choix techniques et leur pourquoi). Les prompts fondateurs sont
archivés dans `docs/`.*

## Vue d'ensemble (30 secondes)

JurisDivorce Analytics = plateforme d'analyse statistique de la jurisprudence
divorce/liquidation-partage. Chaîne : **archives Open Data DILA (CAPP/CASS, XML) →
filtre local 0 token → worker GLM Flash async → SQLite aplanie → API FastAPI →
frontend Next.js 5 vues**. Les deux routes historiques (`/boussole`, `/jurisprudence`)
redirigent vers `/simulateur` et `/decisions`.

## Commandes de vérification (à exécuter après CHAQUE modification)

```bash
# 1. Backend : smoke test complet des endpoints (14 routes doivent répondre 200)
export PYTHONPATH="$PWD/backend"
python -m app.seed              # régénère les données de démo (réinitialise la base)
python - <<'EOF'
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
for u in ["/api/health","/api/stats/overview","/api/stats/facets","/api/stats/comparatif-cours",
          "/api/stats/abattement-distribution","/api/stats/succes-par-nature","/api/stats/pc-correlation",
          "/api/stats/top-motifs-rejet","/api/decisions?page_size=2","/api/decisions/demo-00001",
          "/api/decisions/export?format=json","/api/pipeline/state"]:
    r = c.get(u); assert r.status_code == 200, (u, r.status_code)
print("backend OK")
EOF

# 2. Frontend : type-check + build + prerender (doit passer sans erreur)
cd frontend && npm run build && cd ..

# 3. Pipeline : dry-run (0 token) sur une archive de test
python -m pipeline.ingest run --local <archive.tar.gz> --dry-run --db /tmp/test.db
python -m pipeline.ingest status --db /tmp/test.db
```

## Environnement (machine Windows de l'utilisateur)

- Git Bash + Python 3.11 global + Node 26. Shell : Git Bash.
- **Ports** : backend `8000`, frontend `3100` — le port 3000 est occupé par une autre
  application de l'utilisateur, ne pas y toucher.
- Warnings git `LF will be replaced by CRLF` : **ignorables** (Windows autocrlf).
- Chemins : `/tmp` de Git Bash ≠ `/tmp` vu par Python Windows — utiliser `cygpath -w`.
- **Jamais committer** : `archives/` (dumps DILA jusqu'à ~292 Mo > limite GitHub 100 Mo),
  `backend/jurisprudence.db`, `.env*`. Tout est déjà dans `.gitignore` — vérifier avant `git add -A`.
- Dépôt GitHub : `galaxiel/jurisdivorce-analytics` (privé), branche `main`, `gh` authentifié.

## Règles d'architecture (non négociables)

1. **Thème** : toute couleur/typo/ombre se change UNIQUEMENT dans
   `frontend/theme.config.ts` + `frontend/app/globals.css` (variables HSL `:root`/`.dark`).
2. **Aucun `fetch` dans un composant d'affichage** : tout passe par `frontend/lib/api.ts`
   (hooks `useAnalytics`, `useJurisprudence`, `useDecision`, `usePipeline*`).
3. **`frontend/lib/types.ts` doit refléter `backend/app/schemas.py`** : toute évolution du
   schéma Pydantic est répercutée manuellement côté TS dans le même commit.
4. **Migration DB** : uniquement des `ALTER TABLE ADD COLUMN` via `ensure_schema()`
   (`backend/app/database.py`). Jamais de suppression/drop — compat seed v1/ données réelles.
5. **Ne pas supprimer** `pipeline/ingest_judilibre_brut.py` (script v1 autonome conservé).
6. **Données de démo** toujours marquées `source='SYNTHETIQUE_DEMO'` ; vraies données =
   `source='JUDILIBRE_OD'`. Les stats/filtres n'y font pas de différence — ne jamais mélanger
   silencieusement les deux dans un calcul.
7. **Pause/Stop du pipeline** : le process d'ingestion lit `pipeline_state.status` (SQLite,
   cross-process). Toute boucle longue doit passer par `wait_if_paused()` / `control_status()`.

## Cartographie « où toucher pour quoi »

| Besoin | Fichier(s) |
|---|---|
| Nouveau filtre croisé | `backend/app/schemas.py` (`DecisionFiltersQuery`) + `services/query.py` + `frontend/lib/types.ts` + `components/analytics/filter-bar.tsx` |
| Nouveau graphique | `backend/app/routers/stats.py` + `frontend/components/charts/*` + `app/analytics/page.tsx` |
| Nouvelle vue frontend | `frontend/app/<route>/page.tsx` + composants dédiés ; ancienne route → redirect |
| Évolution du schéma d'extraction LLM | `pipeline/ingest.py` (`SYSTEM_PROMPT`) + `pipeline/core.py` (`save_decision`) + `models.py` + `schemas.py` + `types.ts` (5 fichiers, toujours ensemble) |
| Logique d'estimation « Mon Cas » | `backend/app/services/predictor.py` (percentiles, checklist, alertes) |
| Débit/concurrence GLM | `pipeline/core.py` (`AdaptiveLimiter`) + flags `--concurrency`/`--max-chars` de `pipeline/ingest.py` |
| Sources Open Data | `pipeline/dila.py` (BFS + fonds) ; formats : `parse_juri_xml` (XML DILA) et `_json_payloads` (JSON) dans `core.py`/`ingest.py` |
| Moniteur | `backend/app/routers/pipeline.py` (lit `pipeline_state/logs/processed_archives`) + `frontend/app/pipeline/page.tsx` |

## Pièges connus

- **Nommage Pydantic** : les champs `*_pct` du schéma doivent correspondre EXACTEMENT aux
  kwargs des routers (deux bugs `pc_taux_accorde`/`pc_taux_accorde_pct` déjà corrigés —
  le smoke test du point 1 les détecte).
- **Stats agrégées en Python** (chargement des décisions filtrées) : correct jusqu'à
  ~50 k décisions ; à l'échelle, passer sur agrégats SQL/JSONB (Postgres via `JURISDIVORCE_DB`).
- **CORS** : regex `http://(localhost|127\.0\.0\.1):\d+` — couvre tout port local, rien d'autre.
- **Traitement d'arrière-plan** : les serveurs lancés en background sous Windows peuvent
  survivre au stop de la tâche (`npm start`) → tuer via PowerShell
  `Get-NetTCPConnection -LocalPort <p> | % { Stop-Process -Id $_.OwningProcess -Force }`.
- **Réponse LLM** : toujours passer par `repair_json()` (fences markdown, virgules finales)
  — jamais de `json.loads` brut.
- **Troncature** : `smart_truncate` préserve en-tête + motifs + dispositif ; ne PAS tronquer
  par la fin brute (les montants de l'état liquidatif sont dans les derniers paragraphes).
