import pytest
from backend.app.services.health_telemetry_service import HealthTelemetryService

def test_health_pulse_aggregate_healthy():
    service = HealthTelemetryService()
    report = service.generate_pulse()
    assert report.healthy is True
    assert report.overall_health_score >= 80.0
    assert len(report.subsystems) >= 4
    subsystem_names = [s.name for s in report.subsystems]
    assert 'AdaptiveThrottler' in subsystem_names
    assert 'SnapshotEngine' in subsystem_names
    assert 'ConcurrencyLeases' in subsystem_names
    assert 'CanaryVerifier' in subsystem_names

def test_prometheus_health_metrics_export():
    service = HealthTelemetryService()
    report = service.generate_pulse()
    from backend.app.services.health_telemetry_service import update_prometheus_health_metrics
    update_prometheus_health_metrics(report)
    assert report.overall_health_score > 0
