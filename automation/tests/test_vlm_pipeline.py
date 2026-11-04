"""
Integration Tests for VLM Adapter and Evidence Artifact Pipeline.
"""

from pathlib import Path
from automation.schemas import DefectCategory, Severity, Finding
from automation.vlm_adapter import MockVLMAdapter
from automation.evidence import EvidenceCollector


def test_evidence_collector_directory_structure(tmp_path):
    collector = EvidenceCollector(run_id="run-test-evidence")
    assert collector.run_id == "run-test-evidence"
    assert collector.run_dir.exists()
    assert collector.screenshots_dir.exists()
    assert collector.dom_dir.exists()
    assert collector.logs_dir.exists()

    shot_path = collector.get_screenshot_path("desktop_1440x900", "home")
    assert shot_path.name == "desktop_1440x900_home.png"
    assert len(collector.recorded_screenshots) == 1


def test_mock_vlm_adapter_detects_seeded_defects():
    adapter = MockVLMAdapter()
    sample_screenshots = [
        "desktop_1440x900_home.png",
        "mobile_375x667_cart.png",
        "desktop_1280x800_checkout.png"
    ]
    sample_dom = ["dom1.json", "dom2.json", "dom3.json"]

    report = adapter.audit_viewports(
        run_id="run-test-vlm",
        target_url="http://localhost:5173",
        evidence_dir=Path("."),
        screenshots=sample_screenshots,
        dom_snapshots=sample_dom
    )

    assert report.run_id == "run-test-vlm"
    assert len(report.findings) == 3

    categories = {f.category for f in report.findings}
    assert DefectCategory.ELEMENT_OVERLAP in categories
    assert DefectCategory.ELEMENT_CLIPPING in categories
    assert DefectCategory.ELEMENT_OBSTRUCTION in categories

    assert report.proposed_patch is not None
    assert "defects.css" in report.proposed_patch.target_file
    assert "promo-banner" in report.proposed_patch.diff
