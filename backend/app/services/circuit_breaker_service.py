"""
Circuit Breaker Service for VLM inference resilience and heuristic fallback.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.schemas.resilience_schema import (
    CircuitState, CircuitBreakerStatus, FallbackInferenceRequest, FallbackInferenceResponse
)

class CircuitBreakerService:
    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: float = 30.0, success_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now(timezone.utc).isoformat()
        self.last_failure_timestamp = 0.0
        self.fallback_executions_total = 0
        self.circuit_tripped_total = 0

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_timestamp > self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = datetime.now(timezone.utc).isoformat()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = datetime.now(timezone.utc).isoformat()
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_timestamp = time.time()
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                self.circuit_tripped_total += 1
            self.state = CircuitState.OPEN
            self.last_state_change = datetime.now(timezone.utc).isoformat()

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now(timezone.utc).isoformat()

    def get_status(self) -> CircuitBreakerStatus:
        return CircuitBreakerStatus(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_state_change=self.last_state_change,
            fallback_executions_total=self.fallback_executions_total,
            circuit_tripped_total=self.circuit_tripped_total
        )
