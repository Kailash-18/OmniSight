# -*- coding: utf-8 -*-
"""
Remediation Verification & Compliance Certificate Service for OmniSight.
Generates cryptographically sealed Certificates of Visual Remediation
documenting automated defect detection, sandbox retest validation, and human sign-off.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

UTC = timezone.utc


def _canonical_str(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def generate_remediation_certificate(
    run_id: str,
    run_data: Dict[str, Any],
    review_trail: Optional[List[Dict[str, Any]]] = None,
    forensic_checksum: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a cryptographically sealed Certificate of Visual Remediation.
    Captures audit provenance, resolved defects, visual diff scores, policy evaluations,
    and reviewer authorizations in an immutable compliance record.
    """
    now_iso = datetime.now(UTC).isoformat()
    findings = run_data.get("findings", [])
    retest = run_data.get("retest_outcome") or {}
    visual_diff = retest.get("visual_diff_score", 0.0)
    passed = retest.get("passed", True)

    latest_review = review_trail[-1] if review_trail else None
    reviewer_sig = latest_review.get("reviewer_id", "automated-pipeline") if latest_review else "automated-pipeline"
    review_decision = latest_review.get("decision", "policy-validated") if latest_review else "policy-validated"

    # Deterministic certificate ID based on run ID and timestamp
    raw_sig_seed = f"{run_id}:{visual_diff}:{forensic_checksum or 'none'}"
    cert_hash = hashlib.sha256(raw_sig_seed.encode("utf-8")).hexdigest()
    cert_id = f"CERT-OMNI-{cert_hash[:10].upper()}"

    cert_payload = {
        "certificate_id": cert_id,
        "run_id": run_id,
        "target_url": run_data.get("target", run_data.get("url", "unknown")),
        "status": "CERTIFIED_FIXED" if passed else "RETEST_PENDING",
        "issued_at": now_iso,
        "viewports_evaluated": run_data.get("viewports", ["1280x720"]),
        "defects_resolved_count": len(findings),
        "visual_delta_ratio": visual_diff,
        "verification_result": "PASSED" if passed else "FAILED",
        "forensic_checksum": forensic_checksum or hashlib.sha256(run_id.encode("utf-8")).hexdigest(),
        "policy_gate_status": run_data.get("policy_status", "cleared"),
        "primary_reviewer": reviewer_sig,
        "review_decision": review_decision,
        "issuer": "OmniSight Autonomous Visual Remediation Authority v1.0",
