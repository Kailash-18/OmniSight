from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SubsystemStatus(BaseModel):
    name: str
    healthy: bool
    latency_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)

class HealthPulseReport(BaseModel):
    timestamp: str
    overall_health_score: float = Field(..., ge=0.0, le=100.0, description='Normalized system health index (0-100)')
    healthy: bool
    subsystems: List[SubsystemStatus]
    active_leases: int
    throttle_backpressure_ratio: float
    snapshot_count: int
