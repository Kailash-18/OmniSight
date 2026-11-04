"""
Forensic Audit Bundling and Cryptographic Verification for OmniSight (Team Lead Week 3 deliverable).
Compiles evidence packages, calculates SHA-256 digests, and generates immutable zip archives.
Re-exported from automation.engine for standard repository layout compliance.
"""

from automation.engine import (
    ForensicBundler,
    compute_sha256,
    create_forensic_bundle,
)

__all__ = [
    "ForensicBundler",
    "compute_sha256",
    "create_forensic_bundle",
]
