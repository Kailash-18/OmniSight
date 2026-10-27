# -*- coding: utf-8 -*-
"""
Tests for GitHub Webhook HMAC SHA256 Signature Verification.
"""

import hmac
import hashlib
from app.core.security import verify_github_signature


def test_verify_github_signature_valid():
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "closed", "pull_request": {"number": 12}}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    sig_header = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(payload, sig_header, secret) is True


def test_verify_github_signature_invalid():
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "closed"}'
    sig_header = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    assert verify_github_signature(payload, sig_header, secret) is False


def test_verify_github_signature_missing_header():
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "closed"}'

    assert verify_github_signature(payload, None, secret) is False


def test_verify_github_signature_missing_prefix():
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "closed"}'

    assert verify_github_signature(payload, "12345abcdef", secret) is False


def test_verify_github_signature_empty_secret_bypasses():
    payload = b'{"action": "closed"}'
    assert verify_github_signature(payload, None, "") is True


def test_verify_github_signature_tampered_payload():
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "closed", "pr": 1}'
    tampered = b'{"action": "closed", "pr": 2}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    sig_header = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(tampered, sig_header, secret) is False


from app.core.security import SlidingWindowRateLimiter


def test_sliding_window_rate_limiter_allows_under_limit():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=10)
    assert limiter.is_allowed("192.168.1.1", now=100.0) is True
    assert limiter.is_allowed("192.168.1.1", now=101.0) is True
    assert limiter.is_allowed("192.168.1.1", now=102.0) is True


def test_sliding_window_rate_limiter_blocks_over_limit():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
    assert limiter.is_allowed("10.0.0.1", now=100.0) is True
    assert limiter.is_allowed("10.0.0.1", now=101.0) is True
    assert limiter.is_allowed("10.0.0.1", now=102.0) is False


def test_sliding_window_rate_limiter_window_expiry():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
    assert limiter.is_allowed("10.0.0.2", now=100.0) is True
    assert limiter.is_allowed("10.0.0.2", now=101.0) is True
    assert limiter.is_allowed("10.0.0.2", now=105.0) is False
    # After 10s expires from 100.0 (t >= 111.0)
    assert limiter.is_allowed("10.0.0.2", now=111.0) is True


def test_sliding_window_rate_limiter_reset():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    assert limiter.is_allowed("key1", now=50.0) is True
    assert limiter.is_allowed("key1", now=51.0) is False
    limiter.reset("key1")
    assert limiter.is_allowed("key1", now=52.0) is True

