"""
Integration & API Endpoint Tests for OmniSight Backend Gateway (Member 1).
Verifies build webhook, manual trigger, run queries, patch submission, and SSRF guardrails.
"""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_build_webhook_accepted(client: TestClient):
    payload = {
        "target_url": "http://localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow",
        "commit_sha": "56e42d7f",
        "event_id": "evt-1001"
    }
    response = client.post("/webhook/build", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "queued"
    assert "accepted and queued" in data["message"]


def test_build_webhook_rejects_disallowed_target_host(client: TestClient):
    payload = {
        "target_url": "http://malicious-external-site.com/exploit",
        "branch": "main",
        "scenario": "checkout_flow"
    }
    response = client.post("/webhook/build", json=payload)
    assert response.status_code == 400
    assert "not in allowed target hosts" in response.json()["detail"]


def test_build_webhook_auto_prefixes_scheme(client: TestClient):
    payload = {
        "target_url": "localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow"
    }
    response = client.post("/webhook/build", json=payload)
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    detail = client.get(f"/runs/{run_id}").json()
    assert detail["target"].startswith("http://")


def test_build_webhook_rejects_disallowed_scheme(client: TestClient):
    payload = {
        "target_url": "ftp://localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow"
    }
    response = client.post("/webhook/build", json=payload)
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_list_runs_filtering_and_limit(client: TestClient):
    # Create two runs
    r1 = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"}).json()["run_id"]
    r2 = client.post("/runs", json={"target_url": "http://localhost:5173", "scenario": "checkout_flow"}).json()["run_id"]

    # Filter by queued status
    queued_runs = client.get("/runs?status_filter=queued").json()
    assert all(r["status"] == "queued" for r in queued_runs)

    # Filter by running status
    running_runs = client.get("/runs?status_filter=running").json()
    assert all(r["status"] == "running" for r in running_runs)

    # Test limit
    limited = client.get("/runs?limit=1").json()
    assert len(limited) == 1



def test_list_and_get_run_details(client: TestClient):
    # Create a run via webhook
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    # List runs
    list_res = client.get("/runs")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert len(runs) >= 1
    assert any(r["run_id"] == run_id for r in runs)

    # Get details
    detail_res = client.get(f"/runs/{run_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["run_id"] == run_id
    assert detail["status"] == "queued"


def test_get_unknown_run_returns_404(client: TestClient):
    res = client.get("/runs/run-nonexistent-999")
    assert res.status_code == 404


def test_update_run_record(client: TestClient):
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    update_payload = {
        "status": "audited",
        "steps": ["navigate_home", "open_cart", "navigate_checkout"],
        "retry_count": 1
    }
    put_res = client.put(f"/runs/{run_id}", json=update_payload)
    assert put_res.status_code == 200

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "audited"
    assert detail["steps"] == ["navigate_home", "open_cart", "navigate_checkout"]
    assert detail["retry_count"] == 1


def test_action_engine_parse_endpoint(client: TestClient):
    raw_vlm = """
{
  "findings": [
    {
      "id": "defect-1",
      "category": "element_clipping",
      "severity": "high",
      "description": "Button clipped",
      "viewport": "mobile_375x667",
      "confidence": 0.95,
      "suggested_change": "width: 100%",
      "rationale": "Clipped"
    }
  ],
  "summary": "Detected clipping defect",
  "proposed_patch": {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-.clipped { width: 500px; }\n+.clipped { width: 100%; }",
    "explanation": "Fix button"
  }
}
"""
    res = client.post("/action-engine/parse", json={"raw_vlm_output": raw_vlm})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert len(data["findings"]) == 1
    assert data["validation_status"] is True


def test_submit_patch_rejected_on_allowlist_violation(client: TestClient):
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    bad_patch = {
        "target_file": "backend/app/main.py",
        "diff": "-# old\n+# new",
        "file_content": "malicious content",
        "pr_title": "Rogue patch",
        "pr_body": "Test"
    }
    submit_res = client.post(f"/runs/{run_id}/submit-patch", json=bad_patch)
    assert submit_res.status_code == 400
    assert "not in the approved allowlist" in submit_res.json()["detail"]

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "patch_rejected"


def test_submit_valid_patch_opens_pr(client: TestClient):
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    valid_patch = {
        "target_file": "app-under-test/src/styles/defects.css",
        "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
        "file_content": ".btn { width: 100%; }",
        "pr_title": "OmniSight Auto-repair for checkout button clipping",
        "pr_body": "Verified fix for mobile checkout button clipping."
    }
    submit_res = client.post(f"/runs/{run_id}/submit-patch", json=valid_patch)
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["status"] == "success"
    assert "pr_url" in data
    assert "github.com" in data["pr_url"]

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "pr_opened"
    assert detail["pr_url"] == data["pr_url"]
