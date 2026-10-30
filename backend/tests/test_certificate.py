# -*- coding: utf-8 -*-
"""
Unit tests for Remediation Verification & Compliance Certificate Service.
Verifies cryptographic seal generation, audit provenance, and markdown export.
"""

import pytest

from backend.app.services.certificate_service import (
    generate_remediation_certificate,
    export_certificate_markdown,
)


@pytest.fixture
def sample_run_data():
    return {
        "run_id": "run-cert-500",
        "target": "http://localhost:5173",
        "status": "fixed",
        "findings": [
            {"id": "d1", "description": "Layout overlap on mobile checkout", "category": "element_overlap"}
        ],
        "retest_outcome": {
            "passed": True,
            "visual_diff_score": 0.0,
            "retest_viewport": "mobile_375x667",
            "notes": "Verified in headless sandbox"
        },
        "policy_status": "auto_merge_cleared"
    }


def test_generate_remediation_certificate_structure(sample_run_data):
    cert = generate_remediation_certificate(
        run_id="run-cert-500",
        run_data=sample_run_data,
        forensic_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    assert cert["certificate_id"].startswith("CERT-OMNI-")
    assert cert["run_id"] == "run-cert-500"
    assert cert["status"] == "CERTIFIED_FIXED"
    assert cert["verification_result"] == "PASSED"
    assert cert["visual_delta_ratio"] == 0.0
    assert cert["defects_resolved_count"] == 1
    assert len(cert["cryptographic_seal"]) == 64
    assert cert["forensic_checksum"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_remediation_certificate_incorporates_review_trail(sample_run_data):
    reviews = [
        {"reviewer_id": "lead-sri", "decision": "approved", "comments": "Approved after sandbox inspection"}
    ]
    cert = generate_remediation_certificate(
        run_id="run-cert-500",
        run_data=sample_run_data,
        review_trail=reviews
    )

    assert cert["primary_reviewer"] == "lead-sri"
    assert cert["review_decision"] == "approved"


def test_export_certificate_markdown_content(sample_run_data):
    cert = generate_remediation_certificate(run_id="run-cert-500", run_data=sample_run_data)
    md = export_certificate_markdown(cert)

    assert "# ðŸ›¡ï¸� Certificate of Visual Remediation" in md
    assert cert["certificate_id"] in md
    assert cert["cryptographic_seal"] in md
    assert "VERIFIED FIXED & CERTIFIED" in md


def test_verify_certificate_seal(sample_run_data):
    from backend.app.services.certificate_service import verify_certificate_seal

    cert = generate_remediation_certificate(run_id="run-cert-500", run_data=sample_run_data)
    assert verify_certificate_seal(cert) is True

    # Tamper with certificate data
    tampered = dict(cert)
    tampered["visual_delta_ratio"] = 0.50
    assert verify_certificate_seal(tampered) is False
