import pytest
from backend.app.schemas.throttler_schemas import ThrottleRequest, PriorityLevel
from backend.app.schemas.snapshot_schemas import SnapshotCreateRequest
from backend.app.schemas.concurrency_schema import AcquireLeaseRequest
from backend.app.services.adaptive_throttler_service import adaptive_throttler
from backend.app.services.snapshot_service import snapshot_engine
from backend.app.services.concurrency_service import concurrency_manager
from backend.app.services.health_telemetry_service import health_pulse_hub

def test_e2e_week4_day5_flow():
    run_id = 'e2e-w4d5-run-001'

    # 1. Throttler evaluation
    t_req = ThrottleRequest(worker_id='w-e2e', operation='dom_repair', requested_tokens=2, priority=PriorityLevel.P0_CRITICAL)
    t_res = adaptive_throttler.evaluate(t_req)
    assert t_res.allowed is True

    # 2. Acquire Concurrency Lease
    lease_req = AcquireLeaseRequest(run_id=run_id, target_selector='#banner-hero', ttl_seconds=30)
    lease_res = concurrency_manager.acquire_lease(lease_req)
    assert lease_res.success is True

    # 3. Create baseline snapshot
    snap1 = snapshot_engine.create_snapshot(SnapshotCreateRequest(
        run_id=run_id,
        state_type='dom',
        payload={'dom_version': 1, 'color': 'red', 'width': 100}
    ))
    assert snap1.snapshot_id is not None

    # 4. Mutation & second snapshot
    snap2 = snapshot_engine.create_snapshot(SnapshotCreateRequest(
        run_id=run_id,
        state_type='dom',
        payload={'dom_version': 2, 'color': 'blue', 'width': 120, 'new_attr': 'active'}
    ))

    # 5. Compute Delta
    delta = snapshot_engine.compute_delta(snap1.snapshot_id, snap2.snapshot_id)
    assert delta.has_changes is True
    assert 'new_attr' in delta.added_keys
    assert 'color' in delta.modified_keys

    # 6. Verify System Health Pulse
    pulse = health_pulse_hub.generate_pulse()
    assert pulse.healthy is True
    assert pulse.active_leases >= 1

    # 7. Point-in-time state restore
    restore = snapshot_engine.restore_snapshot(snap1.snapshot_id)
    assert restore.restored is True
    assert restore.run_id == run_id

    # Cleanup lease
    concurrency_manager.release_lease(lease_res.lease.lease_id, run_id)
