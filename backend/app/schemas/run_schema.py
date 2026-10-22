"""
Pydantic Schemas and Enums for OmniSight Backend API.
Enforces data integrity, validation rules, and schema compatibility with Automation & Dashboard.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Execution lifecycle status of an audit run."""
    QUEUED = "queued"
    RUNNING = "running"
    AUDITED = "audited"
    PATCH_REJECTED = "patch_rejected"
    VERIFYING = "verifying"
    FIXED = "fixed"
    NEEDS_REVIEW = "needs_review"
    PR_OPENED = "pr_opened"
    FAILED = "failed"


class DefectCategory(str, Enum):
    """Classification of visual defects."""
    ELEMENT_OVERLAP = "element_overlap"
    ELEMENT_CLIPPING = "element_clipping"
    ELEMENT_OBSTRUCTION = "element_obstruction"
    CONTRAST_ISSUE = "contrast_issue"
    LAYOUT_OVERFLOW = "layout_overflow"


class Severity(str, Enum):
    """Impact severity of visual defects."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Request Payloads
# ---------------------------------------------------------------------------

class BuildWebhookPayload(BaseModel):
    """Simulated CI/CD build event payload."""
    target_url: str = Field(..., description="Target staging or local URL to audit")
    branch: str = Field(default="main", description="Git branch under test")
    scenario: str = Field(default="checkout_flow", description="User journey scenario to execute")
    commit_sha: Optional[str] = Field(default=None, description="Git commit hash")
    event_id: Optional[str] = Field(default=None, description="External CI event identifier")


class RunTriggerPayload(BaseModel):
    """Manual trigger payload for on-demand browser audit."""
    target_url: str = Field(..., description="Local or staging app URL to audit")
    scenario: str = Field(default="checkout_flow", description="Journey scenario")
    viewports: List[str] = Field(
        default_factory=lambda: ["desktop_1440x900", "mobile_375x667"],
        description="List of target viewports"
    )


class FindingSchema(BaseModel):
    """Structured defect report item from VLM visual inspection."""
    id: str = Field(..., description="Unique defect ID (e.g. defect-1-overlap)")
    category: DefectCategory = Field(..., description="Visual defect category")
    severity: Severity = Field(..., description="Impact severity")
    description: str = Field(..., description="Human-readable explanation of the defect")
    viewport: str = Field(..., description="Viewport where defect was identified")
    target_element: Optional[str] = Field(default=None, description="CSS selector or test ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    suggested_change: str = Field(..., description="Proposed CSS/layout rule correction")
    rationale: str = Field(..., description="Visual reasoning justification")
    status: str = Field(default="detected", description="Current remediation status")


class PatchObject(BaseModel):
    """Constrained code/CSS patch suggestion."""
    target_file: str = Field(..., description="Allowlisted relative file path")
    diff: str = Field(..., description="Unified git diff or targeted CSS changes")
    explanation: Optional[str] = Field(default=None, description="Rationale for the patch")
    validation_status: Optional[bool] = Field(default=None, description="Whether patch passed security checks")
    validator_errors: Optional[str] = Field(default=None, description="Error reason if patch was rejected")


class PatchSubmitPayload(BaseModel):
    """Payload to submit, validate, and optionally PR a proposed patch."""
    target_file: str = Field(..., description="Relative file path of patch target")
    diff: str = Field(..., description="Unified diff of the patch")
    file_content: str = Field(..., description="Full modified file content to commit")
    pr_title: str = Field(default="OmniSight Automated Visual Defect Fix", description="PR title")
    pr_body: str = Field(default="", description="Detailed PR description with evidence")


class VLMParseRequest(BaseModel):
    """Payload containing raw VLM natural language or JSON text for Action Engine parsing."""
    raw_vlm_output: str = Field(..., description="Raw text response returned by VLM")
    run_id: Optional[str] = Field(default=None, description="Optional associated run ID")


class RunRecordUpdatePayload(BaseModel):
    """Payload for updating an existing run state and evidence."""
    status: Optional[RunStatus] = None
    steps: Optional[List[str]] = None
    evidence_paths: Optional[Dict[str, Any]] = None
    findings: Optional[List[FindingSchema]] = None
    patch: Optional[PatchObject] = None
    retry_count: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class VLMParseResponse(BaseModel):
    """Result of Action Engine extraction and validation."""
    is_valid: bool = Field(..., description="True if output parsed and structured successfully")
    findings: List[FindingSchema] = Field(default_factory=list, description="Extracted findings")
    summary: Optional[str] = Field(default=None, description="Executive summary of visual audit")
    proposed_patch: Optional[PatchObject] = Field(default=None, description="Extracted and checked patch")
    validation_status: bool = Field(default=False, description="True if patch passed security guardrails")
    validator_errors: Optional[str] = Field(default=None, description="Validation failure details if any")
    parse_errors: List[str] = Field(default_factory=list, description="Parsing or validation warnings")


class RunSummaryResponse(BaseModel):
    """Concise run summary for dashboard list view."""
    run_id: str
    start_time: str
    target: str
    status: RunStatus
    issue_count: int
    pr_url: Optional[str] = None


class RunDetailResponse(BaseModel):
    """Complete forensic run report for dashboard inspection."""
    run_id: str
    start_time: str
    target: str
    status: RunStatus
    steps: List[str] = Field(default_factory=list)
    evidence_paths: Dict[str, Any] = Field(default_factory=dict)
    findings: List[FindingSchema] = Field(default_factory=list)
    patch: Optional[PatchObject] = None
    retry_count: int = 0
    pr_url: Optional[str] = None
    error: Optional[str] = None