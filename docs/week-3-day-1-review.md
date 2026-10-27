# OmniSight — Week 3 Day 1 Backend Deliverables & Review Report

> **Milestone**: Week 3 (Day 1) Autonomous Self-Healing Lifecycle, Gateway API Expansion, and Zero-Trust Hardening  
> **Author**: Member 1 (Sri Khyathi)  
> **Target Branch**: `khyathi` &rarr; `backend-dev` (Pull Request [#17](https://github.com/Kailash-18/OmniSight/pull/17))  
> **Status**: Completed & Verified (108 Passing Tests, 100% Pass Rate)  
> **Date**: October 27, 2026  
> **Python Target**: Python 3.10+ / 3.11+  
> **Scope**: High-frequency status polling, bounded retry tracking, run deletion lifecycle, live GitHub PR status synchronization, Windows reserved device name validation, CSS AST script defense, patch risk scoring, multimodal code block fence tolerance, and defect synonym normalization.

---

## 1. Executive Summary

Member 1 has kicked off **Week 3 (Day 1)** of the OmniSight autonomous visual self-healing platform by expanding the core FastAPI gateway into a robust lifecycle controller and hardening security boundaries. 

In accordance with the Week 3 project roadmap (*"Self-Healing + PR Automation & Lifecycle Orchestration"*), Member 1 expanded test coverage from 97 passing tests (Week 2 Final) to **108 automated passing tests** across unit, security, integration, and serialization test suites.

```mermaid
flowchart TD
    subgraph Automation & CI Triggers
        CLI[Automation CLI / Dashboard] -->|GET /runs/{id}/status| GW[FastAPI Gateway]
        CLI -->|POST /runs/{id}/retry| GW
        CLI -->|DELETE /runs/{id}| GW
        GH_SYNC[Remote GitHub Poll] -->|GET /runs/{id}/pr-status| GW
    end

    subgraph Intelligence & Parsing
        GW -->|Raw Prose & Code Fences| AE[Action Engine]
        AE -->|Case-Insensitive & Tilde Parser| CF[Code Block Extractor]
        AE -->|Category & Severity Synonyms| NORM[Normalizer Engine]
        NORM --> PARSER[Pydantic v2 Models]
    end

    subgraph Zero-Trust Security Layer
        PARSER --> SEC[Zero-Trust Patch Validator]
        SEC -->|Path Traversal & Windows Device Names| C1{Clean Relative?}
        SEC -->|CRLF & Whitespace Normalizer| C2{Normalized Diff?}
        SEC -->|CSS AST: url / expression / vbscript| C3{Safe CSS?}
        SEC -->|assess_patch_risk| RISK[Risk Assessment Engine]
        C1 & C2 & C3 --> APPR[Approved Patch]
    end

    subgraph Automated Remediation
        APPR --> PR_ENG[PyGithub PR Automation]
        PR_ENG -->|sanitize_git_branch_name| BR[Safe Git Ref]
        PR_ENG -->|create_pull_request_for_fix| OPEN_PR[Evidence-Backed PR]
        PR_ENG -->|check_pull_request_status| STATUS[PR State Tracker]
        PR_ENG -->|close_pull_request| CLOSE[PR Closure Flow]
    end
```

---

## 2. Week 3 Day 1 Engineering Deliverables Breakdown

### A. Gateway Lifecycle Expansion & Management Routes
* **Lightweight Status Polling (`GET /runs/{run_id}/status`)**:
  - Implemented high-frequency polling endpoint returning status, start time, target, and error fields without serializing heavy forensic screenshot evidence bundles.
  - Minimizes serialization lag and bandwidth overhead for automation test loops.
* **Bounded Audit Run Retry (`POST /runs/{run_id}/retry`)**:
  - Implemented automated retry mechanism with configurable iteration ceiling (`max_retries = 3` default).
  - Automatically transitions runs exceeding retry limits to `needs_review` and appends `retry_exhausted` timeline events, preventing runaway self-healing loops.
* **Run Deletion with In-Memory State Cleanup (`DELETE /runs/{run_id}`)**:
  - Implemented safe run deletion endpoint that releases in-memory run dictionary entries and returns structured deletion confirmation.
* **Live GitHub PR Status Synchronization (`GET /runs/{run_id}/pr-status`)**:
  - Added real-time polling to verify if an open pull request has been merged or closed on GitHub.
  - Automatically transitions run state to `fixed` upon merge confirmation and appends `pr_merged_verified` events to the audit timeline.
* **Milestone Registry Expansion (`GET /api/milestones`)**:
  - Updated registry tracking 108 passing tests, runtime compatibility, and security allowlists.

### B. Zero-Trust Security Hardening & Risk Assessment
* **Windows Reserved Device Name Defense**:
  - Rejects device names in target paths (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`), preventing filesystem hangs and unauthorized handle access on Windows operating systems.
* **CRLF & Trailing Whitespace Normalization**:
  - Normalized multi-platform line endings (`\r\n` &rarr; `\n`) and trailing whitespace in unified diffs before validator parsing.
* **CSS Safety Protocol Defense**:
  - Hardened `validate_css_safety` against `vbscript:`, dangerous `url()` wrappers, and obfuscated `javascript:` URI schemes.
* **Automated Patch Risk Assessment (`assess_patch_risk`)**:
  - Introduced automated blast radius scoring evaluating modified line count, selector scope, and file extensions.
  - Tags pure CSS style fixes under 40 lines as `auto_merge_eligible = True`, while escalating larger or JSX/JS diffs to mandatory human QA review.

### C. Multimodal Action Engine Resilience
* **Flexible Markdown Code Fence Support**:
  - Extended `ActionEngine.extract_code_blocks` regex to support case-insensitive language identifiers (e.g. ````JSON````, ````Css````, ````DIFF````) and alternative tilde fences (`~~~json`).
* **Defect Category & Severity Synonym Mapping**:
  - Added mapping dictionaries normalizing non-standard VLM classifications (e.g., `overlap` &rarr; `element_overlap`, `clipping` &rarr; `element_clipping`, `blocker` &rarr; `critical`, `trivial` &rarr; `low`).

### D. GitHub PR Automation Service Hardening
* **Git Ref & Branch Name Sanitization (`sanitize_git_branch_name`)**:
  - Cleans arbitrary run identifiers and scenario strings, stripping disallowed characters (`~`, `^`, `:`, `?`, `*`, `[`, `]`, `\`, `@`, `{`, `}`) and duplicate slashes to ensure valid Git refs.
* **Visual Diff Metric Formatting Resilience**:
  - Safely handles non-numeric strings, percentage strings, and floating-point scores when constructing verification tables in `update_pull_request_verification_proof`.
* **PR Lifecycle Helper Functions**:
  - Implemented `check_pull_request_status` and `close_pull_request` helper workflows for programmatic review management.
* **PyGithub Type Annotation Compatibility**:
  - Added explicit `# pyrefly: ignore[missing-import]` annotations and UTF-8 header encoding for reliable cross-IDE diagnostics.

---

## 3. Commit History Audit (Week 3 Day 1 Commits)

All commits are authored by Member 1 (Sri Khyathi) and tracked on branch `khyathi`:

| # | Commit SHA | Type / Scope | Description |
| :---: | :---: | :--- | :--- |
| 1 | `115294e` | `fix(backend)` | Remove datetime.UTC import in main.py and restore Python 3.10+ compatibility |
| 2 | `70bb982` | `fix(backend)` | Synchronize Python 3.11+ runtime badges and resilient UTC import |
| 3 | `1ad594e` | `fix(backend)` | Isolate Python 3.10+ UTC compatibility to backend and align with main |
| 4 | `4fa0b87` | `fix(contract)` | Normalize screenshots and before_screenshots aliases across backend schemas and contract |
| 5 | `00ec16f` | `fix(ide)` | Configure python analysis extra paths to resolve backend modules in ide |
| 6 | `12945cc` | `fix(github)` | Add utf-8 encoding header and resilient backend path resolution in github service |
| 7 | `cfbbf03` | `fix(github)` | Improve type annotations and generic collection imports in github service |
| 8 | `d05ba3f` | `fix(github)` | Handle non-numeric visual diff scores safely in pr verification proof |
| 9 | `02801be` | `fix(github)` | Sanitize git branch names to prevent ref creation errors |
| 10 | `ba36d64` | `refactor(github)` | Robustly handle file node lookups and head branch references in pr creation |
| 11 | `3605eda` | `feat(github)` | Implement pr status check and close helper functions |
| 12 | `606df08` | `test(github)` | Add unit tests for branch name sanitization and score formatting resilience |
| 13 | `0e4e55c` | `test(github)` | Add tests for pr status check and pr closure workflows |
| 14 | `e030b2a` | `fix(security)` | Reject windows reserved device names in patch file paths |
| 15 | `9f60015` | `fix(security)` | Normalize crlf line endings and whitespace in patch diff validator |
| 16 | `6fb221b` | `feat(security)` | Harden css safety validator against encoded javascript and vbscript schemes |
| 17 | `0ca47d4` | `feat(security)` | Introduce risk assessment helper for patch auto-merge eligibility |
| 18 | `0f76a45` | `test(validator)` | Verify rejection of windows reserved device names and encoded scripts |
| 19 | `01ac064` | `fix(parser)` | Support case-insensitive markdown code fences in action engine |
| 20 | `e1ddce1` | `feat(parser)` | Add defect category and severity synonym mapping in action engine |
| 21 | `b3339d0` | `feat(schemas)` | Add lightweight run status and retry payload schemas |
| 22 | `9db555b` | `feat(api)` | Add lightweight run status polling endpoint for automation loop |
| 23 | `eb63698` | `feat(api)` | Implement audit run retry endpoint with bounded iteration tracking |
| 24 | `c2cb62b` | `feat(api)` | Implement run deletion endpoint with timeline cleanup |
| 25 | `a218c1b` | `feat(api)` | Add live github pr status synchronization endpoint |
| 26 | `ceedc0b` | `test(api)` | Add comprehensive integration tests for status polling, retry, and deletion endpoints |
| 27 | `f2a5f64` | `feat(milestones)` | Register lifecycle and api expansion deliverables with 108 tests |
| 28 | `b933465` | `fix(github)` | Add pyrefly ignore annotation to eliminate ide missing-import error |
| 29 | `721b360` | `docs(review)` | Add backend gateway lifecycle and pr automation deliverables report |

---

## 4. Test Matrix & Verification (108 Passing Tests)

```bash
$ pytest backend/tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\Kailash\.gemini\antigravity-ide\scratch\OmniSight
collected 108 items

backend\tests\test_action_engine.py ..............                       [ 12%]
backend\tests\test_api.py .........................................      [ 50%]
backend\tests\test_patch_validator.py ........................           [ 73%]
backend\tests\test_pr_automation.py .............                        [ 85%]
backend\tests\test_schemas.py ................                           [100%]

======================= 108 passed, 1 warning in 0.95s =======================
```

| Test Suite | File | Tests | Coverage Scope |
| :--- | :--- | :---: | :--- |
| **Multimodal Parser** | `test_action_engine.py` | 14 | Case-insensitive fences, tilde fences, synonym normalization, smart quote recovery. |
| **API Gateway & Lifecycle** | `test_api.py` | 41 | Health check, webhooks, filtering, metrics, retest result ingestion, timeline, forensic bundle, status polling, retry bounds, deletion, live PR sync. |
| **Zero-Trust Validator** | `test_patch_validator.py` | 24 | Windows device names, path traversal, CRLF normalization, CSS AST safety, risk assessment. |
| **PR Automation** | `test_pr_automation.py` | 13 | Branch sanitization, PR creation, formatted diff score resilience, PR status checks, PR closure. |
| **Schemas & Models** | `test_schemas.py` | 16 | Lightweight status schemas, retry payloads, timeline event models, enum fallbacks. |
| **Total Backend Suite** | **OmniSight Backend** | **108** | **100% Pass Rate** |

---

## 5. Security & Verification Checkpoints

1. **Pull Request Routing**:
   - Pull Request [#17](https://github.com/Kailash-18/OmniSight/pull/17) targets `backend-dev` as its base branch (**not `main`**).
   - The PR remains in an open, unmerged state pending human QA and team lead review.
2. **Zero Hardcoded Secrets**:
   - Environment variables parameterized via centralized `settings`.
   - Mock fallback ensures fully offline testing without requiring live GitHub API tokens.
3. **Bounded Automation Guardrails**:
   - Self-healing retries are bounded to prevent infinite re-trigger cycles.
   - Patches exceeding allowable lines or targeting executable JavaScript files automatically require manual review.
