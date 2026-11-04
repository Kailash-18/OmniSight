# OmniSight API & Data Contract

This document defines the formal shared schema and API contract between the **FastAPI Backend (Member 1)**, the **Automation & Orchestrator Engine (Team Lead)**, and the **QA Dashboard (Member 2)**.

---

## 1. Endpoints

### `POST /webhook/build`
Accepts build events from external CI/CD systems (GitHub Actions/Jenkins) or simulated triggers.
* **Request Payload**:
  ```json
  {
    "target_url": "http://localhost:5173",
    "branch": "main",
    "scenario": "checkout_flow",
    "commit_sha": "56e42d7f",
    "event_id": "evt-1001"
  }
  ```
* **Response (202 Accepted)**:
  ```json
  {
    "run_id": "run-1729418400",
    "status": "queued",
    "message": "Build event accepted and queued for browser audit."
  }
  ```

### `POST /runs`
Manual trigger for on-demand browser audits on configured staging or local hosts.
* **Request Payload**:
  ```json
  {
    "target_url": "http://localhost:5173",
    "scenario": "checkout_flow",
    "viewports": ["desktop_1440x900", "mobile_375x667"]
  }
  ```
* **Response (201 Created)**:
  ```json
  {
    "run_id": "run-1729418400",
    "status": "running"
  }
  ```

### `GET /runs`
Returns summaries of all recorded test runs for the QA dashboard list view.
* **Response (200 OK)**:
  ```json
  [
    {
      "run_id": "run-1729418400",
      "start_time": "2026-10-20T10:00:00Z",
      "target": "http://localhost:5173",
      "status": "pr_opened",
      "issue_count": 1,
      "pr_url": "https://github.com/Kailash-18/OmniSight/pull/4"
    }
  ]
  ```

### `GET /runs/{run_id}`
Returns complete forensic details, evidence links, findings, and patch status for a single run.
* **Response (200 OK)**:
  ```json
  {
    "run_id": "run-1729418400",
    "start_time": "2026-10-20T10:00:00Z",
    "target": "http://localhost:5173",
    "status": "fixed",
    "steps": ["navigate_home", "add_item", "open_cart", "navigate_checkout"],
    "evidence_paths": {
      "screenshots": [
        "artifacts/runs/run-1729418400/desktop_1440x900_home.png",
        "artifacts/runs/run-1729418400/mobile_375x667_cart.png",
        "artifacts/runs/run-1729418400/desktop_1280x800_checkout.png"
      ],
      "before_screenshots": [
        "artifacts/runs/run-1729418400/desktop_1440x900_home.png",
        "artifacts/runs/run-1729418400/mobile_375x667_cart.png",
        "artifacts/runs/run-1729418400/desktop_1280x800_checkout.png"
      ],
      "after_screenshots": [
        "artifacts/runs/run-1729418400/retest_desktop_1280x800_checkout.png"
      ],
      "dom_snapshot": "artifacts/runs/run-1729418400/dom_snapshot.json"
    },
    "findings": [
      {
        "id": "defect-checkout-submit-obstructed",
        "category": "element_obstruction",
        "severity": "high",
        "description": "Submit order button is covered by promotional free-shipping banner",
        "viewport": "all",
        "confidence": 0.96,
        "suggested_change": "Remove absolute positioning or lower z-index on .promo-banner",
        "rationale": "Element geometry indicates .promo-banner sits directly on top of .btn-primary",
        "status": "remediated"
      }
    ],
    "patch": {
      "target_file": "app-under-test/src/styles/defects.css",
      "diff": "-.promo-banner { position: absolute; }\n+.promo-banner { position: static; }",
      "validation_status": true,
      "validator_errors": null
    },
    "retry_count": 1,
    "pr_url": "https://github.com/Kailash-18/OmniSight/pull/4"
  }
  ```

### `POST /runs/{run_id}/submit-patch`
Submits a generated code/CSS patch for zero-trust security validation and records it on the run. Optionally triggers automatic PR opening if `auto_create_pr` is enabled.
* **Request Payload**:
  ```json
  {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
    "file_content": ".btn { width: 100%; }",
    "pr_title": "fix(ui): automated visual repair for mobile_375x667",
    "pr_body": "Verified fix for mobile checkout button clipping.",
    "auto_create_pr": true,
    "labels": ["omnisight", "automated-fix"]
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "validation_status": true,
    "message": "Patch for app-under-test/src/styles/defects.css passed all zero-trust security guardrails.",
    "pr_url": "https://github.com/Kailash-18/OmniSight/pull/4"
  }
  ```

### `POST /runs/{run_id}/create-pr`
Creates an automated feature branch and opens an evidence-backed Pull Request via PyGithub (or deterministic mock simulation).
* **Request Payload**:
  ```json
  {
    "pr_title": "fix(ui): automated visual repair for mobile_375x667",
    "pr_body": "Verified fix for mobile checkout button clipping.",
    "labels": ["omnisight", "automated-fix"]
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "run_id": "run-1729418400",
    "pr_url": "https://github.com/Kailash-18/OmniSight/pull/4",
    "message": "Pull Request created successfully."
  }
  ```

### `POST /runs/{run_id}/update-pr-verification`
Appends verification retest results, visual diff score, and audit proof badge as an issue comment to an open PR.
* **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "pr_number": 4,
    "comment_posted": true
  }
  ```

### `POST /webhook/github/pull-request`
Ingests GitHub webhook events for pull requests (`opened`, `closed`, `labeled`) and reviews (`submitted`). Synchronizes run records with PR review decisions and merge outcomes.
* **Request Payload**:
  ```json
  {
    "action": "closed",
    "pull_request": {
      "number": 4,
      "html_url": "https://github.com/Kailash-18/OmniSight/pull/4",
      "merged": true,
      "head": {
        "ref": "omnisight-fix-run-1729418400"
      }
    },
    "review": {
      "state": "approved"
    }
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "processed",
    "action": "closed",
    "pr_number": 4,
    "matched_run_id": "run-1729418400",
    "merged": true
  }
  ```

### `GET /api/milestones`
Returns current milestone completion status across team roles and active security allowlists.
* **Response (200 OK)**:
  ```json
  {
    "member": "Member 1 - Backend & PR Automation",
    "week_1_foundation": "completed",
    "week_2_action_engine": "completed",
    "week_2_day_3_integration": "completed",
    "week_3_pr_automation": "in_progress",
    "week_3_progress": "20% - Closed-loop PR automation engine, verification proof comments, and webhook ingestion",
    "allowed_targets": ["localhost", "127.0.0.1", "0.0.0.0", "::1", "staging.internal"],
    "allowed_patch_files": ["app-under-test/src/styles/defects.css", "..."]
  }
  ```

---

## 2. Common Data Structures & Enums

### Run Status Enum
Values must remain identical across backend, automation, and frontend:
* `queued`: Run received and pending execution.
* `running`: Playwright browser session active.
* `audited`: Multimodal VLM analysis complete.
* `patch_rejected`: Proposed fix violated allowlist or security checks.
* `verifying`: Patch applied in sandbox; executing retest.
* `fixed`: Retest confirmed visual defect cleared.
* `needs_review`: AI confidence low or retest failed; human escalation required.
* `pr_opened`: Automated GitHub Pull Request created with evidence.
* `failed`: Execution failed due to network, runtime, or timeout error.

### Evidence Paths Schema
* `screenshots` (primary) / `before_screenshots` (alias): Baseline screenshots captured before remediation. Both keys are supported and normalized across the backend and QA dashboard.
* `after_screenshots`: Verification screenshots captured after sandbox patch application during retesting.
* `dom_snapshot`: Path to the captured DOM structure snapshot.
