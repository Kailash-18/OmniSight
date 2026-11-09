import pytest
from backend.app.schemas.dr_schemas import DRHydrateRequest
from backend.app.services.dr_service import DisasterRecoveryService

def test_dr_hydration_success():
    service = DisasterRecoveryService()
    req = DRHydrateRequest(snapshot_id='snap-001', verify_checksum=True)
    res = service.hydrate_from_snapshot(req)
    assert res.success is True
    assert res.snapshot_id == 'snap-001'
    assert res.rto_ms >= 0.0
    assert 'dlq_engine' in res.components_hydrated

def test_dr_status_retrieval():
    service = DisasterRecoveryService()
    req = DRHydrateRequest(snapshot_id='snap-prod-101', verify_checksum=True)
    service.hydrate_from_snapshot(req)
    status = service.get_recovery_status()
    assert status.snapshot_id == 'snap-prod-101'
    assert status.healthy is True
    assert len(status.state_hash) == 64

def test_dr_failed_checksum():
    service = DisasterRecoveryService()
    req = DRHydrateRequest(snapshot_id='snap-corrupt', verify_checksum=True)
    res = service.hydrate_from_snapshot(req)
    assert res.snapshot_id == 'snap-corrupt'
