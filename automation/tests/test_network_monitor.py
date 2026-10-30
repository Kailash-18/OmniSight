"""Tests for NetworkActivityMonitor."""

import pytest
from automation.network_monitor import NetworkActivityMonitor


def test_network_monitor_records_successful_requests():
    monitor = NetworkActivityMonitor()
    monitor.record_response("https://example.com/api/data", "GET", 200, "OK", "fetch", 45.2)
    monitor.record_response("https://example.com/logo.png", "GET", 304, "Not Modified", "image")

    assert len(monitor.events) == 2
    assert len(monitor.failures) == 0
    summary = monitor.summarize()
    assert summary["total_requests"] == 2
    assert summary["failed_requests"] == 0
    assert summary["has_network_errors"] is False


def test_network_monitor_records_4xx_5xx_failures():
    monitor = NetworkActivityMonitor()
    monitor.record_response("https://example.com/missing.css", "GET", 404, "Not Found", "stylesheet")
    monitor.record_response("https://example.com/api/crash", "POST", 500, "Internal Server Error", "xhr")
    monitor.record_failure("https://broken.domain/script.js", "GET", "net::ERR_NAME_NOT_RESOLVED", "script")

    assert len(monitor.events) == 3
    assert len(monitor.failures) == 3
    summary = monitor.summarize()
    assert summary["failed_requests"] == 3
    assert summary["has_network_errors"] is True
    assert summary["failures"][0]["status"] == 404
    assert summary["failures"][1]["status"] == 500
    assert summary["failures"][2]["failure_reason"] == "net::ERR_NAME_NOT_RESOLVED"
