import pytest
from backend.app.schemas.snapshot_schemas import SnapshotCreateRequest
from backend.app.services.snapshot_service import SnapshotService

def test_create_and_retrieve_snapshot():
    service = SnapshotService()
    req = SnapshotCreateRequest(
        run_id='run-snap-01',
        state_type='dom_checkpoint',
        payload={'selector': '#btn-submit', 'classes': ['btn', 'btn-primary'], 'computed_width': 120}
    )
    manifest = service.create_snapshot(req)
    assert manifest.snapshot_id.startswith('snap-')
    assert len(manifest.payload_hash) == 64
    retrieved = service.get_snapshot(manifest.snapshot_id)
    assert retrieved is not None
    assert retrieved.payload_hash == manifest.payload_hash

def test_snapshot_integrity_verification():
    service = SnapshotService()
    req = SnapshotCreateRequest(
        run_id='run-snap-02',
        state_type='telemetry',
        payload={'fps': 60, 'drift_violations': 0}
    )
    manifest = service.create_snapshot(req)
    assert service.verify_snapshot_integrity(manifest.snapshot_id) is True
