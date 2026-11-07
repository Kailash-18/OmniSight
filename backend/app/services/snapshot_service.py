import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from backend.app.schemas.snapshot_schemas import (
    SnapshotCreateRequest, SnapshotManifest, SnapshotDelta, SnapshotRestoreResult
)

class SnapshotService:
    def __init__(self):
        self._snapshots: Dict[str, SnapshotManifest] = {}
        self._run_index: Dict[str, List[str]] = {}

    def _compute_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def create_snapshot(self, req: SnapshotCreateRequest) -> SnapshotManifest:
        snapshot_id = f'snap-{uuid.uuid4().hex[:12]}'
        payload_hash = self._compute_hash(req.payload)
        manifest = SnapshotManifest(
            snapshot_id=snapshot_id,
            run_id=req.run_id,
            state_type=req.state_type,
            payload_hash=payload_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=req.payload,
            metadata=req.metadata or {}
        )
        self._snapshots[snapshot_id] = manifest
        self._run_index.setdefault(req.run_id, []).append(snapshot_id)
        return manifest

    def get_snapshot(self, snapshot_id: str) -> Optional[SnapshotManifest]:
        return self._snapshots.get(snapshot_id)

    def list_run_snapshots(self, run_id: str) -> List[SnapshotManifest]:
        ids = self._run_index.get(run_id, [])
        return [self._snapshots[sid] for sid in ids if sid in self._snapshots]

    def verify_snapshot_integrity(self, snapshot_id: str) -> bool:
        snap = self.get_snapshot(snapshot_id)
        if not snap:
            return False
        return snap.payload_hash == self._compute_hash(snap.payload)

snapshot_engine = SnapshotService()
