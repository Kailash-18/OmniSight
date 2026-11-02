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
