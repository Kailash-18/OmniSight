# -*- coding: utf-8 -*-
"""
Security Utilities for OmniSight Backend.
Provides cryptographic validation, HMAC webhook signature checking, and request integrity verification.
"""

import hmac
import hashlib
from typing import Optional


def verify_github_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: str
) -> bool:
    """
    Verifies that the incoming GitHub webhook payload matches the X-Hub-Signature-256 header.
    Uses constant-time comparison to prevent timing attacks.
    """
    if not secret:
        # If secret is not configured, signature checking is disabled for development
        return True

    if not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:].strip()
    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


import time
from collections import defaultdict, deque
from typing import Dict, Deque


class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter for gateway API routes and webhooks.
    Tracks timestamps per client key and prunes expired entries beyond window_seconds.
    """
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, now: Optional[float] = None) -> bool:
        """
        Evaluates whether a request from 'key' is permitted under the sliding rate limit.
        Returns True if allowed, False if limit exceeded.
        """
        current_time = now if now is not None else time.time()
        cutoff = current_time - self.window_seconds
        timestamps = self._history[key]

        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) < self.max_requests:
            timestamps.append(current_time)
            return True

        return False

    def reset(self, key: Optional[str] = None) -> None:
        """Resets the history for a specific key or all keys."""
        if key:
            self._history.pop(key, None)
        else:
            self._history.clear()


default_rate_limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=60)
