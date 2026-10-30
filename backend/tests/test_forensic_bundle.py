# -*- coding: utf-8 -*-
"""
Unit and cryptographic integrity tests for Forensic Audit Bundling Service.
Verifies artifact collection, SHA-256 signatures, ZIP export, and tampering detection.
"""

import io
import json
import zipfile
import pytest

from backend.app.services.forensic_service import (
    compute_sha256,
    canonical_json,
    build_artifact_envelope,
    create_forensic_bundle,
    verify_forensic_bundle_integrity,
    export_forensic_zip_archive,
)


@pytest.fixture
def sample_run_data():
    return {
        "run_id": "run-forensic-test-101",
        "target": "http://localhost:5173",
        "status": "fixed",
        "start_time": "2026-10-30T10:00:00Z",
        "issue_count": 2,
        "findings": [
            {
                "id": "defect-1",
                "category": "element_clipping",
                "severity": "high",
                "description": "Button clipped",
                "confidence": 0.95,
                "suggested_change": "width: 100%",
                "viewport": "mobile_375x667",
                "status": "detected"
            }
        ],
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }"
        },
        "retest_outcome": {
            "passed": True,
            "visual_diff_score": 0.0,
            "retest_viewport": "mobile_375x667",
            "notes": "Verified in headless sandbox"
        },
        "timeline": [
            {"event": "run_queued", "timestamp": "2026-10-30T10:00:00Z"},
            {"event": "patch_verified", "timestamp": "2026-10-30T10:01:00Z"}
        ]
    }


def test_compute_sha256_deterministic():
    s1 = "OmniSight Visual Self-Healing"
    h1 = compute_sha256(s1)
    h2 = compute_sha256(s1)
    assert h1 == h2
    assert len(h1) == 64
    assert h1 != compute_sha256("different content")


def test_create_forensic_bundle_structure(sample_run_data):
    bundle = create_forensic_bundle(run_id="run-forensic-test-101", run_data=sample_run_data)

    assert bundle["run_id"] == "run-forensic-test-101"
    assert bundle["bundle_id"].startswith("bundle-run-forensic-test-101-")
    assert len(bundle["root_checksum"]) == 64

    manifest = bundle["manifest"]
    assert manifest["run_id"] == "run-forensic-test-101"
    assert manifest["schema_version"] == "1.0-forensic-certified"
    assert manifest["artifact_count"] >= 5

    artifacts = bundle["artifacts"]
