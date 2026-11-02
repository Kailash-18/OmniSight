"""Tests for RunComparator and compare_runs_endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, runs_db
from app.services.run_comparator import RunComparator

client = TestClient(app)


def test_run_comparator_logic():
    base = {
        "id": "run-base",
        "status": "fixed",
        "target_url": "http://localhost:5173",
        "findings": [
            {
                "category": "element_overlap",
                "selector": ".hero-title",
                "viewport": "1440x900",
                "description": "Hero overlaps card",
            },
            {
                "category": "element_obstruction",
                "selector": ".promo-banner",
                "viewport": "375x667",
                "description": "Promo obstructs button",
            },
        ],
    }

    cand = {
        "id": "run-cand",
        "status": "fixed",
        "target_url": "http://localhost:5173",
        "findings": [
            {
                "category": "element_overlap",
                "selector": ".hero-title",
                "viewport": "1440x900",
                "description": "Hero overlaps card",
            },
        ],
    }

    res = RunComparator.compare_runs(base, cand)
    assert res["baseline_defect_count"] == 2
    assert res["candidate_defect_count"] == 1
    assert res["resolved_defects_count"] == 1
    assert res["new_regressions_count"] == 0
    assert res["persisting_defects_count"] == 1
    assert res["net_improvement_percentage"] == 50.0
    assert res["is_improved"] is True
    assert res["has_new_regressions"] is False


def test_compare_runs_api_endpoint():
    runs_db["run-cmp-1"] = {
        "id": "run-cmp-1",
        "status": "audited",
        "target_url": "http://localhost:5173",
        "created_at": "2026-11-02T10:00:00Z",
        "findings": [
            {
                "category": "element_overlap",
                "selector": ".banner",
                "viewport": "1440x900",
                "description": "Banner overlap",
                "severity": "high",
            }
        ],
    }
    runs_db["run-cmp-2"] = {
        "id": "run-cmp-2",
        "status": "fixed",
        "target_url": "http://localhost:5173",
        "created_at": "2026-11-02T11:00:00Z",
        "findings": [],
    }

    resp = client.get("/runs/run-cmp-1/compare/run-cmp-2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved_defects_count"] == 1
    assert data["candidate_defect_count"] == 0
    assert data["net_improvement_percentage"] == 100.0
