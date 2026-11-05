"""
Pydantic v2 schemas for circuit breaker resilience and inference fallback handling.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = Field(default=3, description="Consecutive failures to trip circuit")
    recovery_timeout_seconds: float = Field(default=30.0, description="Cool-down duration before half-open probe")
    success_threshold: int = Field(default=2, description="Consecutive successes in half-open state to close circuit")
    heuristic_fallback_enabled: bool = Field(default=True, description="Enable local contour heuristic fallback")

class CircuitBreakerStatus(BaseModel):
    service_name: str = "vlm_inference_gateway"
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_state_change: str
    fallback_executions_total: int = 0
    circuit_tripped_total: int = 0

class FallbackInferenceRequest(BaseModel):
    run_id: str
    viewport: str = "desktop_1920x1080"
    crop_coordinates: Dict[str, int]
    error_context: str = "upstream_vlm_timeout_429"

class FallbackInferenceResponse(BaseModel):
    run_id: str
    used_fallback: bool = True
    strategy: str = "heuristic_structural_contour_diff"
    estimated_confidence: float = 0.85
    suggested_patch_selector: str
    suggested_css: str
    generated_at: str
