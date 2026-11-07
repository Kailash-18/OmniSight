from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_throttler_evaluate():
    res = client.post('/api/v1/throttler/evaluate', json={
        'worker_id': 'w-api-01',
        'operation': 'dom_repair',
        'requested_tokens': 1,
        'priority': 'P1',
        'current_latency_ms': 50.0
    })
    assert res.status_code == 200
    data = res.json()
    assert 'allowed' in data
    assert 'bucket_level' in data

def test_api_snapshots_lifecycle():
    create_res = client.post('/api/v1/snapshots/create', json={
        'run_id': 'api-run-snap',
        'state_type': 'test_state',
        'payload': {'key': 'val1'}
    })
    assert create_res.status_code == 200
    snap_id = create_res.json()['snapshot_id']

    get_res = client.get(f'/api/v1/snapshots/{snap_id}')
    assert get_res.status_code == 200
    assert get_res.json()['payload_hash'] == create_res.json()['payload_hash']

    restore_res = client.post(f'/api/v1/snapshots/{snap_id}/restore')
    assert restore_res.status_code == 200
    assert restore_res.json()['restored'] is True

def test_api_health_pulse():
    res = client.get('/api/v1/health/pulse')
    assert res.status_code == 200
    data = res.json()
    assert data['healthy'] is True
    assert 'subsystems' in data
