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

def test_qa_manager_rejected_and_changes_requested():
    """Verify rejected and changes_requested decisions lock auto-merge appropriately."""
    engine = QAManagerApprovalEngine()

    # Rejection
    rej = engine.record_approval(
        run_id="run-qa-2",
        manager_id="lead_qa@infotact.in",
        decision=ApprovalDecision.REJECTED,
        review_notes="Button color deviates from design system tokens."
    )
    assert rej.auto_merge_unlocked is False
    assert rej.resulting_run_status == "failed"

    # Changes Requested
    cr = engine.record_approval(
        run_id="run-qa-3",
        manager_id="lead_qa@infotact.in",
        decision=ApprovalDecision.CHANGES_REQUESTED,
        review_notes="Reduce margin padding by 4px on tablet screens."
    )
    assert cr.auto_merge_unlocked is False
    assert cr.resulting_run_status == "needs_review"

def test_bulk_approval_batch_processing():
    """Verify batch approval processes multiple runs concurrently."""
    engine = QAManagerApprovalEngine()
    run_list = ["run-batch-1", "run-batch-2", "run-batch-3"]
    res = engine.bulk_approve_runs(
        run_ids=run_list,
        manager_id="director_qa@infotact.in",
        decision=ApprovalDecision.APPROVED,
        batch_notes="Weekly release candidate regression approval."
    )
    assert res.total_requested == 3
    assert len(res.successful_runs) == 3
    assert len(res.failed_runs) == 0
    assert res.batch_status == "completed"

    # Verify audit history
    assert len(engine.get_approvals_for_run("run-batch-1")) == 1

def test_telemetry_report_generation():
    """Verify operational telemetry calculation across mock runs store."""
    engine = QAManagerApprovalEngine()
    mock_store = {
        "r1": {"status": "fixed", "pr_opened": True},
        "r2": {"status": "fixed", "pr_opened": True},
        "r3": {"status": "needs_review", "pr_opened": False},
        "r4": {"status": "failed", "pr_opened": False},
    }
    report = engine.generate_telemetry_report(mock_store)
    assert report.total_runs_audited == 4
    assert report.fixed_runs_count == 2
    assert report.healing_success_rate_percent == 50.0
    assert report.total_prs_opened == 2
    assert report.total_tokens_saved > 0
