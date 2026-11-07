import time
from typing import Dict, Any
from backend.app.schemas.throttler_schemas import (
    ThrottleRequest, ThrottleEvaluation, ThrottleStats, PriorityLevel
)

class AdaptiveThrottlerService:
    def __init__(self, capacity: float = 50.0, refill_rate: float = 10.0, latency_sla_ms: float = 200.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.latency_sla_ms = float(latency_sla_ms)
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.total_requests = 0
        self.allowed_requests = 0
        self.throttled_requests = 0
        self.active_workers: Dict[str, float] = {}

    def _refill(self) -> None:
        now = time.time()
        delta = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last_refill = now

    def evaluate(self, req: ThrottleRequest) -> ThrottleEvaluation:
        self._refill()
        self.total_requests += 1
        self.active_workers[req.worker_id] = time.time()

        backpressure = 0.0
        if req.current_latency_ms > self.latency_sla_ms:
            excess = req.current_latency_ms - self.latency_sla_ms
            backpressure = min(1.0, excess / self.latency_sla_ms)

        if backpressure > 0.6 and req.priority == PriorityLevel.P2_BACKGROUND:
            self.throttled_requests += 1
            return ThrottleEvaluation(
                allowed=False,
                wait_ms=int(backpressure * 1000),
                backpressure_ratio=round(backpressure, 3),
                bucket_level=round(self.tokens, 2),
                reason=f'Backpressure shed: latency {req.current_latency_ms:.1f}ms exceeds SLA {self.latency_sla_ms:.1f}ms'
            )

        tokens_needed = float(req.requested_tokens)
        if self.tokens >= tokens_needed:
            self.tokens -= tokens_needed
            self.allowed_requests += 1
            return ThrottleEvaluation(
                allowed=True,
                wait_ms=0,
                backpressure_ratio=round(backpressure, 3),
                bucket_level=round(self.tokens, 2),
                reason='OK'
            )
        else:
            self.throttled_requests += 1
            deficit = tokens_needed - self.tokens
            wait_seconds = deficit / max(0.1, self.refill_rate)
            return ThrottleEvaluation(
                allowed=False,
                wait_ms=int(wait_seconds * 1000),
                backpressure_ratio=round(backpressure, 3),
                bucket_level=round(self.tokens, 2),
                reason=f'Insufficient tokens (required {tokens_needed}, available {self.tokens:.1f})'
            )

    def get_stats(self) -> ThrottleStats:
        self._refill()
        now = time.time()
        active = sum(1 for ts in self.active_workers.values() if now - ts < 60)
        return ThrottleStats(
            total_requests=self.total_requests,
            allowed_requests=self.allowed_requests,
            throttled_requests=self.throttled_requests,
            current_tokens=round(self.tokens, 2),
            active_workers=active,
            backpressure_active=(self.throttled_requests > 0 and self.tokens < self.capacity * 0.2)
        )

adaptive_throttler = AdaptiveThrottlerService()
