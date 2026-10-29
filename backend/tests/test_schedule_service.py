"""Tests for audit schedule service â€” register, list, enable/disable, delete, trigger."""
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
