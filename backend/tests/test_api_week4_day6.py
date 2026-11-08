from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_dlq_lifecycle():
    res = client.post('/api/v1/dlq/enqueue', json={
        'run_id': 'run-api-601',
        'payload': {'key': 'val'},
        'error_reason': 'Test error',
        'max_retries': 3
    })
    assert res.status_code == 200
    assert res.json()['success'] is True

    # Stats
    stats = client.get('/api/v1/dlq/stats')
    assert stats.status_code == 200
    assert stats.json()['total_enqueued'] >= 1

def test_api_autoscale_lifecycle():
    res = client.post('/api/v1/autoscale/evaluate', json={
        'queue_depth': 1,
        'active_workers': 2,
        'p99_latency_ms': 40.0,
        'cpu_utilization_pct': 25.0
    })
    assert res.status_code == 200
    assert 'action' in res.json()

def test_api_quarantine_lifecycle():
    res = client.post('/api/v1/quarantine/isolate', json={
        'node_id': 'test-node-api-1',
        'reason': 'API test isolation',
        'consecutive_failures': 3
    })
    assert res.status_code == 200
    assert res.json()['success'] is True

    status = client.get('/api/v1/quarantine/status')
    assert status.status_code == 200
    assert status.json()['quarantined_nodes'] >= 1
