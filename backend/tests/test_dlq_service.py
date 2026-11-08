import pytest
from backend.app.schemas.dlq_schemas import DLQEnqueueRequest
from backend.app.services.dlq_service import DeadLetterQueueService

@pytest.fixture
def dlq():
    svc = DeadLetterQueueService(base_backoff_sec=0.1, backoff_multiplier=2.0)
    svc.clear()
    return svc

def test_enqueue_and_stats(dlq):
    req = DLQEnqueueRequest(run_id='run-101', payload={'task': 'vlm_eval'}, error_reason='Timeout 5000ms')
    msg = dlq.enqueue(req)
    assert msg.message_id.startswith('dlq-')
    assert msg.retry_count == 0
    assert msg.poison_pill is False
    stats = dlq.get_stats()
    assert stats.total_enqueued == 1
    assert stats.pending_retries == 1

def test_retry_and_poison_pill_tagging(dlq):
    req = DLQEnqueueRequest(run_id='run-102', payload={'task': 'bad_dom'}, error_reason='DOM Crash', max_retries=2)
    msg = dlq.enqueue(req)
    # First failure
    res1 = dlq.record_failure(msg.message_id, 'Still failing')
    assert res1.retry_count == 1
    assert res1.poison_pill is False
    # Second failure -> reaches max_retries
    res2 = dlq.record_failure(msg.message_id, 'Fatal segmentation fault')
    assert res2.retry_count == 2
    assert res2.poison_pill is True
    stats = dlq.get_stats()
    assert stats.poison_pills == 1

def test_replay_pending(dlq):
    req1 = DLQEnqueueRequest(run_id='run-103', payload={'id': 1}, error_reason='Network blip')
    msg1 = dlq.enqueue(req1)
    replayed = dlq.replay_messages(run_id='run-103')
    assert replayed.replayed_count == 1
    assert msg1.message_id in replayed.message_ids
