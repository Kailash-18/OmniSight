import pytest
from backend.app.schemas.throttler_schemas import ThrottleRequest, PriorityLevel
from backend.app.services.adaptive_throttler_service import AdaptiveThrottlerService

def test_token_bucket_basic_allow():
    throttler = AdaptiveThrottlerService(capacity=10.0, refill_rate=5.0)
    req = ThrottleRequest(worker_id='w-01', operation='dom_repair', requested_tokens=2)
    decision = throttler.evaluate(req)
    assert decision.allowed is True
    assert decision.wait_ms == 0
    assert decision.bucket_level < 10.0

def test_token_bucket_burst_exhaustion():
    throttler = AdaptiveThrottlerService(capacity=5.0, refill_rate=1.0)
    req_large = ThrottleRequest(worker_id='w-02', operation='batch_audit', requested_tokens=5)
    first = throttler.evaluate(req_large)
    assert first.allowed is True
    second = throttler.evaluate(req_large)
    assert second.allowed is False
    assert second.wait_ms > 0
    assert 'Insufficient' in second.reason

def test_backpressure_shedding_p2():
    throttler = AdaptiveThrottlerService(capacity=20.0, latency_sla_ms=100.0)
    req_p2 = ThrottleRequest(worker_id='w-p2', operation='analytics', priority=PriorityLevel.P2_BACKGROUND, current_latency_ms=250.0)
    decision = throttler.evaluate(req_p2)
    assert decision.allowed is False
    assert 'Backpressure shed' in decision.reason
    assert decision.backpressure_ratio > 0.6

def test_p0_critical_bypasses_moderate_backpressure():
    throttler = AdaptiveThrottlerService(capacity=20.0, latency_sla_ms=100.0)
    req_p0 = ThrottleRequest(worker_id='w-p0', operation='rollback', priority=PriorityLevel.P0_CRITICAL, current_latency_ms=250.0)
    decision = throttler.evaluate(req_p0)
    assert decision.allowed is True
