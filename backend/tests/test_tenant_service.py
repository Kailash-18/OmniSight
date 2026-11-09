import pytest
from backend.app.schemas.tenant_schemas import TenantCreateRequest
from backend.app.services.tenant_service import TenantIsolationService

def test_create_and_validate_tenant():
    svc = TenantIsolationService()
    req = TenantCreateRequest(tenant_id='org-alpha', max_parallel_runs=3, rate_limit_per_min=100)
    session = svc.create_tenant(req)
    assert session.tenant_id == 'org-alpha'
    assert len(session.session_token) == 64
    
    val = svc.validate_session('org-alpha', session.session_token)
    assert val.valid is True
    assert val.quota_remaining == 3

def test_tenant_slot_contention():
    svc = TenantIsolationService()
    req = TenantCreateRequest(tenant_id='org-beta', max_parallel_runs=2, rate_limit_per_min=50)
    svc.create_tenant(req)
    assert svc.acquire_run_slot('org-beta') is True
    assert svc.acquire_run_slot('org-beta') is True
    assert svc.acquire_run_slot('org-beta') is False  # exhausted quota
    
    svc.release_run_slot('org-beta')
    assert svc.acquire_run_slot('org-beta') is True

def test_invalid_session_token():
    svc = TenantIsolationService()
    val = svc.validate_session('nonexistent-org', 'bogus-token')
    assert val.valid is False
