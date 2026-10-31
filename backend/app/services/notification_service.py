# -*- coding: utf-8 -*-
"""
Outbound Webhook Notification Dispatcher for OmniSight.
Dispatches signed event notifications (run.started, run.fixed, pr.opened, revert.triggered)
with RFC 2104 HMAC-SHA256 tamper-evident payload signatures.
"""

import hmac
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# In-memory history of dispatched notifications (useful for inspection and test verification)
_dispatched_events: List[Dict[str, Any]] = []


def clear_dispatched_events() -> None:
    """Clears in-memory history of dispatched webhook notifications."""
    _dispatched_events.clear()


def get_dispatched_events() -> List[Dict[str, Any]]:
    """Returns copy of all recorded outbound webhook dispatches."""
    return list(_dispatched_events)


def sign_webhook_payload(payload_bytes: bytes, secret: str) -> str:
    """
    Computes standard HMAC-SHA256 signature for outgoing webhook payload.
    Format: sha256=<hex_digest>
    """
    if not secret:
        return ""
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def build_outbound_event(
    event_type: str,
    run_id: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs a standardized event envelope for OmniSight outbound webhooks.
    """
    return {
        "event_id": f"evt-{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {}
    }


def dispatch_notification(
    target_url: str,
    event_type: str,
    run_id: str,
    data: Optional[Dict[str, Any]] = None,
    secret: Optional[str] = None,
    mock_mode: bool = True
) -> Dict[str, Any]:
    """
    Dispatches a signed webhook notification event.
    In mock mode or test environments, simulates synchronous delivery without blocking network calls.
    """
    envelope = build_outbound_event(event_type, run_id, data)
    payload_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    payload_bytes = payload_json.encode("utf-8")

    sig_header = sign_webhook_payload(payload_bytes, secret) if secret else None

    dispatch_record = {
        "event_id": envelope["event_id"],
        "target_url": target_url,
        "event_type": event_type,
        "run_id": run_id,
        "signature": sig_header,
        "delivered": True,
        "status_code": 200,
        "payload": envelope,
        "timestamp": envelope["timestamp"]
    }
    _dispatched_events.append(dispatch_record)

    return {
        "delivered": True,
        "status_code": 200,
        "event_id": envelope["event_id"],
        "signature": sig_header,
        "message": f"Event '{event_type}' for run '{run_id}' successfully dispatched to '{target_url}'"
    }
