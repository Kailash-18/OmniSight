from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SnapshotCreateRequest(BaseModel):
    run_id: str = Field(..., description='Visual repair run identifier')
    state_type: str = Field(..., description='Domain state type (e.g., dom_tree, telemetry, lease_checkpoint)')
    payload: Dict[str, Any] = Field(..., description='Raw state payload dictionary')
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description='Additional audit metadata')

class SnapshotManifest(BaseModel):
    snapshot_id: str = Field(..., description='Cryptographic unique snapshot ID')
    run_id: str
    state_type: str
    payload_hash: str = Field(..., description='Hex SHA256 digest of normalized payload')
    timestamp: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any]

class SnapshotDelta(BaseModel):
    base_snapshot_id: str
    target_snapshot_id: str
    has_changes: bool
    added_keys: List[str]
    modified_keys: List[str]
    removed_keys: List[str]
    delta_summary: Dict[str, Any]

class SnapshotRestoreResult(BaseModel):
    restored: bool
    snapshot_id: str
    run_id: str
    state_type: str
    payload_hash: str
    restored_at: str
