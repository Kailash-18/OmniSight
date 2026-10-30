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
