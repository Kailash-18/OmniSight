"""Tests for annotation creation and retrieval on audit runs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, runs_db, annotations_db

client = TestClient(app)

TEST_RUN_ID = "ann-test-run-001"


def setup_function():
    """Seed a run and clear annotations before each test."""
    runs_db[TEST_RUN_ID] = {
        "run_id": TEST_RUN_ID,
        "url": "https://annotated.com",
        "status": "completed",
        "findings": [],
        "issue_count": 0,
        "timeline": [],
        "tags": [],
    }
    annotations_db.pop(TEST_RUN_ID, None)


def test_create_annotation_success():
    resp = client.post(f"/runs/{TEST_RUN_ID}/annotations", json={
        "author": "qa-reviewer-1",
        "body": "Confirmed layout regression on mobile viewport.",
        "severity_override": "high",
        "tags": ["mobile", "layout"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["annotation_id"].startswith("ann_")
    assert data["author"] == "qa-reviewer-1"
    assert data["severity_override"] == "high"
    assert "mobile" in data["tags"]


def test_create_annotation_run_not_found():
    resp = client.post("/runs/nonexistent-run-999/annotations", json={
        "author": "reviewer",
        "body": "This should 404."
    })
    assert resp.status_code == 404


def test_create_annotation_body_too_short():
    resp = client.post(f"/runs/{TEST_RUN_ID}/annotations", json={
        "author": "reviewer",
        "body": "abc"  # less than 5 chars — should fail validation
    })
    assert resp.status_code == 422


def test_get_annotations_empty():
    resp = client.get(f"/runs/{TEST_RUN_ID}/annotations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["annotations"] == []


def test_get_annotations_after_creation():
    client.post(f"/runs/{TEST_RUN_ID}/annotations", json={
        "author": "reviewer-a",
        "body": "First annotation for this run — layout issue."
    })
    client.post(f"/runs/{TEST_RUN_ID}/annotations", json={
        "author": "reviewer-b",
        "body": "Second annotation — color contrast warning."
    })
    resp = client.get(f"/runs/{TEST_RUN_ID}/annotations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["run_id"] == TEST_RUN_ID


def test_get_annotations_run_not_found():
    resp = client.get("/runs/ghost-run-xyz/annotations")
    assert resp.status_code == 404
