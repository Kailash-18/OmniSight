"""
Pydantic v2 schemas for distributed run concurrency control and DOM mutation leases.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    CONFLICT = "CONFLICT"

class AcquireLeaseRequest(BaseModel):
    run_id: str
    target_selector: str
    url_path: str = "/"
    ttl_seconds: float = Field(default=60.0, ge=0.01, le=300.0)
    requester_id: str = "visual_healing_agent"

class LeaseRecord(BaseModel):
    lease_id: str
    run_id: str
    target_selector: str
    url_path: str
    status: LeaseStatus = LeaseStatus.ACTIVE
    acquired_at: str
    expires_at: str
    renewed_count: int = 0
    requester_id: str

class AcquireLeaseResponse(BaseModel):
    success: bool
    lease: Optional[LeaseRecord] = None
    rejection_reason: Optional[str] = None

class ReleaseLeaseRequest(BaseModel):
    lease_id: str
    run_id: str

class ReleaseLeaseResponse(BaseModel):
    lease_id: str
    released: bool
    message: str

class RenewLeaseRequest(BaseModel):
    extend_seconds: float = Field(default=30.0, ge=0.01, le=120.0)

class RenewLeaseResponse(BaseModel):
    lease_id: str
    renewed: bool
    new_expires_at: Optional[str] = None
    renewed_count: int = 0

class ActiveLeasesResponse(BaseModel):
    total_active: int
    leases: List[LeaseRecord]
