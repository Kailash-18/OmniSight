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
