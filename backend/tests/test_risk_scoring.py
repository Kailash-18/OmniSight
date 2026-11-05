"""
Unit Tests for Confidence-Aware Risk Scoring Engine & Repair Gate.
Verifies composite risk calculation based on model confidence, patch size, and file sensitivity.
"""

from app.schemas.run_schema import DefectCategory, FindingSchema, PatchObject, Severity
from app.services.action_engine import action_engine


def test_risk_scoring_low_risk_patch():
    finding = FindingSchema(
        id="f1",
        category=DefectCategory.ELEMENT_CLIPPING,
        severity=Severity.LOW,
        description="Minor padding adjustment",
        viewport="desktop_1440x900",
        confidence=0.96,
        suggested_change="padding: 12px;",
        rationale="Spacing looks tight",
        status="detected",
    )
    patch = PatchObject(
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn { padding: 4px; }\n+.btn { padding: 12px; }",
        explanation="Increase padding",
    )
    score, verdict = action_engine.calculate_remediation_risk([finding], patch)
    assert score < 50.0
    assert verdict == "auto_pr_allowed"


def test_risk_scoring_high_risk_low_confidence():
    finding = FindingSchema(
        id="f2",
        category=DefectCategory.ELEMENT_OVERLAP,
        severity=Severity.CRITICAL,
        description="Critical collision on checkout",
        viewport="mobile_375x667",
        confidence=0.62,
        suggested_change="Rewrite layout",
        rationale="Severe defect",
        status="detected",
    )
    patch = PatchObject(
        target_file="app-under-test/src/App.jsx",
        diff="""--- a/App.jsx
+++ b/App.jsx
@@ -10,25 +10,25 @@
-function Bad() { ... }
+function Good() { ... }
""",
        explanation="Refactor core component",
    )
    score, verdict = action_engine.calculate_remediation_risk([finding], patch)
    assert score >= 50.0
    assert verdict == "requires_human_review"
