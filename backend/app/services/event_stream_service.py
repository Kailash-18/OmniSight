"""
Real-Time Event Stream Hub for Server-Sent Events (SSE) and live dashboard telemetry.
"""
import uuid
import json
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from backend.app.schemas.stream_schema import (
    StreamEvent, RunEventType, PublishEventRequest, EventStreamHistoryResponse
)

class EventStreamHub:
    def __init__(self, max_buffer: int = 500):
        self.max_buffer = max_buffer
        self._event_buffer: deque = deque(maxlen=max_buffer)
        self._active_subscribers: int = 0

    def publish_event(self, req: PublishEventRequest) -> StreamEvent:
        event = StreamEvent(
            event_id=f"evt_{uuid.uuid4().hex[:10]}",
            run_id=req.run_id,
            event_type=req.event_type,
            payload=req.payload,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        self._event_buffer.append(event)
        return event

    def get_events(self, run_id: Optional[str] = None, limit: int = 50) -> EventStreamHistoryResponse:
        events = list(self._event_buffer)
        if run_id:
            events = [e for e in events if e.run_id == run_id]
        events = events[-limit:]
        return EventStreamHistoryResponse(total_events=len(events), events=events)

    def format_sse(self, event: StreamEvent) -> str:
        data_str = json.dumps(event.model_dump())
        return f"id: {event.event_id}\nevent: {event.event_type.value}\ndata: {data_str}\n\n"

    def increment_subscriber(self):
        self._active_subscribers += 1

    def decrement_subscriber(self):
        self._active_subscribers = max(0, self._active_subscribers - 1)

    def export_prometheus_stream_metrics(self) -> str:
        return (
            f"# HELP omnisight_live_stream_subscribers Current active real-time SSE stream connections\n"
            f"# TYPE omnisight_live_stream_subscribers gauge\n"
            f"omnisight_live_stream_subscribers {self._active_subscribers}\n"
        )

event_stream_hub = EventStreamHub()
