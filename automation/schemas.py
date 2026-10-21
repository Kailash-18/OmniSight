"""
VLM Finding and Visual Audit Data Schemas.
Defines Pydantic models for structured multimodal AI responses.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DefectCategory(str, Enum):
    ELEMENT_OVERLAP = "element_overlap"
    ELEMENT_CLIPPING = "element_clipping"
    ELEMENT_OBSTRUCTION = "element_obstruction"
    CONTRAST_ISSUE = "contrast_issue"
    LAYOUT_OVERFLOW = "layout_overflow"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    id: str = Field(description="Unique defect identifier")
    category: DefectCategory = Field(description="Classification of the visual bug")
    severity: Severity = Field(description="Impact on user journey")
    description: str = Field(description="Clear explanation of the visual flaw")
    viewport: str = Field(description="Viewport(s) where defect is observable")
    target_element: Optional[str] = Field(default=None, description="CSS selector or test ID")
    confidence: float = Field(ge=0.0, le=1.0, description="VLM model confidence score")
    suggested_change: str = Field(description="Proposed CSS/layout rule correction")
    rationale: str = Field(description="Multimodal visual reasoning justification")
    status: str = Field(default="detected", description="Remediation status")


class ProposedPatch(BaseModel):
    target_file: str = Field(description="Allowlisted relative path to file")
    diff: str = Field(description="Unified git diff representing the fix")
    explanation: str = Field(description="Why this patch repairs the visual defect")


class VisualAuditReport(BaseModel):
    run_id: str
    target_url: str
    findings: List[Finding]
    summary: str
    proposed_patch: Optional[ProposedPatch] = None
