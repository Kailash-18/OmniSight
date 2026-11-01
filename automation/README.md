# OmniSight Automation

Autonomous browser automation, multimodal visual QA, and self-healing engine for OmniSight.

---

## 📌 Overview

OmniSight Automation drives headless browser journeys to find visual defects (overlap, clipping, occlusion) that standard functional tests miss. It ground-truths Vision-Language Model (VLM) findings with DOM spatial geometry, applies unified CSS fixes inside an isolated sandbox with atomic rollback, computes pixel-level visual diffs, and compiles tamper-evident SHA-256 forensic audit bundles.

---

## 📁 Architecture & Minimal File Structure

The automation engine is organized into minimal, cohesive modules:

| File | Purpose | Key Responsibilities |
| :--- | :--- | :--- |
| [`core.py`](file:///automation/core.py) | **Configuration & Data Schemas** | Responsive viewport presets, Pydantic defect finding schemas (`Finding`, `ProposedPatch`, `VisualAuditReport`), and `EvidenceCollector` for screenshots/DOM snapshots. |
| [`engine.py`](file:///automation/engine.py) | **RPA, Geometry & Verification Engine** | Headless Playwright runner (`StoreJourney`), pure-Python Axis-Aligned Bounding Box spatial analyzer (`SpatialAnalyzer`), pixel diffing (`VisualComparator`), patch sandbox with rollback (`PatchSandbox`), and cryptographic packaging (`ForensicBundler`). |
| [`orchestrator.py`](file:///automation/orchestrator.py) | **Closed-Loop Orchestration & Backend Bridge** | State machine (`AgentState`, `Orchestrator`) coordinating Inspect &rarr; Audit &rarr; Patch &rarr; Retest &rarr; Release, and `BackendClient` for FastAPI gateway sync. |
| [`cli.py`](file:///automation/cli.py) | **Command-Line Entrypoint** | Terminal interface to run audits with customizable flags. |

---

## 🚀 Quickstart & Usage

### 1. Basic Visual Audit
Run headless Chromium checkout journey and detect visual defects:
```bash
python -m automation.cli --target http://localhost:5173
```

### 2. Retest Verification & Forensic Bundling
Apply proposed CSS patch in an isolated sandbox, calculate pixel delta, and generate SHA-256 archive:
```bash
python -m automation.cli --target http://localhost:5173 --bundle-forensics
```

### 3. Full Closed-Loop with Backend Sync & Automated PR
Sync lifecycle events to the FastAPI gateway and open a GitHub PR upon verified fix:
```bash
python -m automation.cli --target http://localhost:5173 --sync-backend --auto-pr --bundle-forensics
```

---

## ⚙️ Key CLI Options

- `--target <url>`: Target web application URL (default: `http://127.0.0.1:5173`).
- `--viewports <list>`: Selected viewports (`desktop_1440x900`, `desktop_1280x800`, `mobile_390x844`, `mobile_375x667`).
- `--no-retest`: Skip sandboxed retesting.
- `--auto-pr`: Automatically open a GitHub Pull Request upon verified remediation.
- `--bundle-forensics`: Create an immutable ZIP bundle with `checksums.sha256` and `forensic_manifest.json`.
- `--sync-backend`: Stream progress and findings to the FastAPI gateway (`http://127.0.0.1:8000`).
- `--json-output`: Output results as structured JSON for CI/CD integration.

---

## 🧪 Testing

Run the full automation test suite:
```bash
python -m pytest automation/tests
```
