import pytest
from backend.app.schemas.diagnostics_schemas import (
    ReleaseCertificationManifest, VerifyCertificateRequest, VerifyCertificateResponse
)

def test_release_certification_manifest_schema():
    manifest = ReleaseCertificationManifest(
        release_version="1.0.0-final",
        certification_timestamp="2026-11-10T12:00:00Z",
        compliance_seal="fedcba9876543210fedcba9876543210",
        certified_by="Sri Khyathi",
        environment="production",
        test_summary={"total_tests": 367, "passed": 367, "failed": 0},
        subsystem_status={"dr": "READY", "tenants": "ISOLATED", "vlm": "OPTIMIZED"},
        audit_pass=True
    )
    assert manifest.release_version == "1.0.0-final"
    assert manifest.audit_pass is True
    assert manifest.test_summary["passed"] == 367

def test_verify_certificate_request_and_response():
    req = VerifyCertificateRequest(certificate_id="1.0.0-final", compliance_seal="abc123seal")
    res = VerifyCertificateResponse(
        valid=True,
        certificate_id=req.certificate_id,
        message="Cryptographic certificate verified successfully",
        verified_at="2026-11-10T12:05:00Z"
    )
    assert res.valid is True
    assert res.certificate_id == "1.0.0-final"
