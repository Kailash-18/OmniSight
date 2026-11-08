"""
Unit tests for Report Export endpoints (Markdown and JSON) and System Diagnostics API.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app, runs_db


@pytest.fixture
def client():
    return TestClient(app)


def test_export_markdown_not_found(client: TestClient):
    resp = client.get("/runs/non-existent-run-xyz/export/markdown")
    assert resp.status_code == 404


def test_export_markdown_success(client: TestClient):
    run_id = "test-export-md-run"
    runs_db[run_id] = {
        "run_id": run_id,
        "target": "http://localhost:5173",
        "status": "audited",
        "start_time": "2026-11-07T12:00:00Z",
        "findings": [
            {
                "id": "f-1",
                "category": "element_overlap",
                "severity": "high",
                "viewport": "desktop_1440x900",
                "target_element": "header.navbar",
                "description": "Navigation overlap header",
            }
        ],
        "patch": {
            "target_file": "app-under-test/src/App.css",
            "validation_status": True,
            "diff": "--- a\n+++ b\n@@ -1 +1 @@",
        },
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/99",
    }

    resp = client.get(f"/runs/{run_id}/export/markdown")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert f'filename="omnisight-report-{run_id}.md"' in resp.headers["content-disposition"]
    content = resp.text
    assert "# OmniSight Visual QA Audit Report" in content
    assert run_id in content
    assert "Executive Summary" in content
    assert "Navigation overlap header" in content
    assert "https://github.com/Kailash-18/OmniSight/pull/99" in content


def test_export_json_success(client: TestClient):
    run_id = "test-export-json-run"
    runs_db[run_id] = {
        "run_id": run_id,
        "target": "http://localhost:5173",
        "status": "fixed",
        "start_time": "2026-11-07T12:00:00Z",
        "findings": [],
    }

    resp = client.get(f"/runs/{run_id}/export/json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    assert f'filename="omnisight-run-{run_id}.json"' in resp.headers["content-disposition"]
    data = resp.json()
    assert data["run_id"] == run_id
    assert data["status"] == "fixed"


def test_diagnostics_endpoint(client: TestClient):
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "python_version" in data
    assert "platform" in data
    assert "active_runs" in data
