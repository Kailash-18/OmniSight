"""
End-to-end integration test for Week 4 Day 4 deliverables:
Concurrency Leases, Cross-Viewport Canary Verification, and Live SSE Event Streaming.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_e2e_concurrency_lease_workflow(client):
    payload = {"run_id": "run_e2e_day4", "target_selector": ".hero-title", "url_path": "/home", "ttl_seconds": 30.0}
    res = client.post("/api/v1/concurrency/leases/acquire", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    lease_id = data["lease"]["lease_id"]

    res_act = client.get("/api/v1/concurrency/leases/active")
    assert res_act.status_code == 200
    assert res_act.json()["total_active"] >= 1

    res_ren = client.post(f"/api/v1/concurrency/leases/{lease_id}/renew", json={"extend_seconds": 20.0})
    assert res_ren.status_code == 200
    assert res_ren.json()["renewed"] is True

    res_rel = client.post(f"/api/v1/concurrency/leases/{lease_id}/release?run_id=run_e2e_day4")
    assert res_rel.status_code == 200
    assert res_rel.json()["released"] is True

def test_e2e_canary_verification_endpoint(client):
    payload = {
        "run_id": "run_e2e_canary",
        "patch_id": "patch_canary_01",
        "target_selector": ".nav-container",
        "per_viewport_drift": {}
    }
    res = client.post("/api/v1/canary/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_canary_passed"] is True
    assert data["canary_stability_index"] == 100.0

    res_get = client.get("/api/v1/canary/run_e2e_canary/report")
    assert res_get.status_code == 200
    assert res_get.json()["patch_id"] == "patch_canary_01"

def test_e2e_event_streaming_workflow(client):
    pub_payload = {
        "run_id": "run_stream_e2e",
        "event_type": "CANARY_VERIFIED",
        "payload": {"score": 98.5}
    }
    res_pub = client.post("/api/v1/events/publish", json=pub_payload)
    assert res_pub.status_code == 200
    assert res_pub.json()["event_type"] == "CANARY_VERIFIED"

    res_hist = client.get("/api/v1/events/history?run_id=run_stream_e2e")
    assert res_hist.status_code == 200
    assert res_hist.json()["total_events"] >= 1

    res_stream = client.get("/api/v1/events/stream?run_id=run_stream_e2e")
    assert res_stream.status_code == 200
    assert "text/event-stream" in res_stream.headers["content-type"]
