"""
Pydantic v2 schemas for real-time SSE event streaming and live telemetry.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class RunEventType(str, Enum):
    RUN_STARTED = "RUN_STARTED"
    LEASE_ACQUIRED = "LEASE_ACQUIRED"
    INFERENCE_FALLBACK = "INFERENCE_FALLBACK"
    CANARY_VERIFIED = "CANARY_VERIFIED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"
    RUN_COMPLETED = "RUN_COMPLETED"

class StreamEvent(BaseModel):
    event_id: str
    run_id: str
    event_type: RunEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str

class PublishEventRequest(BaseModel):
    run_id: str
    event_type: RunEventType
    payload: Dict[str, Any] = Field(default_factory=dict)

class EventStreamHistoryResponse(BaseModel):
    total_events: int
    events: List[StreamEvent]
