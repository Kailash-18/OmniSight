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
