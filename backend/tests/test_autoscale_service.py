import pytest
from backend.app.schemas.autoscale_schemas import WorkerPoolMetrics, AutoscalePolicy
from backend.app.services.autoscale_service import WorkerPoolAutoscalerService

@pytest.fixture
def autoscaler():
    policy = AutoscalePolicy(min_workers=2, max_workers=8, scale_up_queue_threshold=5, scale_down_queue_threshold=1, cooldown_period_sec=0.1)
    svc = WorkerPoolAutoscalerService(policy=policy)
    svc.reset()
    return svc

def test_scale_up_on_high_queue(autoscaler):
    m = WorkerPoolMetrics(queue_depth=12, active_workers=2, p99_latency_ms=180.0, cpu_utilization_pct=85.0)
    decision = autoscaler.evaluate(m)
    assert decision.action == 'SCALE_UP'
    assert decision.target_worker_count > 2
    assert decision.target_worker_count <= 8

def test_scale_down_on_low_queue(autoscaler):
    import time
    autoscaler._current_workers = 6
    time.sleep(0.15)  # Bypass cooldown
    m = WorkerPoolMetrics(queue_depth=0, active_workers=1, p99_latency_ms=25.0, cpu_utilization_pct=15.0)
    decision = autoscaler.evaluate(m)
    assert decision.action == 'SCALE_DOWN'
    assert decision.target_worker_count < 6
    assert decision.target_worker_count >= 2

def test_cooldown_dampening(autoscaler):
    m = WorkerPoolMetrics(queue_depth=10, active_workers=2, p99_latency_ms=150.0, cpu_utilization_pct=75.0)
    d1 = autoscaler.evaluate(m)
    assert d1.action == 'SCALE_UP'
    # Immediate next evaluation within cooldown
    d2 = autoscaler.evaluate(m)
    assert d2.action == 'MAINTAIN'
    assert 'cooldown' in d2.reason.lower()
