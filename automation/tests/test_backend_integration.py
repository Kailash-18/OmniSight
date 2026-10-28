"""
Integration Tests for Backend Gateway Client and Closed-Loop Orchestrator Coordination.
Validates Week 2 Day 3 Integration Deliverables.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_root = Path(__file__).resolve().parent.parent.parent / "backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app

from automation.backend_client import BackendClient
from automation.orchestrator import AgentState, Orchestrator
from automation.vlm_adapter import MockVLMAdapter


@pytest.fixture
def api_test_client():
    return TestClient(app)


@pytest.fixture
def backend_client(api_test_client):
    return BackendClient(base_url="http://127.0.0.1:8000", test_client=api_test_client)


def test_backend_client_health_check(backend_client: BackendClient):
    assert backend_client.check_health() is True


def test_backend_client_milestones(backend_client: BackendClient):
    milestones = backend_client.get_milestones()
    assert milestones is not None
    assert milestones["week_1_foundation"] == "completed"
    assert milestones["week_2_action_engine"] == "completed"
    assert milestones["week_2_day_3_integration"] == "completed"
    assert "allowed_targets" in milestones
    assert "allowed_patch_files" in milestones


def test_backend_client_register_and_get_run(backend_client: BackendClient):
    run_id = backend_client.register_run(
        target_url="http://127.0.0.1:5173",
        scenario="checkout_flow",
        viewports=["desktop_1440x900", "mobile_375x667"],
    )
    assert run_id is not None
    assert run_id.startswith("run-")

    details = backend_client.get_run_details(run_id)
    assert details is not None
    assert details["run_id"] == run_id
    assert details["status"] == "running"
    assert details["target"] == "http://127.0.0.1:5173"


def test_backend_client_update_run_lifecycle(backend_client: BackendClient):
    run_id = backend_client.register_run("http://127.0.0.1:5173")
    assert run_id is not None

    ok = backend_client.update_run_state(
        run_id=run_id,
        status="audited",
        steps=["navigate_home", "add_product_mug", "navigate_to_cart"],
        findings=[
            {
                "id": "defect-1",
                "category": "element_clipping",
                "severity": "high",
                "description": "Button clipped",
                "viewport": "mobile_375x667",
                "confidence": 0.95,
                "suggested_change": "width: 100%",
                "rationale": "Bounding box overflow",
                "status": "detected",
            }
        ],
    )
    assert ok is True

    details = backend_client.get_run_details(run_id)
    assert details is not None
    assert details["status"] == "audited"
    assert len(details["findings"]) == 1
    assert details["findings"][0]["id"] == "defect-1"


def test_backend_client_action_engine_parsing(backend_client: BackendClient):
    raw_vlm = """
Here is the visual audit:
```json
{
  "findings": [
    {
      "id": "defect-submit-cover",
      "category": "element_obstruction",
      "severity": "critical",
      "description": "Submit button obstructed by promo banner",
      "viewport": "all",
      "confidence": "96%",
      "suggested_change": "position: static",
      "rationale": "Promo banner covers submit button",
      "status": "detected"
    }
  ],
  "proposed_patch": {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-.promo-banner { position: absolute; }\\n+.promo-banner { position: static; }"
  }
}
```
"""
    parsed = backend_client.parse_with_action_engine(raw_vlm)
    assert parsed is not None
    assert parsed["is_valid"] is True
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["id"] == "defect-submit-cover"
    assert parsed["validation_status"] is True


def test_backend_client_submit_patch(backend_client: BackendClient):
    run_id = backend_client.register_run("http://127.0.0.1:5173")
    assert run_id is not None

    submit_res = backend_client.submit_patch(
        run_id=run_id,
        target_file="app-under-test/src/styles/defects.css",
        diff="-.banner { width: 500px; }\n+.banner { width: 100%; }",
        file_content=".banner { width: 100%; }",
    )
    assert submit_res is not None
    assert submit_res["status"] == "success"
    assert submit_res["validation_status"] is True

    # Security rejection test
    bad_res = backend_client.submit_patch(
        run_id=run_id,
        target_file="backend/app/main.py",
        diff="malicious edit",
        file_content="evil",
    )
    assert bad_res is None


def test_backend_client_offline_graceful_fallback():
    offline_client = BackendClient(base_url="http://127.0.0.1:59999", timeout=0.5)
    assert offline_client.check_health() is False
    assert offline_client.register_run("http://127.0.0.1:5173") is None
    assert offline_client.get_run_details("run-nonexistent") is None
    assert offline_client.update_run_state("run-123", status="running") is False


def test_orchestrator_initialization_with_backend_client(backend_client: BackendClient):
    orchestrator = Orchestrator(
        vlm_adapter=MockVLMAdapter(),
        backend_client=backend_client,
        sync_backend=True,
    )
    assert orchestrator.sync_backend is True
    assert orchestrator.backend_client is backend_client
    assert orchestrator.state == AgentState.IDLE


def test_orchestrator_closed_loop_backend_sync(
    backend_client: BackendClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from PIL import Image

    # Create dummy screenshot for retest
    dummy_shot = tmp_path / "mobile_375x667_checkout.png"
    img = Image.new("RGB", (375, 667), color=(255, 255, 255))
    img.save(dummy_shot)

    # Mock journey runner
    def mock_journey(*args, **kwargs):
        return {
            "run_id": "run-sync-test",
            "target_url": "http://127.0.0.1:5173",
            "viewports_evaluated": ["mobile_375x667"],
            "screenshots": [str(dummy_shot)],
            "dom_snapshots": [],
            "steps_completed": ["navigate_home", "continue_to_checkout"],
        }

    monkeypatch.setattr(
        "automation.orchestrator.run_visual_audit_journey", mock_journey
    )

    orchestrator = Orchestrator(
        vlm_adapter=MockVLMAdapter(),
        backend_client=backend_client,
        sync_backend=True,
    )

    result = orchestrator.run_full_remediation_loop(
        target_url="http://127.0.0.1:5173",
        auto_retest=True,
    )

    assert result["status"] == "fixed"
    run_id = result["run_id"]

    # Verify backend received the synchronized state
    backend_details = backend_client.get_run_details(run_id)
    assert backend_details is not None
    assert backend_details["status"] == "fixed"
    assert len(backend_details["findings"]) > 0
    assert backend_details["patch"] is not None
    assert backend_details["patch"]["validation_status"] is True


def test_backend_client_register_run_with_scenario(backend_client: BackendClient):
    run_id = backend_client.register_run(
        target_url="http://127.0.0.1:5173",
        scenario="custom_checkout_scenario",
        viewports=["desktop_1440x900"],
    )
    assert run_id is not None
    details = backend_client.get_run_details(run_id)
    assert details is not None
    assert details["target"] == "http://127.0.0.1:5173"


def test_backend_client_offline_circuit_breaker():
    client = BackendClient(base_url="http://127.0.0.1:59998", timeout=0.1)
    # First health probe sets _is_available to False
    assert client.check_health() is False
    assert client.is_available is False

    # Subsequent request fails fast immediately without attempting network
    assert client._request("GET", "/health") is None


def test_cli_scenario_argument(monkeypatch: pytest.MonkeyPatch):
    from automation import cli

    executed = {}

    def mock_run_full_remediation_loop(self, **kwargs):
        executed.update(kwargs)
        return {"run_id": "test-cli-run", "status": "fixed", "findings": []}

    monkeypatch.setattr(
        "automation.orchestrator.Orchestrator.run_full_remediation_loop",
        mock_run_full_remediation_loop,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "--scenario", "promo_banner_journey", "--json-output"],
    )

    exit_code = cli.main()
    assert exit_code == 0
    assert executed.get("scenario") == "promo_banner_journey"


def test_orchestrator_no_retest_returns_audited_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from PIL import Image

    dummy_shot = tmp_path / "mobile_375x667_checkout.png"
    img = Image.new("RGB", (375, 667), color=(255, 255, 255))
    img.save(dummy_shot)

    def mock_journey(*args, **kwargs):
        return {
            "run_id": "run-no-retest",
            "target_url": "http://127.0.0.1:5173",
            "viewports_evaluated": ["mobile_375x667"],
            "screenshots": [str(dummy_shot)],
            "dom_snapshots": [],
            "steps_completed": ["navigate_home", "checkout"],
        }

    monkeypatch.setattr(
        "automation.orchestrator.run_visual_audit_journey", mock_journey
    )

    orchestrator = Orchestrator(vlm_adapter=MockVLMAdapter())
    result = orchestrator.run_full_remediation_loop(
        target_url="http://127.0.0.1:5173",
        auto_retest=False,
    )

    assert result["status"] == "audited"
    assert orchestrator.state == AgentState.AUDITING
    assert result.get("retest_verification") is None
    assert len(result["findings"]) > 0


def test_cli_no_retest_argument(monkeypatch: pytest.MonkeyPatch):
    from automation import cli

    executed = {}

    def mock_run_full_remediation_loop(self, **kwargs):
        executed.update(kwargs)
        return {
            "run_id": "test-cli-no-retest",
            "status": "audited",
            "findings": [{"category": "element_clipping", "severity": "high", "description": "clip", "viewport": "mobile_375x667", "suggested_change": "fix"}],
            "retest_verification": None,
        }

    monkeypatch.setattr(
        "automation.orchestrator.Orchestrator.run_full_remediation_loop",
        mock_run_full_remediation_loop,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "--no-retest", "--json-output"],
    )

    exit_code = cli.main()
    assert exit_code == 0
    assert executed.get("auto_retest") is False


def test_backend_client_create_pr_mock(backend_client: BackendClient, monkeypatch: pytest.MonkeyPatch):
    """Verify BackendClient create_pull_request triggers PR creation on backend."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)

    run_id = backend_client.register_run("http://127.0.0.1:5173")
    assert run_id is not None

    # First submit a valid patch so the run has patch metadata
    patch_res = backend_client.submit_patch(
        run_id=run_id,
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn { width: 500px; }\n+.btn { width: 100%; }",
        file_content=".btn { width: 100%; }",
        pr_title="Fix button clipping",
        pr_body="Automated repair."
    )
    assert patch_res is not None
    assert patch_res["status"] == "success"

    pr_res = backend_client.create_pull_request(
        run_id=run_id,
        pr_title="fix(ui): responsive button repair",
        labels=["omnisight", "test-pr"]
    )
    assert pr_res is not None
    assert pr_res["status"] == "success"
    assert "pr_url" in pr_res
    assert "github.com" in pr_res["pr_url"]

    details = backend_client.get_run_details(run_id)
    assert details["status"] == "pr_opened"
    assert details["pr_url"] == pr_res["pr_url"]



