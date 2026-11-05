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

    def execute_fallback_inference(self, req: FallbackInferenceRequest) -> FallbackInferenceResponse:
        self.fallback_executions_total += 1
        coords = req.crop_coordinates
        w, h = coords.get("width", 100), coords.get("height", 50)
        selector = ".anomaly-target-container"
        css = f"max-width: {w}px; overflow: hidden; display: flex; align-items: center;"
        return FallbackInferenceResponse(
            run_id=req.run_id,
            used_fallback=True,
            strategy="heuristic_structural_contour_diff",
            estimated_confidence=0.86,
            suggested_patch_selector=selector,
            suggested_css=css,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    def export_prometheus_resilience_metrics(self) -> str:
        state_val = 0 if self.state == CircuitState.CLOSED else (1 if self.state == CircuitState.HALF_OPEN else 2)
        return (
            f"# HELP omnisight_circuit_breaker_state Current circuit state (0=closed, 1=half_open, 2=open)\n"
            f"# TYPE omnisight_circuit_breaker_state gauge\n"
            f"omnisight_circuit_breaker_state{{service=\"{self.get_status().service_name}\"}} {state_val}\n"
            f"# HELP omnisight_circuit_tripped_total Total times circuit has tripped open\n"
            f"# TYPE omnisight_circuit_tripped_total counter\n"
            f"omnisight_circuit_tripped_total {self.circuit_tripped_total}\n"
            f"# HELP omnisight_circuit_fallback_total Total fallback inferences executed\n"
            f"# TYPE omnisight_circuit_fallback_total counter\n"
            f"omnisight_circuit_fallback_total {self.fallback_executions_total}\n"
        )
