import pytest
from fastapi.testclient import TestClient
from main import app, Episode

client = TestClient(app)

def test_invariants_pydantic_enf05():
    """Vérifie le rejet des horodatages et séquences invalides (INV-01 et INV-02)."""
    # Test INV-01 : séquence non strictement croissante
    with pytest.raises(ValueError, match="INV-01"):
        Episode(id="1", agent_id="a", scenario="s", ts_start=1.0, ts_end=2.0, label="benign", events=[
            {"seq": 2, "ts": 1.1, "type": "user_msg", "args_hash": "x", "mem_ids": [], "scores": [], "latency_ms": 1.0},
            {"seq": 1, "ts": 1.2, "type": "user_msg", "args_hash": "y", "mem_ids": [], "scores": [], "latency_ms": 1.0}
        ])

    # Test INV-02 : horodatage non monotone
    with pytest.raises(ValueError, match="INV-02"):
        Episode(id="2", agent_id="a", scenario="s", ts_start=1.0, ts_end=2.0, label="benign", events=[
            {"seq": 1, "ts": 1.5, "type": "user_msg", "args_hash": "x", "mem_ids": [], "scores": [], "latency_ms": 1.0},
            {"seq": 2, "ts": 1.2, "type": "user_msg", "args_hash": "y", "mem_ids": [], "scores": [], "latency_ms": 1.0}
        ])

def test_routes_base_api():
    """Vérifie que les routes de base répondent correctement."""
    response_health = client.get("/healthz")
    assert response_health.status_code == 200

    response_metrics = client.get("/metrics")
    assert response_metrics.status_code == 200

def test_ingest_and_timeline_ef12():
    """Teste l'ingestion d'un épisode et la matérialisation du découplage (EF-01 et EF-12)."""
    # 1. On crée un faux journal avec une écriture à t=2.0 et une relecture à t=4.0
    fichier_jsonl = '{"id": "test_123", "agent_id": "a", "scenario": "s", "ts_start": 1.0, "ts_end": 5.0, "label": "benign", "events": [{"seq": 1, "ts": 2.0, "type": "mem_write", "args_hash": "h1", "mem_ids": ["mem_A"], "scores": [], "latency_ms": 10}, {"seq": 2, "ts": 4.0, "type": "mem_read", "args_hash": "h2", "mem_ids": ["mem_A"], "scores": [], "latency_ms": 10}]}'

    # Test d'ingestion (EF-01)
    files = {"file": ("test.jsonl", fichier_jsonl.encode("utf-8"), "application/json")}
    response = client.post("/ingest", files=files)
    assert response.status_code == 200
    assert response.json()["episodes_acceptes"] >= 0

    # Test du calcul de la frise temporelle (EF-12)
    response_timeline = client.get("/episodes/test_123/timeline")
    assert response_timeline.status_code == 200
    donnees = response_timeline.json()

    # On vérifie que l'arête d'empoisonnement a bien été trouvée et que le délai est de 2 secondes
    assert len(donnees["edges"]) == 1
    assert donnees["edges"][0]["delay_s"] == 2.0  # 4.0 - 2.0 = 2.0