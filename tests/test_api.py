"""Tests de l'API : routes principales, calculateur, pièges, tendances, FTS, démo."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

ALL_ROUTES = [
    "/api/health", "/api/stats/overview", "/api/stats/facets", "/api/stats/comparatif-cours",
    "/api/stats/distribution-pc", "/api/stats/abattement-distribution", "/api/stats/succes-par-nature",
    "/api/stats/pc-correlation", "/api/stats/top-motifs-rejet", "/api/stats/recompenses-par-preuve",
    "/api/stats/tendances", "/api/stats/pieges", "/api/decisions?page_size=2",
    "/api/decisions/export?format=json", "/api/pipeline/state", "/api/pipeline/logs",
    "/api/pipeline/archives", "/api/pipeline/config", "/api/pipeline/benchmark", "/api/demo/count",
]

def test_toutes_les_routes_repondent(client):
    for url in ALL_ROUTES:
        r = client.get(url)
        assert r.status_code == 200, (url, r.status_code, r.text[:200])

def test_health_v3(client):
    h = client.get("/api/health").json()
    assert h["db_ok"] is True
    assert h["version"] == "3.0.1"
    assert h["decisions"] > 0

def test_filtres_croises(client):
    r = client.get("/api/decisions", params={
        "juridiction": "Cour d'appel de Lyon", "annee": 2023,
        "montant_min": 5000, "page_size": 5,
    })
    assert r.status_code == 200
    assert r.json()["total"] >= 0

def test_recherche_fts(client):
    # La recherche plein texte passe par l'index FTS5 (repli LIKE automatique)
    r = client.get("/api/decisions", params={"q": "occupation", "page_size": 5})
    assert r.status_code == 200
    assert r.json()["total"] > 0
    r2 = client.get("/api/decisions", params={"q": "absentdictionnairexyz", "page_size": 5})
    assert r2.status_code == 200  # aucun résultat mais pas d'erreur FTS

def test_detail_et_badges(client):
    item = client.get("/api/decisions", params={"page_size": 1}).json()["items"][0]
    d = client.get(f"/api/decisions/{item['id']}")
    assert d.status_code == 200
    detail = d.json()
    assert detail["resume_3_lignes"]
    assert "raw_excerpt" in detail and "recompenses" in detail

def test_calculateur_occupation(client):
    r = client.post("/api/calculateur/occupation", json={
        "juridiction": "Cour d'appel de Paris", "valeur_locative_mensuelle": 1100,
        "date_debut": "2020-01-01", "date_fin": "2026-11-19", "quote_part_autres_pct": 50,
    })
    assert r.status_code == 200
    res = r.json()
    assert res["mois"] > 0 and res["comparables"] and len(res["comparables"]) <= 10
    assert res["prescription"]["depassement_mois"] > 0  # 82 mois > 60

def test_calculateur_recompense(client):
    r = client.post("/api/calculateur/recompense", json={
        "valeur_bien_avant_travaux": 400000, "valeur_bien_actuelle": 480000,
        "montant_travaux": 60000, "nature": "amelioration",
    })
    assert r.status_code == 200
    res = r.json()
    assert res["regle"] == "Dépense faite"  # plus-value 80k > travaux 60k
    assert res["profit_subsistant"] == 60000.0

def test_pieges_structure(client):
    pieges = client.get("/api/stats/pieges").json()
    assert len(pieges) >= 1
    for p in pieges:
        assert p["nb_cas"] > 0 and 0 <= p["pct_rejets"] <= 100
        assert len(p["exemples"]) <= 3

def test_tendances(client):
    rows = client.get("/api/stats/tendances").json()
    assert len(rows) >= 5
    assert all("annee" in r and "nb_decisions" in r for r in rows)
    assert [r["annee"] for r in rows] == sorted(r["annee"] for r in rows)

def test_boussole_complete(client):
    body = {
        "juridiction": "Cour d'appel de Paris", "regime_matrimonial": "COMMUNAUTE_REDUITE_AUX_ACQUETS",
        "duree_mariage_annees": 18, "nombre_enfants": 2, "valeur_locative_mensuelle": 1100,
        "occupant": "CONJOINT", "mois_occupation": 24, "paye_credit": "MOI",
        "travaux": "MOI", "heritage_injecte": 50000, "preuves": ["FACTURE_NOMINATIVE"],
    }
    r = client.post("/api/boussole", json=body)
    assert r.status_code == 200
    rep = r.json()
    assert rep["indemnite_fourchette"]["mediane"] > 0
    assert rep["chances_travaux"]["taux_pct"] is not None
    assert len(rep["jumelles"]) == 5

def test_mode_demo_seed_et_purge(client):
    before = client.get("/api/demo/count").json()["demo_decisions"]
    r = client.post("/api/demo/seed")
    assert r.status_code == 200 and r.json()["created"] == 50
    total = client.get("/api/stats/overview").json()["total_decisions"]
    assert total >= 50
    r = client.delete("/api/demo")
    assert r.status_code == 200
    after = client.get("/api/demo/count").json()["demo_decisions"]
    assert before == 0 and after == 0

def test_config_a_chaud(client):
    r = client.put("/api/pipeline/config", json={"max_concurrency": 30, "max_chars": 48000})
    assert r.status_code == 200
    assert r.json()["max_concurrency"] == 30
    # remise aux défauts
    r = client.put("/api/pipeline/config", json={"max_concurrency": 25, "model": "glm-4-flash", "max_chars": 48000})
    assert r.status_code == 200

def test_export_csv(client):
    r = client.get("/api/decisions/export", params={"format": "csv", "regime": "SEPARATION_DE_BIENS"})
    assert r.status_code == 200
    assert r.text.splitlines()[0].startswith("id;date")
