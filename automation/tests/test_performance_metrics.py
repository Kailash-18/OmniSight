"""Tests for PerformanceCollector and PagePerformanceMetrics."""

import pytest
from automation.performance_metrics import PerformanceCollector


def test_performance_collector_parses_timings():
    raw_timing = {
        "navigationStart": 1000.0,
        "responseEnd": 1150.0,
        "domInteractive": 1400.0,
        "domContentLoadedEventEnd": 1550.0,
        "loadEventEnd": 1900.0,
        "usedJSHeapSize": 18452000,
    }

    metrics = PerformanceCollector.parse_timing_dict(raw_timing)
    assert metrics.time_to_first_byte_ms == 150.0
    assert metrics.dom_interactive_ms == 400.0
    assert metrics.dom_content_loaded == 550.0
    assert metrics.total_duration_ms == 900.0
    assert metrics.used_js_heap_size_bytes == 18452000

    d = metrics.to_dict()
    assert d["time_to_first_byte_ms"] == 150.0
    assert d["total_duration_ms"] == 900.0


def test_performance_collector_handles_empty_or_zero():
    metrics = PerformanceCollector.parse_timing_dict({})
    assert metrics.total_duration_ms == 0.0
    assert metrics.time_to_first_byte_ms == 0.0
    assert metrics.used_js_heap_size_bytes is None
