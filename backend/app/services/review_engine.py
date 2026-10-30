# -*- coding: utf-8 -*-
"""
Human-in-the-Loop QA Review Decision Engine for OmniSight.
Provides review sign-off, change request feedback, rejection handling,
and QA lead policy overrides for automated visual self-healing runs.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

UTC = timezone.utc

# In-memory registry of recorded QA review decisions per run ID
reviews_db: Dict[str, List[Dict[str, Any]]] = {}

VALID_DECISIONS = {"approved", "rejected", "changes_requested", "override"}


def record_review_decision(
    run_id: str,
    reviewer_id: str,
    decision: str,
    comments: str,
    auto_merge_authorized: bool = False,
    risk_acknowledgement: Optional[str] = None,
    runs_db: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Records a formal human QA review decision for a specific audit run.
    Validates decision type, logs audit event, and updates run state accordingly.
    """
    decision_clean = (decision or "").strip().lower()
    if decision_clean not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision '{decision}'. Must be one of: {sorted(VALID_DECISIONS)}")

    if not reviewer_id or not reviewer_id.strip():
        raise ValueError("Reviewer ID cannot be empty.")

    if not comments or len(comments.strip()) < 5:
        raise ValueError("Review comments must contain at least 5 characters.")

    decision_id = f"rev-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(UTC).isoformat()

    record = {
        "decision_id": decision_id,
        "run_id": run_id,
        "reviewer_id": reviewer_id.strip(),
        "decision": decision_clean,
        "comments": comments.strip(),
        "auto_merge_authorized": auto_merge_authorized,
        "risk_acknowledgement": risk_acknowledgement,
        "created_at": now_iso,
    }

    if run_id not in reviews_db:
        reviews_db[run_id] = []
    reviews_db[run_id].append(record)

    # Reflect review outcome in active run if runs_db is provided
    if runs_db is not None and run_id in runs_db:
        run = runs_db[run_id]
        if decision_clean == "approved":
            # Approved fix
            run["status"] = "fixed"
            run["reviewed_by"] = reviewer_id
            run["review_status"] = "approved"
        elif decision_clean == "rejected":
            run["status"] = "failed"
            run["reviewed_by"] = reviewer_id
            run["review_status"] = "rejected"
        elif decision_clean == "changes_requested":
            run["status"] = "needs_review"
            run["reviewed_by"] = reviewer_id
            run["review_status"] = "changes_requested"
        elif decision_clean == "override":
            run["status"] = "fixed"
            run["reviewed_by"] = reviewer_id
            run["review_status"] = "lead_override"

        # Append timeline entry
        timeline = run.get("timeline", [])
        timeline.append({
            "event": f"Review Decision: {decision_clean.upper()}",
            "reviewer": reviewer_id,
            "timestamp": now_iso,
            "notes": comments.strip()
        })
        run["timeline"] = timeline

    return record


def record_lead_override(
    run_id: str,
    lead_reviewer_id: str,
    override_reason: str,
    acknowledged_risks: Optional[List[str]] = None,
    runs_db: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Allows authorized QA Leads to explicitly override automated policy rejections
    (such as high blast-radius diffs or quarantined defect blocks).
    """
    if not override_reason or len(override_reason.strip()) < 10:
        raise ValueError("Lead override reason must contain at least 10 characters justifying the bypass.")

    risks_str = ", ".join(acknowledged_risks) if acknowledged_risks else "None acknowledged"
    comments = f"EXECUTIVE OVERRIDE: {override_reason.strip()} | Acknowledged Risks: {risks_str}"

    return record_review_decision(
        run_id=run_id,
        reviewer_id=lead_reviewer_id,
        decision="override",
        comments=comments,
        auto_merge_authorized=True,
        risk_acknowledgement=risks_str,
        runs_db=runs_db
    )


def get_review_trail(run_id: str) -> List[Dict[str, Any]]:
    """Returns the full history of review decisions for a given run ID."""
    return list(reviews_db.get(run_id, []))


def clear_reviews_db() -> None:
    """Clears the review decisions registry (used in test isolation)."""
    reviews_db.clear()
