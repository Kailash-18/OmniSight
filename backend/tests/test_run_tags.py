"""Tests for run tagging API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, runs_db

client = TestClient(app)


def test_add_and_remove_run_tags():
    runs_db["run-tag-test"] = {
        "id": "run-tag-test",
        "target_url": "http://localhost:5173",
        "tags": ["smoke-test"],
    }

    # Add new tag
    resp = client.post("/runs/run-tag-test/tags", json={"tag": "release-blocker"})
    assert resp.status_code == 200
    data = resp.json()
    assert "release-blocker" in data["tags"]
    assert "smoke-test" in data["tags"]

    # Deduplication
    resp2 = client.post("/runs/run-tag-test/tags", json={"tag": "release-blocker"})
    assert resp2.status_code == 200
    assert data["tags"].count("release-blocker") == 1

    # Delete tag
    del_resp = client.delete("/runs/run-tag-test/tags/smoke-test")
    assert del_resp.status_code == 200
    assert "smoke-test" not in del_resp.json()["tags"]
    assert "release-blocker" in del_resp.json()["tags"]
