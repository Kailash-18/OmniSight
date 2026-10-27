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
