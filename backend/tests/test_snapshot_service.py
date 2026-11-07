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

def test_snapshot_delta_calculation():
    service = SnapshotService()
    snap_1 = service.create_snapshot(SnapshotCreateRequest(
        run_id='run-delta',
        state_type='dom',
        payload={'width': 100, 'height': 200, 'old_key': 'abc'}
    ))
    snap_2 = service.create_snapshot(SnapshotCreateRequest(
        run_id='run-delta',
        state_type='dom',
        payload={'width': 150, 'height': 200, 'new_key': 'xyz'}
    ))
    delta = service.compute_delta(snap_1.snapshot_id, snap_2.snapshot_id)
    assert delta.has_changes is True
    assert 'new_key' in delta.added_keys
    assert 'width' in delta.modified_keys
    assert 'old_key' in delta.removed_keys

def test_snapshot_point_in_time_restore():
    service = SnapshotService()
    snap = service.create_snapshot(SnapshotCreateRequest(
        run_id='run-restore',
        state_type='dom',
        payload={'status': 'stable', 'version': 1}
    ))
    result = service.restore_snapshot(snap.snapshot_id)
    assert result.restored is True
    assert result.run_id == 'run-restore'
    assert result.payload_hash == snap.payload_hash
