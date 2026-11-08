import time
from backend.app.services.dlq_service import DeadLetterQueueService
from backend.app.services.autoscale_service import WorkerPoolAutoscalerService
from backend.app.schemas.dlq_schemas import DLQEnqueueRequest
from backend.app.schemas.autoscale_schemas import WorkerPoolMetrics

def test_benchmark_dlq_enqueue_throughput():
    svc = DeadLetterQueueService()
    start = time.perf_counter()
    for i in range(100):
        svc.enqueue(DLQEnqueueRequest(run_id=f'bench-{i}', payload={'idx': i}, error_reason='Simulated error'))
    elapsed = time.perf_counter() - start
    # 100 enqueues in memory must take less than 50ms
    assert elapsed < 0.05

def test_benchmark_autoscale_eval_speed():
    svc = WorkerPoolAutoscalerService()
    start = time.perf_counter()
    for _ in range(100):
        svc.evaluate(WorkerPoolMetrics(queue_depth=5, active_workers=2, p99_latency_ms=50.0, cpu_utilization_pct=50.0))
    elapsed = time.perf_counter() - start
    assert elapsed < 0.05
