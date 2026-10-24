# OmniSight Backend Gateway & Action Engine

> **Member 1 Ownership**: FastAPI CI/CD Gateway, Action Engine, Zero-Trust Patch Validator, and GitHub Pull Request Automation.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-2.0%2B-e92063.svg)](https://docs.pydantic.dev/)
[![Pytest](https://img.shields.io/badge/Pytest-41%20Backend%20Tests%20Passed-45ba4b.svg)](https://pytest.org/)
[![Terraform](https://img.shields.io/badge/Terraform-Secured-844FBA.svg)](https://www.terraform.io/)

---

## 📋 Overview

The OmniSight Backend service acts as the central intelligence and security clearinghouse for the autonomous visual self-healing loop:
1. **CI/CD Gateway (`/webhook/build`)**: Ingests build events from external CI/CD pipelines (or manual QA triggers) and schedules browser audit runs.
2. **Action Engine (`/action-engine/parse`)**: Parses multimodal Vision-Language Model (VLM) outputs, extracting structured findings, rationale, confidence scores, and unified git diff code patches from natural language and markdown code blocks.
3. **Zero-Trust Patch Validator**: Verifies that proposed fixes conform to strict security allowlists, rejecting path traversals (`..`), URL-encoded traversal (`%2e%2e`), null bytes, absolute paths, unauthorized file modifications, oversized diffs, and script injection payloads.
4. **GitHub PR Automation**: Once a patch passes automated re-testing in an isolated sandbox, creates a feature branch, commits the approved changes, and opens an evidence-backed Pull Request.

---

## 🗓️ Weekly Milestones (Member 1)

| Period | Milestone | Status | Details |
| :--- | :--- | :---: | :--- |
| **Week 1** | Foundation & API Scaffolding | ✅ Completed | FastAPI service, `/health`, `/webhook/build`, `/runs`, `/runs/{run_id}`, shared Pydantic data schemas. |
| **Week 2 (Day 1-2)** | Action Engine & Security Validator | ✅ Completed | Multimodal JSON/diff extractor (`action_engine.py`), path traversal defense, allowlist checks, script injection filters, 41 unit/integration tests. |
| **Week 2 (Day 3-5)** | Mid-Project Review & Integration | 🚀 Ready | Extraction check verified, sandbox retest coordination with Team Lead & Member 2. |

| **Week 3** | Bounded Self-Healing & PR Engine | ✅ Scaffolded | Branch, commit, and PR creation via PyGithub with mock fallbacks for offline testing. |
| **Week 4** | Production Hardening & Cloud Deploy | ✅ Prepared | Terraform parameterized infrastructure module (`backend/terraform/`). |

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph External Triggers
        A[GitHub Actions / Jenkins Webhook] -->|POST /webhook/build| B(FastAPI Gateway)
        C[QA Dashboard / Manual Trigger] -->|POST /runs| B
    end

    subgraph Backend Core
        B --> D[(In-Memory Run Store)]
        E[VLM Multimodal Engine] -->|Raw Natural Language & JSON| F[Action Engine]
        F -->|Extract Findings & Code Blocks| G[Pydantic Schema Parser]
        G --> H[Patch Security Validator]
        H -->|Allowlist Passed| I[Validated Patch Decision]
        H -->|Path Traversal / Unapproved File| J[Patch Rejected with 400]
    end

    subgraph Remediation & Review
        I --> K[PyGithub Automation]
        K --> L[GitHub Pull Request with Evidence]
        D -->|GET /runs| M[React QA Dashboard]
    end
```

---

## 🔒 Security Guardrails & Zero-Trust Architecture

To ensure the AI cannot harm repository integrity or internal network services, the backend enforces the following controls:

1. **SSRF Protection (`_validate_target_host`)**:
   Incoming target URLs are checked against `ALLOWED_TARGET_HOSTS` (`localhost`, `127.0.0.1`, `staging.internal`). Unapproved external hosts are rejected with HTTP 400.
2. **Strict File Allowlist**:
   Patches can ONLY modify approved styling and component files:
   * `app-under-test/src/styles/defects.css`
   * `app-under-test/src/styles/base.css`
   * `app-under-test/src/components/` (`.jsx`, `.js`, `.css`)
   * `app-under-test/src/App.jsx`
   Any attempt to modify server code (`backend/app/main.py`), configs (`package.json`), or root files is immediately rejected.
3. **Path Traversal Defense**:
   Target file paths containing `..`, absolute indicators (`/`, `C:\`), or backslashes are blocked.
4. **Script & Code Injection Defense**:
   Diff contents are scanned for malicious script signatures:
   * `<script`, `javascript:`, `expression(`, `eval(`, `exec(`, `onerror=`, `onload=`, `document.cookie`.
5. **Diff Size Boundaries**:
   Diffs exceeding 300 lines or 30KB are rejected to prevent runaway code overwrites.

---

## 📡 API Reference

### 1. Health Check
* **Endpoint**: `GET /health`
* **Response (200 OK)**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-10-22T12:00:00Z",
    "version": "1.0.0"
  }
  ```

### 2. CI/CD Build Webhook
* **Endpoint**: `POST /webhook/build`
* **Request**:
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

### 3. Manual Audit Trigger
* **Endpoint**: `POST /runs`
* **Request**:
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

### 4. Action Engine VLM Parser
* **Endpoint**: `POST /action-engine/parse`
* **Request**:
  ```json
  {
    "raw_vlm_output": "The checkout button is clipped on mobile viewports. ```json\n{\n  \"findings\": [ ... ],\n  \"proposed_patch\": { \"target_file\": \"app-under-test/src/styles/defects.css\", \"diff\": \"...\" }\n}\n```"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "is_valid": true,
    "findings": [
      {
        "id": "defect-1",
        "category": "element_clipping",
        "severity": "high",
        "description": "Place Order button clipped on mobile",
        "viewport": "mobile_375x667",
        "confidence": 0.94,
        "suggested_change": "width: 100%",
        "rationale": "Bounding box extends past viewport right boundary",
        "status": "detected"
      }
    ],
    "proposed_patch": {
      "target_file": "app-under-test/src/styles/defects.css",
      "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
      "validation_status": true,
      "validator_errors": null
    },
    "validation_status": true,
    "validator_errors": null,
    "parse_errors": []
  }
  ```

### 5. Submit and PR Validated Patch
* **Endpoint**: `POST /runs/{run_id}/submit-patch`
* **Request**:
  ```json
  {
    "target_file": "app-under-test/src/styles/defects.css",
    "diff": "-.btn { width: 500px; }\n+.btn { width: 100%; }",
    "file_content": ".btn { width: 100%; }",
    "pr_title": "fix(ui): repair mobile checkout button clipping",
    "pr_body": "Automated patch verified by sandbox re-test."
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "pr_url": "https://github.com/Kailash-18/OmniSight/pull/12"
  }
  ```

---

## 🛠️ Environment Configuration & Zero Hardcoding

Credentials and settings are managed through environment variables. **No API keys or tokens are hardcoded into the source code.**

Copy `.env.example` to `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

| Variable | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `GITHUB_TOKEN` | string | GitHub fine-grained PAT (Contents: R/W, Pull Requests: R/W) | _None_ |
| `REPO_NAME` | string | Target repository name | `Kailash-18/OmniSight` |
| `MOCK_GITHUB` | bool | When `true`, simulates PR creation without making live GitHub calls | `false` |
| `ALLOWED_TARGET_HOSTS` | string | Comma-separated allowed hostnames for audit runs | `localhost,127.0.0.1,staging.internal` |
| `ALLOWED_PATCH_FILES` | string | Comma-separated allowed patch target files/paths | `app-under-test/src/styles/defects.css,...` |
| `BACKEND_PORT` | int | Server port | `8000` |

---

## ☁️ Terraform Deployment Security (`backend/terraform/`)

Infrastructure definitions for deploying the backend containerized service are located in `backend/terraform/`:
* `variables.tf`: All parameters (CPU, memory, region, allowed hosts, and sensitive tokens) are parameterized via Terraform variables. The GitHub token is flagged as `sensitive = true`.
* `main.tf`: Deploys the service without any hardcoded credentials.
* `terraform.tfvars.example`: Example variable definition file.

> [!IMPORTANT]
> **Terraform Security Rule**:
> Never commit `terraform.tfvars` containing live credentials to git. All `*.tfvars` and `*.tfstate` files are excluded by `.gitignore`.

To use Terraform locally:
```bash
cd backend/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your parameters
terraform init
terraform plan
```

---

### 4. List All Runs (With Optional Filtering & Pagination)
* **Endpoint**: `GET /runs?limit=50&status_filter=queued`
* **Query Parameters**:
  * `limit` (int, default 50): Maximum number of run summaries to return.
  * `status_filter` (string, optional): Filter by lifecycle status (`queued`, `running`, `audited`, `fixed`, `pr_opened`, etc.).
* **Response (200 OK)**:
  Returns run summaries sorted in reverse chronological order.

### 5. Action Engine VLM Parser
* **Endpoint**: `POST /action-engine/parse`
* **Capabilities**: Supports JSON objects, top-level JSON arrays, markdown code fences, and percentage confidence strings (e.g., `"95%"`).

### 6. Submit and PR Validated Patch
* **Endpoint**: `POST /runs/{run_id}/submit-patch`

---

## 🧪 Running the Backend & Tests

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Start the Backend API Server
```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```
Interactive Swagger docs: `http://localhost:8000/docs`

### 3. Run Backend Test Suite
```bash
python -m pytest backend/tests/ -v
```
All **32 backend tests** verify Action Engine parsing, patch allowlist validation, path traversal defense, script injection resistance, idempotency, and API endpoints.

### 4. Quick API Smoke Test via cURL
```bash
# Health check
curl -X GET http://localhost:8000/health

# Trigger simulated build webhook
curl -X POST http://localhost:8000/webhook/build \
  -H "Content-Type: application/json" \
  -d '{"target_url":"http://localhost:5173","branch":"main","scenario":"checkout_flow"}'

# List active runs
curl -X GET http://localhost:8000/runs
```


