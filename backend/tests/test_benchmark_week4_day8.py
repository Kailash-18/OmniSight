import time
import pytest
from backend.app.services.system_diagnostics_service import system_diagnostics_service
from backend.app.services.release_certification_service import release_certification_service

def test_benchmark_sub_50ms_system_diagnostics():
    start = time.perf_counter()
    report = system_diagnostics_service.run_full_diagnostics()
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert elapsed_ms < 50.0, f"Diagnostics took {elapsed_ms:.2f}ms, exceeding 50ms SLA"
    assert report.components_checked == 5

def test_benchmark_sub_10ms_certification_issuance():
    start = time.perf_counter()
    cert = release_certification_service.generate_release_certificate("1.0.0-perf-bench")
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert elapsed_ms < 10.0, f"Certification took {elapsed_ms:.2f}ms, exceeding 10ms SLA"
    assert cert.audit_pass is True
