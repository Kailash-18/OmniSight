import pytest
from backend.app.services.dlq_service import DeadLetterQueueService
from backend.app.services.autoscale_service import WorkerPoolAutoscalerService
from backend.app.services.quarantine_service import ClusterQuarantineService
from backend.app.schemas.dlq_schemas import DLQEnqueueRequest
from backend.app.schemas.autoscale_schemas import WorkerPoolMetrics
from backend.app.schemas.quarantine_schemas import QuarantineRequest

def test_e2e_resilience_pipeline():
    # Setup isolated services
    dlq = DeadLetterQueueService(base_backoff_sec=0.01)
    autoscale = WorkerPoolAutoscalerService()
    quarantine = ClusterQuarantineService(default_cluster_size=8)

    # 1. Enqueue job into DLQ due to failure
    msg = dlq.enqueue(DLQEnqueueRequest(run_id='run-e2e-601', payload={'box': [10, 20, 50, 60]}, error_reason='GPU OOM'))
    assert msg.retry_count == 0

    # 2. Worker autoscaler evaluates high queue depth
    metrics = WorkerPoolMetrics(queue_depth=15, active_workers=2, p99_latency_ms=190.0, cpu_utilization_pct=80.0)
    decision = autoscale.evaluate(metrics)
    assert decision.action == 'SCALE_UP'
    assert decision.target_worker_count > 2

    # 3. Corrupted visual node isolated into quarantine
    q_rec = quarantine.isolate_node(QuarantineRequest(node_id='worker-node-oom-1', reason='Repeated GPU OOM', consecutive_failures=3))
    assert q_rec.quarantine_status == 'ISOLATED'
    assert quarantine.is_isolated('worker-node-oom-1') is True

    # 4. Replay from DLQ once workers scaled up and bad node isolated
    replay = dlq.replay_messages(run_id='run-e2e-601')
    assert replay.replayed_count == 1
    assert replay.success is True
