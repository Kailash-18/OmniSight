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
