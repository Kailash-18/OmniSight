"""
Unit Tests for Automation Configuration and Viewport Matrix.
"""

from automation.config import config
from automation.viewports import (
    STANDARD_VIEWPORTS,
    get_viewport,
    get_desktop_viewports,
    get_mobile_viewports,
    ViewportSpec
)
from automation.manifest import RunManifest


def test_standard_viewports_exist():
    assert "desktop_1440x900" in STANDARD_VIEWPORTS
    assert "desktop_1280x800" in STANDARD_VIEWPORTS
    assert "mobile_390x844" in STANDARD_VIEWPORTS
    assert "mobile_375x667" in STANDARD_VIEWPORTS


def test_viewport_classification():
    desktop_vps = get_desktop_viewports()
    mobile_vps = get_mobile_viewports()

    assert len(desktop_vps) == 2
    assert len(mobile_vps) == 2

    for vp in desktop_vps:
        assert not vp.is_mobile
        assert not vp.has_touch

    for vp in mobile_vps:
        assert vp.is_mobile
        assert vp.has_touch


def test_run_manifest_serialization():
    manifest = RunManifest(
        run_id="run-test-101",
        target_url="http://localhost:5173",
        status="running",
        viewports=["desktop_1440x900"]
    )
    assert manifest.status == "running"
    assert manifest.issue_count == 0

    manifest.finalize(status="audited", issue_count=3)
    data = manifest.to_dict()

    assert data["status"] == "audited"
    assert data["issue_count"] == 3
    assert data["end_time"] is not None
    assert "os" in data["environment"]
