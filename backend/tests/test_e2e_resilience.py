"""
End-to-end integration test connecting Circuit Breaker, Regression Guard, and Rollback.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_e2e_resilience_and_circuit_breaker(client):
    # Check initial status
    resp = client.get("/api/v1/resilience/circuit-breaker/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] in ["CLOSED", "OPEN", "HALF_OPEN"]

    # Trip circuit by recording failures
    client.post("/api/v1/resilience/circuit-breaker/record-failure")
    client.post("/api/v1/resilience/circuit-breaker/record-failure")
    resp_fail = client.post("/api/v1/resilience/circuit-breaker/record-failure")
    assert resp_fail.status_code == 200
    assert resp_fail.json()["state"] == "OPEN"

    # Reset
    resp_reset = client.post("/api/v1/resilience/circuit-breaker/reset")
    assert resp_reset.status_code == 200
    assert resp_reset.json()["state"] == "CLOSED"

def test_e2e_regression_guard_endpoint(client):
    payload = {
        "run_id": "run_e2e_rg",
        "target_selector": ".nav-button",
        "baseline_nodes": [
            {"node_id": "n1", "selector": ".header", "x": 0, "y": 0, "width": 1200, "height": 80}
        ],
        "patched_nodes": [
            {"node_id": "n1", "selector": ".header", "x": 0, "y": 0, "width": 1200, "height": 80}
        ]
    }
    resp = client.post("/api/v1/regression-guard/verify-invariants", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["invariant_preserved"] is True
    assert body["violations_detected"] == 0
