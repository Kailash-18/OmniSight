"""
Comprehensive Integration Tests for Advanced Automation & Backend Optimization Features.
Verifies end-to-end chaining of:
- Component cropping & token optimization
- Accessibility auditing & WCAG scoring
- Sandbox cryptographic rollback guard
- Remediation risk scoring & gate verdicts
"""

from pathlib import Path
from PIL import Image
import pytest

from automation.engine import (
    AccessibilityScanner,
    BoundingBox,
    ComponentCropper,
    PatchSandbox,
)
from backend.app.schemas.run_schema import DefectCategory, FindingSchema, PatchObject, Severity
from backend.app.services.action_engine import action_engine


def test_chain_cropping_and_risk_scoring(tmp_path: Path):
    # 1. Create mock screenshot
    shot_path = tmp_path / "defect_shot.png"
    Image.new("RGB", (1280, 800), color=(255, 255, 255)).save(shot_path)

    # 2. Crop component
    crop_path = tmp_path / "crop_result.png"
    cropper = ComponentCropper(padding=16)
    crop_res = cropper.crop_region(shot_path, BoundingBox(50, 50, 100, 60), crop_path)
    assert crop_res.area_reduction_percentage > 85.0
    assert crop_res.estimated_token_savings_percentage > 80.0

    # 3. Assess remediation risk
    finding = FindingSchema(
        id="c1",
        category=DefectCategory.ELEMENT_CLIPPING,
        severity=Severity.HIGH,
        description="Checkout button clipping",
        viewport="mobile_375x667",
        confidence=0.92,
        suggested_change="width: 100%",
        rationale="Button clipped",
        status="detected",
    )
    patch = PatchObject(
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn { width: 500px; }\n+.btn { width: 100%; }",
        explanation="Make responsive",
    )
    score, verdict = action_engine.calculate_remediation_risk([finding], patch)
    assert score < 50.0
    assert verdict == "auto_pr_allowed"


def test_chain_accessibility_and_sandbox_guard(tmp_path: Path):
    # 1. Accessibility audit
    dom = [
        {"tag": "button", "test_id": "checkout", "text": "Checkout", "box": {"width": 120, "height": 40}},
        {"tag": "img", "test_id": "logo", "alt": None, "box": {"width": 80, "height": 80}},
    ]
    a11y_issues = AccessibilityScanner.audit_element_tree(dom)
    assert len(a11y_issues) == 1
    assert a11y_issues[0].issue_type == "missing_alt_text"

    # 2. Sandbox atomic rollback
    css_file = tmp_path / "style.css"
    css_file.write_text("body { background: white; }\n", encoding="utf-8")
    diff = """--- a/style.css
+++ b/style.css
@@ -1,1 +1,1 @@
-body { background: white; }
+body { background: black; }
"""
    with PatchSandbox(css_file, diff, bypass_allowlist_for_testing=True) as sandbox:
        assert sandbox.is_applied is True
        assert "background: black;" in css_file.read_text(encoding="utf-8")

    assert css_file.read_text(encoding="utf-8") == "body { background: white; }\n"
    assert sandbox.verify_restoration() is True
