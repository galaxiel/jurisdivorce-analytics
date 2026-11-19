# AGENTS.md — Instructions pour tout agent IA travaillant sur ce dépôt

*Lis ce fichier en premier. Contexte détaillé : `docs/STATE.md` (état vérifié) et
`docs/DECISIONS.md` (choix techniques et leur pourquoi). Les prompts fondateurs sont
archivés dans `docs/`.*

## 🚨 Règle d'Or N°5 — Périmètre du droit (Loi du 31 décembre 1971) 🚨

> **BOUCLIER JURIDIQUE — LECTURE OBLIGATOIRE AVANT TOUTE MODIFICATION D'INTERFACE, DE
> CALCULATEUR, DE SIMULATEUR OU D'EXPORT**

En France, la consultation juridique personnalisée est un **monopole réservé aux avocats
et notaires** (loi n° 71-1130 du 31 décembre 1971). Cette plateforme est un outil
**statistique et factuel** : elle observe la jurisprudence passée, elle ne conseille pas.

### INTERDICTIONS ABSOLUES

- ❌ Ne génère JAMAIS un texte prescriptif : *"Vous avez droit à X €"*, *"Demandez X €
  au juge"*, *"Votre ex-conjoint est en tort"*, *"Vous allez gagner"*, *"Nous vous
  conseillons de…"*, *"La solution est…"*.
- ❌ N'utilise JAMAIS les titres suivants dans un export : *"Conclusions"*, *"Avis
  juridique"*, *"Assignation"*, *"Requête"*, *"Plaidoirie"*.
- ❌ Ne présente JAMAIS une fourchette comme un montant "du", "obtenu", "garanti" ou
  "auquel vous avez droit" — uniquement comme "médiane observée", "fourchette
  constatée", "percentile".

### OBLIGATIONS DE FORMULATION

- ✅ **Statistique et factuelle uniquement** : *"Dans X % des arrêts similaires rendus par
  la Cour d'appel de [Ville], le montant médian constaté est de Y €."*
- ✅ *"Les motifs de rejet les plus fréquemment relevés dans la base pour ce type de
  demande sont…"*
- ✅ *"Sur [N] décisions comparables, la fourchette observée va de X € à Z €, avec une
  médiane à Y €."*
- ✅ **TITRE OBLIGATOIRE DES EXPORTS** : *"Dossier de synthèse statistique et
  jurisprudentielle pour préparer votre rendez-vous avec votre avocat ou notaire"* —
  jamais *"Conclusions"*, *"Avis juridique"* ou *"Assignation"*.
- ✅ **CLAUSE DE NON-RESPONSABILITÉ** : le composant `<LegalDisclaimerFooter />` doit être
  présent en pied de page de toutes les routes publiques et en en-tête de chaque document
  exporté. Ne jamais le supprimer ni le raccourcir.

### Checklist avant commit

- [ ] Aucun texte prescriptif ajouté dans les composants, exports ou calculateurs ?
- [ ] Le composant `<LegalDisclaimerFooter />` est-il présent sur toutes les routes ?
- [ ] Les titres d'exports respectent-ils la formulation obligatoire ?
- [ ] Les montants sont-ils présentés comme des observations statistiques (médiane,
      fourchette, percentile) et non comme des droits ?

## Vue d'ensemble (30 secondes)

JurisDivorce Analytics = plateforme d'analyse statistique de la jurisprudence
divorce/liquidation-partage. Chaîne : **archives Open Data DILA (CAPP/CASS, XML) →
filtre local 0 token → worker GLM Flash async → SQLite aplanie → API FastAPI →
frontend Next.js 5 vues**. Les deux routes historiques (`/boussole`, `/jurisprudence`)
redirigent vers `/simulateur` et `/decisions`.

## Commandes de vérification (à exécuter après CHAQUE modification)

```bash
# 1. Suite pytest formelle : 26 tests (pipeline + API, ~3 s) — DOIT rester vert
pytest tests -q
#    (après toute modification du seed/schéma : python -m app.seed depuis backend/ d'abord)

# 2. Frontend : type-check + build + prerender (doit passer sans erreur)
cd frontend && npm run build && cd ..

# 3. Pipeline : dry-run (0 token) sur une archive de test
python -m pipeline.ingest run --local <archive.tar.gz> --dry-run --db /tmp/test.db
python -m pipeline.ingest status --db /tmp/test.db

# La CI (.github/workflows/ci.yml) rejoue 1 + 2 + un dry-run pipeline à chaque push :
# `gh run list --repo galaxiel/jurisdivorce-analytics` pour vérifier qu'elle reste verte.
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
| Nouveau graphique / tendance | `backend/app/routers/stats.py` + `frontend/components/charts/*` + `app/analytics/page.tsx` |
| Nouvelle vue frontend | `frontend/app/<route>/page.tsx` + composants dédiés ; ancienne route → redirect |
| Évolution du schéma d'extraction LLM | `pipeline/ingest.py` (`SYSTEM_PROMPT`) + `pipeline/core.py` (`save_decision`) + `models.py` + `schemas.py` + `types.ts` (5 fichiers, toujours ensemble) |
| Logique d'estimation « Mon Cas » | `backend/app/services/predictor.py` (percentiles, checklist, alertes) |
| Calculateur juridique (815-9 / 1469) | `backend/app/routers/calculateur.py` + `frontend/app/calculateur/page.tsx` |
| Radar des pièges | `/api/stats/pieges` (`routers/stats.py`) + `frontend/app/pieges/page.tsx` |
| Export de documents (Dire à Notaire) | `frontend/lib/dossier.ts` (Markdown / Word .doc / impression) |
| Débit/concurrence GLM | `pipeline/core.py` (`AdaptiveLimiter`, `BatchWriter`) + flags `--concurrency`/`--max-chars` de `pipeline/ingest.py` + config à chaud (`app_config`, GET/PUT `/api/pipeline/config`) |
| Recherche plein texte (FTS5) | `backend/app/database.py` (`ensure_fts` : index + triggers + rebuild) + `services/query.py` (`_fts_search_ids`, repli LIKE) |
| Sources Open Data | `pipeline/dila.py` (BFS + tri + fonds) ; formats : `parse_juri_xml` (XML DILA) et `_json_payloads` (JSON) dans `core.py`/`ingest.py` |
| DLQ / relance des échecs | table `failed_decisions` + `record_failure()`/`read_config()` (core.py) + `drain_failed` (ingest.py) + POST `/api/pipeline/retry-failed` + CLI `retry-failed` |
| Moniteur / santé | `backend/app/routers/pipeline.py` + `/api/health` (main.py) + `frontend/app/pipeline/page.tsx` + dot navbar (`header.tsx`) |
| Mode démo | `backend/app/routers/demo.py` (`is_demo=true`) + `components/demo-banner.tsx` |

## Pièges connus

- **Nommage Pydantic** : les champs `*_pct` du schéma doivent correspondre EXACTEMENT aux
  kwargs des routers (deux bugs `pc_taux_accorde`/`pc_taux_accorde_pct` déjà corrigés —
  `pytest tests -q` les détecte).
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
- **BatchWriter** : `task_done()` doit être appelé **par item** (pas par lot) sinon
  `queue.join()` n'aboutit jamais (deadlock).
- **FTS5** : ne JAMAIS splitter le SQL des triggers sur `;` (BEGIN…END en contiennent) —
  utiliser la liste `FTS_STATEMENTS` ; `executescript()` n'existe pas sur une connexion
  SQLAlchemy. Rebuild automatique si compte `decisions_fts` ≠ `decisions`.
- **null vs 0** : `montant_accorde = 0` réservé aux demandes REJETE (règle prompt n°4 +
  `norm_amount` + save_decision) ; agrégats toujours sur valeurs non-NULL.
