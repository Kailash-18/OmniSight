"""Resilient retry policy with exponential backoff for OmniSight clients.

Provides bounded execution retries for network calls, external webhook deliveries,
and browser page navigation under intermittent network conditions.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional, Type


class RetryPolicy:
    """Executes a callable with bounded exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_sec: float = 0.05,
        backoff_multiplier: float = 2.0,
        max_delay_sec: float = 1.0,
        retryable_exceptions: Optional[tuple[Type[BaseException], ...]] = None,
    ):
        self.max_attempts = max(1, max_attempts)
        self.initial_delay = initial_delay_sec
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay_sec
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    def execute(self, func: Callable[[], Any]) -> Any:
        delay = self.initial_delay
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func()
            except self.retryable_exceptions as exc:
                last_exception = exc
                if attempt == self.max_attempts:
                    break
                time.sleep(delay)
                delay = min(self.max_delay, delay * self.backoff_multiplier)

        if last_exception:
            raise last_exception
        raise RuntimeError("RetryPolicy exhausted attempts without execution")
