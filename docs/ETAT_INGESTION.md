# ÉTAT D'INGESTION — plan en cours (à jour 2026-11-21)

> **Fichier opérationnel** : quiconque reprend le projet (agent ou humain) lit ceci AVANT de lancer
> quoi que ce soit sur le pipeline. Mis à jour à chaque étape. Ne pas écraser la config sans lire.

## ⚠️ Consignes pendant la campagne (sinon collision garantie)

- **NE PAS soumettre le formulaire** `/pipeline` (PUT /api/pipeline/config) tant que
  `pipeline_state.status = running` — c'est le seul écrivain d'`app_config` et une soumission
  périmée a déjà provoqué 14 000 échecs (noms de modèles croisés entre endpoints).
- **NE PAS cliquer « Relancer les échecs »** : le backend draine avec SON client (endpoint Zhipu)
  et SON modèle → mauvaise combinaison avec la campagne OpenRouter en cours.
- Config attendue pendant la campagne (table `app_config`) :
  `model=tencent/hy4-flash` · `max_concurrency=8` · `max_chars=16000`.
  Un **watchdog** (tâche de fond de la session ZCode du 2026-11-21) la restaure toutes les 5 min.
- Un seul process de campagne à la fois. Vérifier :
  `powershell "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? CommandLine -match 'pipeline'"`.

## Situation au 2026-11-21

- **Campagne OpenRouter hy4-flash EN COURS** (validée par probe 5/5, ~2-3 €, decision utilisateur) :
  `python -m pipeline.ingest run --local archives/Freemium_capp… archives/Freemium_cass… --force
  --analyze --keep-archives` avec `JURISDIVORCE_PROVIDER=openrouter` + env de `backend/.env`.
- 1 600 décisions analysées ; ~15 000 lignes en DLQ (échecs des deux époques : 429 z.ai gratuits
  + collision décrite plus haut) → **toutes retentables**, aucune donnée perdue.
- Démo SYNTHETIQUE_DEMO **supprimée** (base 100 % réelle, ~1 900 décisions et montante).

## Étapes restantes (dans l'ordre)

1. **Fin de campagne** (notification ou `pipeline_state.status != running`).
2. **Drain DLQ** avec hy4-flash sur OpenRouter — boucle jusqu'à DLQ vide :
   ```bash
   set -a && source backend/.env && set +a
   export JURISDIVORCE_PROVIDER=openrouter ZHIPU_BASE_URL=https://openrouter.ai/api/v1
   # app_config : model=tencent/hy4-flash, max_concurrency=8, max_chars=16000
   python -m pipeline.ingest retry-failed   # traite 500 lignes/run, répéter (attempts++ si échec, delete si succès)
   ```
   Puis purger les lignes DLQ devenues inutiles :
   `DELETE FROM failed_decisions WHERE decision_id IN (SELECT id FROM decisions)`.
3. **Ingestion INCA** (dump déjà téléchargé : `archives/Freemium_inca_global_20261108-140000.tar.gz`,
   664 Mo) — `INCA` est déjà dans `KNOWN_FONDS` (pipeline/dila.py) :
   ```bash
   python -m pipeline.ingest run --local archives/Freemium_inca_global_20261108-140000.tar.gz --force --analyze --keep-archives
   ```
   (même env OpenRouter/hy4 ; probe d'abord si doute : `python -m pipeline.ingest probe --provider openrouter --model tencent/hy4-flash --n 5`)
4. **Nettoyage CAPP** : vérifier que le trou « s'arrête au 30/06/2009 » est comblé —
   `SELECT min(date_decision), max(date_decision) FROM decisions` doit couvrir 1995→2026
   (le trou venait de l'interruption du 1ᵉʳ run z.ai, ordre par identifiant = dates croissantes).
5. **Rapport final chiffré** (demandé par Hermes) : total décisions ; min/max `date_decision` par
   source ; répartition des juridictions INCA ; preuve de dédoublonnage :
   `SELECT count(*) = count(DISTINCT UPPER(juridiction)||date_decision||re.sub("[^A-Z0-9]", "", UPPER(numero_rg))) FROM decisions` (calculer la clé en Python, pas en SQL).
6. **Re-générer les snapshots statiques** (`scripts/export_static_bundle.py`) — ils contiennent
   encore la démo. **Ne pas redéployer le cloud sans ajuster le seed** (re-seederait la démo).
7. **Commit + push** de tous les correctifs non commités (attempts DLQ, providers+probe,
   timezone backend, INCA+fonds+test, garde dédoublonnage, duree int, watchdog note).

## Correctifs non commités au 2026-11-21 (working tree)

- `pipeline/ingest.py` : `record_failure(attempts=)` (crash DLQ) ; presets fournisseurs
  (`--provider` openrouter/groq/mistral/deepseek/zai/bigmodel) ; sous-commande `probe`
  (validation déterministe GO/NO-GO, exit 0 si ≥80 %) ; précédence clé provider > ZHIPU_API_KEY.
- `pipeline/core.py` : garde dédoublonnage cross-fonds dans `save_decision` ; `duree_mariage_annees`
  /`nombre_enfants` castés en int (les modèles renvoient 39.4 → le schéma API veut int).
- `backend/app/routers/pipeline.py` : fix timezone naïf/aware sur /state et /benchmark (500 moniteur).
- `pipeline/dila.py` : `INCA` dans `KNOWN_FONDS`.
- `tests/test_pipeline_core.py` : tests resolve_provider, _validate_extraction, fonds/parse INCA.
- Base : 40 tests pytest verts ; démo supprimée ; data float castée.
