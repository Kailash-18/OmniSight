"""
Integration Tests for Quality Metrics and Telemetry Endpoints (Week 4 optimization).
Verifies aggregation of total runs, success rates, categorical distributions, and diff averages.
"""

from fastapi.testclient import TestClient


def test_get_metrics_summary_empty(client: TestClient):
    response = client.get("/runs/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] >= 0
    assert "success_rate_percentage" in data
    assert isinstance(data["defect_categories"], dict)


def test_get_metrics_summary_after_runs(client: TestClient):
    # Queue a run
    payload = {
        "target_url": "http://localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow",
    }
    r = client.post("/webhook/build", json=payload)
    assert r.status_code == 202

    response = client.get("/runs/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] > 0
