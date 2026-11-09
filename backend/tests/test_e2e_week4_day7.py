import pytest
from backend.app.schemas.dr_schemas import DRHydrateRequest
from backend.app.schemas.tenant_schemas import TenantCreateRequest
from backend.app.schemas.readiness_schemas import ReleaseSignOffRequest
from backend.app.services.dr_service import dr_service
from backend.app.services.tenant_service import tenant_service
from backend.app.services.readiness_service import readiness_service

def test_e2e_dr_tenant_readiness_lifecycle():
    dr_res = dr_service.hydrate_from_snapshot(DRHydrateRequest(snapshot_id='snap-final-audit'))
    assert dr_res.success is True
    
    tenant_res = tenant_service.create_tenant(TenantCreateRequest(tenant_id='acme-corp', max_parallel_runs=5))
    assert len(tenant_res.session_token) == 64
    assert tenant_service.acquire_run_slot('acme-corp') is True
    
    checklist = readiness_service.evaluate_readiness()
    assert checklist.sign_off_status == 'APPROVED'
    assert checklist.dr_hydration_verified is True
    
    sign_off = readiness_service.record_sign_off(ReleaseSignOffRequest(engineer_id='srikhyathi', sign_off_notes='All Month 1 targets met.'))
    assert sign_off.status == 'RELEASE_CERTIFIED'
