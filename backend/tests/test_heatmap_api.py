from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app, runs_db


@pytest.fixture
def client():
    return TestClient(app)


def test_heatmap_and_annotated_endpoints(client, tmp_path, monkeypatch):
    from app.services.spatial_service import spatial_service
    monkeypatch.setattr(spatial_service, "artifacts_dir", tmp_path)

    run_id = "run-test-heatmap-123"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-11-07T00:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "findings": [{"id": "f1", "bounding_box": [10, 10, 100, 80]}],
    }

    shots_dir = tmp_path / "runs" / run_id / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy before and after images
    before_img = Image.new("RGB", (200, 200), (255, 0, 0))
    after_img = Image.new("RGB", (200, 200), (0, 255, 0))
    before_img.save(shots_dir / "desktop_1440x900_home.png", "PNG")
    after_img.save(shots_dir / "desktop_1440x900_home_after.png", "PNG")

    # 1. Test heatmap endpoint
    res_heatmap = client.get(f"/runs/{run_id}/heatmap?viewport=desktop_1440x900&page=home")
    assert res_heatmap.status_code == 200
    assert res_heatmap.headers["content-type"] == "image/png"

    # 2. Test annotated endpoint
    res_annotated = client.get(f"/runs/{run_id}/annotated?viewport=desktop_1440x900&page=home")
    assert res_annotated.status_code == 200
    assert res_annotated.headers["content-type"] == "image/png"


def test_heatmap_uses_retest_after_screenshot(client, tmp_path, monkeypatch):
    # Real runs save the post-fix capture in runs/<id>/retest/, not screenshots/.
    from app.services.spatial_service import spatial_service
    monkeypatch.setattr(spatial_service, "artifacts_dir", tmp_path)

    run_id = "run-test-heatmap-retest"
    runs_db[run_id] = {"run_id": run_id, "start_time": "2026-11-07T00:00:00Z",
                       "target": "http://localhost:5173", "status": "fixed", "findings": []}
    shots_dir = tmp_path / "runs" / run_id / "screenshots"
    retest_dir = tmp_path / "runs" / run_id / "retest"
    shots_dir.mkdir(parents=True)
    retest_dir.mkdir(parents=True)
    Image.new("RGB", (200, 200), (255, 0, 0)).save(shots_dir / "desktop_1440x900_checkout.png", "PNG")
    Image.new("RGB", (200, 200), (0, 255, 0)).save(retest_dir / "desktop_1440x900_checkout_after.png", "PNG")

    res = client.get(f"/runs/{run_id}/heatmap?viewport=desktop_1440x900&page=checkout")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
