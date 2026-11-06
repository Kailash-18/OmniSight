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

def test_canary_detects_mobile_regression(engine):
    bad_metric = SpatialDriftMetric(
        node_id="n_mobile", selector=".sidebar", dx=12, dy=8, d_width=0, d_height=0,
        euclidean_shift=14.4, area_delta_pct=15.0, is_invariant_preserved=False, severity=DriftSeverity.REGRESSION_VIOLATION
    )
    good_metric = SpatialDriftMetric(
        node_id="n_desk", selector=".header", dx=0, dy=0, d_width=0, d_height=0,
        euclidean_shift=0.0, area_delta_pct=0.0, is_invariant_preserved=True, severity=DriftSeverity.STABLE
    )
    req = CanaryVerificationRequest(
        run_id="run_reg1", patch_id="patch_reg1", target_selector=".btn",
        per_viewport_drift={
            "mobile_375x667": [bad_metric],
            "desktop_1920x1080": [good_metric]
        }
    )
    report = engine.verify_canary_patch(req)
    assert report.overall_canary_passed is False
    assert "mobile_375x667" in report.breaking_viewports
    assert report.quarantine_recommended is True
    assert report.canary_stability_index < 100.0

def test_canary_get_report_cache(engine):
    req = CanaryVerificationRequest(run_id="run_cached", patch_id="p1", target_selector=".hero")
    report = engine.verify_canary_patch(req)
    assert engine.get_report("run_cached") is not None
    assert engine.get_report("non_existent") is None
