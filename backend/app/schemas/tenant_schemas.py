from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time

class TenantSession(BaseModel):
    tenant_id: str
    session_token: str
    max_parallel_runs: int = 5
    active_runs: int = 0
    rate_limit_per_min: int = 60
    created_at: float = Field(default_factory=time.time)

class TenantCreateRequest(BaseModel):
    tenant_id: str
    max_parallel_runs: int = 5
    rate_limit_per_min: int = 60

class TenantValidateResponse(BaseModel):
    valid: bool
    tenant_id: str
    quota_remaining: int
    message: str
