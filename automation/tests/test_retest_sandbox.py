"""
Tests for Patch Sandbox and Retest Verification Engine.
Verifies security allowlist guardrails, path traversal prevention,
sandbox backup/restore lifecycle, and visual retest verification.
"""

from pathlib import Path
import pytest
from PIL import Image

from automation.patch_sandbox import (
    validate_patch_target,
    apply_unified_diff,
    PatchSandbox,
    RetestRunner,
    ALLOWED_PATCH_TARGETS,
)
from automation.schemas import ProposedPatch, RetestStatus
from automation.evidence import EvidenceCollector


def test_allowlist_validation_success():
    for target in ALLOWED_PATCH_TARGETS:
        resolved = validate_patch_target(target)
        assert resolved.name in target


def test_allowlist_validation_with_git_prefixes():
    resolved = validate_patch_target("a/app-under-test/src/styles/defects.css")
    assert "defects.css" in str(resolved)

    resolved_b = validate_patch_target("b/app-under-test/src/App.css")
    assert "App.css" in str(resolved_b)

    resolved_comp = validate_patch_target("app-under-test/src/components/ProductCard.jsx")
    assert "ProductCard.jsx" in str(resolved_comp)

    resolved_app = validate_patch_target("app-under-test/src/App.jsx")
    assert "App.jsx" in str(resolved_app)


def test_allowlist_disallowed_target_rejected():
    with pytest.raises(ValueError, match="outside the authorized allowlist"):
        validate_patch_target("backend/app/main.py")

    with pytest.raises(ValueError, match="outside the authorized allowlist"):
        validate_patch_target("automation/orchestrator.py")


def test_path_traversal_prevention():
    with pytest.raises(PermissionError, match="path traversal detected"):
        validate_patch_target("../../etc/passwd")

    with pytest.raises(PermissionError, match="path traversal detected"):
        validate_patch_target("app-under-test/../../../secret.env")


def test_apply_unified_diff():
    original = (
        "header {\n"
        "  color: blue;\n"
        "}\n"
        ".banner {\n"
        "  position: absolute;\n"
        "  z-index: 99;\n"
        "}\n"
        "footer {\n"
        "  margin: 10px;\n"
        "}\n"
    )

    diff = (
        "--- a/file.css\n"
        "+++ b/file.css\n"
        "@@ -4,4 +4,0 @@\n"
        "-.banner {\n"
        "-  position: absolute;\n"
        "-  z-index: 99;\n"
        "-}\n"
    )

    patched = apply_unified_diff(original, diff)
    assert ".banner" not in patched
    assert "header {" in patched
    assert "footer {" in patched


def test_patch_sandbox_guaranteed_restoration(tmp_path: Path):
    target_file = tmp_path / "styles.css"
    initial_text = "body { background: white; }\n.broken { display: none; }\n"
    target_file.write_text(initial_text, encoding="utf-8")

    diff = (
        "--- a/styles.css\n"
        "+++ b/styles.css\n"
        "@@ -2,1 +2,1 @@\n"
        "-.broken { display: none; }\n"
        "+.broken { display: block; }\n"
    )

    # Within sandbox, file has the patch
    with PatchSandbox(target_file, diff, bypass_allowlist_for_testing=True) as sb:
        assert sb.is_applied is True
        assert ".broken { display: block; }" in target_file.read_text(encoding="utf-8")

    # Outside sandbox, file is completely restored to initial text
    assert target_file.read_text(encoding="utf-8") == initial_text


def test_patch_sandbox_restores_on_exception(tmp_path: Path):
    target_file = tmp_path / "styles.css"
    initial_text = ".original-content { color: red; }\n"
    target_file.write_text(initial_text, encoding="utf-8")

    diff = (
        "--- a/styles.css\n"
        "+++ b/styles.css\n"
        "@@ -1,1 +1,1 @@\n"
        "+.new-content { color: green; }\n"
    )

    with pytest.raises(RuntimeError, match="Simulated error"):
        with PatchSandbox(target_file, diff, bypass_allowlist_for_testing=True):
            raise RuntimeError("Simulated error")

    # Must be restored despite exception
    assert target_file.read_text(encoding="utf-8") == initial_text


def test_retest_runner_verify_patch(tmp_path: Path):
    evidence = EvidenceCollector(run_id="test-retest-runner")
    evidence.run_dir = tmp_path
    evidence.retest_dir = tmp_path / "retest"
    evidence.retest_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy before screenshot
    before_path = tmp_path / "before.png"
    img = Image.new("RGB", (375, 667), (255, 255, 255))
    img.save(before_path)

    # Create dummy style file
    style_file = tmp_path / "defects.css"
    style_file.write_text(".broken { display: block; }\n", encoding="utf-8")

    diff = (
        "--- a/defects.css\n"
        "+++ b/defects.css\n"
        "@@ -1,1 +1,0 @@\n"
        "-.broken { display: block; }\n"
    )

    patch = ProposedPatch(
        target_file=str(style_file),
        diff=diff,
        explanation="Remove broken rule",
    )

    runner = RetestRunner()
    verification = runner.verify_patch(
        app_url="http://127.0.0.1:5173",
        target_viewport="mobile_375x667",
        before_screenshot=str(before_path),
        proposed_patch=patch,
        evidence=evidence,
        defect_step="checkout",
        bypass_allowlist_for_testing=True,
    )

    assert verification.status == RetestStatus.FIXED
    assert verification.mismatch_percentage > 0.0
    assert Path(verification.after_screenshot).exists()
    assert Path(verification.diff_screenshot).exists()
    assert "defect-remediated" in verification.resolved_findings


def test_orchestrator_closed_loop_retest_flow(monkeypatch, tmp_path: Path):
    from automation.orchestrator import Orchestrator
    from automation.vlm_adapter import MockVLMAdapter

    orchestrator = Orchestrator(vlm_adapter=MockVLMAdapter())

    shot_path = tmp_path / "mobile_375x667_checkout.png"
    img = Image.new("RGB", (375, 667), (200, 200, 200))
    img.save(shot_path)

    dom_path = tmp_path / "mobile_375x667_checkout_dom.json"
    dom_path.write_text('{"viewport": {"width": 375, "height": 667}, "elements": []}', encoding="utf-8")

    def mock_journey(*args, **kwargs):
        evidence = kwargs.get("evidence")
        if evidence:
            evidence.run_dir = tmp_path
            evidence.retest_dir = tmp_path / "retest"
            evidence.retest_dir.mkdir(parents=True, exist_ok=True)
            evidence.annotated_dir = tmp_path / "annotated"
            evidence.annotated_dir.mkdir(parents=True, exist_ok=True)
        return {
            "run_id": "test-closed-loop",
            "target_url": "http://127.0.0.1:5173",
            "viewports_evaluated": ["mobile_375x667"],
            "screenshots": [str(shot_path)],
            "dom_snapshots": [str(dom_path)],
            "steps_completed": ["home", "cart", "checkout"],
        }

    monkeypatch.setattr(
        "automation.orchestrator.run_visual_audit_journey",
        mock_journey,
    )

    result = orchestrator.run_full_remediation_loop(
        target_url="http://127.0.0.1:5173",
        viewports=["mobile_375x667"],
        auto_retest=True,
    )

    assert result["status"] == "fixed"
    assert "retest_verification" in result
    assert result["retest_verification"] is not None
    assert result["retest_verification"]["status"] == "fixed"
    assert len(result["findings"]) > 0

