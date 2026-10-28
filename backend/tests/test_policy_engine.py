# -*- coding: utf-8 -*-
"""
Unit Test Suite for OmniSight Self-Healing Policy Engine & Auto-Merge Gating.
Verifies multi-rule release gates, security clearance, diff thresholds, and risk scoring.
"""

import pytest
from app.services.policy_engine import evaluate_merge_policy
from app.services.flakiness_service import quarantine_defect, reset_flakiness_tracker


@pytest.fixture(autouse=True)
def clean_flakiness_state():
    reset_flakiness_tracker()
    yield
    reset_flakiness_tracker()


VALID_CSS_DIFF = """--- a/app-under-test/src/styles/defects.css
+++ b/app-under-test/src/styles/defects.css
@@ -10,3 +10,4 @@
 .checkout-btn {
+  width: 100%;
 }
"""


def test_policy_eval_auto_merge_success():
    """Verify compliant, small, verified pure CSS patch is approved for auto-merge."""
    eval_res = evaluate_merge_policy(
        run_id="run-auto-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=VALID_CSS_DIFF,
        visual_diff_score=0.00,
        defect_severities=["medium", "low"],
        defect_fingerprints=["dfp-btn-overlap"],
    )
    assert eval_res["gate_level"] == "auto_merge"
    assert eval_res["auto_merge_allowed"] is True
    assert eval_res["overall_risk_score"] < 25.0
    assert len(eval_res["blocking_reasons"]) == 0
    assert "diff_line_budget" in eval_res["passed_rules"]
    assert "pure_css_scope" in eval_res["passed_rules"]
    assert "retest_visual_verification" in eval_res["passed_rules"]


def test_policy_eval_rejects_security_violation():
    """Verify patches failing zero-trust validation are immediately rejected."""
    bad_diff = """--- a/app-under-test/src/styles/defects.css
+++ b/app-under-test/src/styles/defects.css
@@ -1,3 +1,4 @@
+body { background: url('javascript:alert(1)'); }
"""
    eval_res = evaluate_merge_policy(
        run_id="run-reject-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=bad_diff,
        visual_diff_score=0.00,
    )
    assert eval_res["gate_level"] == "rejected"
    assert eval_res["auto_merge_allowed"] is False
    assert eval_res["overall_risk_score"] == 100.0
    assert any("Security check failed" in r for r in eval_res["blocking_reasons"])


def test_policy_eval_human_review_for_jsx():
    """Verify JSX modifications escalate gate to human review."""
    jsx_diff = """--- a/app-under-test/src/App.jsx
+++ b/app-under-test/src/App.jsx
@@ -5,3 +5,4 @@
+<div className="safe-wrapper"></div>
"""
    eval_res = evaluate_merge_policy(
        run_id="run-jsx-1",
        target_file="app-under-test/src/App.jsx",
        diff_content=jsx_diff,
        visual_diff_score=0.00,
    )
    assert eval_res["gate_level"] == "human_review"
    assert eval_res["auto_merge_allowed"] is False
    assert any("modifies JSX/JS" in w for w in eval_res["warnings"])


def test_policy_eval_human_review_for_large_diff():
    """Verify patches modifying more than 40 lines require human QA oversight."""
    # Build 45 modified lines
    large_lines = ["--- a/app-under-test/src/styles/defects.css", "+++ b/app-under-test/src/styles/defects.css", "@@ -1,1 +1,45 @@"]
    for i in range(45):
        large_lines.append(f"+.selector-{i} {{ margin: 0; }}")
    large_diff = "\n".join(large_lines)

    eval_res = evaluate_merge_policy(
        run_id="run-large-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=large_diff,
        visual_diff_score=0.00,
    )
    assert eval_res["gate_level"] == "human_review"
    assert eval_res["auto_merge_allowed"] is False
    assert any("ceiling" in w for w in eval_res["warnings"])


def test_policy_eval_human_review_for_unverified_retest():
    """Verify missing or failing sandbox retest blocks auto-merge."""
    eval_res = evaluate_merge_policy(
        run_id="run-unverified-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=VALID_CSS_DIFF,
        visual_diff_score=None,  # Not retested yet
    )
    assert eval_res["gate_level"] == "human_review"
    assert eval_res["auto_merge_allowed"] is False

    # Score exceeding 0.05%
    eval_res2 = evaluate_merge_policy(
        run_id="run-high-diff-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=VALID_CSS_DIFF,
        visual_diff_score=0.15,
    )
    assert eval_res2["gate_level"] == "human_review"
    assert eval_res2["auto_merge_allowed"] is False


def test_policy_eval_human_review_for_critical_defect():
    """Verify patches addressing critical severity defects mandate human approval."""
    eval_res = evaluate_merge_policy(
        run_id="run-critical-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=VALID_CSS_DIFF,
        visual_diff_score=0.00,
        defect_severities=["critical"],
    )
    assert eval_res["gate_level"] == "human_review"
    assert eval_res["auto_merge_allowed"] is False
    assert any("CRITICAL" in w for w in eval_res["warnings"])


def test_policy_eval_human_review_for_quarantined_defect():
    """Verify addressing a quarantined defect prevents automated auto-merge."""
    quarantine_defect("dfp-flaky-card", reason="Flaky animation timing")

    eval_res = evaluate_merge_policy(
        run_id="run-quarantine-1",
        target_file="app-under-test/src/styles/defects.css",
        diff_content=VALID_CSS_DIFF,
        visual_diff_score=0.00,
        defect_fingerprints=["dfp-flaky-card"],
    )
    assert eval_res["gate_level"] == "human_review"
    assert eval_res["auto_merge_allowed"] is False
    assert any("quarantined" in w for w in eval_res["warnings"])
