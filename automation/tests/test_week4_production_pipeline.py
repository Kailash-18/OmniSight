"""
Integration Tests for OmniSight Week 4 Production Pipeline.
Verifies component cropping token economics, WCAG 2.1 AA accessibility auditing,
visual diff heatmap rendering, and atomic sandbox rollback with forensic verification.
"""

import json
from pathlib import Path
from PIL import Image
import pytest

from automation.engine import (
    AccessibilityScanner,
    BoundingBox,
    ComponentCropper,
    ForensicBundler,
    PatchSandbox,
    VisualComparator,
)
from app.services.forensics_service import verify_forensic_bundle_integrity


def test_week4_component_cropping_token_economics(tmp_path: Path):
    screenshot_path = tmp_path / "viewport.png"
    cropped_path = tmp_path / "crop.png"

    # Create 1440x900 canvas
    Image.new("RGB", (1440, 900), color=(250, 250, 250)).save(screenshot_path, "PNG")

    cropper = ComponentCropper(padding=20)
    box = BoundingBox(x=200, y=150, width=300, height=100)
    result = cropper.crop_region(screenshot_path, box, cropped_path)

    assert Path(result.cropped_image_path).exists()
    assert result.original_dimensions == (1440, 900)
    assert result.cropped_dimensions[0] == 300 + 40
    assert result.cropped_dimensions[1] == 100 + 40
    # Area reduction should be > 90%
    assert result.area_reduction_percentage > 90.0
    assert result.estimated_token_savings_percentage > 85.0


def test_week4_accessibility_wcag_scanner():
    scanner = AccessibilityScanner()
    elements = [
        {"tag": "button", "test_id": "btn-search", "text": "", "aria_label": "", "box": {"width": 30, "height": 30}},
        {"tag": "img", "test_id": "logo-banner", "alt": None, "box": {"width": 120, "height": 40}},
        {"tag": "button", "test_id": "btn-tiny", "text": "X", "aria_label": "Close", "box": {"width": 16, "height": 16}},
        {"tag": "span", "test_id": "subtext", "text": "Low contrast", "color": "#888888", "background_color": "#ffffff"},
    ]

    findings = scanner.audit_element_tree(elements)
    assert len(findings) == 4

    types = [f.issue_type for f in findings]
    assert "missing_accessible_name" in types
    assert "missing_alt_text" in types
    assert "substandard_target_size" in types
    assert "insufficient_contrast_ratio" in types


def test_week4_closed_loop_sandbox_rollback_and_forensics(tmp_path: Path):
    target_css = tmp_path / "style.css"
    initial_css = ".card { padding: 10px; }\n"
    target_css.write_text(initial_css, encoding="utf-8")

    diff = "--- a/style.css\n+++ b/style.css\n@@ -1,1 +1,1 @@\n-.card { padding: 10px; }\n+.card { padding: 20px; }\n"

    with PatchSandbox(target_file=target_css, diff=diff, bypass_allowlist_for_testing=True) as sandbox:
        assert sandbox.is_applied is True
        assert target_css.read_text(encoding="utf-8") == ".card { padding: 20px; }\n"

    # Verify atomic rollback
    assert target_css.read_text(encoding="utf-8") == initial_css

    # Stage mock run artifacts
    run_id = "run-week4-test-101"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({"run_id": run_id, "status": "fixed"}), encoding="utf-8")
    (run_dir / "target.css").write_text(initial_css, encoding="utf-8")

    bundler = ForensicBundler(artifacts_base_dir=tmp_path)
    bundle_meta = bundler.bundle_run(run_id=run_id, run_dir=run_dir, run_data={"target_file": "style.css", "patch_diff": diff})

    assert "bundle_file" in bundle_meta
    assert Path(bundle_meta["bundle_file"]).exists()

    verify_res = verify_forensic_bundle_integrity(run_id=run_id, artifacts_base_dir=tmp_path)
    assert verify_res["is_valid"] is True
    assert verify_res["verified_files_count"] >= 2
    assert len(verify_res["discrepancies"]) == 0
