"""
Pydantic v2 schemas for visual invariant verification and layout drift detection.
"""
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class DriftSeverity(str, Enum):
    STABLE = "STABLE"
    MINOR_SHIFT = "MINOR_SHIFT"
    REGRESSION_VIOLATION = "REGRESSION_VIOLATION"

class NodeSpatialSnapshot(BaseModel):
    node_id: str
    selector: str
    x: int
    y: int
    width: int
    height: int

class SpatialDriftMetric(BaseModel):
    node_id: str
    selector: str
    dx: int
    dy: int
    d_width: int
    d_height: int
    euclidean_shift: float
    area_delta_pct: float
    is_invariant_preserved: bool
    severity: DriftSeverity

class VisualInvariantCheckRequest(BaseModel):
    run_id: str
    target_selector: str
    baseline_nodes: List[NodeSpatialSnapshot]
    patched_nodes: List[NodeSpatialSnapshot]
    max_allowed_shift_px: float = Field(default=2.0, description="Max allowed pixel drift for untouched nodes")
    max_allowed_area_change_pct: float = Field(default=5.0, description="Max allowed area variation %")

class VisualInvariantCheckResponse(BaseModel):
    run_id: str
    total_nodes_evaluated: int
    invariant_preserved: bool
    layout_stability_score: float
    violations_detected: int
    drift_details: List[SpatialDriftMetric]
    evaluated_at: str
