from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

class DisasterRecoveryState(BaseModel):
    cluster_id: str
    snapshot_id: str
    state_hash: str
    hydrated_at: float = Field(default_factory=time.time)
    rto_ms: float
    healthy: bool = True
    components_restored: List[str] = Field(default_factory=list)

class DRHydrateRequest(BaseModel):
    snapshot_id: str
    verify_checksum: bool = True
    force_hydration: bool = False

class DRHydrateResponse(BaseModel):
    success: bool
    snapshot_id: str
    rto_ms: float
    components_hydrated: List[str]
    message: str
