"""Network activity monitor for Playwright browser automation.

Intercepts and records network request failures (HTTP 4xx, 5xx) and unhandled
network exceptions to provide diagnostic telemetry in visual audit runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NetworkEvent:
    url: str
    method: str
    status: Optional[int]
    status_text: Optional[str]
    resource_type: str
    duration_ms: Optional[float] = None
    failure_reason: Optional[str] = None

    @property
    def is_failure(self) -> bool:
        if self.failure_reason:
            return True
        if self.status and self.status >= 400:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "status_text": self.status_text,
            "resource_type": self.resource_type,
            "duration_ms": self.duration_ms,
            "failure_reason": self.failure_reason,
            "is_failure": self.is_failure,
        }


class NetworkActivityMonitor:
    """Collects and summarizes network events from browser page contexts."""

    def __init__(self) -> None:
        self.events: List[NetworkEvent] = []

    def record_response(
        self,
        url: str,
        method: str,
        status: int,
        status_text: str = "",
        resource_type: str = "other",
        duration_ms: Optional[float] = None,
    ) -> NetworkEvent:
        event = NetworkEvent(
            url=url,
            method=method,
            status=status,
            status_text=status_text,
            resource_type=resource_type,
            duration_ms=duration_ms,
        )
        self.events.append(event)
        return event

    def record_failure(
        self,
        url: str,
        method: str,
        reason: str,
        resource_type: str = "other",
    ) -> NetworkEvent:
        event = NetworkEvent(
            url=url,
            method=method,
            status=None,
            status_text=None,
            resource_type=resource_type,
            failure_reason=reason,
        )
        self.events.append(event)
        return event

    @property
    def failures(self) -> List[NetworkEvent]:
        return [e for e in self.events if e.is_failure]

    def summarize(self) -> Dict[str, Any]:
        failures = self.failures
        return {
            "total_requests": len(self.events),
            "failed_requests": len(failures),
            "has_network_errors": len(failures) > 0,
            "failures": [f.to_dict() for f in failures],
        }
