# OmniSight — Week 2 Complete Backend Deliverables & Final Review Report

> **Milestone**: Week 2 (Days 1–6) Full Backend Gateway, Action Engine, Zero-Trust Security, and PR Automation Finalization  
> **Author**: Member 1 (Sri Khyathi)  
> **Status**: Completed (97 Passing Tests, 100% Pass Rate)  
> **Date**: October 25, 2026  
> **Python Target**: Python 3.11+  
> **Scope**: Complete Week 2 roadmap covering multimodal VLM parsing, zero-trust CSS guardrails, automated PR lifecycle, verification retest synchronization, chronological event timeline, and forensic bundle archiving.

---

## 1. Executive Summary

Member 1 has completed and finalized all backend deliverables for **Week 2 (Days 1 through 6)** of the OmniSight autonomous visual self-healing platform. The backend service now provides complete closed-loop lifecycle synchronization, zero-trust code modification boundaries, automated GitHub Pull Request workflows, and deep forensic auditing.

The test suite expanded from 32 tests (Day 2) &rarr; 67 tests (Day 3) &rarr; 82 tests (Day 4) to **97 fully automated passing tests** across unit, security, integration, and serialization test suites.

```mermaid
flowchart TD
    subgraph CI and Triggers
        A[External CI/CD Webhook] -->|POST /webhook/build| GW[FastAPI Gateway]
        B[QA Review Dashboard] -->|POST /runs| GW
    end

    subgraph Intelligence & Parsing
        GW -->|Raw Prose & Diff| AE[Action Engine]
        AE -->|Smart Quote & Python Dict Normalizer| PARSER[Pydantic JSON Parser]
        PARSER --> FINDINGS[Structured Visual Findings]
        PARSER --> PATCH[Constrained CSS Patch]
    end

    subgraph Security Layer
        PATCH --> SEC[Zero-Trust Patch Validator]
        SEC -->|Path Traversal Check| C1{Clean Relative?}
        SEC -->|Allowlist Check| C2{Approved File?}
        SEC -->|CSS AST Guardrails| C3{No @import / expression / javascript:?}
        C1 -- No --> REJ[400 Validation Error]
        C2 -- No --> REJ
        C3 -- No --> REJ
        C1 & C2 & C3 -- Yes --> APPR[Approved Patch]
    end

    subgraph Remediation & Verification
        APPR --> SANDBOX[Sandbox Retest Runner]
        SANDBOX -->|POST /runs/{id}/retest-result| GW
        GW -->|Fixed?| PR[PyGithub Automation]
        PR -->|POST /runs/{id}/update-pr-verification| GH[GitHub PR with Visual Evidence]
    end

    subgraph Audit & Forensics
        GW --> TIMELINE[(Chronological Event Stream)]
        GW -->|GET /runs/{id}/export-bundle| ARCHIVE[Forensic Compliance Bundle]
        GW -->|GET /runs/metrics/summary| METRICS[Aggregate Analytics Engine]
    end
```

---

## 2. Daily Engineering Deliverables Breakdown (Week 2 Days 1–6)

### Day 1: Action Engine Multimodal Parser & Code Extraction
* Implemented `ActionEngine.extract_json_object` and `ActionEngine.extract_code_blocks` (`backend/app/services/action_engine.py`).
* Supported prose text containing embedded JSON blocks, top-level arrays, and isolated `diff`/`css` code blocks.
* Designed and locked shared Pydantic v2 data models: `FindingSchema`, `PatchObject`, `RunStatus`, `DefectCategory`, and `Severity`.
* Unit tests verified markdown fenced blocks, JSON array extraction, and confidence score normalization.

### Day 2: Zero-Trust Patch Validator & Security Boundaries
* Implemented strict path traversal defense in `validate_patch` (`backend/app/services/patch_validator.py`), blocking `..`, `%2e%2e`, null bytes (`\x00`), and absolute paths.
* Enforced file allowlist boundary (`app-under-test/src/styles/` and component files), immediately rejecting any modifications targeting server code (`backend/app/main.py`) or package configs.
* Added SSRF host protection in `_validate_target_host`, validating schemes and restricting target hosts to `ALLOWED_TARGET_HOSTS`.
* Implemented script injection scanners for `<script`, `javascript:`, `expression(`, `eval(`, and cookie exfiltration patterns.

### Day 3: Mid-Project Review, Integration & OpenAPI Documentation
* Standardized OpenAPI 3.0 tags and endpoint metadata across all routes for Swagger UI documentation.
* Configured reverse-chronological query ordering in `GET /runs` with multi-attribute sorting and pagination limits.
* Added idempotent upsert capabilities in `PUT /runs/{run_id}` to support seamless synchronization with the automation runner.
* Preserved visual defect `rationale` strings across all finding serializers to empower human QA reviewers.

### Day 4: Pull Request Automation, GitHub Webhooks & Batch Metrics
* Implemented PyGithub automated PR service (`backend/app/services/github_service.py`) with branch creation, commit creation, and automated label assignment (`omnisight`, `automated-fix`).
* Built GitHub webhook receiver (`POST /webhook/github`) for tracking human review decisions and PR merge events in real time.
* Added multi-dimensional query filtering to `GET /runs` (`branch`, `scenario`, `target`, `has_pr`, `has_issues`).
* Implemented high-performance aggregate batch metrics summary (`GET /runs/metrics/summary`) computing defect distributions and clean run rates.
* Built GitHub Markdown evidence exporter (`GET /runs/{run_id}/export-evidence-markdown`).

### Day 5: Verification Retest Result Synchronization & Audit Event Timeline
* Implemented `POST /runs/{run_id}/retest-result` to receive proof outcomes from isolated sandbox verification runs.
* Automatically transitions run lifecycle from `verifying` &rarr; `fixed` (when verified) or `needs_review` (when retest fails).
* Stores `visual_diff_score` (e.g. 0.00% pixel mismatch) and retest before/after screenshot paths.
* Built automated PR verification proof updater (`POST /runs/{run_id}/update-pr-verification`) attaching verified proof tables and status badges to open PRs.
* Implemented chronological event logging with unique event IDs and exposed `GET /runs/{run_id}/timeline`.
* Added partial finding status remediation endpoint (`PATCH /runs/{run_id}/findings/{finding_id}`).

### Day 6: CSS AST Security Hardening, Forensics & Production Readiness
* Hardened `validate_css_safety` against CSS `expression()`, dangerous `javascript:` URI schemes, and `data:text/html` injection payloads.
* Enhanced `ActionEngine` with smart quote normalization (`“`, `”`, `‘`, `’`) and Python single-quoted dictionary recovery (`ast.literal_eval`).
* Implemented complete forensic audit bundle export (`GET /runs/{run_id}/export-bundle`) containing run summaries, findings, diffs, validation logs, retest metrics, and timeline events in a unified JSON archive.
* Standardized timezone handling for Python 3.11+ using `timezone.utc` with fallback resilience.
* Finalized system milestone registry at `GET /api/milestones`.

---

## 3. Comprehensive Test Matrix (97 Passing Tests)

```bash
$ pytest backend/tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\Kailash\.gemini\antigravity-ide\scratch\OmniSight
collected 97 items

backend\tests\test_action_engine.py ............                         [ 12%]
backend\tests\test_api.py .....................................          [ 50%]
backend\tests\test_patch_validator.py ......................             [ 73%]
backend\tests\test_pr_automation.py .........                            [ 82%]
backend\tests\test_schemas.py .................                          [100%]

======================== 97 passed, 1 warning in 2.21s ========================
```

| Test Suite | File | Tests | Coverage Scope |
| :--- | :--- | :---: | :--- |
| **Multimodal Parser** | `test_action_engine.py` | 12 | Prose extraction, code fences, single quotes, smart quotes, confidence normalization. |
| **API Gateway & Lifecycle** | `test_api.py` | 37 | Health, build webhooks, run queries, metrics, retest ingestion, timeline, forensic bundle. |
| **Zero-Trust Validator** | `test_patch_validator.py` | 22 | Traversal defense, allowlist checks, CSS AST safety, expressions, protocol checks. |
| **PR Automation** | `test_pr_automation.py` | 9 | Branch creation, PR generation, label assignment, retest comment formatting, mock fallback. |
| **Schemas & Models** | `test_schemas.py` | 17 | Pydantic v2 constraints, enum resilience, timeline events, retest payloads, serializations. |
| **Total Backend Suite** | **OmniSight Backend** | **97** | **100% Pass Rate Across All Suites** |

---

## 4. Verification Checkpoints

1. **Python Compatibility**:
   - Backend requires and targets **Python 3.11+**.
   - Timezone operations use `timezone.utc` ensuring zero deprecation warnings and cross-version compatibility.
2. **Quote Resilience**:
   - Action Engine successfully parses standard JSON double quotes, single-quoted Python dictionaries, and rich Unicode curly quotes.
3. **Zero Hardcoded Secrets**:
   - GitHub tokens, repository names, and API keys are strictly parameterized via environment variables and Terraform variables.
4. **Isolated Sandbox Verification**:
   - Every approved patch requires sandbox retest proof before PR verification status is upgraded to `fixed`.
