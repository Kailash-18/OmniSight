"""Browser performance and Web Vitals metric extractor for OmniSight.

Collects Navigation Timing metrics (TTFB, DOMContentLoaded, Page Load duration,
and memory utilization) from Playwright page sessions for performance benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PagePerformanceMetrics:
    navigation_start: float = 0.0
    response_end: float = 0.0
    dom_content_loaded: float = 0.0
    load_event_end: float = 0.0
    total_duration_ms: float = 0.0
    time_to_first_byte_ms: float = 0.0
    dom_interactive_ms: float = 0.0
    used_js_heap_size_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration_ms": round(self.total_duration_ms, 2),
            "time_to_first_byte_ms": round(self.time_to_first_byte_ms, 2),
            "dom_content_loaded_ms": round(self.dom_content_loaded, 2),
            "dom_interactive_ms": round(self.dom_interactive_ms, 2),
            "used_js_heap_size_bytes": self.used_js_heap_size_bytes,
        }


class PerformanceCollector:
    """Parses raw browser performance.timing entries into structured metrics."""

    @staticmethod
    def parse_timing_dict(raw: Dict[str, Any]) -> PagePerformanceMetrics:
        nav_start = float(raw.get("navigationStart") or raw.get("fetchStart") or 0.0)
        resp_end = float(raw.get("responseEnd") or nav_start)
        dom_interactive = float(raw.get("domInteractive") or resp_end)
        dom_content_loaded = float(raw.get("domContentLoadedEventEnd") or dom_interactive)
        load_event = float(raw.get("loadEventEnd") or dom_content_loaded)

        ttfb = max(0.0, resp_end - nav_start)
        dom_int = max(0.0, dom_interactive - nav_start)
        dcl = max(0.0, dom_content_loaded - nav_start)
        total = max(0.0, load_event - nav_start)

        heap = raw.get("usedJSHeapSize")

        return PagePerformanceMetrics(
            navigation_start=nav_start,
            response_end=resp_end,
            dom_content_loaded=dcl,
            load_event_end=load_event,
            total_duration_ms=total,
            time_to_first_byte_ms=ttfb,
            dom_interactive_ms=dom_int,
            used_js_heap_size_bytes=int(heap) if heap else None,
        )
