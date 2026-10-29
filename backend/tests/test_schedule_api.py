"""API tests for audit schedule CRUD endpoints."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from app.services import schedule_service as svc

client = TestClient(app)


def setup_function():
    """Reset schedule registry before each test function."""
    svc._schedule_registry.clear()


def test_create_schedule_success():
    resp = client.post("/schedules", json={
        "target_url": "https://example.com",
        "cron_expression": "@daily",
        "viewports": ["1280x720"],
        "enabled": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["schedule_id"].startswith("sched_")
    assert data["target_url"] == "https://example.com"
    assert data["cron_expression"] == "@daily"
    assert data["enabled"] is True
    assert "next_run_at" in data


def test_create_schedule_invalid_cron():
    resp = client.post("/schedules", json={
        "target_url": "https://example.com",
        "cron_expression": "bad_expr"
    })
    assert resp.status_code == 422


def test_list_schedules_empty():
    resp = client.get("/schedules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["schedules"] == []


def test_list_schedules_after_creation():
    client.post("/schedules", json={"target_url": "https://a.com", "cron_expression": "@hourly"})
    client.post("/schedules", json={"target_url": "https://b.com", "cron_expression": "@weekly"})
    resp = client.get("/schedules")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_delete_schedule_success():
    create_resp = client.post("/schedules", json={
        "target_url": "https://del.com",
        "cron_expression": "@daily"
    })
    sid = create_resp.json()["schedule_id"]
    del_resp = client.delete(f"/schedules/{sid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


def test_delete_schedule_not_found():
    resp = client.delete("/schedules/nonexistent_id_xyz")
    assert resp.status_code == 404


def test_enable_schedule_endpoint():
    create_resp = client.post("/schedules", json={
        "target_url": "https://enable.com",
        "cron_expression": "@weekly"
    })
    sid = create_resp.json()["schedule_id"]
    svc.disable_schedule(sid)
    enable_resp = client.patch(f"/schedules/{sid}/enable")
    assert enable_resp.status_code == 200
    assert enable_resp.json()["enabled"] is True


def test_enable_nonexistent_schedule():
    resp = client.patch("/schedules/missing_sched_id/enable")
    assert resp.status_code == 404
