"""
Unit tests for RegressionGuardEngine spatial invariant verification.
"""
import pytest
from backend.app.services.regression_guard_service import RegressionGuardEngine
from backend.app.schemas.regression_guard_schema import (
    NodeSpatialSnapshot, VisualInvariantCheckRequest, DriftSeverity
)

def test_zero_drift_preserves_invariants():
    engine = RegressionGuardEngine()
    baseline = [
        NodeSpatialSnapshot(node_id="btn_1", selector=".btn-primary", x=100, y=200, width=120, height=40),
        NodeSpatialSnapshot(node_id="nav_1", selector=".navbar", x=0, y=0, width=1920, height=60)
    ]
    patched = [
        NodeSpatialSnapshot(node_id="btn_1", selector=".btn-primary", x=100, y=200, width=120, height=40),
        NodeSpatialSnapshot(node_id="nav_1", selector=".navbar", x=0, y=0, width=1920, height=60)
    ]
    req = VisualInvariantCheckRequest(
        run_id="run_inv_01",
        target_selector=".btn-primary",
        baseline_nodes=baseline,
        patched_nodes=patched
    )
    res = engine.verify_spatial_invariants(req)
    assert res.invariant_preserved is True
    assert res.layout_stability_score == 1.0
    assert res.violations_detected == 0

def test_cascade_drift_violates_invariants():
    engine = RegressionGuardEngine()
    baseline = [
        NodeSpatialSnapshot(node_id="card_1", selector=".card-sidebar", x=200, y=100, width=300, height=400)
    ]
    # Severe drift of 15px vertically
    patched = [
        NodeSpatialSnapshot(node_id="card_1", selector=".card-sidebar", x=200, y=115, width=300, height=400)
    ]
    req = VisualInvariantCheckRequest(
        run_id="run_inv_02",
        target_selector=".hero-banner",
        baseline_nodes=baseline,
        patched_nodes=patched,
        max_allowed_shift_px=2.0
    )
    res = engine.verify_spatial_invariants(req)
    assert res.invariant_preserved is False
    assert res.violations_detected == 1
    assert res.drift_details[0].severity == DriftSeverity.REGRESSION_VIOLATION
    penalty = engine.compute_cls_penalty(res.drift_details)
    assert penalty > 0.0
