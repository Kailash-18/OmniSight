import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_health_full_audit(client):
    res = client.get('/health/full-audit')
    assert res.status_code == 200
    data = res.json()
    assert data['overall_status'] in ['HEALTHY', 'DEGRADED']
    assert data['components_checked'] == 5
    assert len(data['audit_digest']) == 64

def test_api_release_final_certificate_and_verify(client):
    res = client.get('/release/final-certificate')
    assert res.status_code == 200
    cert = res.json()
    assert cert['release_version'] == '1.0.0-final'
    assert cert['certified_by'] == 'Sri Khyathi'
    assert len(cert['compliance_seal']) == 64

    # Verify certificate
    v_res = client.post('/release/verify-certificate', json={
        'certificate_id': cert['release_version'],
        'compliance_seal': cert['compliance_seal']
    })
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data['valid'] is True
