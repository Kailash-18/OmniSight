"""
Automated API tests for OmniSight Forensic Endpoints.
Tests POST /runs/{run_id}/forensics, GET /runs/{run_id}/forensics, and GET /runs/{run_id}/forensics/download.
"""

from pathlib import Path
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app, runs_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def staged_run_id(client: TestClient):
    """Creates a sample run in runs_db for forensic testing."""
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main"})
    assert res.status_code == 202
    run_id = res.json()["run_id"]

    # Mark as fixed with sample patch
    client.put(
        f"/runs/{run_id}",
        json={
            "status": "fixed",
            "findings": [
                {
                    "id": "defect-promo",
                    "category": "element_obstruction",
                    "severity": "critical",
                    "description": "Promo banner blocks button",
                    "viewport": "mobile_375x667",
                    "confidence": 0.98,
                    "suggested_change": "remove position absolute",
                    "rationale": "Overlaps CTA",
                    "status": "remediated"
                }
            ],
            "retest_outcome": {
                "passed": True,
                "visual_diff_score": 0.04,
                "retest_viewport": "mobile_375x667",
                "notes": "Verified in sandbox"
            }
        }
    )
    return run_id


def test_post_forensics_bundle(client: TestClient, staged_run_id: str):
    res = client.post(f"/runs/{staged_run_id}/forensics")
    assert res.status_code == 200
    data = res.json()

    assert data["run_id"] == staged_run_id
    assert data["bundle_name"] == f"forensic_bundle_{staged_run_id}.zip"
    assert len(data["sha256_checksum"]) == 64
    assert data["artifact_count"] >= 3
    assert data["size_bytes"] > 0
    assert data["download_url"] == f"/runs/{staged_run_id}/forensics/download"
    assert "manifest" in data
    assert data["manifest"]["run_id"] == staged_run_id


def test_get_forensics_bundle(client: TestClient, staged_run_id: str):
    res = client.get(f"/runs/{staged_run_id}/forensics")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == staged_run_id
    assert len(data["sha256_checksum"]) == 64


def test_download_forensics_bundle(client: TestClient, staged_run_id: str, tmp_path: Path):
    res = client.get(f"/runs/{staged_run_id}/forensics/download")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert f"forensic_bundle_{staged_run_id}.zip" in res.headers["content-disposition"]

    # Verify downloaded ZIP content
    dest = tmp_path / "downloaded.zip"
    dest.write_bytes(res.content)
    with zipfile.ZipFile(dest, "r") as zf:
        names = zf.namelist()
        assert any(n.endswith("checksums.sha256") for n in names)
        assert any(n.endswith("forensic_manifest.json") for n in names)


def test_forensics_unknown_run_returns_404(client: TestClient):
    res = client.get("/runs/unknown-run-99999/forensics")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_forensics_recompiles_when_screenshots_arrive_after_initial_check(client: TestClient, tmp_path: Path, monkeypatch):
    from PIL import Image
    from app.core.config import settings

    monkeypatch.setattr(settings, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(settings, "ALLOWED_TARGET_HOSTS", ["*"])

    res = client.post("/webhook/build", json={"target_url": "https://example.com", "branch": "main"})
    assert res.status_code == 202
    run_id = res.json()["run_id"]

    # First query while run is still running (before screenshots exist)
    early = client.get(f"/runs/{run_id}/forensics")
    assert early.status_code == 200

    # Screenshots are subsequently saved by the browser runner and run finishes
    shots_dir = tmp_path / "runs" / run_id / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    shot_file = shots_dir / "desktop_1440x900_home.png"
    Image.new("RGB", (120, 80), (20, 90, 180)).save(shot_file, "PNG")

    client.put(
        f"/runs/{run_id}",
        json={
            "status": "fixed",
            "evidence_paths": {"screenshots": [str(shot_file)]},
        },
    )

    dl = client.get(f"/runs/{run_id}/forensics/download")
    assert dl.status_code == 200
    dest = tmp_path / "final.zip"
    dest.write_bytes(dl.content)
    with zipfile.ZipFile(dest, "r") as zf:
        names = zf.namelist()
        assert f"{run_id}/screenshots/desktop_1440x900_home.png" in names
