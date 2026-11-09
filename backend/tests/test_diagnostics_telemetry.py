import pytest
from backend.app.services.health_telemetry_service import update_diagnostic_telemetry

def test_update_diagnostic_telemetry():
    # Verify execution does not throw exceptions and updates gauges cleanly
    update_diagnostic_telemetry(100.0, True)
    update_diagnostic_telemetry(85.5, False)
