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
