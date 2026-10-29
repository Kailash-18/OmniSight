"""Tests for SLA violation and defect heatmap analytics endpoints."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from backend.app.main import app, runs_db

client = TestClient(app)


def setup_function():
    """Clear runs DB before each test."""
    runs_db.clear()


def _make_run(run_id, status="pending", age_hours=0, viewport="1280x720", findings=None):
    """Helper to insert a run entry."""
    created_at = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    runs_db[run_id] = {
        "run_id": run_id,
        "url": f"https://test.com/{run_id}",
        "status": status,
        "viewport": viewport,
        "findings": findings or [],
        "issue_count": len(findings or []),
        "created_at": created_at,
        "timeline": [],
        "tags": [],
    }


def test_sla_violations_empty():
    resp = client.get("/runs/analytics/sla-violations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_violations"] == 0
    assert data["violations"] == []


def test_sla_violations_detects_aged_pending_run():
    _make_run("old-run-01", status="pending", age_hours=30)
    resp = client.get("/runs/analytics/sla-violations?threshold_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_violations"] == 1
    assert data["violations"][0]["run_id"] == "old-run-01"
    assert data["violations"][0]["age_hours"] >= 24


def test_sla_violations_skips_completed_runs():
    _make_run("done-run-01", status="completed", age_hours=48)
    resp = client.get("/runs/analytics/sla-violations?threshold_hours=24")
    assert resp.status_code == 200
    assert resp.json()["total_violations"] == 0


def test_sla_violations_custom_threshold():
    _make_run("fresh-run-01", status="running", age_hours=10)
    resp_24 = client.get("/runs/analytics/sla-violations?threshold_hours=24")
    assert resp_24.json()["total_violations"] == 0
    resp_6 = client.get("/runs/analytics/sla-violations?threshold_hours=6")
    assert resp_6.json()["total_violations"] == 1


def test_heatmap_empty():
    resp = client.get("/runs/analytics/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs_analyzed"] == 0
    assert data["viewports"] == []
    assert data["hottest_viewport"] is None


def test_heatmap_groups_by_viewport():
    _make_run("r1", viewport="1280x720", findings=[{"severity": "high", "element": "btn"}])
    _make_run("r2", viewport="375x812", findings=[{"severity": "critical", "element": "nav"}])
    _make_run("r3", viewport="1280x720", findings=[{"severity": "medium", "element": "form"}])
    resp = client.get("/runs/analytics/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs_analyzed"] == 3
    viewports = {v["viewport"]: v for v in data["viewports"]}
    assert "1280x720" in viewports
    assert viewports["1280x720"]["defect_count"] == 2
    assert data["hottest_viewport"] == "1280x720"
