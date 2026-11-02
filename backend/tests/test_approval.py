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

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_qa_approval_and_bulk_flow():
    """Integration test verifying QA manager approval and bulk release endpoints."""
    # Step 1: Submit single approval
    appr_payload = {
        "run_id": "test-api-appr-1",
        "manager_id": "lead_qa@infotact.in",
        "decision": "approved",
        "review_notes": "Tested in responsive mobile viewport.",
        "signoff_role": "qa_lead"
    }
    resp = client.post("/runs/test-api-appr-1/qa-approval", json=appr_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "approved"
    assert data["auto_merge_unlocked"] is True

    # Step 2: Get approval trail
    trail_resp = client.get("/runs/test-api-appr-1/qa-approval")
    assert trail_resp.status_code == 200
    assert trail_resp.json()["total"] >= 1

    # Step 3: Bulk approval
    bulk_payload = {
        "run_ids": ["test-bulk-1", "test-bulk-2"],
        "manager_id": "lead_qa@infotact.in",
        "decision": "approved",
        "batch_notes": "Bulk staging validation"
    }
    bulk_resp = client.post("/runs/qa-approval/bulk", json=bulk_payload)
    assert bulk_resp.status_code == 200
    assert bulk_resp.json()["total_requested"] == 2

    # Step 4: Telemetry report
    telem_resp = client.get("/runs/telemetry/report")
    assert telem_resp.status_code == 200
    assert "healing_success_rate_percent" in telem_resp.json()

    # Step 5: CSV export
    csv_resp = client.get("/runs/export/csv")
    assert csv_resp.status_code == 200
    assert "run_id" in csv_resp.text and "status" in csv_resp.text
