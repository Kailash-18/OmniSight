"""
Unit tests for CircuitBreakerService state transitions and resilience mechanisms.
"""
import pytest
from backend.app.services.circuit_breaker_service import CircuitBreakerService
from backend.app.schemas.resilience_schema import CircuitState

def test_circuit_initial_state_is_closed():
    cb = CircuitBreakerService(failure_threshold=3, recovery_timeout_seconds=1.0)
    status = cb.get_status()
    assert status.state == CircuitState.CLOSED
    assert status.failure_count == 0
    assert cb.allow_request() is True

def test_circuit_trips_to_open_after_threshold():
    cb = CircuitBreakerService(failure_threshold=3, recovery_timeout_seconds=5.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.get_status().state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.get_status().state == CircuitState.OPEN
    assert cb.allow_request() is False
    assert cb.get_status().circuit_tripped_total == 1

def test_circuit_recovery_half_open_to_closed():
    cb = CircuitBreakerService(failure_threshold=2, recovery_timeout_seconds=0.01, success_threshold=2)
    cb.record_failure()
    cb.record_failure()
    assert cb.get_status().state == CircuitState.OPEN
    import time
    time.sleep(0.02)
    assert cb.allow_request() is True
    assert cb.get_status().state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.get_status().state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.get_status().state == CircuitState.CLOSED

def test_fallback_inference_execution():
    cb = CircuitBreakerService()
    from backend.app.schemas.resilience_schema import FallbackInferenceRequest
    req = FallbackInferenceRequest(
        run_id="run_test_fallback",
        crop_coordinates={"x": 100, "y": 200, "width": 300, "height": 150}
    )
    resp = cb.execute_fallback_inference(req)
    assert resp.used_fallback is True
    assert resp.estimated_confidence >= 0.8
    assert ".anomaly-target-container" in resp.suggested_patch_selector
