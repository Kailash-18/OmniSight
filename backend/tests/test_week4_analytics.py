"""
Analytics and QA approval integration test suite for Week 4.
"""
import pytest
from backend.app.services.approval_service import QAManagerApprovalEngine
from backend.app.schemas.approval_schema import (
    ApprovalDecision,
    BulkApprovalRequest,
)

def test_qa_approval_lifecycle():
    engine = QAManagerApprovalEngine()
    resp = engine.record_approval(
        run_id="run-qa-1",
        manager_id="lead_qa@infotact.in",
        decision=ApprovalDecision.APPROVED,
        review_notes="Approved automated patch after visual verification."
    )
    assert resp.decision == ApprovalDecision.APPROVED
    assert resp.manager_id == "lead_qa@infotact.in"
    assert resp.auto_merge_unlocked is True

def test_telemetry_csv_export_format():
    engine = QAManagerApprovalEngine()
    mock_runs = {
        "run-qa-csv": {
            "status": "fixed",
            "retest_evidence": {"visual_diff_score": 0.0},
            "findings": [{"severity": "high"}]
        }
    }
    report = engine.generate_telemetry_report(mock_runs)
    assert report.total_runs_audited >= 1
    assert report.fixed_runs_count >= 1
