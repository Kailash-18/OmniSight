"""
Audit Schedule Service — cron-like registry for recurring audit runs.
Supports @hourly, @daily, @weekly, every_Nh intervals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# In-memory schedule registry
# ---------------------------------------------------------------------------
_schedule_registry: Dict[str, Dict[str, Any]] = {}

_CRON_DELTAS: Dict[str, timedelta] = {
    "@hourly": timedelta(hours=1),
    "@daily": timedelta(days=1),
    "@weekly": timedelta(weeks=1),
}


def _parse_interval(cron_expr: str) -> timedelta:
    """Parse a cron expression string into a timedelta."""
    if cron_expr in _CRON_DELTAS:
        return _CRON_DELTAS[cron_expr]
    # Handle every_Nh pattern, e.g. every_6h
    if cron_expr.startswith("every_") and cron_expr.endswith("h"):
        try:
            hours = int(cron_expr[len("every_"):-1])
            return timedelta(hours=hours)
        except ValueError:
            pass
    raise ValueError(f"Unsupported cron expression: '{cron_expr}'. Use @hourly, @daily, @weekly, or every_Nh.")


def register_schedule(
    target_url: str,
    cron_expression: str,
    viewports: Optional[List[str]] = None,
    notify_webhook: Optional[str] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """Register a new recurring audit schedule and return the registry entry."""
    _parse_interval(cron_expression)  # validate expression up front
    schedule_id = f"sched_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    try:
        delta = _parse_interval(cron_expression)
        next_run_at = (now + delta).isoformat()
    except ValueError:
        next_run_at = None

    entry: Dict[str, Any] = {
        "schedule_id": schedule_id,
        "target_url": target_url,
        "cron_expression": cron_expression,
        "viewports": viewports or ["1280x720"],
        "notify_webhook": notify_webhook,
        "enabled": enabled,
        "next_run_at": next_run_at,
        "created_at": now.isoformat(),
        "last_triggered_at": None,
        "trigger_count": 0,
    }
    _schedule_registry[schedule_id] = entry
    return entry


def get_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single schedule by ID."""
    return _schedule_registry.get(schedule_id)


def list_schedules() -> List[Dict[str, Any]]:
    """Return all registered schedules."""
    return list(_schedule_registry.values())


def disable_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
    """Disable a schedule without deleting it."""
    entry = _schedule_registry.get(schedule_id)
    if entry is None:
        return None
    entry["enabled"] = False
    return entry


def enable_schedule(schedule_id: str) -> Optional[Dict[str, Any]]:
    """Re-enable a previously disabled schedule."""
    entry = _schedule_registry.get(schedule_id)
    if entry is None:
        return None
    entry["enabled"] = True
    now = datetime.now(timezone.utc)
    try:
        delta = _parse_interval(entry["cron_expression"])
        entry["next_run_at"] = (now + delta).isoformat()
    except ValueError:
        pass
    return entry


def delete_schedule(schedule_id: str) -> bool:
    """Delete a schedule. Returns True if it existed."""
    if schedule_id in _schedule_registry:
        del _schedule_registry[schedule_id]
        return True
    return False


def record_trigger(schedule_id: str) -> Optional[Dict[str, Any]]:
    """Mark a schedule as triggered — updates counters and next_run_at."""
    entry = _schedule_registry.get(schedule_id)
    if entry is None:
        return None
    now = datetime.now(timezone.utc)
    entry["last_triggered_at"] = now.isoformat()
    entry["trigger_count"] += 1
    try:
        delta = _parse_interval(entry["cron_expression"])
        entry["next_run_at"] = (now + delta).isoformat()
    except ValueError:
        entry["next_run_at"] = None
    return entry
