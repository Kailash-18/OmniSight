# -*- coding: utf-8 -*-
"""
Unit and Integration Test Suite for OmniSight Outbound Webhook Dispatcher.
Verifies RFC 2104 HMAC SHA-256 signature generation, event serialization, and delivery simulation.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.notification_service import (
    sign_webhook_payload,
    build_outbound_event,
    dispatch_notification,
    get_dispatched_events,
    clear_dispatched_events,
)


@pytest.fixture(autouse=True)
def clean_notifications():
    clear_dispatched_events()
    yield
    clear_dispatched_events()


@pytest.fixture
def client():
    return TestClient(app)


def test_sign_webhook_payload_deterministic_hmac():
    """Verify HMAC SHA-256 signature is deterministic and formatted as sha256=<hex>."""
    payload = b'{"event":"test","status":"ok"}'
    secret = "super-secret-key"

    sig1 = sign_webhook_payload(payload, secret)
    sig2 = sign_webhook_payload(payload, secret)

    assert sig1.startswith("sha256=")
    assert len(sig1) == 7 + 64  # "sha256=" + 64 hex chars
    assert sig1 == sig2

    # Different secret generates different signature
    sig_diff = sign_webhook_payload(payload, "another-key")
    assert sig1 != sig_diff

    # Empty secret returns empty string
    assert sign_webhook_payload(payload, "") == ""


def test_build_outbound_event_envelope():
    """Verify outbound event envelopes conform to OmniSight standard structure."""
    event = build_outbound_event(
        event_type="pr.opened",
        run_id="run-evt-001",
        data={"pr_number": 42, "url": "https://github.com/Kailash-18/OmniSight/pull/42"}
    )
    assert event["event_id"].startswith("evt-")
    assert event["event_type"] == "pr.opened"
    assert event["run_id"] == "run-evt-001"
    assert "timestamp" in event
    assert event["data"]["pr_number"] == 42


def test_dispatch_notification_simulated():
    """Verify dispatch_notification records delivery and generates signed records."""
    res = dispatch_notification(
        target_url="https://hooks.slack.com/services/T00/B00/X00",
        event_type="run.fixed",
        run_id="run-notif-99",
        data={"remediation": "CSS overflow fixed"},
        secret="webhook-token-abc"
    )
    assert res["delivered"] is True
    assert res["status_code"] == 200
    assert res["signature"].startswith("sha256=")

    # Verify event stored in history
    history = get_dispatched_events()
    assert len(history) == 1
    rec = history[0]
    assert rec["run_id"] == "run-notif-99"
    assert rec["event_type"] == "run.fixed"
    assert rec["signature"] == res["signature"]


def test_outbound_webhook_test_endpoint(client: TestClient):
    """Verify POST /webhooks/test-dispatch executes and returns simulated delivery status."""
    res = client.post(
        "/webhooks/test-dispatch",
        params={
            "target_url": "http://localhost:9000/webhook",
            "event_type": "run.completed",
            "run_id": "run-ep-dispatch",
            "secret": "my-secret-token"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["delivered"] is True
    assert data["status_code"] == 200
    assert data["signature"].startswith("sha256=")
    assert "run-ep-dispatch" in data["message"]


def test_clear_and_get_dispatched_events():
    """Verify history reset clears event records completely."""
    dispatch_notification("http://test.local", "run.started", "run-1")
    dispatch_notification("http://test.local", "run.fixed", "run-1")
    assert len(get_dispatched_events()) == 2

    clear_dispatched_events()
    assert len(get_dispatched_events()) == 0
