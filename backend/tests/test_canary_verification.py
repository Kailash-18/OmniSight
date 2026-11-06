"""
Unit test suite for CanaryVerificationEngine and responsive cross-viewport stability.
"""
import pytest
from backend.app.schemas.canary_schema import CanaryVerificationRequest, ViewportProfile
from backend.app.schemas.regression_guard_schema import SpatialDriftMetric, DriftSeverity
from backend.app.services.canary_service import CanaryVerificationEngine

@pytest.fixture
def engine():
    return CanaryVerificationEngine()

def test_canary_verification_all_viewports_pass(engine):
    stable_metric = SpatialDriftMetric(
        node_id="n1", selector=".logo", dx=0, dy=0, d_width=0, d_height=0,
        euclidean_shift=0.0, area_delta_pct=0.0, is_invariant_preserved=True, severity=DriftSeverity.STABLE
    )
    req = CanaryVerificationRequest(
        run_id="run_c1", patch_id="patch_c1", target_selector=".btn",
        per_viewport_drift={
            "mobile_375x667": [stable_metric],
            "tablet_768x1024": [stable_metric],
            "desktop_1920x1080": [stable_metric]
        }
    )
    report = engine.verify_canary_patch(req)
    assert report.overall_canary_passed is True
    assert report.canary_stability_index == 100.0
    assert len(report.breaking_viewports) == 0
    assert report.quarantine_recommended is False

def test_csi_score_calculation(engine):
    req = CanaryVerificationRequest(run_id="run_empty", patch_id="patch_0", target_selector=".nav")
    report = engine.verify_canary_patch(req)
    assert report.canary_stability_index == 100.0
