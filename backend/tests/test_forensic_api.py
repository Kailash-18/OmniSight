# -*- coding: utf-8 -*-
"""
API Integration tests for Week 3 Day 4 endpoints:
Forensic audit bundling, ZIP download, integrity verification, review decisions, and certificates.
"""

import io
import sys
from pathlib import Path
import zipfile
import pytest
from fastapi.testclient import TestClient

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.main import app, runs_db
from app.services.review_engine import clear_reviews_db, reviews_db

client = TestClient(app)

TEST_RUN_ID = "run-day4-integration-999"


@pytest.fixture(autouse=True)
def setup_test_run():
    clear_reviews_db()
    reviews_db.clear()
    runs_db[TEST_RUN_ID] = {
        "run_id": TEST_RUN_ID,
        "target": "http://localhost:5173",
        "url": "http://localhost:5173",
        "status": "audited",
        "start_time": "2026-10-30T10:00:00Z",
        "issue_count": 1,
        "findings": [
            {
                "id": "defect-1",
                "category": "element_clipping",
                "severity": "high",
                "description": "Place Order button clipped on mobile",
                "confidence": 0.95,
                "suggested_change": "width: 100%",
                "viewport": "mobile_375x667",
                "status": "detected"
            }
        ],
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }"
        },
        "retest_outcome": {
            "passed": True,
            "visual_diff_score": 0.0,
            "retest_viewport": "mobile_375x667",
            "notes": "Verified in headless sandbox"
        },
        "timeline": [
            {"event": "run_queued", "timestamp": "2026-10-30T10:00:00Z"}
        ],
        "tags": ["mobile", "p1"]
    }
    yield
    clear_reviews_db()
    reviews_db.clear()


def test_api_get_forensic_bundle():
    resp = client.get(f"/runs/{TEST_RUN_ID}/forensic-bundle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == TEST_RUN_ID
    assert "manifest" in data
    assert "artifacts" in data
    assert len(data["root_checksum"]) == 64


def test_api_get_forensic_bundle_404():
    resp = client.get("/runs/nonexistent-run-xyz/forensic-bundle")
    assert resp.status_code == 404


def test_api_download_forensic_zip():
    resp = client.get(f"/runs/{TEST_RUN_ID}/forensic-bundle/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert f"forensic-bundle-{TEST_RUN_ID}.zip" in resp.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    namelist = zf.namelist()
    assert "manifest.json" in namelist
    assert "findings.json" in namelist
    assert "audit_log.txt" in namelist


def test_api_verify_forensic_integrity():
    resp = client.post(f"/runs/{TEST_RUN_ID}/verify-forensic-integrity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["status"] == "VERIFIED_AUTHENTIC"
    assert data["tampered_artifacts"] == []


def test_api_submit_review_approved():
    resp = client.post(f"/runs/{TEST_RUN_ID}/review", json={
        "reviewer_id": "qa-engineer-alice",
        "decision": "approved",
        "comments": "Inspected mobile layout fix and confirmed 0% visual delta.",
        "auto_merge_authorized": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "approved"
    assert data["reviewer_id"] == "qa-engineer-alice"
    assert data["auto_merge_authorized"] is True
    assert runs_db[TEST_RUN_ID]["status"] == "fixed"


def test_api_get_review_trail():
    client.post(f"/runs/{TEST_RUN_ID}/review", json={
        "reviewer_id": "qa-reviewer-1",
        "decision": "changes_requested",
        "comments": "Need adjustments to padding."
    })
    client.post(f"/runs/{TEST_RUN_ID}/review", json={
        "reviewer_id": "qa-reviewer-2",
        "decision": "approved",
        "comments": "Padding adjustments verified."
    })
    resp = client.get(f"/runs/{TEST_RUN_ID}/review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_reviews"] == 2
    assert len(data["reviews"]) == 2


def test_api_lead_override():
    resp = client.post(f"/runs/{TEST_RUN_ID}/override", json={
        "lead_reviewer_id": "qa-lead-kailash",
        "override_reason": "Urgent deployment required for hotfix pipeline.",
        "acknowledged_risks": ["expedited_release"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "override"
    assert runs_db[TEST_RUN_ID]["status"] == "fixed"


def test_api_get_certificate():
    resp = client.get(f"/runs/{TEST_RUN_ID}/certificate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["certificate_id"].startswith("CERT-OMNI-")
    assert data["status"] == "CERTIFIED_FIXED"
    assert len(data["cryptographic_seal"]) == 64


def test_api_get_certificate_markdown():
    resp = client.get(f"/runs/{TEST_RUN_ID}/certificate/markdown")
    assert resp.status_code == 200
    data = resp.json()
    assert "markdown" in data
    assert "# 🛡️ Certificate of Visual Remediation" in data["markdown"]


def test_api_milestones_reflects_week_3_day_4():
    resp = client.get("/api/milestones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["week_3_day_4_deliverables"] == "completed"
    assert "75%" in data["week_3_progress"]
