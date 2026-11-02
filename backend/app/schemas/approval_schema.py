"""
OmniSight QA Manager Review & Release Approval Schemas.
Defines data models for formal QA sign-offs, bulk release triage, and operational telemetry.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class ApprovalDecision(str, Enum):
    """Allowed QA Manager sign-off decision states."""
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class QAManagerApprovalRequest(BaseModel):
    """Request payload for a QA manager to formally sign off on an automated fix."""
    run_id: str = Field(..., description="Unique audit run identifier", min_length=3)
    manager_id: str = Field(..., description="Corporate identity or email of reviewing QA manager", min_length=3)
    decision: ApprovalDecision = Field(..., description="Formal sign-off decision")
    review_notes: str = Field(..., description="Review justification and sign-off rationale", min_length=5)
    signoff_role: str = Field(default="qa_lead", description="Authorizing role (e.g. qa_lead, release_architect)")

class QAManagerApprovalResponse(BaseModel):
    """Formal sign-off confirmation receipt."""
    approval_id: str = Field(..., description="Unique immutable approval audit identifier")
    run_id: str = Field(..., description="Audit run identifier")
    manager_id: str = Field(..., description="Signing QA manager identity")
    decision: ApprovalDecision = Field(..., description="Recorded approval state")
    timestamp: float = Field(..., description="Unix epoch timestamp of sign-off")
    auto_merge_unlocked: bool = Field(..., description="Whether automated PR merge gate is cleared")
    resulting_run_status: str = Field(..., description="Updated run lifecycle status")


class BulkApprovalRequest(BaseModel):
    """Payload to batch-approve or reject multiple audit runs simultaneously."""
    run_ids: List[str] = Field(..., description="List of audit run identifiers to process", min_length=1)
    manager_id: str = Field(..., description="Signing QA manager identity")
    decision: ApprovalDecision = Field(..., description="Uniform decision applied across the batch")
    batch_notes: str = Field(default="Bulk approved via QA manager dashboard", description="Shared review notes")

class BulkApprovalResponse(BaseModel):
    """Execution summary for a bulk approval batch."""
    total_requested: int = Field(..., description="Total runs submitted for approval", ge=1)
    successful_runs: List[str] = Field(..., description="List of successfully updated run IDs")
    failed_runs: List[str] = Field(default_factory=list, description="List of runs that encountered errors")
    applied_decision: ApprovalDecision = Field(..., description="Decision applied across batch")
    batch_status: str = Field(default="completed", description="Overall batch execution outcome")


class TelemetryReportResponse(BaseModel):
    """Comprehensive operational telemetry and self-healing success metrics."""
    total_runs_audited: int = Field(..., description="Cumulative count of completed audit executions", ge=0)
    fixed_runs_count: int = Field(..., description="Count of successfully healed and verified runs", ge=0)
    healing_success_rate_percent: float = Field(..., description="Percentage of visual defects healed without human intervention", ge=0.0, le=100.0)
    average_latency_ms: float = Field(..., description="Average end-to-end self-healing latency in milliseconds", ge=0.0)
    total_tokens_saved: int = Field(..., description="Cumulative prompt tokens conserved via spatial optimization", ge=0)
    total_prs_opened: int = Field(..., description="Count of evidence-backed Pull Requests submitted to GitHub", ge=0)

class QAManagerAuditSignature(BaseModel):
    """Cryptographic audit signature attached to QA approval decisions."""
    signature_hash: str = Field(..., description="Deterministic SHA-256 digest of approval metadata")
    approval_id: str = Field(..., description="Associated approval ID")
    verified: bool = Field(default=True, description="Signature verification validity status")
