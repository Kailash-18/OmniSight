import pytest
from backend.app.services.system_diagnostics_service import system_diagnostics_service
from backend.app.services.release_certification_service import release_certification_service
from backend.app.schemas.diagnostics_schemas import VerifyCertificateRequest

def test_e2e_golden_path_production_lifecycle():
    # 1. Run diagnostic audit
    report = system_diagnostics_service.run_full_diagnostics()
    assert report.system_readiness_score >= 85.0
    assert report.failures == 0

    # 2. Generate Release Certification
    cert = release_certification_service.generate_release_certificate("1.0.0-final")
    assert cert.audit_pass is True
    assert cert.test_summary["passed"] == 367

    # 3. Verify Certificate Seal
    verification = release_certification_service.verify_certificate(VerifyCertificateRequest(
        certificate_id=cert.release_version,
        compliance_seal=cert.compliance_seal
    ))
    assert verification.valid is True
