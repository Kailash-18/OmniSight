"""
Pydantic Schemas and Enums for OmniSight Backend API.
Enforces data integrity, validation rules, and schema compatibility with Automation & Dashboard.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


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

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_clean = value.strip().lower().replace("-", "_")
            for member in cls:
                if member.value == val_clean:
                    return member
        return cls.FAILED


class DefectCategory(str, Enum):
    """Classification of visual defects."""
    ELEMENT_OVERLAP = "element_overlap"
    ELEMENT_CLIPPING = "element_clipping"
    ELEMENT_OBSTRUCTION = "element_obstruction"
    CONTRAST_ISSUE = "contrast_issue"
    LAYOUT_OVERFLOW = "layout_overflow"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().lower().replace("-", "_")
            for member in cls:
                if member.value == clean:
                    return member
        return cls.ELEMENT_OVERLAP


class Severity(str, Enum):
    """Impact severity of visual defects."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().lower()
            for member in cls:
                if member.value == clean:
                    return member
        return cls.MEDIUM


class HealthCheckResponse(BaseModel):
    """Health check status and server metadata."""
    status: str = Field(default="healthy", description="Readiness status of API gateway")
    timestamp: str = Field(..., description="Current UTC timestamp in ISO 8601 format")
    version: str = Field(..., description="API software version")


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
    rationale: Optional[str] = Field(default=None, description="Multimodal visual reasoning justification")
    status: str = Field(default="detected", description="Current remediation status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "defect-1-clipping",
                "category": "element_clipping",
                "severity": "high",
                "description": "Place Order button clipped beyond right boundary",
                "viewport": "mobile_375x667",
                "target_element": "button[data-testid='checkout-submit']",
                "confidence": 0.95,
                "suggested_change": "width: 100%; max-width: 100%;",
                "rationale": "Bounding box right edge exceeds viewport width of 375px",
                "status": "detected"
            }
        }
    }

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v: Any) -> float:
        try:
            if isinstance(v, str):
                v_clean = v.strip().rstrip("%")
                f = float(v_clean)
            else:
                f = float(v)
            if f > 1.0:
                f = f / 100.0
            return max(0.0, min(1.0, f))
        except (ValueError, TypeError):
            return 0.8

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            s = v.strip().lower().replace("-", "_")
            try:
                return DefectCategory(s)
            except ValueError:
                return DefectCategory.ELEMENT_OVERLAP
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> Any:
        if isinstance(v, str):
            s = v.strip().lower()
            try:
                return Severity(s)
            except ValueError:
                return Severity.MEDIUM
        return v



class PatchObject(BaseModel):
    """Constrained code/CSS patch suggestion."""
    target_file: str = Field(..., description="Allowlisted relative file path")
    diff: str = Field(..., description="Unified git diff or targeted CSS changes")
    explanation: Optional[str] = Field(default=None, description="Rationale for the patch")
    validation_status: Optional[bool] = Field(default=None, description="Whether patch passed security checks")
    validator_errors: Optional[str] = Field(default=None, description="Error reason if patch was rejected")

    @field_validator("target_file", mode="before")
    @classmethod
    def normalize_target_file(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().replace("\\", "/")
        return str(v)



class PatchSubmitPayload(BaseModel):
    """Payload to submit, validate, and optionally PR a proposed patch."""
    target_file: str = Field(..., description="Relative file path of patch target")
    diff: str = Field(..., description="Unified diff of the patch")
    file_content: str = Field(..., description="Full modified file content to commit")
    pr_title: str = Field(default="OmniSight Automated Visual Defect Fix", description="PR title")
    pr_body: str = Field(default="", description="Detailed PR description with evidence")
    labels: List[str] = Field(default_factory=lambda: ["omnisight", "automated-fix"], description="GitHub labels to attach to created PR")


class GitHubPullRequestInfo(BaseModel):
    """Details of the PR associated with a GitHub webhook event."""
    html_url: str = Field(..., description="Web URL of the pull request")
    number: int = Field(..., description="GitHub pull request number")
    state: str = Field(default="open", description="State: open or closed")
    merged: bool = Field(default=False, description="True if the PR was merged")
    merged_at: Optional[str] = Field(default=None, description="ISO timestamp of merge")
    title: Optional[str] = Field(default=None, description="PR title")
    head_ref: Optional[str] = Field(default=None, description="Source branch name")


class GitHubWebhookPayload(BaseModel):
    """Webhook payload sent by GitHub for pull_request and review events."""
    action: str = Field(..., description="Action event (e.g. opened, closed, reopened, review_submitted)")
    number: Optional[int] = Field(default=None, description="PR number")
    pull_request: Optional[GitHubPullRequestInfo] = Field(default=None, description="PR metadata if pull_request event")
    repository: Optional[Dict[str, Any]] = Field(default=None, description="Repository metadata")
    sender: Optional[Dict[str, Any]] = Field(default=None, description="Sender metadata")



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


class RunMetricsSummaryResponse(BaseModel):
    """Aggregate audit and PR metrics for the QA dashboard."""
    total_runs: int = Field(..., description="Total runs recorded")
    active_runs: int = Field(..., description="Currently queued or running audits")
    fixed_runs: int = Field(..., description="Runs successfully fixed or verified")
    prs_opened: int = Field(..., description="Total Pull Requests created")
    total_defects_detected: int = Field(..., description="Total visual anomalies detected")
    clean_run_rate_percent: float = Field(..., description="Percentage of runs clean or resolved")
    defects_by_category: Dict[str, int] = Field(default_factory=dict, description="Count per defect category")
    runs_by_status: Dict[str, int] = Field(default_factory=dict, description="Count per run lifecycle status")