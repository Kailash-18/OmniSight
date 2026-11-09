import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_dr_endpoints():
    res = client.post('/dr/hydrate', json={'snapshot_id': 'snap-api-01', 'verify_checksum': True})
    assert res.status_code == 200
    assert res.json()['success'] is True
    
    status = client.get('/dr/status')
    assert status.status_code == 200
    assert status.json()['healthy'] is True

def test_api_tenant_endpoints():
    res = client.post('/tenants/session', json={'tenant_id': 'org-gamma', 'max_parallel_runs': 4})
    assert res.status_code == 200
    token = res.json()['session_token']
    
    val = client.post(f'/tenants/validate?tenant_id=org-gamma&session_token={token}')
    assert val.status_code == 200
    assert val.json()['valid'] is True

def test_api_readiness_endpoints():
    chk = client.get('/release/readiness')
    assert chk.status_code == 200
    assert chk.json()['sign_off_status'] == 'APPROVED'
    
    sign = client.post('/release/sign-off', json={'engineer_id': 'lead_srikhyathi', 'sign_off_notes': 'Month 1 Certified', 'approved': True})
    assert sign.status_code == 200
    assert sign.json()['status'] == 'RELEASE_CERTIFIED'
