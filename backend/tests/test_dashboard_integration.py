"""
End-to-End integration tests for Dashboard and Diagnostic APIs.
Verifies target host configuration, risk scoring, heatmap diagnostics,
forensic verification alias, and run telemetry summary endpoints.
"""

from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app, runs_db
from app.services.forensics_service import compile_forensic_bundle


@pytest.fixture
def client():
    return TestClient(app)


def test_target_hosts_endpoint(client: TestClient):
    """Ensure dashboard can discover allowed audit hostnames and wildcards."""
    res = client.get("/config/target-hosts")
    assert res.status_code == 200
    data = res.json()
    assert "allowed_hosts" in data
    assert any("flipkart.com" in host for host in data["allowed_hosts"])


def test_dashboard_run_detail_includes_risk_metrics(client: TestClient):
    """Ensure run detail payload includes confidence-aware remediation risk evaluation."""
    run_id = "test-dashboard-risk-run"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-11-07T00:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "--- a/defects.css\n+++ b/defects.css\n@@ -1,3 +1,3 @@\n-color: red;\n+color: blue;\n",
            "explanation": "Fix contrast",
            "validation_status": True,
        },
        "findings": [
            {
                "id": "find-1",
                "category": "accessibility",
                "confidence": 0.95,
                "description": "Button contrast issue",
                "severity": "high",
                "viewport": "desktop_1440x900",
                "suggested_change": "Update contrast ratio",
                "rationale": "WCAG 2.1 AA compliance",
            }
        ],
    }

    res = client.get(f"/runs/{run_id}")
    assert res.status_code == 200
    data = res.json()
    assert "risk_score" in data
    assert "risk_verdict" in data
    assert isinstance(data["risk_score"], float)
    assert data["risk_verdict"] in ["auto_pr_allowed", "requires_human_review"]


def test_dashboard_verify_bundle_alias(client: TestClient, tmp_path: Path, monkeypatch):
    """Ensure dashboard's /verify-bundle alias properly validates forensic bundles."""
    run_id = "test-dashboard-verify-run"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifact.txt").write_text("Integrity content", encoding="utf-8")

    compile_forensic_bundle(
        run_id=run_id,
        run_data={"run_id": run_id, "status": "fixed"},
        artifacts_base_dir=tmp_path,
    )

    from app.services.forensics_service import verify_forensic_bundle_integrity
    monkeypatch.setattr(
        "app.main.verify_forensic_bundle_integrity",
        lambda rid: verify_forensic_bundle_integrity(rid, artifacts_base_dir=tmp_path),
    )

    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-11-07T00:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
    }

    res = client.get(f"/runs/{run_id}/verify-bundle")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["verified_files_count"] >= 1
    assert data["discrepancies"] == []


def test_dashboard_spatial_heatmaps_and_annotations(client: TestClient, tmp_path: Path, monkeypatch):
    """Ensure spatial diagnostic heatmap and annotation endpoints stream image bytes."""
    from app.services.spatial_service import spatial_service
    monkeypatch.setattr(spatial_service, "artifacts_dir", tmp_path)

    run_id = "test-spatial-run"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-11-07T00:00:00Z",
        "target": "https://www.flipkart.com",
        "status": "fixed",
        "findings": [{"id": "box-1", "bounding_box": [15, 20, 80, 60]}],
    }

    shots_dir = tmp_path / "runs" / run_id / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    before_img = Image.new("RGB", (100, 100), (255, 0, 0))
    after_img = Image.new("RGB", (100, 100), (0, 255, 0))
    before_img.save(shots_dir / "desktop_1440x900_home.png", "PNG")
    after_img.save(shots_dir / "desktop_1440x900_home_after.png", "PNG")

    r1 = client.get(f"/runs/{run_id}/heatmap?viewport=desktop_1440x900&page=home")
    assert r1.status_code == 200
    assert r1.headers["content-type"] == "image/png"

    r2 = client.get(f"/runs/{run_id}/annotated?viewport=desktop_1440x900&page=home")
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "image/png"


def test_dashboard_metrics_summary(client: TestClient):
    """Ensure telemetry summary returns metrics for dashboard analytics."""
    res = client.get("/runs/metrics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_runs" in data
    assert "success_rate_percentage" in data
    assert "average_diff_reduction" in data
