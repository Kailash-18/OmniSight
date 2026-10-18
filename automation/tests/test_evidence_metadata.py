"""Tests for EvidenceMetadataManager."""

import pytest
from automation.evidence_metadata import EvidenceMetadataManager


def test_evidence_metadata_manager():
    mgr = EvidenceMetadataManager(run_id="run-meta-101")
    mgr.register_screenshot("home_before.png", "desktop_1440x900", "home", "before", 1440, 900)
    mgr.register_screenshot("cart_after.png", "desktop_1440x900", "cart", "after", 1440, 900)
    mgr.register_screenshot("mobile_diff.png", "mobile_375x667", "checkout", "diff", 375, 667)

    manifest = mgr.compile_manifest()
    assert manifest["run_id"] == "run-meta-101"
    assert manifest["total_screenshots"] == 3
    assert "desktop_1440x900" in manifest["viewports_covered"]
    assert "mobile_375x667" in manifest["viewports_covered"]
    assert "before" in manifest["stages_covered"]
    assert "diff" in manifest["stages_covered"]
