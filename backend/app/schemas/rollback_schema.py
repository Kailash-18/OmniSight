"""
Pydantic v2 schemas for atomic multi-file patch rollback manifests.
"""
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class RollbackStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

class RollbackPatchItem(BaseModel):
    target_file: str
    original_css: str
    patched_css: str
    reverse_diff: str
    sha256_checksum: str

class AtomicRollbackManifest(BaseModel):
    rollback_id: str
    run_id: str
    pr_number: Optional[int] = None
    target_files: List[str]
    items: List[RollbackPatchItem]
    rollback_token: str
    created_at: str
    status: RollbackStatus = RollbackStatus.PENDING

class RollbackExecutionRequest(BaseModel):
    rollback_id: str
    rollback_token: str
    trigger_reason: str = "visual_regression_detected"
    author: str = "srikhyathi"

class RollbackExecutionResponse(BaseModel):
    rollback_id: str
    success: bool
    reverted_files_count: int
    audit_log_digest: str
    executed_at: str
