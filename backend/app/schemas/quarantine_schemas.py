from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

class QuarantineRecord(BaseModel):
    node_id: str
    reason: str
    consecutive_failures: int
    isolated_at: float = Field(default_factory=time.time)
    quarantine_status: str = 'ISOLATED'  # 'ISOLATED', 'PROBATION', 'RELEASED'
    probe_attempts: int = 0

class QuarantineRequest(BaseModel):
    node_id: str
    reason: str
    consecutive_failures: int = 3

class QuarantineReleaseRequest(BaseModel):
    node_id: str
    force: bool = False

class QuarantineClusterStatus(BaseModel):
    total_nodes: int
    healthy_nodes: int
    quarantined_nodes: int
    records: List[QuarantineRecord]
