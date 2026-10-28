"""
Integration & API Endpoint Tests for OmniSight Backend Gateway (Member 1).
Verifies build webhook, manual trigger, run queries, patch submission, and SSRF guardrails.
"""

from fastapi.testclient import TestClient
from app.main import runs_db


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
        "evidence_paths": {"screenshots": ["artifacts/home.png"]},
        "retry_count": 1
    }
    put_res = client.put(f"/runs/{run_id}", json=update_payload)
    assert put_res.status_code == 200

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "audited"
    assert detail["steps"] == ["navigate_home", "open_cart", "navigate_checkout"]
    assert detail["retry_count"] == 1
    assert "screenshots" in detail["evidence_paths"]
    assert "before_screenshots" in detail["evidence_paths"]
    assert detail["evidence_paths"]["before_screenshots"] == ["artifacts/home.png"]


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


def test_cors_headers_present(client: TestClient):
    response = client.get("/health", headers={"origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")


def test_get_milestones_status(client: TestClient):
    response = client.get("/api/milestones")
    assert response.status_code == 200
    data = response.json()
    assert data["foundation_scaffolding"] == "completed"
    assert data["action_engine_and_security"] == "completed"
    assert data["system_integration"] == "completed"
    assert data["remediation_mttr_and_checksum_verification"] == "completed"
    assert data["telemetry_and_compliance_export"] == "completed"
    assert data["backend_tests_passed"] >= 130
    assert "allowed_targets" in data
    assert "allowed_patch_files" in data





def test_process_run_vlm_output_convenience_endpoint(client: TestClient):
    raw_vlm = """
{
  "findings": [
    {
      "id": "defect-convenience",
      "category": "contrast_issue",
      "severity": "medium",
      "description": "Low contrast ratio on footer text",
      "viewport": "desktop_1440x900",
      "confidence": 0.89,
      "suggested_change": "color: #111827",
      "rationale": "Contrast ratio below WCAG AA"
    }
  ],
  "summary": "Detected contrast defect",
  "proposed_patch": {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-footer { color: #ccc; }\n+footer { color: #111827; }",
    "explanation": "Fix contrast ratio"
  }
}
"""
    run_res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = run_res.json()["run_id"]

    parse_res = client.post(f"/runs/{run_id}/process-vlm-output", json={"raw_vlm_output": raw_vlm})
    assert parse_res.status_code == 200
    assert parse_res.json()["is_valid"] is True

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "audited"
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["id"] == "defect-convenience"


def test_package_schema_and_service_exports():
    """Verify clean top-level package namespace exports for schemas and services."""
    import app.schemas as schemas
    import app.services as services

    assert hasattr(schemas, "FindingSchema")
    assert hasattr(schemas, "PatchObject")
    assert hasattr(schemas, "RunStatus")
    assert hasattr(schemas, "BuildWebhookPayload")
    assert hasattr(services, "validate_patch")
    assert hasattr(services, "action_engine")
    assert hasattr(services, "create_pull_request_for_fix")


def test_update_run_upserts_if_not_present(client: TestClient):
    unregistered_run_id = f"run-worker-standalone-{uuid_hex()}"
    update_payload = {
        "status": "audited",
        "steps": ["step_one", "step_two"],
        "retry_count": 0
    }
    put_res = client.put(f"/runs/{unregistered_run_id}", json=update_payload)
    assert put_res.status_code == 200

    detail = client.get(f"/runs/{unregistered_run_id}").json()
    assert detail["status"] == "audited"
    assert detail["steps"] == ["step_one", "step_two"]


def test_webhook_run_id_uniqueness(client: TestClient):
    payload = {"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"}
    r1 = client.post("/webhook/build", json=payload).json()["run_id"]
    r2 = client.post("/webhook/build", json=payload).json()["run_id"]
    assert r1 != r2


def test_submit_patch_rejects_malicious_file_content(client: TestClient):
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    submit_payload = {
        "target_file": "app-under-test/src/styles/defects.css",
        "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
        "file_content": ".btn { width: 100%; } <script>evil()</script>",
        "pr_title": "fix(ui): inject script",
        "pr_body": "Dangerous payload"
    }
    submit_res = client.post(f"/runs/{run_id}/submit-patch", json=submit_payload)
    assert submit_res.status_code == 400
    assert "Malicious script injection" in submit_res.json()["detail"]


def uuid_hex():
    import uuid
    return uuid.uuid4().hex[:6]


def test_submit_patch_stores_normalized_target_path(client: TestClient):
    """Verify submit-patch normalizes leading ./ and git prefixes in stored patch."""
    res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = res.json()["run_id"]

    submit_payload = {
        "target_file": "./app-under-test/src/styles/defects.css",
        "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
        "file_content": ".btn { width: 100%; }",
        "pr_title": "fix(ui): normalized prefix test",
        "pr_body": "Verification test"
    }
    submit_res = client.post(f"/runs/{run_id}/submit-patch", json=submit_payload)
    assert submit_res.status_code == 200

    detail = client.get(f"/runs/{run_id}").json()
    assert detail["patch"]["target_file"] == "app-under-test/src/styles/defects.css"


def test_run_details_preserves_finding_rationale(client: TestClient):
    """Verify finding rationale is preserved in full forensic run detail responses."""
    run_res = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "checkout_flow"})
    run_id = run_res.json()["run_id"]

    update_payload = {
        "findings": [
            {
                "id": "defect-checkout-obstructed",
                "category": "element_obstruction",
                "severity": "high",
                "description": "Submit CTA obstructed",
                "viewport": "mobile_375x667",
                "confidence": 0.98,
                "suggested_change": "position: static;",
                "rationale": "Promo banner completely covers submit CTA on mobile viewport",
                "status": "detected"
            }
        ]
    }
    client.put(f"/runs/{run_id}", json=update_payload)
    detail = client.get(f"/runs/{run_id}").json()
    assert len(detail["findings"]) == 1
    assert detail["findings"][0]["rationale"] == "Promo banner completely covers submit CTA on mobile viewport"


def test_runs_reverse_chronological_ordering(client: TestClient):
    """Verify GET /runs returns records in reverse chronological order by start_time."""
    r1 = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "flow_1"}).json()["run_id"]
    r2 = client.post("/webhook/build", json={"target_url": "http://localhost:5173", "branch": "main", "scenario": "flow_2"}).json()["run_id"]
    runs = client.get("/runs").json()
    assert len(runs) >= 2
    # Verify newest run appears first
    assert runs[0]["run_id"] == r2


def test_pr_markdown_description_format():
    """Verify PR body markdown generation includes defect details and evidence tables."""
    from app.services.github_service import generate_pr_markdown_description

    body = generate_pr_markdown_description(
        defect_title="Button Clipping",
        viewport="mobile_375x667",
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn { width: 500px; }\n+.btn { width: 100%; }"
    )
    assert "OmniSight Automated Visual QA Fix" in body
    assert "Button Clipping" in body
    assert "mobile_375x667" in body
    assert "Visual Evidence" in body


def test_openapi_spec_tags_and_endpoint_metadata(client: TestClient):
    """Verify OpenAPI 3.0 schema generation includes proper tags, metadata, and path models."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    assert "openapi" in spec
    assert "paths" in spec
    assert "/webhook/build" in spec["paths"]
    assert "CI/CD Webhook" in spec["paths"]["/webhook/build"]["post"]["tags"]
    assert "/runs" in spec["paths"]
    assert "Audit Runs" in spec["paths"]["/runs"]["get"]["tags"]
    assert "/action-engine/parse" in spec["paths"]
    assert "Action Engine" in spec["paths"]["/action-engine/parse"]["post"]["tags"]


def test_github_webhook_pr_merged_updates_run_to_fixed(client: TestClient):
    """Verify GitHub webhook with merged PR transitions matching run status to FIXED."""
    run_id = "run-hook-test-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-24T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "pr_opened",
        "steps": ["patch_submitted"],
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/101",
        "findings": []
    }

    payload = {
        "action": "closed",
        "number": 101,
        "pull_request": {
            "html_url": "https://github.com/Kailash-18/OmniSight/pull/101",
            "number": 101,
            "state": "closed",
            "merged": True,
            "head_ref": f"omnisight-fix-{run_id}"
        }
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["matched_run_id"] == run_id
    assert runs_db[run_id]["status"] == "fixed"
    assert "github_pr_merged" in runs_db[run_id]["steps"]


def test_github_webhook_pr_closed_unmerged_updates_run_to_needs_review(client: TestClient):
    """Verify GitHub webhook with closed unmerged PR transitions run status to NEEDS_REVIEW."""
    run_id = "run-hook-test-2"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-24T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "pr_opened",
        "steps": ["patch_submitted"],
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/102",
        "findings": []
    }

    payload = {
        "action": "closed",
        "number": 102,
        "pull_request": {
            "html_url": "https://github.com/Kailash-18/OmniSight/pull/102",
            "number": 102,
            "state": "closed",
            "merged": False,
            "head_ref": f"omnisight-fix-{run_id}"
        }
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    assert runs_db[run_id]["status"] == "needs_review"
    assert "github_pr_closed_unmerged" in runs_db[run_id]["steps"]


def test_github_webhook_unmatched_run_processed_gracefully(client: TestClient):
    """Verify GitHub webhook without matching run completes without error."""
    payload = {
        "action": "closed",
        "number": 999,
        "pull_request": {
            "html_url": "https://github.com/Kailash-18/OmniSight/pull/999",
            "number": 999,
            "state": "closed",
            "merged": False,
            "head_ref": "feature/unrelated"
        }
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    assert response.json()["matched_run_id"] is None


def test_list_runs_advanced_filtering(client: TestClient):
    """Verify list_runs filters by branch, scenario, target, has_pr, and has_issues."""
    # Seed specific runs
    runs_db["run-filter-alpha"] = {
        "run_id": "run-filter-alpha",
        "start_time": "2026-10-24T14:00:00Z",
        "target": "http://localhost:5173",
        "branch": "feat/checkout-redesign",
        "scenario": "checkout_flow",
        "status": "pr_opened",
        "issue_count": 2,
        "findings": [{"id": "d1"}, {"id": "d2"}],
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/77"
    }
    runs_db["run-filter-beta"] = {
        "run_id": "run-filter-beta",
        "start_time": "2026-10-24T13:00:00Z",
        "target": "http://127.0.0.1:5173",
        "branch": "main",
        "scenario": "product_browsing",
        "status": "fixed",
        "issue_count": 0,
        "findings": [],
        "pr_url": None
    }

    # Filter by branch
    r_branch = client.get("/runs?branch=feat/checkout-redesign")
    assert r_branch.status_code == 200
    ids_branch = [r["run_id"] for r in r_branch.json()]
    assert "run-filter-alpha" in ids_branch
    assert "run-filter-beta" not in ids_branch

    # Filter by scenario
    r_scenario = client.get("/runs?scenario=product_browsing")
    assert r_scenario.status_code == 200
    ids_scenario = [r["run_id"] for r in r_scenario.json()]
    assert "run-filter-beta" in ids_scenario
    assert "run-filter-alpha" not in ids_scenario

    # Filter by has_pr=true
    r_pr = client.get("/runs?has_pr=true")
    assert r_pr.status_code == 200
    ids_pr = [r["run_id"] for r in r_pr.json()]
    assert "run-filter-alpha" in ids_pr
    assert "run-filter-beta" not in ids_pr

    # Filter by has_issues=false
    r_clean = client.get("/runs?has_issues=false")
    assert r_clean.status_code == 200
    ids_clean = [r["run_id"] for r in r_clean.json()]
    assert "run-filter-beta" in ids_clean
    assert "run-filter-alpha" not in ids_clean


def test_runs_metrics_summary_calculation(client: TestClient):
    """Verify /runs/metrics/summary computes accurate totals, categories, and percentages."""
    # Seed explicit test data in runs_db
    runs_db.clear()

    runs_db["run-m1"] = {
        "run_id": "run-m1",
        "start_time": "2026-10-24T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "issue_count": 1,
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/1",
        "findings": [{"id": "f1", "category": "element_clipping"}]
    }
    runs_db["run-m2"] = {
        "run_id": "run-m2",
        "start_time": "2026-10-24T11:00:00Z",
        "target": "http://localhost:5173",
        "status": "running",
        "issue_count": 2,
        "pr_url": None,
        "findings": [
            {"id": "f2", "category": "element_clipping"},
            {"id": "f3", "category": "contrast_issue"}
        ]
    }
    runs_db["run-m3"] = {
        "run_id": "run-m3",
        "start_time": "2026-10-24T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "issue_count": 0,
        "pr_url": None,
        "findings": []
    }

    response = client.get("/runs/metrics/summary")
    assert response.status_code == 200
    metrics = response.json()

    assert metrics["total_runs"] == 3
    assert metrics["active_runs"] == 1  # run-m2 is running
    assert metrics["fixed_runs"] == 1   # run-m1 is fixed
    assert metrics["prs_opened"] == 1   # run-m1 has pr_url
    assert metrics["total_defects_detected"] == 3
    assert metrics["defects_by_category"]["element_clipping"] == 2
    assert metrics["defects_by_category"]["contrast_issue"] == 1
    # 2 out of 3 runs are clean or resolved (run-m1 fixed, run-m3 0 issues) -> 66.7%
    assert metrics["clean_run_rate_percent"] == 66.7


def test_export_run_evidence_markdown_success(client: TestClient):
    """Verify export evidence markdown returns formatted report with defect table and diff."""
    run_id = "run-export-md-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-24T15:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/88",
        "findings": [
            {
                "id": "def-1",
                "category": "element_clipping",
                "severity": "high",
                "description": "Button clipped",
                "viewport": "mobile_375x667",
                "confidence": 0.95
            }
        ],
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "-width: 500px;\n+width: 100%;",
            "validation_status": True
        }
    }

    response = client.get(f"/runs/{run_id}/export-evidence-markdown")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    md = data["markdown"]
    assert f"OmniSight Visual QA Report: `{run_id}`" in md
    assert "Button clipped" in md
    assert "element_clipping" in md
    assert "width: 100%;" in md
    assert "https://github.com/Kailash-18/OmniSight/pull/88" in md


def test_export_run_evidence_markdown_not_found(client: TestClient):
    """Verify 404 is returned when requesting markdown for unknown run."""
    response = client.get("/runs/run-nonexistent-999/export-evidence-markdown")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_retest_result_success_transitions_run_to_fixed(client: TestClient):
    """Verify posting a passed retest result updates status to FIXED and stores visual diff score."""
    run_id = "run-retest-pass-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "verifying",
        "evidence_paths": {},
        "findings": []
    }
    payload = {
        "passed": True,
        "visual_diff_score": 0.0,
        "retest_viewport": "mobile_375x667",
        "retest_screenshots": {"after": "artifacts/retest_after.png"},
        "notes": "Button clipping resolved"
    }
    res = client.post(f"/runs/{run_id}/retest-result", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "fixed"
    assert data["passed"] is True
    assert data["visual_diff_score"] == 0.0
    assert runs_db[run_id]["status"] == "fixed"
    assert runs_db[run_id]["evidence_paths"]["retest_screenshots"]["after"] == "artifacts/retest_after.png"


def test_retest_result_failure_transitions_to_needs_review(client: TestClient):
    """Verify posting a failed retest result updates status to NEEDS_REVIEW."""
    run_id = "run-retest-fail-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "verifying",
        "evidence_paths": {},
        "findings": []
    }
    payload = {
        "passed": False,
        "visual_diff_score": 0.15,
        "retest_viewport": "desktop_1440x900",
        "notes": "Modal overlap remains after patch"
    }
    res = client.post(f"/runs/{run_id}/retest-result", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "needs_review"
    assert data["passed"] is False
    assert runs_db[run_id]["status"] == "needs_review"


def test_update_pr_verification_success(client: TestClient):
    """Verify update PR verification creates comment and returns success."""
    run_id = "run-pr-verify-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/55",
        "retest_outcome": {
            "passed": True,
            "visual_diff_score": 0.001,
            "retest_viewport": "mobile_375x667",
            "notes": "Clipped element cleared"
        }
    }
    res = client.post(f"/runs/{run_id}/update-pr-verification")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["pr_number"] == 55
    assert data["comment_posted"] is True


def test_run_timeline_ordered_event_history(client: TestClient):
    """Verify run timeline returns chronological events with unique IDs."""
    run_id = "run-timeline-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "timeline": [
            {
                "event_id": "evt-1",
                "timestamp": "2026-10-25T10:00:01Z",
                "event_type": "build_webhook_received",
                "description": "Triggered from CI",
                "metadata": {}
            },
            {
                "event_id": "evt-2",
                "timestamp": "2026-10-25T10:00:05Z",
                "event_type": "vlm_parsed",
                "description": "Defect detected",
                "metadata": {"count": 1}
            }
        ]
    }
    res = client.get(f"/runs/{run_id}/timeline")
    assert res.status_code == 200
    events = res.json()
    assert len(events) == 2
    assert events[0]["event_type"] == "build_webhook_received"
    assert events[1]["event_type"] == "vlm_parsed"


def test_update_finding_status_remediated(client: TestClient):
    """Verify patching individual finding status updates the run record."""
    run_id = "run-finding-update-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "findings": [
            {
                "id": "defect-checkout-btn",
                "category": "element_clipping",
                "severity": "high",
                "description": "Button clipped",
                "viewport": "mobile_375x667",
                "confidence": 0.95,
                "suggested_change": "width: 100%",
                "status": "detected"
            }
        ]
    }
    update_payload = {
        "status": "remediated",
        "suggested_change": "width: 100%; max-width: 100%;",
        "notes": "Resolved via responsive media query fix"
    }
    res = client.patch(f"/runs/{run_id}/findings/defect-checkout-btn", json=update_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "remediated"
    assert runs_db[run_id]["findings"][0]["status"] == "remediated"


def test_export_run_forensic_bundle(client: TestClient):
    """Verify export forensic bundle compiles comprehensive audit archive."""
    run_id = "run-bundle-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/77",
        "findings": [
            {
                "id": "def-1",
                "category": "contrast_issue",
                "severity": "medium",
                "description": "Contrast below WCAG AA",
                "viewport": "desktop_1440x900",
                "confidence": 0.89,
                "suggested_change": "color: #111827",
                "status": "fixed"
            }
        ],
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "-color: #ccc;\n+color: #111827;",
            "validation_status": True
        },
        "retest_outcome": {
            "passed": True,
            "visual_diff_score": 0.0
        },
        "timeline": [
            {
                "event_id": "evt-1",
                "timestamp": "2026-10-25T10:00:00Z",
                "event_type": "audit_started",
                "description": "Audit started",
                "metadata": {}
            }
        ]
    }
    res = client.get(f"/runs/{run_id}/export-bundle")
    assert res.status_code == 200
    bundle = res.json()
    assert bundle["run_id"] == run_id
    assert bundle["summary"]["status"] == "fixed"
    assert bundle["detail"]["findings"][0]["category"] == "contrast_issue"
    assert len(bundle["timeline"]) == 1
    assert bundle["retest_outcome"]["passed"] is True
    assert "bundle_sha256" in bundle
    assert len(bundle["bundle_sha256"]) == 64


def test_get_run_status_lightweight(client: TestClient):
    """Verify GET /runs/{run_id}/status returns concise status summary."""
    run_id = "run-status-poll-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-26T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "running",
        "issue_count": 2,
        "retry_count": 1,
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/55",
        "error": None
    }

    res = client.get(f"/runs/{run_id}/status")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["status"] == "running"
    assert data["issue_count"] == 2
    assert data["retry_count"] == 1
    assert data["has_pr"] is True
    assert data["pr_url"] == "https://github.com/Kailash-18/OmniSight/pull/55"

    # Nonexistent run
    res_404 = client.get("/runs/nonexistent-run/status")
    assert res_404.status_code == 404


def test_retry_audit_run_endpoint(client: TestClient):
    """Verify POST /runs/{run_id}/retry increments count and bounds retries."""
    run_id = "run-retry-test-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-26T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "verifying",
        "retry_count": 0,
        "timeline": []
    }

    # 1. First retry succeeds
    res1 = client.post(f"/runs/{run_id}/retry", json={"reason": "visual defect persists", "max_retries": 2})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["retry_allowed"] is True
    assert data1["retry_count"] == 1
    assert data1["status"] == "running"

    # 2. Second retry succeeds
    res2 = client.post(f"/runs/{run_id}/retry", json={"max_retries": 2})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["retry_allowed"] is True
    assert data2["retry_count"] == 2

    # 3. Third retry is rejected (exhausted bound)
    res3 = client.post(f"/runs/{run_id}/retry", json={"max_retries": 2})
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["retry_allowed"] is False
    assert data3["status"] == "needs_review"
    assert "Maximum retry limit" in data3["message"]


def test_delete_run_endpoint(client: TestClient):
    """Verify DELETE /runs/{run_id} removes run from database."""
    run_id = "run-delete-me-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-26T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed"
    }

    res = client.delete(f"/runs/{run_id}")
    assert res.status_code == 200
    assert res.json()["deleted"] is True
    assert run_id not in runs_db

    # Subsequent GET returns 404
    get_res = client.get(f"/runs/{run_id}")
    assert get_res.status_code == 404

    # Deleting again returns 404
    del_again = client.delete(f"/runs/{run_id}")
    assert del_again.status_code == 404


def test_get_run_pr_status_endpoint(client: TestClient, monkeypatch):
    """Verify GET /runs/{run_id}/pr-status queries live PR info."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)

    run_id = "run-pr-sync-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-26T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "pr_opened",
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/123",
        "timeline": []
    }

    res = client.get(f"/runs/{run_id}/pr-status")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["pr_info"]["pr_number"] == 123
    assert data["pr_info"]["state"] == "open"


def test_correlation_id_middleware_generated_and_propagated(client: TestClient):
    """Verify X-Correlation-ID is generated if missing and preserved if provided."""
    # 1. Generated when missing
    res1 = client.get("/health")
    assert res1.status_code == 200
    assert "X-Correlation-ID" in res1.headers
    assert res1.headers["X-Correlation-ID"].startswith("req-")
    assert "X-Response-Time-Ms" in res1.headers

    # 2. Preserved when provided
    custom_cid = "custom-test-correlation-uuid-999"
    res2 = client.get("/health", headers={"X-Correlation-ID": custom_cid})
    assert res2.status_code == 200
    assert res2.headers["X-Correlation-ID"] == custom_cid


def test_liveness_probe_endpoint(client: TestClient):
    """Verify GET /live returns alive status and uptime."""
    res = client.get("/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "timestamp" in data


def test_readiness_probe_endpoint(client: TestClient):
    """Verify GET /ready returns ready status and connected state."""
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "active_runs" in data


def test_list_runs_date_range_and_severity_filters(client: TestClient):
    """Verify GET /runs filters correctly by start_after, start_before, and min_severity."""
    runs_db["run-temp-1"] = {
        "run_id": "run-temp-1",
        "start_time": "2026-10-20T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "findings": [{"id": "f1", "severity": "low", "category": "element_clipping"}]
    }
    runs_db["run-temp-2"] = {
        "run_id": "run-temp-2",
        "start_time": "2026-10-25T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "findings": [{"id": "f2", "severity": "critical", "category": "element_clipping"}]
    }

    # 1. Date range filter
    res_after = client.get("/runs?start_after=2026-10-22T00:00:00Z")
    assert res_after.status_code == 200
    ids_after = [r["run_id"] for r in res_after.json()]
    assert "run-temp-2" in ids_after
    assert "run-temp-1" not in ids_after

    # 2. Min severity filter (critical only)
    res_crit = client.get("/runs?min_severity=critical")
    assert res_crit.status_code == 200
    ids_crit = [r["run_id"] for r in res_crit.json()]
    assert "run-temp-2" in ids_crit
    assert "run-temp-1" not in ids_crit


def test_revert_run_patch_endpoint(client: TestClient, monkeypatch):
    """Verify POST /runs/{run_id}/revert creates revert branch and transitions status to patch_reverted."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)

    run_id = "run-revert-test-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-26T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "needs_review",
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "-.btn { color: red; }\n+.btn { color: blue; }"
        },
        "timeline": []
    }

    res = client.post(f"/runs/{run_id}/revert")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["reverted"] is True
    assert "revert/" in data["revert_branch"]
    assert runs_db[run_id]["status"] == "patch_reverted"


def test_revert_run_patch_not_found(client: TestClient):
    """Verify POST /runs/{run_id}/revert returns 404 for unknown run."""
    res = client.post("/runs/run-revert-unknown-999/revert")
    assert res.status_code == 404


def test_runs_metrics_summary_mttr_calculation(client: TestClient):
    """Verify get_runs_metrics_summary computes mean time to remediation."""
    run_id = "run-mttr-test-1"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-27T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "findings": [{"id": "f1", "category": "element_clipping"}],
        "retest_outcome": {
            "passed": True,
            "verified_at": "2026-10-27T10:02:30Z"  # 150 seconds
        }
    }

    res = client.get("/runs/metrics/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["resolved_runs_count"] >= 1
    assert data["mean_time_to_remediation_seconds"] is not None
    assert data["mean_time_to_remediation_seconds"] > 0


def test_prometheus_metrics_scrape_endpoint(client: TestClient):
    """Verify GET /metrics returns valid OpenMetrics formatted lines and headers."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    text = res.text
    assert "# HELP omnisight_runs_total" in text
    assert "# TYPE omnisight_runs_total counter"
    assert "omnisight_runs_total" in text
    assert "omnisight_active_runs" in text
    assert "omnisight_mttr_seconds" in text
    assert "omnisight_uptime_seconds" in text


def test_prometheus_metrics_reflects_run_counts(client: TestClient):
    """Verify Prometheus metrics counters dynamically reflect runs_db states."""
    test_run_id = "run-prom-test-99"
    runs_db[test_run_id] = {
        "run_id": test_run_id,
        "start_time": "2026-10-27T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "timeline": [{"event": "run_fixed", "timestamp": "2026-10-27T10:01:00Z"}]
    }
    res = client.get("/metrics")
    assert res.status_code == 200
    text = res.text
    assert 'omnisight_runs_by_status{status="fixed"}' in text
    for line in text.splitlines():
        if line.startswith('omnisight_runs_by_status{status="fixed"}'):
            count = int(line.split()[1])
            assert count >= 1


def test_export_runs_csv_format_and_headers(client: TestClient):
    """Verify GET /runs/export/csv returns valid CSV format with correct header and rows."""
    test_run_id = "run-csv-test-01"
    runs_db[test_run_id] = {
        "run_id": test_run_id,
        "start_time": "2026-10-27T10:00:00Z",
        "target": "http://localhost:5173",
        "branch": "feat/csv-test",
        "scenario": "checkout_flow",
        "status": "fixed",
        "findings": [{"id": "f1", "category": "contrast_issue"}],
        "retry_count": 1,
        "pr_url": "https://github.com/Kailash-18/OmniSight/pull/99",
        "retest_outcome": {"passed": True}
    }

    res = client.get("/runs/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "omnisight_audit_runs.csv" in res.headers.get("content-disposition", "")
    lines = res.text.strip().splitlines()
    assert len(lines) >= 2
    header = lines[0].split(",")
    assert "run_id" in header
    assert "status" in header
    assert "target" in header
    assert "issue_count" in header
    assert any("run-csv-test-01" in line for line in lines)





def test_batch_run_trigger_spawns_matrix(client: TestClient):
    """Verify POST /runs/batch spawns runs across scenarios x viewports matrix."""
    payload = {
        "target_url": "http://localhost:5173",
        "scenarios": ["checkout_flow", "cart_review"],
        "viewports": ["desktop_1440x900", "mobile_375x667"],
        "branch": "feat/batch-test",
        "batch_label": "integration-matrix-1"
    }
    res = client.post("/runs/batch", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["total_runs"] == 4
    assert len(data["run_ids"]) == 4
    assert data["overall_status"] == "queued"
    for r_id in data["run_ids"]:
        assert r_id in runs_db
        assert runs_db[r_id]["batch_id"] == data["batch_id"]


def test_batch_run_trigger_rejects_disallowed_host(client: TestClient):
    """Verify POST /runs/batch rejects unapproved target URLs."""
    payload = {
        "target_url": "http://malicious-external-site.com",
        "scenarios": ["checkout_flow"],
        "viewports": ["desktop_1440x900"]
    }
    res = client.post("/runs/batch", json=payload)
    assert res.status_code == 400
    assert "not in the allowed target hosts" in res.json()["detail"]


def test_batch_status_tracking_and_aggregation(client: TestClient):
    """Verify GET /runs/batch/{batch_id} dynamically reflects individual run statuses."""
    payload = {
        "target_url": "http://localhost:5173",
        "scenarios": ["checkout_flow"],
        "viewports": ["desktop_1440x900", "mobile_375x667"]
    }
    spawn_res = client.post("/runs/batch", json=payload)
    batch_id = spawn_res.json()["batch_id"]
    run_ids = spawn_res.json()["run_ids"]

    # Mark one fixed, one failed
    runs_db[run_ids[0]]["status"] = "fixed"
    runs_db[run_ids[1]]["status"] = "failed"

    status_res = client.get(f"/runs/batch/{batch_id}")
    assert status_res.status_code == 200
    b_data = status_res.json()
    assert b_data["total_runs"] == 2
    assert b_data["completed_runs"] == 1
    assert b_data["failed_runs"] == 1
    assert b_data["overall_status"] == "partially_failed"


def test_bulk_retry_batch_runs(client: TestClient):
    """Verify POST /runs/batch/{batch_id}/retry reschedules failed runs in batch."""
    payload = {
        "target_url": "http://localhost:5173",
        "scenarios": ["checkout_flow"],
        "viewports": ["desktop_1440x900"]
    }
    spawn_res = client.post("/runs/batch", json=payload)
    batch_id = spawn_res.json()["batch_id"]
    run_id = spawn_res.json()["run_ids"][0]

    runs_db[run_id]["status"] = "failed"
    runs_db[run_id]["retry_count"] = 0

    retry_res = client.post(f"/runs/batch/{batch_id}/retry", json={"only_failed_or_needs_review": True})
    assert retry_res.status_code == 200
    r_data = retry_res.json()
    assert r_data["retried_runs_count"] == 1
    assert run_id in r_data["retried_run_ids"]
    assert runs_db[run_id]["status"] == "queued"
    assert runs_db[run_id]["retry_count"] == 1


def test_evaluate_run_policy_endpoint(client: TestClient):
    """Verify POST /runs/{run_id}/policy/evaluate returns full gating breakdown."""
    run_id = "run-policy-ep-test"
    runs_db[run_id] = {
        "run_id": run_id,
        "status": "verifying",
        "patch": {
            "target_file": "app-under-test/src/styles/defects.css",
            "diff": "--- a/app-under-test/src/styles/defects.css\n+++ b/app-under-test/src/styles/defects.css\n@@ -1,2 +1,3 @@\n+.fixed { margin: 0; }\n"
        },
        "retest_outcome": {"visual_diff_score": 0.00, "passed": True},
        "findings": [{"id": "f1", "category": "element_overlap", "severity": "low"}]
    }

    res = client.post(f"/runs/{run_id}/policy/evaluate")
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["run_id"] == run_id
    assert p_data["gate_level"] == "auto_merge"
    assert p_data["auto_merge_allowed"] is True
    assert len(p_data["rule_evaluations"]) >= 5


def test_add_and_remove_run_tags(client: TestClient):
    """Verify POST /runs/{run_id}/tags and DELETE /runs/{run_id}/tags/{tag}."""
    run_id = "run-tag-test-01"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-28T10:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "tags": ["existing-tag"],
        "timeline": []
    }

    # Add tags
    res = client.post(f"/runs/{run_id}/tags", json={"tags": ["nightly", "smoke", "p0"]})
    assert res.status_code == 200
    data = res.json()
    assert set(data["tags"]) == {"existing-tag", "nightly", "smoke", "p0"}
    assert "tags_updated" in [e["event_type"] for e in runs_db[run_id]["timeline"]]

    # Remove single tag
    del_res = client.delete(f"/runs/{run_id}/tags/nightly")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert "nightly" not in del_data["tags"]
    assert "smoke" in del_data["tags"]
    assert "tag_removed" in [e["event_type"] for e in runs_db[run_id]["timeline"]]


def test_tagging_endpoints_404_for_unknown_run(client: TestClient):
    """Verify 404 is returned when modifying tags on non-existent runs."""
    res1 = client.post("/runs/non-existent-run-999/tags", json={"tags": ["smoke"]})
    assert res1.status_code == 404
    res2 = client.delete("/runs/non-existent-run-999/tags/smoke")
    assert res2.status_code == 404


def test_list_runs_filtered_by_tags(client: TestClient):
    """Verify GET /runs?tags=... filters runs matching all required tags."""
    r1 = "run-filter-tag-1"
    r2 = "run-filter-tag-2"
    runs_db[r1] = {
        "run_id": r1,
        "start_time": "2026-10-28T12:00:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "tags": ["smoke", "p0", "canary"],
        "findings": []
    }
    runs_db[r2] = {
        "run_id": r2,
        "start_time": "2026-10-28T12:05:00Z",
        "target": "http://localhost:5173",
        "status": "fixed",
        "tags": ["nightly", "regression"],
        "findings": []
    }

    # Query single tag
    res_smoke = client.get("/runs?tags=smoke")
    assert res_smoke.status_code == 200
    smoke_ids = [r["run_id"] for r in res_smoke.json()]
    assert r1 in smoke_ids
    assert r2 not in smoke_ids

    # Query multi-tags
    res_multi = client.get("/runs?tags=smoke,p0")
    assert res_multi.status_code == 200
    multi_ids = [r["run_id"] for r in res_multi.json()]
    assert r1 in multi_ids
    assert r2 not in multi_ids

    # Query non-matching tag combination
    res_none = client.get("/runs?tags=smoke,regression")
    assert res_none.status_code == 200
    none_ids = [r["run_id"] for r in res_none.json()]
    assert r1 not in none_ids
    assert r2 not in none_ids


def test_run_details_includes_tags_payload(client: TestClient):
    """Verify GET /runs/{run_id} includes metadata tags array."""
    run_id = "run-detail-tag-check"
    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": "2026-10-28T14:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "tags": ["production-canary", "mobile-audit"],
        "findings": [],
        "timeline": []
    }
    res = client.get(f"/runs/{run_id}")
    assert res.status_code == 200
    data = res.json()
    assert "tags" in data
    assert "production-canary" in data["tags"]
    assert "mobile-audit" in data["tags"]


def test_defect_clusters_endpoint_aggregates_across_runs(client: TestClient):
    """Verify GET /defects/clusters returns aggregated clusters across multiple test runs."""
    r1 = "run-cluster-test-1"
    r2 = "run-cluster-test-2"

    runs_db[r1] = {
        "run_id": r1,
        "start_time": "2026-10-28T14:30:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "findings": [
            {
                "id": "f-c1",
                "category": "element_clipping",
                "severity": "high",
                "description": "Button clipped",
                "viewport": "mobile_375x667",
                "target_element": "button.submit-primary",
                "confidence": 0.94,
                "suggested_change": "width: 100%;"
            }
        ],
        "timeline": []
    }
    runs_db[r2] = {
        "run_id": r2,
        "start_time": "2026-10-28T14:35:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "findings": [
            {
                "id": "f-c2",
                "category": "element_clipping",
                "severity": "medium",
                "description": "Button clipped in tablet",
                "viewport": "tablet_768x1024",
                "target_element": "button.submit-primary",
                "confidence": 0.88,
                "suggested_change": "width: 100%;"
            }
        ],
        "timeline": []
    }

    res = client.get("/defects/clusters")
    assert res.status_code == 200
    data = res.json()
    assert "clusters" in data
    assert data["total_clusters"] >= 1

    matching = [c for c in data["clusters"] if c.get("target_element") == "button.submit-primary"]
    assert len(matching) == 1
    cl = matching[0]
    assert cl["occurrences"] >= 2
    assert r1 in cl["run_ids"]
    assert r2 in cl["run_ids"]
    assert "mobile_375x667" in cl["viewports"]
    assert "tablet_768x1024" in cl["viewports"]


def test_defect_flakiness_report_endpoint(client: TestClient):
    """Verify GET /defects/flakiness retrieves system-wide stability metrics."""
    from app.services.flakiness_service import record_defect_observation, reset_flakiness_tracker
    reset_flakiness_tracker()

    record_defect_observation(
        fingerprint="dfp-sample-flaky-01",
        detected=True,
        target_element="div.banner",
        category="color_contrast"
    )
    record_defect_observation(
        fingerprint="dfp-sample-flaky-01",
        detected=False,
        target_element="div.banner",
        category="color_contrast"
    )

    res = client.get("/defects/flakiness")
    assert res.status_code == 200
    data = res.json()
    assert data["total_tracked_defects"] >= 1
    rec = [d for d in data["defects"] if d["fingerprint"] == "dfp-sample-flaky-01"][0]
    assert rec["total_observations"] == 2
    assert rec["defect_occurrences"] == 1
    assert rec["flakiness_score"] == 1.0


def test_defect_quarantine_and_unquarantine_lifecycle(client: TestClient):
    """Verify POST and DELETE /defects/{fingerprint}/quarantine endpoints manage quarantine state."""
    fp = "dfp-quarantine-test-01"

    # 1. Place under quarantine
    payload = {
        "reason": "Intermittent CSS transition causing occasional snapshot timing offset",
        "quarantined_by": "qa-automation"
    }
    res_q = client.post(f"/defects/{fp}/quarantine", json=payload)
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["fingerprint"] == fp
    assert data_q["is_quarantined"] is True
    assert "successfully placed under quarantine" in data_q["message"]

    # 2. Verify reflected in flakiness report
    res_rep = client.get("/defects/flakiness")
    assert res_rep.status_code == 200
    assert any(d["fingerprint"] == fp and d["is_quarantined"] is True for d in res_rep.json()["defects"])

    # 3. Release from quarantine
    res_del = client.delete(f"/defects/{fp}/quarantine")
    assert res_del.status_code == 200
    data_del = res_del.json()
    assert data_del["fingerprint"] == fp
    assert data_del["is_quarantined"] is False
    assert "released from quarantine" in data_del["message"]


def test_defect_clusters_endpoint_category_filtering_and_pagination(client: TestClient):
    """Verify category filtering and skip/limit pagination on GET /defects/clusters."""
    r_id = "run-cluster-filter-test"
    runs_db[r_id] = {
        "run_id": r_id,
        "start_time": "2026-10-28T15:00:00Z",
        "target": "http://localhost:5173",
        "status": "audited",
        "findings": [
            {
                "id": "f-overlap-1",
                "category": "element_overlap",
                "severity": "high",
                "description": "Hero overlap",
                "viewport": "desktop_1440x900",
                "target_element": "div.hero-title",
                "suggested_change": "margin: 0;"
            },
            {
                "id": "f-contrast-1",
                "category": "color_contrast",
                "severity": "medium",
                "description": "Low contrast",
                "viewport": "desktop_1440x900",
                "target_element": "p.caption",
                "suggested_change": "color: #111;"
            }
        ],
        "timeline": []
    }

    # Query with category filter
    res_cat = client.get("/defects/clusters?category=color_contrast")
    assert res_cat.status_code == 200
    data_cat = res_cat.json()
    assert all(c["category"] == "contrast_issue" for c in data_cat["clusters"])
    assert any(c.get("target_element") == "p.caption" for c in data_cat["clusters"])

    # Query with limit
    res_lim = client.get("/defects/clusters?limit=1")
    assert res_lim.status_code == 200
    data_lim = res_lim.json()
    assert len(data_lim["clusters"]) <= 1


