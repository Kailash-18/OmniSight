from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import time

class WorkerPoolMetrics(BaseModel):
    queue_depth: int
    active_workers: int
    p99_latency_ms: float
    cpu_utilization_pct: float
    timestamp: float = Field(default_factory=time.time)

class ScaleDecision(BaseModel):
    action: str  # 'SCALE_UP', 'SCALE_DOWN', 'MAINTAIN'
    previous_worker_count: int
    target_worker_count: int
    reason: str
    cooldown_remaining_sec: float = 0.0

class AutoscalePolicy(BaseModel):
    min_workers: int = 2
    max_workers: int = 16
    scale_up_queue_threshold: int = 10
    scale_down_queue_threshold: int = 2
    cooldown_period_sec: float = 15.0

class WorkerPoolStatus(BaseModel):
    current_workers: int
    min_workers: int
    max_workers: int
    last_scale_action: str
    last_scale_timestamp: float
