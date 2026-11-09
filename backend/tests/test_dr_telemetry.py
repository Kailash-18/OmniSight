import pytest
from backend.app.services.health_telemetry_service import HealthTelemetryService
from backend.app.services.dr_service import dr_service
from backend.app.services.tenant_service import tenant_service
from backend.app.schemas.dr_schemas import DRHydrateRequest
from backend.app.schemas.tenant_schemas import TenantCreateRequest

def test_dr_telemetry_metrics():
    dr_service.hydrate_from_snapshot(DRHydrateRequest(snapshot_id='snap-tel-01'))
    pulse = HealthTelemetryService()
    tel = pulse.get_dr_tenant_telemetry()
    assert 'dr' in tel
    assert tel['dr']['snapshot_id'] == 'snap-tel-01'
    assert tel['dr']['healthy'] is True

def test_tenant_saturation_gauge():
    tenant_service.create_tenant(TenantCreateRequest(tenant_id='tenant-org-1', max_parallel_runs=5))
    pulse = HealthTelemetryService()
    tel = pulse.get_dr_tenant_telemetry()
    assert tel['active_tenants'] >= 1
