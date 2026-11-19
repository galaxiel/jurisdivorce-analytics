# ÉTAT DU PROJET — snapshot pour reprise par un agent

*Dernière mise à jour : 2026-11-19 · dépôt `galaxiel/jurisdivorce-analytics` (privé, `main`)*
*Lire aussi : `AGENTS.md` (règles + commandes) et `docs/DECISIONS.md` (pourquoi des choix).*

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

**Données actuelles** : `backend/jurisprudence.db` = 1 135 décisions `SYNTHETIQUE_DEMO`
(seed v2) + tables pipeline (`pipeline_state`, `pipeline_logs`, `processed_archives` avec
l'archive CAPP réelle).

## ❌ Ce qui n'existe PAS encore (roadmap priorisée)

1. **Campagne `--analyze` réelle avec ZHIPU_API_KEY** — tout est prêt (worker, dedup,
   reprise, monitor) ; il manque la clé + le lancement :
   `python -m pipeline.ingest run --download --fonds CAPP,CASS --analyze --concurrency 50 --max-chars 16000`.
2. **API PISTE / Judilibre officielle** (Phase 4 du cahier des charges) : abstraction
   `JudilibreClient` à créer dans `pipeline/` pour dépasser le périmètre freemium
   (le dump public CAPP = 26 k décisions toutes matières, dont 2 001 pertinentes ;
   le volume « 85 % des partages chiffrés » au-delà exige PISTE).
3. **CI GitHub Actions** (build frontend + smoke backend à chaque push) — dépôt prêt, workflow absent.
4. **Tests unitaires formels** (pytest pour filter/predictor/repair_json, vitest/jest front) —
   aujourd'hui validations via smoke scripts heredoc dans `AGENTS.md`.
5. **Export PDF vrai** (actuellement : Markdown téléchargeable + `window.print()`).
6. **Recherche sémantique** (embeddings) — l'explorateur est plein texte LIKE ; le schéma le
   permet (colonne `resume_3_lignes` + `extracted_json`).
7. **Postgres + agrégats SQL** — voir piège « stats agrégées en Python » dans `AGENTS.md`.
8. **Monétisation / auth** (Phase 4) — aucune authentification aujourd'hui.

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
