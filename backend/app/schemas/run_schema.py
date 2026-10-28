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
    fingerprint: Optional[str] = Field(default=None, description="Deterministic SHA-256 visual defect fingerprint")

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



class RetestResultPayload(BaseModel):
    """Payload reporting verification retest results from sandbox execution."""
    passed: bool = Field(..., description="True if visual retest verified defect was cleared")
    visual_diff_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Visual difference ratio (0.0 = identical)")
    retest_viewport: Optional[str] = Field(default=None, description="Viewport used during sandbox verification")
    retest_screenshots: Dict[str, str] = Field(default_factory=dict, description="Artifact paths for retest screenshots")
    notes: Optional[str] = Field(default=None, description="Optional diagnostic notes or execution details")


class FindingStatusUpdatePayload(BaseModel):
    """Payload for updating the remediation status of a specific finding."""
    status: str = Field(..., description="Target status: detected, fixed, verified, or needs_review")
    suggested_change: Optional[str] = Field(default=None, description="Updated suggested correction if refined")
    notes: Optional[str] = Field(default=None, description="Resolution rationale or explanation")


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
    tags: List[str] = Field(default_factory=list, description="Metadata tags")
    error: Optional[str] = None

    @field_validator("evidence_paths", mode="before")
    @classmethod
    def normalize_evidence_paths(cls, v: Any) -> Any:
        if isinstance(v, dict):
            res = dict(v)
            if "screenshots" in res and "before_screenshots" not in res:
                res["before_screenshots"] = res["screenshots"]
            elif "before_screenshots" in res and "screenshots" not in res:
                res["screenshots"] = res["before_screenshots"]
            return res
        return v


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
    tags: List[str] = Field(default_factory=list, description="Metadata tags")
    pr_url: Optional[str] = None
    error: Optional[str] = None

    @field_validator("evidence_paths", mode="before")
    @classmethod
    def normalize_evidence_paths(cls, v: Any) -> Any:
        if isinstance(v, dict):
            res = dict(v)
            if "screenshots" in res and "before_screenshots" not in res:
                res["before_screenshots"] = res["screenshots"]
            elif "before_screenshots" in res and "screenshots" not in res:
                res["screenshots"] = res["before_screenshots"]
            return res
        return v


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
    mean_time_to_remediation_seconds: Optional[float] = Field(default=None, description="Average seconds from audit trigger to verified fix")
    resolved_runs_count: int = Field(default=0, description="Total verified fixed runs contributing to MTTR")


class TimelineEvent(BaseModel):
    """Chronological event log item tracking run progression."""
    event_id: str = Field(..., description="Unique event identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    event_type: str = Field(..., description="Classification (e.g. webhook_received, vlm_parsed, patch_validated, retest_verified, pr_opened)")
    description: str = Field(..., description="Human-readable event summary")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual payload or metrics")


class RetestResultResponse(BaseModel):
    """Response confirming ingestion of sandbox verification retest."""
    run_id: str
    status: RunStatus
    passed: bool
    message: str
    visual_diff_score: Optional[float] = None


class ForensicBundleResponse(BaseModel):
    """Complete forensic bundle for audit archiving and compliance review."""
    run_id: str
    generated_at: str
    summary: RunSummaryResponse
    detail: RunDetailResponse
    timeline: List[TimelineEvent] = Field(default_factory=list)
    retest_outcome: Optional[Dict[str, Any]] = None
    bundle_sha256: Optional[str] = Field(default=None, description="SHA-256 cryptographic digest of bundle payload")


class RunStatusResponse(BaseModel):
    """Lightweight status response for rapid polling during browser execution."""
    run_id: str
    status: RunStatus
    issue_count: int
    retry_count: int
    has_pr: bool
    pr_url: Optional[str] = None
    error: Optional[str] = None


class RetryRunPayload(BaseModel):
    """Request payload to initiate or record a retry iteration."""
    reason: Optional[str] = Field(default=None, description="Reason for triggering the retry iteration")
    max_retries: int = Field(default=2, ge=1, le=5, description="Upper bound on allowed retries")


class RetryRunResponse(BaseModel):
    """Response confirming retry registration."""
    run_id: str
    status: RunStatus
    retry_count: int
    retry_allowed: bool
    message: str


class DeleteRunResponse(BaseModel):
    """Response confirming deletion of a run."""
    run_id: str
    message: str
    deleted: bool


class LivenessProbeResponse(BaseModel):
    """Response returned by /live liveness probe."""
    status: str
    uptime_seconds: float
    timestamp: str


class ReadinessProbeResponse(BaseModel):
    """Response returned by /ready readiness probe."""
    status: str
    database: str
    active_runs: int
    timestamp: str


class RunFilterParams(BaseModel):
    """Granular query filters for audit runs."""
    status_filter: Optional[str] = None
    branch: Optional[str] = None
    scenario: Optional[str] = None
    target: Optional[str] = None
    has_pr: Optional[bool] = None
    has_issues: Optional[bool] = None
    min_severity: Optional[str] = None
    start_after: Optional[str] = None
    start_before: Optional[str] = None


class PatchRevertResponse(BaseModel):
    """Response payload confirming rollback of an unmerged or rejected patch."""
    run_id: str
    reverted: bool
    revert_branch: Optional[str] = None
    message: str
    timestamp: str



class DefectFingerprint(BaseModel):
    """Deterministic visual defect fingerprint and normalized signature."""
    fingerprint: str = Field(..., description="Deterministic SHA-256 hash identifying the defect pattern")
    category: DefectCategory = Field(..., description="Visual defect category")
    target_element: Optional[str] = Field(default=None, description="Normalized CSS selector or element path")
    viewport: str = Field(..., description="Viewport where defect was identified")
    suggested_property: Optional[str] = Field(default=None, description="Primary CSS property involved")


class DefectCluster(BaseModel):
    """Cluster of identical visual defects grouped across runs or viewports."""
    fingerprint: str = Field(..., description="Unique fingerprint key of the cluster")
    category: DefectCategory = Field(..., description="Visual defect category")
    target_element: Optional[str] = Field(default=None, description="Target CSS selector")
    occurrences: int = Field(default=1, description="Count of occurrences across runs")
    run_ids: List[str] = Field(default_factory=list, description="IDs of runs exhibiting this defect")
    viewports: List[str] = Field(default_factory=list, description="Affected viewports")
    severities: List[Severity] = Field(default_factory=list, description="Associated severity ratings")
    first_seen: str = Field(..., description="ISO timestamp when first detected")
    last_seen: str = Field(..., description="ISO timestamp when most recently detected")


class DefectClusterResponse(BaseModel):
    """Response containing aggregated defect clusters."""
    total_clusters: int = Field(..., description="Total unique defect clusters identified")
    clusters: List[DefectCluster] = Field(default_factory=list, description="Aggregated defect clusters")


class DefectStabilityRecord(BaseModel):
    """Historical stability and flakiness tracking record for a visual defect."""
    fingerprint: str = Field(..., description="Unique defect fingerprint")
    target_element: Optional[str] = Field(default=None, description="Normalized element selector")
    category: DefectCategory = Field(..., description="Visual defect category")
    total_observations: int = Field(default=1, description="Total audit runs inspecting target journey")
    defect_occurrences: int = Field(default=1, description="Number of times defect was visually detected")
    flakiness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Computed flakiness ratio (0.0=stable, 1.0=fully erratic)")
    is_quarantined: bool = Field(default=False, description="Whether this defect is currently quarantined from gating")
    quarantined_at: Optional[str] = Field(default=None, description="ISO timestamp when quarantine was applied")
    quarantine_reason: Optional[str] = Field(default=None, description="Justification for quarantine")


class QuarantineRequest(BaseModel):
    """Payload to place a defect into quarantine or update quarantine reason."""
    reason: str = Field(..., description="Justification for quarantining this visual defect (e.g. animation timing)")
    quarantined_by: Optional[str] = Field(default="system", description="User or automated agent requesting quarantine")


class QuarantineResponse(BaseModel):
    """Confirmation response for defect quarantine state change."""
    fingerprint: str = Field(..., description="Defect fingerprint")
    is_quarantined: bool = Field(..., description="Updated quarantine status")
    message: str = Field(..., description="Status explanation")
    quarantined_at: Optional[str] = None


class FlakinessReportResponse(BaseModel):
    """System-wide summary of defect stability, flakiness scores, and quarantined defects."""
    total_tracked_defects: int
    quarantined_count: int
    high_flakiness_count: int
    defects: List[DefectStabilityRecord] = Field(default_factory=list)


class PolicyGateLevel(str, Enum):
    """Automated release gate decision level for self-healing fixes."""
    AUTO_MERGE = "auto_merge"
    HUMAN_REVIEW = "human_review"
    REJECTED = "rejected"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            clean = value.strip().lower().replace("-", "_")
            for member in cls:
                if member.value == clean:
                    return member
        return cls.HUMAN_REVIEW


class PolicyRuleResult(BaseModel):
    """Result of an individual policy evaluation rule."""
    rule_name: str = Field(..., description="Name of the evaluated policy rule")
    passed: bool = Field(..., description="Whether the check satisfied policy criteria")
    severity: str = Field(default="info", description="Severity level if check fails (blocking, warning, info)")
    message: str = Field(..., description="Detailed evaluation justification")


class PolicyEvaluationRequest(BaseModel):
    """Input parameters to evaluate self-healing release gate policy."""
    run_id: str = Field(..., description="Audit run identifier")
    target_file: Optional[str] = Field(default=None, description="Path of target modified file")
    diff_content: Optional[str] = Field(default=None, description="Unified diff content of suggested patch")
    visual_diff_score: Optional[float] = Field(default=None, description="Retest visual difference metric")
    defect_severities: List[str] = Field(default_factory=list, description="Severities of addressed defects")
    defect_fingerprints: List[str] = Field(default_factory=list, description="Fingerprints of addressed defects")
    author: Optional[str] = Field(default="omnisight-agent", description="Author initiating the patch")


class PolicyEvaluationResponse(BaseModel):
    """Outcome of self-healing auto-merge policy gating evaluation."""
    run_id: str = Field(..., description="Audit run identifier")
    gate_level: PolicyGateLevel = Field(..., description="Gate decision (auto_merge, human_review, rejected)")
    auto_merge_allowed: bool = Field(..., description="True if patch can be merged autonomously")
    overall_risk_score: float = Field(..., description="Aggregate risk score between 0.0 and 100.0")
    passed_rules: List[str] = Field(default_factory=list, description="List of passing rule names")
    blocking_reasons: List[str] = Field(default_factory=list, description="Reasons preventing auto-merge or approval")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking advisories")
    rule_evaluations: List[PolicyRuleResult] = Field(default_factory=list, description="Detailed rule breakdown")
    timestamp: str = Field(..., description="Evaluation ISO 8601 UTC timestamp")


class BatchRunTriggerPayload(BaseModel):
    """Payload to initiate a matrix batch of visual audit runs."""
    target_url: str = Field(..., description="Target staging or local URL to audit")
    scenarios: List[str] = Field(default_factory=lambda: ["checkout_flow"], description="Journey scenarios")
    viewports: List[str] = Field(
        default_factory=lambda: ["desktop_1440x900", "mobile_375x667"],
        description="Target viewports across matrix"
    )
    branch: str = Field(default="main", description="Git branch under test")
    batch_label: Optional[str] = Field(default=None, description="Descriptive batch identifier (e.g. nightly-regression)")


class BatchRunSummaryResponse(BaseModel):
    """Aggregated execution status of a matrix batch of audit runs."""
    batch_id: str = Field(..., description="Unique batch identifier")
    total_runs: int = Field(..., description="Total runs spawned in this batch")
    completed_runs: int = Field(..., description="Count of successfully resolved or audited runs")
    failed_runs: int = Field(..., description="Count of runs in failed state")
    active_runs: int = Field(..., description="Count of currently pending/verifying runs")
    run_ids: List[str] = Field(default_factory=list, description="IDs of runs belonging to this batch")
    overall_status: str = Field(..., description="Aggregate status (queued, running, completed, partially_failed)")
    created_at: str = Field(..., description="Batch creation ISO timestamp")


class BatchRetryPayload(BaseModel):
    """Payload to trigger bulk retries across runs in a batch."""
    only_failed_or_needs_review: bool = Field(default=True, description="Only retry runs needing repair")
    max_retries_per_run: int = Field(default=2, ge=1, le=5, description="Per-run maximum retry ceiling")


class BatchRetryResponse(BaseModel):
    """Confirmation response for bulk batch retries."""
    batch_id: str = Field(..., description="Target batch identifier")
    retried_runs_count: int = Field(..., description="Number of runs rescheduled for retry")
    retried_run_ids: List[str] = Field(default_factory=list, description="IDs of retried runs")
    skipped_run_ids: List[str] = Field(default_factory=list, description="IDs of skipped runs")
    message: str = Field(..., description="Summary status message")


class RunTagPayload(BaseModel):
    """Payload to assign or synchronize metadata tags on an audit run."""
    tags: List[str] = Field(..., description="List of alphanumeric tag strings (e.g. nightly, smoke, p0)")


class RunTagResponse(BaseModel):
    """Confirmation response of updated run metadata tags."""
    run_id: str = Field(..., description="Audit run identifier")
    tags: List[str] = Field(default_factory=list, description="Current assigned metadata tags")
    message: str = Field(..., description="Status message")
