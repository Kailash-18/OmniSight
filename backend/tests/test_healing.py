"""
Unit and Integration Tests for Autonomous Self-Healing Decision Engine and PR Labeling.
"""

import pytest
from backend.app.schemas.healing_schema import (
    HealingStrategyType,
    HealingStrategyRequest,
    HealingStrategyResponse,
    PRLabelCalculationRequest,
    RollbackPreviewRequest,
)
from backend.app.services.healing_service import HealingEngine, healing_engine


def test_immediate_patch_strategy_on_zero_diff():
    """Verify that diff score <= 0.005 immediately yields IMMEDIATE_PATCH strategy."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-101", visual_diff_score=0.002, iteration_count=1)
    assert resp.strategy == HealingStrategyType.IMMEDIATE_PATCH
    assert resp.can_auto_merge is True
    assert resp.rollback_recommended is False
    assert "visually verified" in resp.action_rationale.lower()

def test_human_escalation_on_exceeded_max_retries():
    """Verify that exceeding max_retries escalates to human review with rollback recommendation."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-102", visual_diff_score=0.15, iteration_count=2, max_retries=2)
    assert resp.strategy == HealingStrategyType.HUMAN_ESCALATION
    assert resp.can_auto_merge is False
    assert resp.rollback_recommended is True
    assert "max_retries" in resp.action_rationale


def test_catastrophic_regression_triggers_rollback():
    """Verify that visual diff score > 0.40 triggers ROLLBACK_REQUIRED strategy."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-103", visual_diff_score=0.55, iteration_count=1, max_retries=3)
    assert resp.strategy == HealingStrategyType.ROLLBACK_REQUIRED
    assert resp.rollback_recommended is True
    assert "catastrophic" in resp.action_rationale.lower()


def test_iterative_refinement_within_budget():
    """Verify that minor diff within retry budget triggers ITERATIVE_REFINEMENT."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-104", visual_diff_score=0.08, iteration_count=1, max_retries=3)
    assert resp.strategy == HealingStrategyType.ITERATIVE_REFINEMENT
    assert resp.can_auto_merge is False
    assert resp.rollback_recommended is False

def test_compute_pr_labels_triage_and_colors():
    """Verify dynamic label calculation produces standard tags, viewport tags, and severity levels."""
    engine = HealingEngine()
    res = engine.compute_pr_labels(
        finding_count=2,
        max_severity="critical",
        viewport_name="mobile",
        is_verified=True,
        defect_categories=["element_clipping", "contrast_issue"]
    )
    assert "omnisight" in res.labels
    assert "automated-fix" in res.labels
    assert "severity:critical" in res.labels
    assert "viewport:mobile" in res.labels
    assert "status:retest-verified" in res.labels
    assert "defect:element-clipping" in res.labels
    assert res.priority_level == "P0"
    assert "severity:critical" in res.color_map

def test_record_healing_cycles_and_summary():
    """Verify multi-cycle recording and aggregate summary calculation."""
    engine = HealingEngine()
    engine.record_healing_cycle("run-105", iteration=1, diff_score=0.25, strategy="iterative_refinement")
    engine.record_healing_cycle("run-105", iteration=2, diff_score=0.001, strategy="immediate_patch")

    summary = engine.get_healing_summary("run-105")
    assert summary.run_id == "run-105"
    assert summary.total_iterations == 2
    assert summary.initial_diff_score == 0.25
    assert summary.final_diff_score == 0.001
    assert summary.resolution_status == "fixed"
    assert summary.duration_seconds > 0.0


def test_rollback_preview_request_validation():
    """Verify rollback preview validates path traversal defensively."""
    req = RollbackPreviewRequest(run_id="run-106", target_file="app-under-test/src/styles/defects.css")
    assert req.target_file == "app-under-test/src/styles/defects.css"

    with pytest.raises(ValueError):
        RollbackPreviewRequest(run_id="run-106", target_file="../../backend/app/main.py")

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_healing_strategy_and_summary_flow():
    """Integration test verifying healing strategy evaluation and summary retrieval endpoints."""
    # Step 1: Evaluate strategy
    payload = {
        "run_id": "test-heal-run-99",
        "visual_diff_score": 0.003,
        "iteration_count": 1,
        "max_retries": 2
    }
    resp = client.post("/runs/test-heal-run-99/healing-strategy", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "immediate_patch"
    assert data["can_auto_merge"] is True

    # Step 2: Get healing summary
    sum_resp = client.get("/runs/test-heal-run-99/healing-summary")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["run_id"] == "test-heal-run-99"
    assert sum_data["resolution_status"] == "fixed"


def test_api_compute_labels_endpoint():
    """Integration test for computing PR triage labels."""
    req_data = {
        "finding_count": 3,
        "max_severity": "high",
        "viewport_name": "mobile_375x667",
        "is_verified": True,
        "defect_categories": ["element_overlap"]
    }
    resp = client.post("/runs/test-label-run-1/compute-labels", json=req_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "omnisight" in data["labels"]
    assert "severity:high" in data["labels"]
    assert data["priority_level"] == "P1"


def test_api_rollback_preview_endpoint():
    """Integration test for patch rollback preview."""
    req = {
        "run_id": "test-rb-run-1",
        "target_file": "app-under-test/src/styles/defects.css",
        "reason": "visual_regression"
    }
    resp = client.post("/runs/test-rb-run-1/rollback-preview", json=req)
    assert resp.status_code == 200
    assert resp.json()["is_restorable"] is True
