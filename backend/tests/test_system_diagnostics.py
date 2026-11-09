import pytest
from backend.app.schemas.diagnostics_schemas import (
    SystemDiagnosticCheck, FullSystemDiagnosticsReport
)

def test_system_diagnostic_check_schema():
    check = SystemDiagnosticCheck(
        component="storage_engine",
        status="PASS",
        latency_ms=1.25,
        details={"path": "/var/data", "iops": 1200},
        checked_at="2026-11-10T10:00:00Z"
    )
    assert check.component == "storage_engine"
    assert check.status == "PASS"
    assert check.latency_ms == 1.25

def test_full_system_diagnostics_report_schema():
    report = FullSystemDiagnosticsReport(
        overall_status="HEALTHY",
        system_readiness_score=100.0,
        components_checked=5,
        passed_checks=5,
        warnings=0,
        failures=0,
        checks=[],
        audit_digest="a1b2c3d4e5f67890",
        generated_at="2026-11-10T10:00:00Z"
    )
    assert report.overall_status == "HEALTHY"
    assert report.system_readiness_score == 100.0
    assert report.failures == 0


def test_system_diagnostics_service_execution():
    from backend.app.services.system_diagnostics_service import system_diagnostics_service
    report = system_diagnostics_service.run_full_diagnostics()
    assert report.components_checked == 5
    assert report.overall_status in ["HEALTHY", "DEGRADED"]
    assert report.system_readiness_score >= 85.0
    assert len(report.audit_digest) == 64
    assert all(c.latency_ms >= 0.0 for c in report.checks)
