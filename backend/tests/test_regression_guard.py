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
