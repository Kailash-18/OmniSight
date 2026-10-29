"""
Audit Schedule Service â€” cron-like registry for recurring audit runs.
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
