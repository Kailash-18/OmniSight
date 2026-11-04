"""
Unit test suite for Audit Telemetry & Cryptographic SOC2 Compliance.
"""
import pytest
from backend.app.services.audit_telemetry_service import AuditTelemetryEngine
from backend.app.schemas.telemetry_schema import (
    AuditRunRecord,
    AnomalySeverity
)

def test_prometheus_gauge_export():
    engine = AuditTelemetryEngine()
    records = [
        AuditRunRecord(run_id="r1", timestamp="2026-11-04T10:00:00Z", visual_diff_score=0.04, tokens_saved=920, is_auto_remediated=True),
        AuditRunRecord(run_id="r2", timestamp="2026-11-04T10:30:00Z", visual_diff_score=0.12, tokens_saved=780, is_auto_remediated=True)
    ]
    gauges = engine.export_prometheus_gauges(records)
    assert len(gauges) == 3
    assert gauges[0].value == 2.0
    assert gauges[1].value == 850.0
    assert gauges[2].value == 1.0
