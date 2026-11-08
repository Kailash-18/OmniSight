import pytest
from backend.app.schemas.quarantine_schemas import QuarantineRequest
from backend.app.services.quarantine_service import ClusterQuarantineService

@pytest.fixture
def quarantine():
    svc = ClusterQuarantineService()
    svc.clear()
    return svc

def test_isolate_and_status(quarantine):
    req = QuarantineRequest(node_id='node-worker-3', reason='Frequent memory leak', consecutive_failures=4)
    rec = quarantine.isolate_node(req)
    assert rec.node_id == 'node-worker-3'
    assert rec.quarantine_status == 'ISOLATED'
    status = quarantine.get_cluster_status()
    assert status.quarantined_nodes == 1
    assert quarantine.is_isolated('node-worker-3') is True

def test_probation_and_release(quarantine):
    req = QuarantineRequest(node_id='node-worker-4', reason='GPU driver crash')
    quarantine.isolate_node(req)
    prob = quarantine.probe_node('node-worker-4')
    assert prob.quarantine_status == 'PROBATION'
    rel = quarantine.release_node('node-worker-4')
    assert rel.quarantine_status == 'RELEASED'
    assert quarantine.is_isolated('node-worker-4') is False
