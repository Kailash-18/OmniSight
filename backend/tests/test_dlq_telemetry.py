from backend.app.services.health_telemetry_service import HealthTelemetryService
from backend.app.services.dlq_service import dlq_service
from backend.app.schemas.dlq_schemas import DLQEnqueueRequest

def test_health_pulse_with_dlq_integration():
    dlq_service.clear()
    pulse_service = HealthTelemetryService()
    report = pulse_service.generate_pulse()
    assert report.healthy is True
    assert report.overall_health_score >= 80.0

    # Enqueue a poison pill
    req = DLQEnqueueRequest(run_id='run-tel-1', payload={}, error_reason='Poison pill simulation', max_retries=1)
    msg = dlq_service.enqueue(req)
    dlq_service.record_failure(msg.message_id, 'Fatal poison pill')

    # Telemetry export
    telemetry = pulse_service.get_dlq_worker_telemetry()
    assert 'dlq' in telemetry
    assert telemetry['dlq']['total_enqueued'] == 1
    assert telemetry['dlq']['poison_pills'] == 1
