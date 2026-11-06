"""
Unit test suite for EventStreamHub and Server-Sent Events (SSE) formatting.
"""
import pytest
from backend.app.schemas.stream_schema import PublishEventRequest, RunEventType
from backend.app.services.event_stream_service import EventStreamHub

@pytest.fixture
def hub():
    return EventStreamHub(max_buffer=10)

def test_event_publish_and_retrieve(hub):
    req = PublishEventRequest(
        run_id="run_stream_1",
        event_type=RunEventType.LEASE_ACQUIRED,
        payload={"lease_id": "lease_123", "selector": ".hero"}
    )
    evt = hub.publish_event(req)
    assert evt.event_id.startswith("evt_")
    assert evt.event_type == RunEventType.LEASE_ACQUIRED

    hist = hub.get_events("run_stream_1")
    assert hist.total_events == 1
    assert hist.events[0].payload["selector"] == ".hero"

def test_event_stream_sse_formatting(hub):
    req = PublishEventRequest(run_id="run_sse", event_type=RunEventType.RUN_COMPLETED, payload={"status": "PASSED"})
    evt = hub.publish_event(req)
    sse_msg = hub.format_sse(evt)
    assert f"id: {evt.event_id}" in sse_msg
    assert "event: RUN_COMPLETED" in sse_msg
    assert "data: {" in sse_msg

def test_event_stream_history_limit(hub):
    for i in range(15):
        hub.publish_event(PublishEventRequest(run_id="run_loop", event_type=RunEventType.RUN_STARTED, payload={"idx": i}))
    hist = hub.get_events("run_loop", limit=20)
    assert hist.total_events == 10
    assert hist.events[-1].payload["idx"] == 14

def test_telemetry_metrics_export(hub):
    hub.increment_subscriber()
    metrics = hub.export_prometheus_stream_metrics()
    assert "omnisight_live_stream_subscribers 1" in metrics
    hub.decrement_subscriber()
