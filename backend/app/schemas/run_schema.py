"""
Pydantic Schemas and Enums for OmniSight Backend API.
Enforces data integrity, validation rules, and schema compatibility with Automation & Dashboard.
"""

from enum import Enum
from typing import Any

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
    commit_sha: str | None = Field(default=None, description="Git commit hash")
    event_id: str | None = Field(default=None, description="External CI event identifier")


class RunTriggerPayload(BaseModel):
    """Manual trigger payload for on-demand browser audit."""
    target_url: str = Field(..., description="Local or staging app URL to audit")
    scenario: str = Field(default="checkout_flow", description="Journey scenario")
    viewports: list[str] = Field(
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
    target_element: str | None = Field(default=None, description="CSS selector or test ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")
    suggested_change: str = Field(..., description="Proposed CSS/layout rule correction")
    rationale: str = Field(..., description="Visual reasoning justification")
    status: str = Field(default="detected", description="Current remediation status")

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

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "defect-checkout-clipped",
                "category": "element_clipping",
                "severity": "high",
                "description": "Place Order CTA clipped on mobile 375x667 viewport",
                "viewport": "mobile_375x667",
                "target_element": "[data-testid='btn-place-order']",
                "confidence": 0.94,
                "suggested_change": "width: 100%; box-sizing: border-box;",
                "rationale": "Bounding box extends past viewport right boundary",
                "status": "detected"
            }
        }
    }



class PatchObject(BaseModel):
    """Constrained code/CSS patch suggestion."""
    target_file: str = Field(..., description="Allowlisted relative file path")
    diff: str = Field(..., description="Unified git diff or targeted CSS changes")
    explanation: str | None = Field(default=None, description="Rationale for the patch")
    validation_status: bool | None = Field(default=None, description="Whether patch passed security checks")
    validator_errors: str | None = Field(default=None, description="Error reason if patch was rejected")

    @field_validator("target_file", mode="before")
    @classmethod
    def normalize_target_file(cls, v: Any) -> str:
        if isinstance(v, str):
            cleaned = v.strip().replace("\\", "/")
            cleaned = cleaned.removeprefix("./")
            if cleaned.startswith(("a/", "b/")):
                cleaned = cleaned[2:]
            return cleaned
        return str(v)



class PatchSubmitPayload(BaseModel):
    """Payload to submit, validate, and optionally PR a proposed patch."""
    target_file: str = Field(..., description="Relative file path of patch target")
    diff: str = Field(..., description="Unified diff of the patch")
    file_content: str = Field(..., description="Full modified file content to commit")
    pr_title: str = Field(default="OmniSight Automated Visual Defect Fix", description="PR title")
    pr_body: str = Field(default="", description="Detailed PR description with evidence")
    labels: list[str] | None = Field(default=None, description="Optional GitHub issue labels")
    auto_create_pr: bool = Field(default=False, description="Whether to automatically open PR if patch passes")

    @field_validator("target_file", mode="before")
    @classmethod
    def normalize_target_file(cls, v: Any) -> str:
        if isinstance(v, str):
            cleaned = v.strip().replace("\\", "/")
            cleaned = cleaned.removeprefix("./")
            if cleaned.startswith(("a/", "b/")):
                cleaned = cleaned[2:]
            return cleaned
        return str(v)


class VLMParseRequest(BaseModel):
    """Payload containing raw VLM natural language or JSON text for Action Engine parsing."""
    raw_vlm_output: str = Field(..., description="Raw text response returned by VLM")
    run_id: str | None = Field(default=None, description="Optional associated run ID")


class RunRecordUpdatePayload(BaseModel):
    """Payload for updating an existing run state and evidence."""
    status: RunStatus | None = None
    steps: list[str] | None = None
    evidence_paths: dict[str, Any] | None = None
    findings: list[FindingSchema] | None = None
    patch: PatchObject | None = None
    retry_count: int | None = None
    pr_url: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class VLMParseResponse(BaseModel):
    """Result of Action Engine extraction and validation."""
    is_valid: bool = Field(..., description="True if output parsed and structured successfully")
    findings: list[FindingSchema] = Field(default_factory=list, description="Extracted findings")
    summary: str | None = Field(default=None, description="Executive summary of visual audit")
    proposed_patch: PatchObject | None = Field(default=None, description="Extracted and checked patch")
    validation_status: bool = Field(default=False, description="True if patch passed security guardrails")
    validator_errors: str | None = Field(default=None, description="Validation failure details if any")
    parse_errors: list[str] = Field(default_factory=list, description="Parsing or validation warnings")


class RunSummaryResponse(BaseModel):
    """Concise run summary for dashboard list view."""
    run_id: str
    start_time: str
    target: str
    status: RunStatus
    issue_count: int
    pr_url: str | None = None


class RunDetailResponse(BaseModel):
    """Complete forensic run report for dashboard inspection."""
    run_id: str
    start_time: str
    target: str
    status: RunStatus
    steps: list[str] = Field(default_factory=list)
    evidence_paths: dict[str, Any] = Field(default_factory=dict)
    findings: list[FindingSchema] = Field(default_factory=list)
    patch: PatchObject | None = None
    retry_count: int = 0
    pr_url: str | None = None
    error: str | None = None


class CreatePRPayload(BaseModel):
    """Payload to trigger or re-run GitHub PR creation for a run with validated patch."""
    target_file: str | None = Field(default=None, description="Optional target file override")
    file_content: str | None = Field(default=None, description="Optional modified file content override")
    commit_message: str | None = Field(default=None, description="Custom Git commit message")
    pr_title: str | None = Field(default=None, description="Custom Pull Request title")
    pr_body: str | None = Field(default=None, description="Custom Markdown Pull Request description")
    labels: list[str] | None = Field(default=None, description="Optional issue/PR labels")


class CreatePRResponse(BaseModel):
    """Response returned upon PR creation or mock PR generation."""
    status: str = "success"
    run_id: str
    pr_url: str
    message: str = "Pull Request created successfully."