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
