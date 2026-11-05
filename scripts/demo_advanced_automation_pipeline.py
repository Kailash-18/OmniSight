"""
OmniSight Advanced Multimodal Self-Healing & RPA Pipeline Demo Script.
Executes complete closed-loop workflow:
1. Multi-viewport Playwright capture
2. Spatial anomaly detection & accessibility audit
3. Component screenshot cropping & token optimization
4. Confidence-aware risk scoring
5. Atomic patch sandboxing & retest verification
6. Forensic audit bundling with cryptographic SHA-256 manifests
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
for p in [REPO_ROOT, BACKEND_ROOT]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from PIL import Image

from automation.engine import (
    AccessibilityScanner,
    BoundingBox,
    ComponentCropper,
    ForensicBundler,
    PatchSandbox,
    SpatialAnalyzer,
    VisualComparator,
)
from app.schemas.run_schema import DefectCategory, FindingSchema, PatchObject, Severity
from app.services.action_engine import action_engine


def main():
    print("=" * 70)
    print("[*] OMNISIGHT ADVANCED MULTIMODAL PIPELINE DEMONSTRATION")
    print("=" * 70)

    demo_dir = Path("artifacts/runs/demo-advanced-week3")
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate synthetic viewport evidence
    print("\n[1/6] Generating responsive baseline screenshots...")
    desktop_shot = demo_dir / "desktop_1440x900_checkout.png"
    mobile_shot = demo_dir / "mobile_375x667_checkout.png"
    Image.new("RGB", (1440, 900), (250, 250, 252)).save(desktop_shot)
    Image.new("RGB", (375, 667), (250, 250, 252)).save(mobile_shot)
    print(f"  [+] Saved desktop: {desktop_shot}")
    print(f"  [+] Saved mobile:  {mobile_shot}")

    # Step 2: Spatial & Accessibility audits
    print("\n[2/6] Executing Spatial & Accessibility Scans...")
    mock_dom = [
        {"tag": "button", "test_id": "btn-place-order", "text": "Place Order", "box": {"x": 20, "y": 600, "width": 500, "height": 48}},
        {"tag": "img", "test_id": "cart-item-mug", "alt": None, "box": {"x": 20, "y": 100, "width": 80, "height": 80}},
    ]
    a11y_findings = AccessibilityScanner.audit_element_tree(mock_dom)
    print(f"  [+] Found {len(a11y_findings)} accessibility violation(s): {[f.issue_type for f in a11y_findings]}")

    # Step 3: Focused component cropping
    print("\n[3/6] Cropping anomalous UI components for VLM efficiency...")
    cropper = ComponentCropper(padding=24)
    crop_path = demo_dir / "crop_btn_place_order.png"
    crop_res = cropper.crop_region(mobile_shot, BoundingBox(20, 600, 355, 48), crop_path)
    print(f"  [+] Cropped component: {crop_res.cropped_dimensions} (original: {crop_res.original_dimensions})")
    print(f"  [+] Area reduction: {crop_res.area_reduction_percentage}%")
    print(f"  [+] Estimated token savings: {crop_res.estimated_token_savings_percentage}%")

    # Step 4: Risk scoring
    print("\n[4/6] Evaluating remediation risk gate...")
    finding = FindingSchema(
        id="demo-defect-1",
        category=DefectCategory.ELEMENT_CLIPPING,
        severity=Severity.HIGH,
        description="Checkout button overflows mobile viewport boundary",
        viewport="mobile_375x667",
        confidence=0.94,
        suggested_change="width: 100%; box-sizing: border-box;",
        rationale="Button extends outside viewport boundary",
        status="detected",
    )
    patch = PatchObject(
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn-order { width: 500px; }\n+.btn-order { width: 100%; box-sizing: border-box; }",
        explanation="Make checkout button fluid",
    )
    score, verdict = action_engine.calculate_remediation_risk([finding], patch)
    print(f"  [+] Risk Score: {score}/100.0 (Verdict: {verdict})")

    # Step 5: Sandbox atomic rollback test
    print("\n[5/6] Testing patch application in atomic sandbox...")
    dummy_css = demo_dir / "temp_defects.css"
    dummy_css.write_text(".btn-order { width: 500px; }\n", encoding="utf-8")
    with PatchSandbox(dummy_css, patch.diff, bypass_allowlist_for_testing=True) as sandbox:
        print("  [+] Patch safely applied in sandbox.")
        assert "width: 100%" in dummy_css.read_text(encoding="utf-8")
    print("  [+] Sandbox exited. Rollback verified: " + str(sandbox.verify_restoration()))

    # Step 6: Forensic bundle compilation
    print("\n[6/6] Generating SHA-256 forensic audit bundle...")
    bundler = ForensicBundler(artifacts_base_dir=demo_dir.parent.parent)
    bundle_res = bundler.bundle_run(
        run_id="demo-advanced-week3",
        run_dir=demo_dir,
        run_data={"status": "fixed", "risk_score": score, "verdict": verdict},
    )
    print(f"  [+] Forensic Bundle: {bundle_res['bundle_name']}")
    print(f"  [+] Cryptographic SHA-256: {bundle_res.get('sha256')}")
    print(f"  [+] Packed Artifacts: {bundle_res['artifact_count']} files ({bundle_res['size_bytes']} bytes)")

    print("\n" + "=" * 70)
    print("[+] CLOSED-LOOP MULTIMODAL DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
