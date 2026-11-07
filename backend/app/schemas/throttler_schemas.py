from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class PriorityLevel(str, Enum):
    P0_CRITICAL = 'P0'
    P1_STANDARD = 'P1'
    P2_BACKGROUND = 'P2'

class ThrottleRequest(BaseModel):
    worker_id: str = Field(..., description='Unique identifier of the requesting worker')
    operation: str = Field(..., description='Operation type (e.g. dom_repair, visual_audit, token_calc)')
    requested_tokens: int = Field(default=1, ge=1, le=100, description='Number of execution tokens requested')
    priority: PriorityLevel = Field(default=PriorityLevel.P1_STANDARD, description='Request priority tier')
    current_latency_ms: float = Field(default=0.0, ge=0.0, description='Observed downstream worker latency')

class ThrottleEvaluation(BaseModel):
    allowed: bool = Field(..., description='Whether the request is permitted to proceed')
    wait_ms: int = Field(default=0, description='Suggested backoff wait time in milliseconds')
    backpressure_ratio: float = Field(..., description='Current backpressure severity ratio between 0.0 and 1.0')
    bucket_level: float = Field(..., description='Current available token balance in the bucket')
    reason: str = Field(default='OK', description='Explanation of the throttling decision')

class ThrottleStats(BaseModel):
    total_requests: int
    allowed_requests: int
    throttled_requests: int
    current_tokens: float
    active_workers: int
    backpressure_active: bool
