"""
Unit and Integration Tests for QA Manager Review & Release Approval Engine and Telemetry.
"""

import pytest
from backend.app.schemas.approval_schema import (
    ApprovalDecision,
    QAManagerApprovalRequest,
    BulkApprovalRequest,
)
from backend.app.services.approval_service import QAManagerApprovalEngine, qa_approval_engine


def test_qa_manager_approved_decision():
    """Verify approved decision unlocks automated merge and transitions status to fixed."""
    engine = QAManagerApprovalEngine()
    resp = engine.record_approval(
        run_id="run-qa-1",
        manager_id="lead_qa@infotact.in",
        decision=ApprovalDecision.APPROVED,
        review_notes="Verified visual alignment on mobile and desktop."
    )
    assert resp.run_id == "run-qa-1"
    assert resp.decision == ApprovalDecision.APPROVED
    assert resp.auto_merge_unlocked is True
    assert resp.resulting_run_status == "fixed"
    assert "APPR-QA-" in resp.approval_id
