import time
from typing import Optional
from backend.app.schemas.autoscale_schemas import (
    WorkerPoolMetrics, ScaleDecision, AutoscalePolicy, WorkerPoolStatus
)

class WorkerPoolAutoscalerService:
    def __init__(self, policy: Optional[AutoscalePolicy] = None):
        self.policy = policy or AutoscalePolicy()
        self._current_workers = self.policy.min_workers
        self._last_scale_action = 'INIT'
        self._last_scale_timestamp = 0.0

    def reset(self) -> None:
        self._current_workers = self.policy.min_workers
        self._last_scale_action = 'INIT'
        self._last_scale_timestamp = 0.0

    def evaluate(self, metrics: WorkerPoolMetrics) -> ScaleDecision:
        now = time.time()
        elapsed = now - self._last_scale_timestamp
        prev = self._current_workers

        # Check cooldown
        if elapsed < self.policy.cooldown_period_sec and self._last_scale_action != 'INIT':
            return ScaleDecision(
                action='MAINTAIN',
                previous_worker_count=prev,
                target_worker_count=prev,
                reason=f'Cooldown active: {self.policy.cooldown_period_sec - elapsed:.1f}s remaining',
                cooldown_remaining_sec=max(0.0, self.policy.cooldown_period_sec - elapsed)
            )

        # Scale Up logic
        if metrics.queue_depth >= self.policy.scale_up_queue_threshold or metrics.p99_latency_ms > 250.0:
            step = max(1, metrics.queue_depth // 5)
            target = min(self.policy.max_workers, prev + step)
            if target > prev:
                self._current_workers = target
                self._last_scale_action = 'SCALE_UP'
                self._last_scale_timestamp = now
                return ScaleDecision(
                    action='SCALE_UP',
                    previous_worker_count=prev,
                    target_worker_count=target,
                    reason=f'Queue depth {metrics.queue_depth} exceeds threshold {self.policy.scale_up_queue_threshold}'
                )

        # Scale Down logic
        if metrics.queue_depth <= self.policy.scale_down_queue_threshold and metrics.cpu_utilization_pct < 30.0:
            target = max(self.policy.min_workers, prev - 1)
            if target < prev:
                self._current_workers = target
                self._last_scale_action = 'SCALE_DOWN'
                self._last_scale_timestamp = now
                return ScaleDecision(
                    action='SCALE_DOWN',
                    previous_worker_count=prev,
                    target_worker_count=target,
                    reason=f'Queue depth {metrics.queue_depth} below idle threshold {self.policy.scale_down_queue_threshold}'
                )

        return ScaleDecision(
            action='MAINTAIN',
            previous_worker_count=prev,
            target_worker_count=prev,
            reason='Metrics within balanced equilibrium'
        )

    def get_status(self) -> WorkerPoolStatus:
        return WorkerPoolStatus(
            current_workers=self._current_workers,
            min_workers=self.policy.min_workers,
            max_workers=self.policy.max_workers,
            last_scale_action=self._last_scale_action,
            last_scale_timestamp=self._last_scale_timestamp
        )

worker_autoscaler = WorkerPoolAutoscalerService()
