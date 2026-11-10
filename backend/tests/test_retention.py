"""Tests for RunRetentionService and cleanup endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, runs_db
from app.services.retention_service import RunRetentionService

client = TestClient(app)


def test_retention_service_pruning():
    dummy_db = {
        f"run-{i}": {"id": f"run-{i}", "status": "failed" if i < 3 else "fixed"}
        for i in range(10)
    }

    res = RunRetentionService.cleanup_runs(dummy_db, max_runs_to_keep=5, preserve_fixed=True)
    assert res["total_runs_after"] == 5
    assert len(res["pruned_run_ids"]) == 5
    # Non-fixed runs should be pruned first
    assert "run-0" in res["pruned_run_ids"]
    assert "run-1" in res["pruned_run_ids"]
    assert "run-2" in res["pruned_run_ids"]


def test_cleanup_api_endpoint():
    runs_db.clear()
    for i in range(8):
        runs_db[f"run-cleanup-{i}"] = {"id": f"run-cleanup-{i}", "status": "audited"}

    resp = client.post("/runs/cleanup?max_runs=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs_after"] == 4
    assert len(data["pruned_run_ids"]) == 4
