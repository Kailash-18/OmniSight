"""Tests for audit schedule service — register, list, enable/disable, delete, trigger."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import importlib
import pytest

import backend.app.services.schedule_service as svc


def _reset():
    """Clear the registry between tests."""
    svc._schedule_registry.clear()


def test_register_schedule_creates_entry():
    _reset()
    entry = svc.register_schedule("https://example.com", "@daily")
    assert entry["schedule_id"].startswith("sched_")
    assert entry["target_url"] == "https://example.com"
    assert entry["cron_expression"] == "@daily"
    assert entry["enabled"] is True
    assert entry["next_run_at"] is not None


def test_register_schedule_every_Nh():
    _reset()
    entry = svc.register_schedule("https://test.io", "every_6h", viewports=["375x812"])
    assert entry["viewports"] == ["375x812"]
    assert "next_run_at" in entry


def test_register_schedule_invalid_cron_raises():
    _reset()
    with pytest.raises(ValueError, match="Unsupported cron"):
        svc.register_schedule("https://bad.com", "bad_cron")


def test_list_schedules_returns_all():
    _reset()
    svc.register_schedule("https://a.com", "@hourly")
    svc.register_schedule("https://b.com", "@weekly")
    schedules = svc.list_schedules()
    assert len(schedules) == 2


def test_disable_schedule():
    _reset()
    entry = svc.register_schedule("https://c.com", "@daily")
    sid = entry["schedule_id"]
    result = svc.disable_schedule(sid)
    assert result["enabled"] is False


def test_enable_schedule():
    _reset()
    entry = svc.register_schedule("https://d.com", "@weekly")
    sid = entry["schedule_id"]
    svc.disable_schedule(sid)
    result = svc.enable_schedule(sid)
    assert result["enabled"] is True
    assert result["next_run_at"] is not None


def test_delete_schedule():
    _reset()
    entry = svc.register_schedule("https://e.com", "@daily")
    sid = entry["schedule_id"]
    deleted = svc.delete_schedule(sid)
    assert deleted is True
    assert svc.get_schedule(sid) is None


def test_delete_nonexistent_schedule():
    _reset()
    assert svc.delete_schedule("nonexistent_id") is False


def test_record_trigger_increments_count():
    _reset()
    entry = svc.register_schedule("https://f.com", "@hourly")
    sid = entry["schedule_id"]
    svc.record_trigger(sid)
    svc.record_trigger(sid)
    updated = svc.get_schedule(sid)
    assert updated["trigger_count"] == 2
    assert updated["last_triggered_at"] is not None
