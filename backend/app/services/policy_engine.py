# -*- coding: utf-8 -*-
"""
Autonomous Self-Healing Policy Engine & Merge Gating for OmniSight.
Enforces multi-tier release policies, assessing blast radius, visual diff tolerances,
defect severity ceilings, and flakiness quarantine status.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.services.patch_validator import validate_patch
from app.services.flakiness_service import is_defect_quarantined


MAX_AUTO_MERGE_DIFF_LINES = 40
MAX_AUTO_MERGE_VISUAL_DIFF_THRESHOLD = 0.05  # 0.05% pixel mismatch tolerance


def evaluate_merge_policy(
    run_id: str,
    target_file: Optional[str] = None,
    diff_content: Optional[str] = None,
    visual_diff_score: Optional[float] = None,
    defect_severities: Optional[List[str]] = None,
    defect_fingerprints: Optional[List[str]] = None,
    author: Optional[str] = "omnisight-agent"
) -> Dict[str, Any]:
    """
    Evaluates whether a generated visual repair satisfies auto-merge policy criteria.
    Returns structured gate level (auto_merge, human_review, rejected), risk scores,
    and granular rule evaluation breakdowns.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    passed_rules: List[str] = []
    blocking_reasons: List[str] = []
    warnings: List[str] = []
    rule_evaluations: List[Dict[str, Any]] = []

    severities = [s.lower() for s in (defect_severities or [])]
    fingerprints = defect_fingerprints or []

    # -------------------------------------------------------------------------
    # Rule 1: Zero-Trust Security & Path Validation
    # -------------------------------------------------------------------------
    if not target_file or not diff_content:
        val_status = False
        val_msg = "Target file or diff content is missing."
    else:
        val = validate_patch(target_file, diff_content)
        val_status = val["validation_status"]
        val_msg = val.get("validator_errors") or "Patch passed security checks."

    rule_evaluations.append({
        "rule_name": "zero_trust_security_validation",
        "passed": val_status,
        "severity": "blocking",
        "message": val_msg
    })

    if not val_status:
        blocking_reasons.append(f"Security check failed: {val_msg}")
        return {
            "run_id": run_id,
            "gate_level": "rejected",
            "auto_merge_allowed": False,
            "overall_risk_score": 100.0,
            "passed_rules": [],
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "rule_evaluations": rule_evaluations,
            "timestamp": now_iso
        }
    passed_rules.append("zero_trust_security_validation")

    # -------------------------------------------------------------------------
    # Rule 2: Pure CSS vs JSX/JS Scope
    # -------------------------------------------------------------------------
    is_pure_css = target_file.lower().endswith(".css")
    if is_pure_css:
        passed_rules.append("pure_css_scope")
        rule_evaluations.append({
            "rule_name": "pure_css_scope",
            "passed": True,
            "severity": "info",
            "message": "Patch targets pure CSS stylesheet."
        })
    else:
        warnings.append("Patch modifies JSX/JS component logic; requires mandatory human QA sign-off.")
        rule_evaluations.append({
            "rule_name": "pure_css_scope",
            "passed": False,
            "severity": "warning",
            "message": "Patch modifies code beyond pure CSS stylesheets."
        })

    # -------------------------------------------------------------------------
    # Rule 3: Diff Blast Radius & Line Budget
    # -------------------------------------------------------------------------
    diff_lines = len([l for l in (diff_content or "").splitlines() if l.startswith("+") or l.startswith("-")])
    within_line_budget = diff_lines <= MAX_AUTO_MERGE_DIFF_LINES
    if within_line_budget:
        passed_rules.append("diff_line_budget")
        rule_evaluations.append({
            "rule_name": "diff_line_budget",
            "passed": True,
            "severity": "info",
            "message": f"Diff modified lines ({diff_lines}) within auto-merge ceiling ({MAX_AUTO_MERGE_DIFF_LINES})."
        })
    else:
        warnings.append(f"Diff modified {diff_lines} lines (ceiling: {MAX_AUTO_MERGE_DIFF_LINES}); requires human review.")
        rule_evaluations.append({
            "rule_name": "diff_line_budget",
            "passed": False,
            "severity": "warning",
            "message": f"Diff line count ({diff_lines}) exceeds auto-merge limit."
        })

    # -------------------------------------------------------------------------
    # Rule 4: Sandbox Retest Visual Verification Threshold
    # -------------------------------------------------------------------------
    if visual_diff_score is None:
        retest_passed = False
        retest_msg = "Retest verification has not been recorded."
        warnings.append("Retest visual diff verification pending.")
    else:
        retest_passed = visual_diff_score <= MAX_AUTO_MERGE_VISUAL_DIFF_THRESHOLD
        retest_msg = f"Visual diff score {visual_diff_score}% (threshold <= {MAX_AUTO_MERGE_VISUAL_DIFF_THRESHOLD}%)."
        if not retest_passed:
            warnings.append(f"Visual diff score {visual_diff_score}% exceeds tolerance threshold.")

    rule_evaluations.append({
        "rule_name": "retest_visual_verification",
        "passed": retest_passed,
        "severity": "blocking" if visual_diff_score is None else "warning",
        "message": retest_msg
    })
    if retest_passed:
        passed_rules.append("retest_visual_verification")

    # -------------------------------------------------------------------------
    # Rule 5: Critical Defect Severity Ceiling
    # -------------------------------------------------------------------------
    has_critical = "critical" in severities
    if not has_critical:
        passed_rules.append("severity_ceiling_acceptable")
        rule_evaluations.append({
            "rule_name": "severity_ceiling_acceptable",
            "passed": True,
            "severity": "info",
            "message": "No critical defects require human escalation."
        })
    else:
        warnings.append("Patch addresses CRITICAL severity defect; mandatory human review required.")
        rule_evaluations.append({
            "rule_name": "severity_ceiling_acceptable",
            "passed": False,
            "severity": "warning",
            "message": "Critical defect present."
        })

    # -------------------------------------------------------------------------
    # Rule 6: Flakiness & Quarantine Check
    # -------------------------------------------------------------------------
    quarantined_fps = [fp for fp in fingerprints if is_defect_quarantined(fp)]
    if not quarantined_fps:
        passed_rules.append("quarantine_clearance")
        rule_evaluations.append({
            "rule_name": "quarantine_clearance",
            "passed": True,
            "severity": "info",
            "message": "None of the addressed defects are currently quarantined."
        })
    else:
        warnings.append(f"Contains quarantined defects ({', '.join(quarantined_fps)}); held for review.")
        rule_evaluations.append({
            "rule_name": "quarantine_clearance",
            "passed": False,
            "severity": "warning",
            "message": "Contains quarantined defect."
        })

    # -------------------------------------------------------------------------
    # Risk Score & Final Gate Determination
    # -------------------------------------------------------------------------
    base_risk = 10.0
    if not is_pure_css:
        base_risk += 35.0
    if not within_line_budget:
        base_risk += 25.0
    if not retest_passed:
        base_risk += 20.0
    if has_critical:
        base_risk += 20.0
    if quarantined_fps:
        base_risk += 15.0

    overall_risk = min(100.0, base_risk)

    # Auto-merge eligibility criteria:
    # 1. Zero-trust security passed
    # 2. Pure CSS stylesheet modification
    # 3. Diff <= 40 lines
    # 4. Retest visual diff <= 0.05%
    # 5. No critical severity defects
    # 6. No quarantined defects
    can_auto_merge = (
        val_status and
        is_pure_css and
        within_line_budget and
        retest_passed and
        not has_critical and
        not quarantined_fps
    )

    gate_level = "auto_merge" if can_auto_merge else "human_review"

    return {
        "run_id": run_id,
        "gate_level": gate_level,
        "auto_merge_allowed": can_auto_merge,
        "overall_risk_score": round(overall_risk, 2),
        "passed_rules": passed_rules,
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "rule_evaluations": rule_evaluations,
        "timestamp": now_iso
    }
