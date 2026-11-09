import pytest
import time
from backend.app.schemas.dr_schemas import DRHydrateRequest
from backend.app.services.dr_service import DisasterRecoveryService

def test_benchmark_dr_rto_sub_second():
    service = DisasterRecoveryService()
    start = time.perf_counter()
    for i in range(50):
        res = service.hydrate_from_snapshot(DRHydrateRequest(snapshot_id=f'snap-{i}'))
        assert res.success is True
    elapsed = (time.perf_counter() - start) * 1000.0
    avg_rto = elapsed / 50.0
    assert avg_rto < 50.0

def test_benchmark_tenant_token_throughput():
    from backend.app.services.tenant_service import TenantIsolationService
    from backend.app.schemas.tenant_schemas import TenantCreateRequest
    svc = TenantIsolationService()
    start = time.perf_counter()
    for i in range(50):
        svc.create_tenant(TenantCreateRequest(tenant_id=f'tenant-{i}'))
    elapsed = (time.perf_counter() - start) * 1000.0
    assert elapsed < 100.0
