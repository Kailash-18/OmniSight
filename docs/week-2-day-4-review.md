# OmniSight — Week 2 Day 4 Backend & PR Automation Deliverables Report

> **Milestone**: Week 2 (Day 4) Pull Request Automation & System Hardening  
> **Author**: Member 1 (Sri Khyathi)  
> **Status**: Completed (82 Passing Tests)  
> **Date**: October 24, 2026  
> **Scope**: PR Automation Service, GitHub Webhook Ingestion, Query Filters, Metrics Aggregator, and Zero-Trust CSS Security Guardrails.

---

## 1. Executive Summary

During the Day 4 milestone, Member 1 finalized and hardened the **GitHub PR Automation Engine** and **FastAPI CI/CD Gateway**, expanding test coverage from 67 to **82 passing tests** across unit, security, and integration test suites.

```mermaid
flowchart TD
    subgraph GitHub Integration
        GH[GitHub Repository] -->|POST /webhook/github| GW[FastAPI Gateway]
        PR[Automated PR Engine] -->|Create PR with Labels & Diff| GH
        PR -->|Append Verification Retest Comment| GH
    end

    subgraph Backend Intelligence
        GW --> DB[(In-Memory Runs DB)]
        GW -->|GET /runs/metrics/summary| METRICS[Aggregate Metrics Engine]
        GW -->|GET /runs/{id}/export-evidence-markdown| EXP[Markdown Evidence Exporter]
    end

    subgraph Security Layer
        DIFF[VLM Patch Diff] --> SEC[CSS AST & Zero-Trust Validator]
        SEC -->|Reject @import & behavior:| REJ[400 Validation Error]
        SEC -->|Approved Layout CSS| PR
    end
```

---

## 2. Core Capabilities Implemented Today

### A. Automated Pull Request Label Management
* Added `labels` configuration to `PatchSubmitPayload` and `create_pull_request_for_fix`.
* Categorizes created PRs automatically (e.g. `omnisight`, `automated-fix`, `viewport:mobile`).
* Handles mock simulation logging and live GitHub PR label assignment via PyGithub.

### B. GitHub PR Lifecycle Webhook Receiver (`POST /webhook/github`)
* Ingests GitHub `pull_request` event webhooks to track human review and merge outcomes in real time.
* Automatically transitions run records:
  * **Merged**: transitions run status to `fixed` and records `github_pr_merged` in timeline.
  * **Closed (Unmerged)**: transitions run status to `needs_review`.
  * **Opened / Reopened**: transitions status to `pr_opened`.

### C. Advanced Multi-Dimensional Run Query Filters (`GET /runs`)
* Added granular query parameters to `GET /runs`:
  * `branch`: Filter by source branch (e.g., `feat/checkout-redesign`).
  * `scenario`: Filter by journey (e.g., `checkout_flow`, `product_browsing`).
  * `target`: Substring matching on target host URLs.
  * `has_pr`: Boolean filter for runs that produced an opened Pull Request.
  * `has_issues`: Boolean filter for runs with detected visual defects vs clean runs.

### D. Aggregate Batch Metrics Summary (`GET /runs/metrics/summary`)
* High-performance calculation for QA dashboard analytics:
  * Total runs, active audits, and resolved fixes count.
  * Defect category distribution (`element_clipping`, `element_overlap`, `contrast_issue`, etc.).
  * Total PRs opened and clean run rate percentage (`clean_run_rate_percent`).

### E. Evidence Markdown Exporter (`GET /runs/{run_id}/export-evidence-markdown`)
* Generates formatted GitHub-ready markdown summaries of any run, including findings tables, confidence ratings, and unified diff blocks, ready for PR discussions or issue tracking.

### F. Zero-Trust CSS Security Guardrails
* Enhanced `validate_patch` and added `validate_css_safety`:
  * Rejects `@import` directives (preventing stylesheet exfiltration and CSS injection).
  * Rejects legacy execution properties (`behavior:`, `-moz-binding:`).
  * Validates and accepts valid responsive media queries (`@media (max-width: ...)`) and flex/grid layout fixes.

---

## 3. Test Matrix & Verification

```bash
$ pytest backend/tests
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\Kailash\.gemini\antigravity-ide\scratch\OmniSight
plugins: anyio-4.15.1
collected 82 items

backend\tests\test_action_engine.py ..........                           [ 12%]
backend\tests\test_api.py ...............................                [ 50%]
backend\tests\test_patch_validator.py ...................                [ 73%]
backend\tests\test_pr_automation.py ........                             [ 82%]
backend\tests\test_schemas.py ..............                             [100%]

======================== 82 passed, 1 warning in 0.50s ========================
```

Total passing tests across OmniSight repository: **95 tests** (82 backend + 13 automation).
