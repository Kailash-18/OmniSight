"""
OmniSight Self-Healing Orchestration & Dynamic PR Labeling Schemas.
Defines data models for automated healing strategies, rollback decisions, and GitHub labels.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class HealingStrategyType(str, Enum):
    """Supported automated self-healing strategy decisions."""
    IMMEDIATE_PATCH = "immediate_patch"
    ITERATIVE_REFINEMENT = "iterative_refinement"
    ROLLBACK_REQUIRED = "rollback_required"
    HUMAN_ESCALATION = "human_escalation"


class HealingStrategyRequest(BaseModel):
    """Payload to request an automated healing strategy recommendation."""
    run_id: str = Field(..., description="Unique audit run identifier", min_length=3)
    visual_diff_score: float = Field(..., description="Current visual diff mismatch ratio (0.00 to 1.00)", ge=0.0, le=1.0)
    iteration_count: int = Field(default=1, description="Current iteration number", ge=1)
    max_retries: int = Field(default=2, description="Upper bound on allowable autonomous retries", ge=1, le=5)

class HealingStrategyResponse(BaseModel):
    """Strategy recommendation evaluated for a visual healing cycle."""
    run_id: str = Field(..., description="Audit run identifier")
    strategy: HealingStrategyType = Field(..., description="Recommended self-healing strategy")
    action_rationale: str = Field(..., description="Reasoning and evaluation justification", min_length=10)
    recommended_action: str = Field(..., description="Specific next step for orchestrator loop")
    rollback_recommended: bool = Field(default=False, description="Whether immediate patch rollback is advised")
    can_auto_merge: bool = Field(default=False, description="Whether the run qualifies for automated merging")


class HealingSummaryResponse(BaseModel):
    """High-level summary of an audit run's complete self-healing cycle."""
    run_id: str = Field(..., description="Unique audit run identifier")
    total_iterations: int = Field(..., description="Number of healing cycles executed", ge=1)
    initial_diff_score: float = Field(..., description="Initial visual diff mismatch ratio", ge=0.0, le=1.0)
    final_diff_score: float = Field(..., description="Final visual diff mismatch ratio achieved", ge=0.0, le=1.0)
    resolution_status: str = Field(..., description="Final resolution outcome (e.g. fixed, escalated, rolled_back)")
    duration_seconds: float = Field(..., description="Total elapsed remediation time in seconds", ge=0.0)
    pr_url: Optional[str] = Field(default=None, description="Associated GitHub Pull Request URL if opened")

class PRLabelCalculationRequest(BaseModel):
    """Payload to compute dynamic GitHub PR labels for visual defects."""
    finding_count: int = Field(default=1, description="Total number of detected visual findings", ge=0)
    max_severity: str = Field(default="medium", description="Highest severity among detected defects")
    viewport_name: str = Field(default="desktop", description="Target viewport device profile")
    is_verified: bool = Field(default=True, description="Whether patch has passed sandbox visual retest")
    defect_categories: List[str] = Field(default_factory=list, description="Unique categories of detected defects")


class PRLabelCalculationResponse(BaseModel):
    """Computed GitHub label metadata for automated PR triage."""
    labels: List[str] = Field(..., description="List of sanitized GitHub label names")
    color_map: Dict[str, str] = Field(default_factory=dict, description="Hex color mapping per label")
    priority_level: str = Field(..., description="Computed triage priority (P0, P1, P2, P3)")

class RollbackPreviewRequest(BaseModel):
    """Request payload to simulate a patch rollback for a failed healing run."""
    run_id: str = Field(..., description="Unique audit run identifier", min_length=3)
    target_file: str = Field(..., description="Relative path of file to restore")
    reason: str = Field(default="visual_regression_detected", description="Operator or automated rationale for rollback")

    @field_validator("target_file")
    @classmethod
    def validate_target_file(cls, v: str) -> str:
        clean = v.strip().replace("\\", "/")
        if ".." in clean or clean.startswith("/"):
            raise ValueError("Target file path must be a clean relative path without traversal")
        return clean


class RollbackPreviewResponse(BaseModel):
    """Simulation preview of a file rollback operation."""
    run_id: str = Field(..., description="Unique audit run identifier")
    target_file: str = Field(..., description="File selected for rollback")
    is_restorable: bool = Field(..., description="Whether clean pristine state can be restored")
    restored_status: str = Field(default="rolled_back", description="Target state after rollback")
    audit_event_logged: bool = Field(default=True, description="Confirmation that rollback was recorded in timeline")
