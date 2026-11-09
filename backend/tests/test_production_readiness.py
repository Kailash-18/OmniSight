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
