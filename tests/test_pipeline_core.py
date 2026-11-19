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
    normalize_regime,
    parse_juri_xml,
    repair_json,
    save_decision,
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
    assert normalize_regime("indivision simple") == "INDIVISION"

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
