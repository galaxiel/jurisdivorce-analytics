# Cahier des Charges & Mega-Prompt Technique : JurisDivorce Analytics

*Spécification complète pour la création d'une plateforme d'analyse statistique et décisionnelle de la jurisprudence en droit de la famille (Divorce, Liquidation de régime matrimonial & Partage).*

> Archive : prompt d'origine du projet (conversation ZCode du 19/11/2026), conservé à l'identique.

---

## 1. Vision du Projet & Architecture Générale

### 1.1 Objectif
Construire une plateforme web moderne ("Boussole & Analytics Liquidation-Partage") qui transforme des dizaines de milliers de décisions de justice brutes (Cour de cassation, Cours d'appel, Tribunaux) en un **moteur d'intelligence décisionnelle et statistique**.

L'application permet à un particulier en instance de divorce, un avocat ou un notaire de :
1. **Évaluer objectivement la valeur d'un litige** (indemnités d'occupation, récompenses, créances, prestation compensatoire).
2. **Connaître le taux de succès réel** des arguments juridiques et des types de preuves fournies.
3. **Comparer les disparités statistiques** entre Cours d'appel (Paris vs Lyon vs Aix-en-Provence, etc.).
4. **Simuler son propre cas** ("Mon Cas") pour obtenir une estimation chiffrée basée sur la jurisprudence réelle.

### 1.2 Principes d'Architecture & Modularité Élevée
Pour garantir la pérennité du projet et la possibilité de **refondre l'interface visuelle à tout moment via un autre LLM**, l'architecture repose sur un **découplage strict** entre le pipeline de données, l'API REST backend et les composants d'interface UI.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       1. SOURCES DE DONNÉES HYBRIDES                        │
│  [ Archives Brutes Open Data Tar.gz ]  -->  (Futur) [ API PISTE Judilibre ] │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 2. PIPELINE D'INGESTION & TRAITEMENT BATCH                  │
│  - Extraction & Filtre Mots-clés Regex (Local Python, 0 token)              │
│  - Worker Asynchrone GLM-4/5 Flash (Zhipu AI - OpenAI Compliant API)       │
│  - Traitement d'erreur, Rate-Limiting & Parseur JSON Strict                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3. BASE DE DONNÉES CENTRALISÉE                           │
│  - PostgreSQL / SQLite (SQLModel / SQLAlchemy)                              │
│  - Indexation Mots-Clés, JSONB, Index Spatiaux / Juridictionnels           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ API REST JSON (OpenAPI / Swagger)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    4. FRONTEND MODULAIRE (NEXT.JS 14+)                      │
│  - UI Layer (Tailwind CSS, Shadcn/UI, Lucide Icons, Recharts/Tremor)        │
│  - Composants indépendants et découplés (Themeable / Easy Re-skinning)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Hybride des Données & Consommation de Tokens

### 2.1 Mode Données Brutes (Priorité Immédiate)
L'ingestion initiale ne nécessite aucune clé d'API administrative. Elle télécharge directement les dumps Open Data hébergés sur `echanges.dila.gouv.fr` ou `data.gouv.fr`.

1. **Téléchargement & Pré-filtrage Local (0 Token) :**
   * Un script Python scanne les archives `.tar.gz` / `.json` des décisions de justice.
   * Il applique une expression régulière (Regex) stricte pour ne retenir **que** les affaires liées au partage matrimonial.
   * *Mots-clés de filtrage :* `"liquidation du régime matrimonial"`, `"état liquidatif"`, `"indemnité d'occupation"`, `"récompense"`, `"créance entre époux"`, `"prestation compensatoire"`, `"procès-verbal de difficultés"`, `"juge aux affaires familiales"`.

2. **Élimination des Doublon & Décisions Incomplètes :**
   * Calcul du hash MD5 de la décision pour éviter les doublons.
   * Ignorer les décisions où les motifs sont occultés (principalement certaines 1res instances JAF) pour ne garder que les décisions exploitables (Cours d'appel & Cour de cassation).

### 2.2 Mode API PISTE / Judilibre (Évolution Future)
L'interface backend contiendra une abstraction `JudilibreClient` basculant via un simple drapeau de configuration (`USE_LIVE_API=true`) pour interroger l'API officielle Judilibre dès que les clés d'accès PISTE seront configurées.

### 2.3 Worker Asynchrone GLM-4/5 Flash (Zhipu AI / Z.ai)
Le script de traitement est optimisé pour maximiser le débit sans dépasser les quotas :
* **Base URL :** `https://open.bigmodel.cn/api/paas/v4/` (Compatible client `openai` Python).
* **Parallélisme Asyncio :** 15 à 30 requêtes simultanées (`asyncio.gather` avec `asyncio.Semaphore`).
* **Gestion des Rate Limits & Retry :** Backoff exponentiel automatique avec la librairie `tenacity`.
* **Rendu JSON Forcé :** Utilisation du paramètre `response_format={"type": "json_object"}`.

---

## 3. Schéma d'Extraction JSON (Prompt Système LLM)

Chaque décision retenue est soumise au LLM avec le prompt système d'extraction structurée ci-dessous :

```system_prompt
Tu es un expert juriste en droit de la famille et un analyste de données judiciaires français.
Ta tâche est d'analyser l'arrêt ou le jugement fourni et d'extraire TOUTES les informations financières, factuelles et juridiques sous la forme d'un objet JSON STRICT respectant scrupuleusement le schéma demandé.

Règles de traitement :
1. Si une information est absente du texte, indique `null`. Ne devine ni n'invente jamais d'information.
2. Exprime tous les montants monétaires en nombres purs (ex: 1500.50 et non "1 500,50 €").
3. Garde une synthèse neutre, factuelle et orientée sur le raisonnement de la décision.

Schéma JSON de sortie :
{
  "metadata": {
    "juridiction": "Nom de la Cour d'appel ou Tribunal (ex: Cour d'appel de Paris)",
    "chambre": "Nom de la chambre (ex: Pole 3 Chambre 1)",
    "date_decision": "YYYY-MM-DD",
    "numero_pourvoi_rg": "Numéro RG ou de pourvoi"
  },
  "contexte_familial": {
    "regime_matrimonial": "COMMUNAUTE_REDUITE_AUX_ACQUETS | SEPARATION_DE_BIENS | PARTICIPATION_AUX_ACQUETS | COMMUNAUTE_UNIVERSELLE | INCONNU",
    "duree_mariage_annees": number | null,
    "nombre_enfants": number | null
  },
  "biens_litigieux": {
    "bien_immobilier_principal": boolean,
    "valeur_bien_principal": number | null,
    "entreprises_societes": boolean,
    "comptes_epargne": boolean
  },
  "indemnite_occupation": {
    "demandee": boolean,
    "accordee": boolean,
    "montant_mensuel_base_valeur_locative": number | null,
    "pourcentage_abattement_accorde": number | null,
    "montant_mensuel_final": number | null,
    "duree_mois_retenue": number | null,
    "montant_total_accorde": number | null,
    "motifs_rejet_ou_reduction": "Texte explicatif court des raisons de l'abattement ou du rejet"
  },
  "recompenses_et_creances": [
    {
      "categorie": "TRAVAUX_BIEN_PROPRE | REMBOURSEMENT_EMPRUNT | APPORT_FONDS_PROPRE | AUTRE",
      "demandeur": "EPOUX_A | EPOUX_B",
      "montant_reclame": number | null,
      "montant_accorde": number | null,
      "statut": "ACCORDE_TOTALEMENT | ACCORDE_PARTIELLEMENT | REJETE",
      "preuve_clef_retenue": "Description de la preuve qui a fait gagner (ex: factures avec nom exact)",
      "motif_echec": "Raison si rejeté (ex: attestation insuffisante, défaut de preuve du paiement personnel)"
    }
  ],
  "prestation_compensatoire": {
    "demandee": boolean,
    "accordee": boolean,
    "forme": "CAPITAL_UNIQUE | RENTE_MENSUELLE | MIXTE | AUCUNE",
    "montant_capital_accorde": number | null,
    "montant_rente_mensuelle": number | null,
    "duree_rente_mois": number | null
  },
  "frais_et_depens": {
    "article_700_montant": number | null,
    "partage_depens": "DESIGNE_EPOUX_A | DESIGNE_EPOUX_B | PARTAGE_MOITIE | REJET"
  },
  "analyse_strategique": {
    "points_forts_gagnants": ["Liste des 2 à 4 arguments juridiques/preuves décisifs"],
    "pieges_et_erreurs_a_eviter": ["Liste des 2 à 4 erreurs commises par la partie perdante"],
    "resume_decision_3_lignes": "Résumé limpide pour un non-juriste"
  }
}
```

---

## 4. Spécification Fonctionnelle & Expérience Utilisateur (UI/UX)

L'interface utilisateur doit être **ultra-moderne, épurée, responsive** et proposer un mode Sombre/Clair (*Dark/Light Mode*).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             MENU DE NAVIGATION                              │
│ [ Dashboard Analytics ]  [ Boussole / Mon Cas ]  [ Explorer Jurisprudence ] │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module 1 : Dashboard Analytics Général
Un tableau de bord macroscopique montrant les tendances et les moyennes réelles de la justice française :
* **Cartes KPI Clés :**
  * Taux moyen d'abattement sur l'indemnité d'occupation (ex: 20 % en moyenne nationale).
  * Montant moyen d'une récompense pour travaux sur bien propre.
  * Taux d'échec des réclamations sans factures nominatives (ex: 78 % de rejet).
* **Graphiques Interactifs (Recharts / Tremor) :**
  * *Distribution des Prestations Compensatoires* selon la durée du mariage.
  * *Comparatif par Cour d'Appel :* Histogramme des montants moyens d'indemnité d'occupation attribués à Paris vs Lyon vs Marseille vs Rennes.
  * *Top 5 des motifs de rejet* de créances entre époux.

### Module 2 : "La Boussole" (Simulateur / "Mon Cas")
Un questionnaire dynamique en 4 étapes permettant à un utilisateur d'entrer sa situation personnelle pour obtenir un **Rapport Prédictif Statistique** :
1. **Étape 1 — Statut & Régime :** Juridiction (Cour d'appel régionale), Régime matrimonial, Durée du mariage, Nombre d'enfants.
2. **Étape 2 — Le Bien & L'Occupation :** Valeur locative estimée de la maison, Qui a occupé le bien seul, Pendant combien de mois.
3. **Étape 3 — Travaux & Financement :** Qui a payé le crédit, Qui a fait des travaux, Quels types de preuves sont possédées (Factures nominatives, relevés bancaires personnels, attestations d'artisans, aucune).
4. **Résultat — Le Dashboard Prédictif :**
   * **Fourchette d'Indemnité d'Occupation estimée** (Minimum, Médiane, Maximum).
   * **Chances de succès calculées (%)** pour le remboursement des travaux selon les preuves cochées.
   * **5 Décisions de justice "Jumelles"** (cas réels ayant les caractéristiques les plus proches).

### Module 3 : Moteur de Recherche de Jurisprudence Avancé
Une vue tableau (Data Table) puissante avec filtres combinés en temps réel :
* **Filtres :** Cour d'Appel, Régime Matrimonial, Statut de la Récompense (Accordée / Rejetée), Présence de Prestation Compensatoire.
* **Fiche Décisionnelle Détaillée (Drawer / Modal) :** 
  * Vue côte-à-côte : Résumé structuré IA vs Extrait brut officiel de l'arrêt.
  * Badge de fiabilité et score de correspondance.

### Module 4 : Module d'Exportation PDF / Dossier d'Avocat
Génération d'un rapport synthétique téléchargeable en PDF (pour transmission à son avocat ou notaire lors d'un rendez-vous) synthétisant les statistiques du cas et les 3 arrêts de référence les plus favorables.

---

## 5. Structure du Code & Modularité Frontend (Facilité de Re-skinning)

Le code frontend doit respecter une organisation stricte permettant à n'importe quel développeur ou LLM d'effectuer une refonte graphique (Re-skinning) sans casser la logique de données.

### 5.1 Arborescence du Projet Next.js (App Router)

```text
frontend/
├── app/
│   ├── (routes)/
│   │   ├── layout.tsx                # Structure globale & ThemeProvider
│   │   ├── page.tsx                  # Landing Page / Dashboard Public
│   │   ├── analytics/page.tsx        # Vue Statistiques Globales
│   │   ├── boussole/page.tsx         # Simulateur "Mon Cas"
│   │   └── jurisprudence/page.tsx    # Moteur de recherche & Tableaux
│   └── globals.css                   # Tailwind CSS & variables de thème
├── components/
│   ├── ui/                           # Composants Atomiques Shadcn (Boutons, Inputs, Modals)
│   ├── charts/                       # Composants Graphiques isolés (Pie, Bar, Line)
│   ├── boussole/                     # Étapes du questionnaire
│   ├── jurisprudence/                # Tableaux & Cartes de cas
│   └── layout/                       # Header, Sidebar, Footer (Facilement remplaçables)
├── lib/
│   ├── api.ts                        # Layer Client HTTP (Fetch API REST)
│   ├── types.ts                      # Types TypeScript générés depuis le schéma JSON
│   └── utils.ts                      # Formatters de monnaie, dates, filtres
```

### 5.2 Directives UI pour le LLM Graphique
* **Thème Tailwind par variables CSS :** Les couleurs (`primary`, `secondary`, `accent`, `background`) doivent utiliser des variables CSS HSL dans `globals.css` pour permettre un changement de thème instantané.
* **Composants d'affichage isolés :** Ne jamais mélanger les appels `fetch()` dans les composants de rendu d'UI. Utiliser des hooks React custom (`useAnalytics()`, `useJurisprudence()`).

---

## 6. Guide de Démarrage & Script d'Ingestion Python (Prêt à l'Emploi)

Ce script Python `ingest_judilibre_brut.py` télécharge les archives Open Data, filtre les décisions pertinentes et les soumet de manière asynchrone à l'API Zhipu AI GLM Flash.

```python
import os
import re
import json
import asyncio
import aiohttp
import tarfile
import sqlite3
from typing import Dict, Any, List
from openai import AsyncOpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "VOTRE_CLE_API_ZHIPU")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
DB_PATH = "jurisprudence_divorce.db"
CONCURRENCY_LIMIT = 20

KEYWORDS_REGEX = re.compile(
    r"(liquidation du régime matrimonial|état liquidatif|indemnité d'occupation|récompense|créance entre époux|prestation compensatoire)",
    re.IGNORECASE
)

client = AsyncOpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL)
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# ---------------------------------------------------------------------------
# BASE DE DONNÉES LOCALES (SQLite)
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions_analysées (
            id TEXT PRIMARY KEY,
            numero_rg TEXT,
            juridiction TEXT,
            date_decision TEXT,
            raw_text TEXT,
            extracted_json JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_decision(decision_id: str, metadata: dict, raw_text: str, extracted_json: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO decisions_analysées (id, numero_rg, juridiction, date_decision, raw_text, extracted_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        decision_id,
        metadata.get("numero_pourvoi_rg"),
        metadata.get("juridiction"),
        metadata.get("date_decision"),
        raw_text,
        json.dumps(extracted_json, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# APPEL LLM ASYNCHRONE (GLM-4/5 Flash)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Tu es un expert juriste en droit de la famille français. Analyse l'arrêt fourni et extrait TOUTES les données selon le schéma JSON strict demandé. Réponds UNIQUEMENT avec l'objet JSON."""

async def process_decision_with_llm(decision_id: str, text: str):
    async with semaphore:
        # Tronquer le texte si supérieur à 30 000 caractères
        truncated_text = text[:30000]
        try:
            response = await client.chat.completions.create(
                model="glm-4-flash", # Ou version ultérieure
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Voici le texte de la décision de justice :\n\n{truncated_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            result_json = json.loads(response.choices[0].message.content)
            metadata = result_json.get("metadata", {})
            save_decision(decision_id, metadata, truncated_text, result_json)
            print(f"[SUCCESS] Décision {decision_id} analysée et enregistrée.")
        except Exception as e:
            print(f"[ERROR] Échec du traitement de la décision {decision_id}: {e}")

# ---------------------------------------------------------------------------
# PIPELINE D'EXTRACTION DE FICHIERS TAR.GZ / JSON
# ---------------------------------------------------------------------------
async def run_pipeline(tar_gz_path: str):
    init_db()
    tasks = []
    
    print(f"Ouverture de l'archive : {tar_gz_path}")
    with tarfile.open(tar_gz_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile() and member.name.endswith(".json"):
                f = tar.extractfile(member)
                if f:
                    content = f.read().decode('utf-8', errors='ignore')
                    try:
                        data = json.loads(content)
                        text_content = data.get("text", "") or data.get("contenu", "")
                        
                        # Filtre Regex local sans consommer de tokens
                        if KEYWORDS_REGEX.search(text_content):
                            decision_id = data.get("id", member.name)
                            tasks.append(process_decision_with_llm(decision_id, text_content))
                    except Exception as err:
                        continue
                        
    print(f"{len(tasks)} décisions pertinentes trouvées. Lancement de l'analyse LLM...")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Remplacer par le chemin vers votre archive Open Data téléchargée
    archive_path = "export_judilibre_cour_appel_2025.tar.gz"
    if os.path.exists(archive_path):
        asyncio.run(run_pipeline(archive_path))
    else:
        print(f"Veuillez télécharger l'archive Open Data et ajuster le chemin : {archive_path}")
```

---

## 7. Plan de Déploiement & Évolutions

1. **Phase 1 (Jours 1 à 3) :** Ingestion massive des archives de 3 Cours d'appel majeures (Paris, Versailles, Aix-en-Provence) et population de la base SQLite/Postgres.
2. **Phase 2 (Jours 4 à 7) :** Lancement de l'API Backend FastAPI exposant les endpoints de statistiques de filtres et du simulateur "Mon Cas".
3. **Phase 3 (Jours 8 à 12) :** Intégration du Frontend Next.js + Tailwind CSS avec les composants graphiques et la Data Table.
4. **Phase 4 (Post-Quota) :** Bascule vers la mise à jour continue via l'API PISTE Judilibre et monétisation des accès ou exports PDF.
