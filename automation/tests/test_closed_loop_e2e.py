"""
End-to-End Closed-Loop Verification Test Suite for OmniSight Week 3.
Validates complete autonomous lifecycle:
Inspection -> VLM Audit -> Security Patch Validation -> Retest Proof -> PR Generation -> Webhook Merge -> Forensic Bundling.
"""

from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app, runs_db
from automation.backend_client import BackendClient
from automation.orchestrator import Orchestrator
from automation.schemas import RetestStatus
from automation.vlm_adapter import MockVLMAdapter


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def integrated_backend_client(test_client: TestClient):
    return BackendClient(base_url="http://testserver", test_client=test_client)


def test_complete_week3_closed_loop_workflow(
    integrated_backend_client: BackendClient,
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    # Generate valid PNG baseline screenshots using Pillow
    fake_desktop_shot = tmp_path / "desktop_1440x900_home.png"
    Image.new("RGB", (1440, 900), (240, 240, 240)).save(fake_desktop_shot, "PNG")

    fake_mobile_shot = tmp_path / "mobile_375x667_checkout.png"
    Image.new("RGB", (375, 667), (250, 250, 250)).save(fake_mobile_shot, "PNG")

    fake_dom = tmp_path / "desktop_1440x900_home_dom.json"
    fake_dom.write_text('{"elements": [{"tag": "h1", "test_id": "hero-title", "box": {"x": 10, "y": 10, "width": 200, "height": 50}}]}')

    def mock_journey(*args, **kwargs):
        evidence = kwargs.get("evidence")
        return {
            "run_id": evidence.run_id if evidence else "run-mock-journey",
            "viewports_evaluated": ["desktop_1440x900", "mobile_375x667"],
            "screenshots": [str(fake_desktop_shot), str(fake_mobile_shot)],
            "dom_snapshots": [str(fake_dom)],
            "steps_completed": ["home", "cart", "checkout"],
        }

    monkeypatch.setattr(
        "automation.orchestrator.run_visual_audit_journey", mock_journey
    )

    # 1. Initialize Orchestrator with auto-PR and backend sync enabled
    orchestrator = Orchestrator(
        vlm_adapter=MockVLMAdapter(),
        backend_client=integrated_backend_client,
        sync_backend=True,
        auto_create_pr=True,
    )

    # 2. Run full autonomous remediation loop with forensic bundling
    result = orchestrator.run_full_remediation_loop(
        target_url="http://127.0.0.1:5173",
        viewports=["desktop_1440x900", "mobile_375x667"],
        auto_retest=True,
        auto_create_pr=True,
        bundle_forensics=True,
    )

    run_id = result["run_id"]
    assert result["status"] == "pr_opened"
    assert len(result["findings"]) > 0
    assert result["proposed_patch"] is not None
    assert result["retest_verification"]["status"] == RetestStatus.FIXED.value
    assert result["pr_url"] is not None
    assert "github.com" in result["pr_url"]

    # 3. Verify forensic bundle generation
    assert result["forensic_bundle"] is not None
    bundle = result["forensic_bundle"]
    assert bundle["bundle_name"] == f"forensic_bundle_{run_id}.zip"
    assert len(bundle["sha256"]) == 64
    assert Path(bundle["bundle_file"]).exists()

    # 4. Verify backend database state synchronization
    run_entry = runs_db.get(run_id)
    assert run_entry is not None
    assert run_entry["status"] == "pr_opened"
    assert run_entry["pr_url"] == result["pr_url"]
    assert run_entry["retest_outcome"]["passed"] is True

    # 5. Simulate GitHub review and merge webhook ingestion
    webhook_payload = {
        "action": "closed",
        "pull_request": {
            "number": 42,
            "html_url": result["pr_url"],
            "merged": True,
            "head": {"ref": f"omnisight-fix-{run_id}"},
            "labels": [{"name": "omnisight"}, {"name": "automated-fix"}],
        },
    }
    webhook_res = test_client.post("/webhook/github/pull-request", json=webhook_payload)
    assert webhook_res.status_code == 200
    assert webhook_res.json()["matched_run_id"] == run_id

    # 6. Verify run transitioned to fixed status after PR merge
    updated_run = runs_db.get(run_id)
    assert updated_run["status"] == "fixed"
    assert updated_run["merged"] is True

    # 7. Verify forensic download endpoint serves the archive
    download_res = test_client.get(f"/runs/{run_id}/forensics/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/zip"
    assert len(download_res.content) > 0
