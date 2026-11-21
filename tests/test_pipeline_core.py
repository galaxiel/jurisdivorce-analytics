"""Tests du pipeline : filtre, normalisation, null/0, réparation JSON, troncature,
extraction XML DILA, limiteur adaptatif et BatchWriter."""
import asyncio

import pytest

from pipeline.core import (
    AdaptiveLimiter,
    BatchWriter,
    PipelineStateWriter,
    connect_db,
    decision_filter,
    norm_amount,
    normalize_juridiction,
    normalize_mode_garde,
    normalize_nature,
    normalize_pc_forme,
    normalize_regime,
    normalize_type_procedure,
    parse_juri_xml,
    repair_json,
    save_decision,
    save_raw_fiche,
    smart_truncate,
)

# ---------------------------------------------------------- filtre normalisé
def test_fort_terme_sans_accents():
    texte = "L'INDIVISION POST-COMMUNAUTAIRE est liquidée par le notaire… " * 30
    keep, why = decision_filter(texte)
    assert keep and why.startswith("fort:")

def test_deux_termes_secondaires_avec_epoux():
    texte = "Après le divorce, l'attribution préférentielle de la soulte et l'article 270 ont été discutés par les époux. " * 30
    keep, why = decision_filter(texte)
    assert keep and why.startswith("secondaires:")

def test_rejets_du_filtre():
    assert decision_filter("Trop court")[0] is False
    keep, why = decision_filter("Les motifs de la decision occultes rendent l'arrêt inexploitable. " * 80)
    assert not keep and why == "motifs occultes"
    keep, why = decision_filter("Contrat de travail et licenciement sans rapport. " * 200)
    assert not keep and why == "hors champ"

def test_pseudonymisation_nest_pas_un_rejet():
    texte = "Décision pseudonymisée avec [...] et *** sur les noms, liquidation du régime matrimonial. " * 60
    assert decision_filter(texte)[0] is True

def test_filtre_concubinage_et_demandes_annexes():
    # Contexte concubinage/PACS (pas de « divorce » ni « époux ») + 2 termes secondaires
    t1 = ("Indivision entre concubins après rupture de l'union libre : soulte et licitation du bien. " * 30)
    assert decision_filter(t1)[0] is True
    # Pension alimentaire + art. 700 dans un contexte divorce
    t2 = ("Le divorce est prononcé ; pension alimentaire pour les enfants et condamnation art. 700 CPC. " * 30)
    assert decision_filter(t2)[0] is True
    # art. 262-1 + communauté universelle (dans un contexte divorce)
    t3 = ("Le divorce est prononcé. Date des effets patrimoniaux fixée au 262-1 ; communauté universelle avec préciput. " * 30)
    assert decision_filter(t3)[0] is True
    # Sans contexte famille, même avec des termes secondaires → rejet (anti-bruit)
    t3b = ("Date des effets patrimoniaux fixée au 262-1 ; communauté universelle avec préciput. " * 30)
    assert decision_filter(t3b)[0] is False
    # Toujours hors champ sans contexte famille
    t4 = ("Soulte et licitation ordonnées en matière de succession entre frères et sœurs. " * 30)
    assert decision_filter(t4)[0] is False
    # Rappel élargi : 1 seul terme secondaire suffit dès qu'il y a le contexte famille
    t5 = ("Le divorce est prononcé ; une soulte est mise à la charge de l'époux. " * 30)
    assert decision_filter(t5)[0] is True

def test_save_raw_fiche_conserve_tout():
    conn = connect_db(":memory:")
    assert save_raw_fiche(conn, "id-1", "md5-1", "texte intégral de l'arrêt", "CASS", "arch.tar.gz") is True
    # doublon md5/id -> pas réinséré
    assert save_raw_fiche(conn, "id-1", "md5-1", "texte intégral de l'arrêt", "CASS", "arch.tar.gz") is False
    row = conn.execute("SELECT raw_text, fonds FROM raw_fiches WHERE id = 'id-1'").fetchone()
    assert row["raw_text"] == "texte intégral de l'arrêt" and row["fonds"] == "CASS"
    # une fiche REJETÉE par le filtre est quand même conservée
    rejet = "Texte sans aucun terme du champ, juste du contentieux commercial. " * 60
    assert decision_filter(rejet)[0] is False
    assert save_raw_fiche(conn, "id-2", "md5-2", rejet, "CAPP", "arch.tar.gz") is True

def test_raw_fiches_conservation_non_negociable():
    """Tripwire (Règle d'Or N°6) : la boucle d'ingestion doit sauvegarder la fiche brute
    AVANT d'appliquer le pré-filtre, et la table raw_fiches doit exister dans les schémas."""
    import io, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = io.open(os.path.join(root, "pipeline", "ingest.py"), encoding="utf-8").read()
    i_save = src.find("save_raw_fiche(")
    i_filter = src.find("decision_filter(")
    assert i_save != -1, "save_raw_fiche a disparu de pipeline/ingest.py (Règle d'Or N°6)"
    assert i_filter != -1, "decision_filter a disparu de pipeline/ingest.py"
    assert i_save < i_filter, "save_raw_fiche doit être appelé AVANT decision_filter (fiche sauvée même si rejetée)"
    core = io.open(os.path.join(root, "pipeline", "core.py"), encoding="utf-8").read()
    assert "CREATE TABLE IF NOT EXISTS raw_fiches" in core, "table raw_fiches manquante dans le schéma pipeline"
    db = io.open(os.path.join(root, "backend", "app", "database.py"), encoding="utf-8").read()
    assert "CREATE TABLE IF NOT EXISTS raw_fiches" in db, "table raw_fiches manquante dans le schéma backend"

# ---------------------------------------------------------- normalisation
def test_normalize_juridiction():
    assert normalize_juridiction("CA PARIS") == "Cour d'appel de Paris"
    assert normalize_juridiction("cour d'appel, Lyon, France") == "Cour d'appel de Lyon"
    assert normalize_juridiction("Cour d'appel d'AIX-EN-PROVENCE") == "Cour d'appel d'Aix-en-Provence"
    assert normalize_juridiction("Tribunal de grande instance de Lyon") == "Tribunal de grande instance de Lyon"

def test_normalize_juridiction_alias_villes_sans_ca():
    # Marseille relève d'Aix-en-Provence ; Nantes de Rennes — ces CA n'existent pas
    assert normalize_juridiction("Cour d'appel de Marseille") == "Cour d'appel d'Aix-en-Provence"
    assert normalize_juridiction("CA NANTES") == "Cour d'appel de Rennes"

def test_normalize_regime():
    assert normalize_regime("Séparation de biens") == "SEPARATION_DE_BIENS"
    assert normalize_regime("communauté réduite aux acquêts") == "COMMUNAUTE_REDUITE_AUX_ACQUETS"
    assert normalize_regime("communauté légale") == "COMMUNAUTE_REDUITE_AUX_ACQUETS"
    assert normalize_regime("communauté conventionnelle") == "COMMUNAUTE_REDUITE_AUX_ACQUETS"
    assert normalize_regime("communauté universelle") == "COMMUNAUTE_UNIVERSELLE"
    assert normalize_regime("participation aux acquêts") == "PARTICIPATION_AUX_ACQUETS"
    assert normalize_regime("indivision simple") == "INDIVISION"
    # Contrat avec clause de partage : parts inégales, préciput, attribution intégrale
    assert normalize_regime("contrat avec clause d'attribution intégrale") == "COMMUNAUTE_AVEC_CLAUSE"
    assert normalize_regime("communauté avec préciput au profit du conjoint survivant") == "COMMUNAUTE_AVEC_CLAUSE"
    assert normalize_regime("clause de parts inégales 70/30") == "COMMUNAUTE_AVEC_CLAUSE"
    assert normalize_regime("communauté universelle avec clause d'attribution intégrale") == "COMMUNAUTE_UNIVERSELLE"

def test_normalize_nature():
    # Codes du prompt → codes canoniques
    assert normalize_nature("TRAVAUX_BIEN_PROPRE") == "TRAVAUX_BIEN_PROPRE"
    # Labels FR (ancien prompt / variantes LLM) → codes
    assert normalize_nature("Travaux amélioration") == "TRAVAUX_BIEN_PROPRE"
    assert normalize_nature("Financement bien propre") == "FINANCEMENT_ACQUISITION"
    assert normalize_nature("Remboursement emprunt immobilier post-séparation") == "REMBOURSEMENT_EMPRUNT"
    assert normalize_nature("Apport fonds propres / héritage") == "APPORT_FONDS_PROPRES"
    assert normalize_nature("Recel de communauté") == "RECEL_COMMUNAUTE"
    assert normalize_nature("Compte joint vidé") == "COMPTE_JOINT_VIDE"
    assert normalize_nature("Taxes foncières / assurance") == "TAXES_ASSURANCE"
    # Inconnu → AUTRE (filtrable), jamais de texte brut
    assert normalize_nature("quelque chose d'inédit") == "AUTRE"
    assert normalize_nature(None) is None

def test_normalize_type_procedure():
    assert normalize_type_procedure("Liquidation-partage après divorce") == "Liquidation-partage après divorce"
    assert normalize_type_procedure("liquidation du régime matrimonial") == "Liquidation-partage après divorce"
    assert normalize_type_procedure("divorce pour altération définitive") == "Divorce contentieux"
    assert normalize_type_procedure("Appel sur ordonnance JAF") == "Appel sur ordonnance JAF"
    assert normalize_type_procedure(None) is None

def test_normalize_pc_forme_mode_garde():
    assert normalize_pc_forme("CAPITAL_UNIQUE") == "CAPITAL_UNIQUE"
    assert normalize_pc_forme("Capital unique") == "CAPITAL_UNIQUE"
    assert normalize_pc_forme("rente viagère mensuelle") == "RENTE_MENSUELLE"
    assert normalize_pc_forme("attribution du bien") == "ATTRIBUTION_BIEN"
    assert normalize_pc_forme("xyz") is None
    assert normalize_mode_garde("Garde alternée") == "Garde alternée"
    assert normalize_mode_garde("garde alternee") == "Garde alternée"
    assert normalize_mode_garde("classique") == "Résidence classique + DVH"
    assert normalize_mode_garde(None) is None

def test_norm_amount():
    assert norm_amount("-5") is None
    assert norm_amount("1200.50") == 1200.5
    assert norm_amount("abc") is None
    assert norm_amount(None) is None

# ---------------------------------------------------------- null vs 0
def test_save_decision_rejete_vaut_zero_et_accorde_inconnu_vaut_null():
    conn = connect_db(":memory:")
    ex = {
        "metadata": {"juridiction": "CA PARIS"},
        "contexte_familial": {"regime_matrimonial": "Séparation de biens"},
        "reclamations_financieres": [
            {"nature": "Travaux amélioration", "statut": "REJETE", "montant_reclame": 5000, "montant_accorde": None},
            {"nature": "Travaux amélioration", "statut": "ACCORDE_TOTALEMENT", "montant_reclame": 3000, "montant_accorde": 3000},
            {"nature": "Autre", "statut": "ACCORDE_PARTIELLEMENT", "montant_reclame": 1000},
        ],
    }
    save_decision(conn, "T1", "m1", "x" * 1300, ex)
    rows = conn.execute("SELECT statut, montant_accorde FROM recompenses ORDER BY id").fetchall()
    assert rows[0]["montant_accorde"] == 0.0      # rejeté explicite → 0
    assert rows[1]["montant_accorde"] == 3000.0   # accordé chiffré → valeur
    assert rows[2]["montant_accorde"] is None     # partiellement accordé non chiffré → NULL
    assert conn.execute("SELECT juridiction FROM decisions").fetchone()[0] == "Cour d'appel de Paris"

# ---------------------------------------------------------- réparation JSON
def test_repair_json_fences_et_virgules():
    assert repair_json('```json\n{"a": 1, "b": [1,2,],}\n```') == {"a": 1, "b": [1, 2]}
    assert repair_json('Voici le JSON : {"metadata": {"juridiction": "Paris"},}')["metadata"]["juridiction"] == "Paris"
    with pytest.raises(ValueError):
        repair_json("pas de json ici")

# ---------------------------------------------------------- troncature
def test_smart_truncate_preserve_en_tete_et_dispositif():
    arret = "EN-TETE AFFAIRE X c/ Y. " + ("DISCUSSION SUR LES RECOMPENSES. " * 3000) \
        + "PAR CES MOTIFS la Cour prononce l'etat liquidatif. " * 40
    tr = smart_truncate(arret, 48000)
    assert len(tr) <= 48000
    assert tr.startswith("EN-TETE")
    assert "PAR CES MOTIFS" in tr[-4500:]

# ---------------------------------------------------------- XML DILA
SAMPLE_XML = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><TEXTE_JURI_JUDI><META><META_COMMUN>"
    "<ID>JURITEXT000001</ID><NATURE>ARRET</NATURE></META_COMMUN>"
    "<META_SPEC><META_JURI><JURIDICTION>Cour d'appel de Versailles</JURIDICTION>"
    "<DATE_DEC>1998-05-07</DATE_DEC></META_JURI>"
    "<META_JURI_JUDI><NUMEROS_AFFAIRES><NUMERO_AFFAIRE>1994-9050</NUMERO_AFFAIRE></NUMEROS_AFFAIRES>"
    "</META_JURI_JUDI></META_SPEC></META><TEXTE><T>"
    + "La liquidation du régime matrimonial et l'état liquidatif sont prononcés. " * 20
    + "</T></TEXTE></TEXTE_JURI_JUDI>"
).encode()

def test_parse_juri_xml():
    parsed = parse_juri_xml(SAMPLE_XML)
    assert parsed and parsed["id"] == "JURITEXT000001"
    assert "COUR D'APPEL DE VERSAILLES" in parsed["text"]
    assert "1994-9050" in parsed["text"]

# ---------------------------------------------------------- fonds INCA (Cassation inédite)
SAMPLE_INCA_XML = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?><TEXTE_JURI_JUDI><META><META_COMMUN>"
    "<ID>INCA0001234</ID><NATURE>ARRET</NATURE><DATE_TEXTE>2024-03-15</DATE_TEXTE></META_COMMUN>"
    "<META_SPEC><META_JURI><JURIDICTION>COUR DE CASSATION</JURIDICTION>"
    "<DATE_DEC>2024-03-15</DATE_DEC></META_JURI></META_SPEC></META>"
    "<META_JURI_JUDI><NUMEROS_AFFAIRES><NUMERO_AFFAIRE>R 23-10.456</NUMERO_AFFAIRE></NUMEROS_AFFAIRES></META_JURI_JUDI>"
    "<PUBLI_BULL publie=\"non\"/>"
    "<TEXTE><BLOC_TEXTUEL><CONTENU>"
    + "Pourvoi inédit : la prestation compensatoire et la liquidation du régime matrimonial sont examinées. " * 24
    + "</CONTENU></BLOC_TEXTUEL></TEXTE></TEXTE_JURI_JUDI>"
).encode()


def test_fonds_inca_et_parse_inca():
    from pipeline.dila import fonds_from_path
    # fonds détecté depuis le nom de fichier ET depuis l'arborescence (…/juri/inca/global/…)
    assert fonds_from_path(
        "https://echanges.dila.gouv.fr/OPENDATA/INCA/Freemium_inca_global_20261108-140000.tar.gz") == "INCA"
    assert fonds_from_path(
        "archive/20261108/juri/inca/global/civile/JURI/TEXT/000001.xml") == "INCA"
    # structure identique à CASS : TEXTE_JURI_JUDI + PUBLI_BULL publie="non" (inédite)
    parsed = parse_juri_xml(SAMPLE_INCA_XML)
    assert parsed and parsed["id"] == "INCA0001234"
    assert "COUR DE CASSATION" in parsed["text"]
    assert "R 23-10.456" in parsed["text"]


# ---------------------------------------------------------- limiteur adaptatif
def test_adaptive_limiter_halving_and_set_target():
    async def scenario():
        lim = AdaptiveLimiter(50)
        assert lim.on_rate_limited() == 25
        assert lim.on_rate_limited() == 12
        await lim.acquire()
        await lim.release()
        await lim.set_target(40)
        assert lim.max_size == 40
    asyncio.run(scenario())

# ---------------------------------------------------------- Fournisseurs LLM (openai-compatibles)
def test_resolve_provider_presets():
    from pipeline.ingest import resolve_provider, PROVIDER_BASE_URLS
    # preset connu, casse insensible
    assert resolve_provider("OpenRouter", None) == "https://openrouter.ai/api/v1"
    assert resolve_provider("zai", None) == "https://api.z.ai/api/paas/v4/"
    # URL explicite : prioritaire sur tout
    assert resolve_provider("openrouter", "https://exemple.local/v1") == "https://exemple.local/v1"
    # défaut (bigmodel) sans provider ni URL
    assert resolve_provider(None, None) == PROVIDER_BASE_URLS["bigmodel"]
    # fournisseur inconnu -> ValueError
    with pytest.raises(ValueError):
        resolve_provider("inconnu", None)


# ---------------------------------------------------------- Validation déterministe des extractions
def test_validate_extraction_regles_chiffres():
    from pipeline.ingest import _validate_extraction
    # extraction propre : montants numériques ou null, juridiction normalisable
    bon = {"metadata": {"juridiction": "CA de Lyon"}, "montant_accorde": 12500, "capital": None,
           "indemnite_occupation": {"demandee": True, "montant_accorde": 25000}}
    assert _validate_extraction(bon) == []
    # montants non numériques → alertes (avec chemin complet)
    mauvais = {"metadata": {"juridiction": "CA de Lyon"}, "montant_accorde": "12 500 €",
               "soulte": {"montant": "12500 €"}, "taux": True}
    problems = _validate_extraction(mauvais)
    assert any("montant_accorde" in p for p in problems)
    assert any("soulte.montant" in p for p in problems)
    assert any("taux" in p for p in problems)
    # juridiction absente/non normalisable → alerte
    assert any("juridiction" in p for p in _validate_extraction({"montant_accorde": 5}))

# ---------------------------------------------------------- BatchWriter
def test_batch_writer_writes_all_decisions(tmp_path):
    async def scenario():
        db_path = str(tmp_path / "t.db")
        conn = connect_db(db_path)
        state = PipelineStateWriter(db_path)
        state.init("test", 0)
        writer = BatchWriter(conn, state, batch_size=25)
        task = asyncio.create_task(writer.run())
        for i in range(1, 61):
            ex = {"metadata": {"juridiction": "Lyon"},
                  "contexte_familial": {"regime_matrimonial": "Indivision"}}
            await writer.put(f"T{i:03d}", f"m{i}", "x" * 1300, ex)
        await asyncio.wait_for(writer.flush_remaining(), timeout=15)
        task.cancel()
        n = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        conn.close()
        state.close()
        return n
    assert asyncio.run(scenario()) == 60
