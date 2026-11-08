from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

class DLQMessage(BaseModel):
    message_id: str
    run_id: str
    payload: Dict[str, Any]
    error_reason: str
    retry_count: int = 0
    max_retries: int = 3
    poison_pill: bool = False
    enqueued_at: float = Field(default_factory=time.time)
    next_retry_at: float = 0.0
    resolved: bool = False

class DLQEnqueueRequest(BaseModel):
    run_id: str
    payload: Dict[str, Any]
    error_reason: str
    max_retries: int = 3

class DLQReplayRequest(BaseModel):
    message_id: Optional[str] = None
    run_id: Optional[str] = None
    force_poison_pill: bool = False

class DLQReplayResponse(BaseModel):
    replayed_count: int
    message_ids: List[str]
    success: bool

class DLQStats(BaseModel):
    total_enqueued: int
    pending_retries: int
    poison_pills: int
    resolved_count: int
