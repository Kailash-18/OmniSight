"""
Unit & Integration Tests for Production Readiness Probes and Concurrency Telemetry.
Verifies /health/liveness, /health/readiness, /api/system/concurrency, and graceful shutdown states.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.main import app
import app.main as main_module


@pytest.fixture
def client():
    return TestClient(app)


def test_health_liveness_endpoint(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
    assert "version" in data


def test_health_readiness_endpoint(client):
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["store"] == "ok"
    assert data["checks"]["artifact_storage"] == "ok"
    assert data["checks"]["concurrency"] == "ok"
    assert data["capacity_available"] is True


def test_health_readiness_failure_on_storage_error(client):
    with patch("pathlib.Path.write_text", side_effect=PermissionError("Read-only volume")):
        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["artifact_storage"] == "error"


def test_concurrency_metrics_endpoint(client):
    response = client.get("/api/system/concurrency")
    assert response.status_code == 200
    data = response.json()
    assert data["max_concurrent_runs"] == 5
    assert data["active_runs_count"] >= 0
    assert data["available_slots"] <= 5
    assert data["is_shutting_down"] is False


def test_graceful_shutdown_draining_readiness(client):
    orig = main_module.IS_SHUTTING_DOWN
    try:
        main_module.IS_SHUTTING_DOWN = True
        response = client.get("/health/readiness")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "draining"
        assert data["capacity_available"] is False
    finally:
        main_module.IS_SHUTTING_DOWN = orig


def test_stream_run_events_endpoint(client):
    import json
    # Unknown run returns 404
    resp = client.get("/runs/non-existent-run-xyz/events")
    assert resp.status_code == 404

    # Known completed run streams event and closes
    main_module.runs_db["run-sse-test-1"] = {
        "run_id": "run-sse-test-1",
        "status": "fixed",
        "findings": [{"id": "f1"}],
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/10"
    }
    with client.stream("GET", "/runs/run-sse-test-1/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        lines = [line for line in response.iter_lines() if line]
        assert len(lines) >= 1
        data = json.loads(lines[0].replace("data: ", ""))
        assert data["run_id"] == "run-sse-test-1"
        assert data["status"] == "fixed"
