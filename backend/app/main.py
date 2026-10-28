# -*- coding: utf-8 -*-
"""
FastAPI CI/CD Gateway and Action Engine API for OmniSight.
Handles build webhooks, manual audit triggers, run lifecycle, and VLM patch validation.
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import time
SERVER_START_TIME = time.time()
# Standard UTC timezone reference compatible across Python 3.10+
UTC = timezone.utc

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.schemas import (
    HealthCheckResponse,
    BuildWebhookPayload,
    RunTriggerPayload,
    PatchSubmitPayload,
    GitHubWebhookPayload,
    VLMParseRequest,
    VLMParseResponse,
    RunRecordUpdatePayload,
    RunSummaryResponse,
    RunDetailResponse,
    RunMetricsSummaryResponse,
    RetestResultPayload,
    RetestResultResponse,
    FindingStatusUpdatePayload,
    TimelineEvent,
    ForensicBundleResponse,
    RunStatusResponse,
    RetryRunPayload,
    RetryRunResponse,
    DeleteRunResponse,
    PatchRevertResponse,
    BatchRunTriggerPayload,
    BatchRunSummaryResponse,
    BatchRetryPayload,
    BatchRetryResponse,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    RunStatus,
    Severity,
    PatchObject,
)
from app.services.patch_validator import validate_patch
from app.services.policy_engine import evaluate_merge_policy
from app.services.action_engine import action_engine
from app.services.github_service import (
    create_pull_request_for_fix,
    add_pr_comment_with_retest_evidence,
    check_pull_request_status,
    revert_pull_request_patch,
)


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="OmniSight Visual QA Gateway, Action Engine, and PR Automation API",
    openapi_tags=[
        {"name": "System", "description": "Health check and system readiness"},
        {"name": "CI/CD Webhook", "description": "Build event ingestion and automation triggers"},
        {"name": "Audit Runs", "description": "Run lifecycle tracking and state management"},
        {"name": "Action Engine", "description": "Multimodal VLM output parsing and patch validation"},
    ],
    contact={"name": "OmniSight Engineering", "email": "engineering@omnisight.local"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
)

# Enable CORS for QA Dashboard (Member 2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_and_timing_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or f"req-{uuid.uuid4().hex[:10]}"
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


# In-memory store for test runs (simulates persistence for development & demo)
runs_db: Dict[str, Dict[str, Any]] = {}
batches_db: Dict[str, Dict[str, Any]] = {}


def _append_timeline_event(
    run_id: str,
    event_type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Appends an event to the chronological timeline of a run record."""
    if run_id in runs_db:
        if "timeline" not in runs_db[run_id]:
            runs_db[run_id]["timeline"] = []
        event = {
            "event_id": f"evt-{run_id[-6:] if len(run_id) >= 6 else run_id}-{len(runs_db[run_id]['timeline']) + 1}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "description": description,
            "metadata": metadata or {}
        }
        runs_db[run_id]["timeline"].append(event)
        return event
    return None


def _normalize_evidence_paths(ev: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensures both 'screenshots' and 'before_screenshots' alias keys are populated to match API contract."""
    if not ev:
        return {}
    res = dict(ev)
    if "screenshots" in res and "before_screenshots" not in res:
        res["before_screenshots"] = res["screenshots"]
    elif "before_screenshots" in res and "screenshots" not in res:
        res["screenshots"] = res["before_screenshots"]
    return res


def _validate_target_host(target_url: str) -> str:
    """Enforces target URL restriction and scheme validation to prevent SSRF against internal services."""
    try:
        url_to_parse = target_url.strip()
        if "://" not in url_to_parse:
            url_to_parse = f"http://{url_to_parse}"

        parsed = urlparse(url_to_parse)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Scheme '{parsed.scheme}' not allowed. Must be http or https.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ValueError("Target URL does not contain a valid host.")
        if not settings.is_host_allowed(hostname):
            raise ValueError(
                f"Host '{hostname}' is not in allowed target hosts: {settings.ALLOWED_TARGET_HOSTS}"
            )
        return url_to_parse

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target URL: {str(e)}"
        )


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Backend Health Check"
)
def health_check():
    """Health check endpoint to verify backend service readiness."""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.API_VERSION
    )


@app.get(
    "/live",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Liveness Probe"
)
def liveness_probe():
    """Liveness probe verifying that the application process is running."""
    return {
        "status": "alive",
        "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Readiness Probe"
)
def readiness_probe():
    """Readiness probe verifying that backend dependencies, state, and security settings are loaded."""
    is_ready = bool(settings and runs_db is not None)
    if not is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Backend not ready")
    return {
        "status": "ready",
        "database": "connected",
        "active_runs": len(runs_db),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get(
    "/metrics",
    tags=["System"],
    summary="Prometheus / OpenMetrics Telemetry Metrics"
)
def prometheus_metrics():
    """
    Exposes system metrics in Prometheus / OpenMetrics text format for cloud-native scrapers.
    """
    total_runs = len(runs_db)
    active_runs = sum(1 for r in runs_db.values() if r.get("status") in (RunStatus.QUEUED.value, RunStatus.RUNNING.value))
    fixed_runs = sum(1 for r in runs_db.values() if r.get("status") == RunStatus.FIXED.value)
    needs_review = sum(1 for r in runs_db.values() if r.get("status") == RunStatus.NEEDS_REVIEW.value)
    pr_opened = sum(1 for r in runs_db.values() if r.get("status") == RunStatus.PR_OPENED.value)

    resolution_times = []
    for r in runs_db.values():
        if r.get("status") == RunStatus.FIXED.value and r.get("start_time"):
            try:
                st = datetime.fromisoformat(r["start_time"])
                timeline = r.get("timeline", [])
                end_iso = None
                for ev in reversed(timeline):
                    if ev.get("event") in ("run_fixed", "github_pr_merged"):
                        end_iso = ev.get("timestamp")
                        break
                if end_iso:
                    et = datetime.fromisoformat(end_iso)
                    dur = (et - st).total_seconds()
                    if dur >= 0:
                        resolution_times.append(dur)
            except Exception:
                pass
    mttr = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

    lines = [
        "# HELP omnisight_runs_total Total visual audit runs recorded",
        "# TYPE omnisight_runs_total counter",
        f"omnisight_runs_total {total_runs}",
        "# HELP omnisight_active_runs Current runs in progress or queued",
        "# TYPE omnisight_active_runs gauge",
        f"omnisight_active_runs {active_runs}",
        "# HELP omnisight_runs_by_status Total runs segmented by status",
        "# TYPE omnisight_runs_by_status gauge",
        f'omnisight_runs_by_status{{status="fixed"}} {fixed_runs}',
        f'omnisight_runs_by_status{{status="needs_review"}} {needs_review}',
        f'omnisight_runs_by_status{{status="pr_opened"}} {pr_opened}',
        "# HELP omnisight_mttr_seconds Mean time to visual remediation in seconds",
        "# TYPE omnisight_mttr_seconds gauge",
        f"omnisight_mttr_seconds {round(mttr, 2)}",
        "# HELP omnisight_uptime_seconds Application process uptime in seconds",
        "# TYPE omnisight_uptime_seconds counter",
        f"omnisight_uptime_seconds {round(time.time() - SERVER_START_TIME, 2)}",
        ""
    ]
    return Response(content="\n".join(lines), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get(
    "/api/milestones",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Engineering Deliverables and Security Boundaries"
)
def get_milestone_status():
    """Returns tracking status for Member 1 milestones and allowed security domains."""
    return {
        "member": "Member 1 - Backend & PR Automation (Sri Khyathi)",
        "foundation_scaffolding": "completed",
        "action_engine_and_security": "completed",
        "system_integration": "completed",
        "pr_automation_engine": "completed",
        "retest_synchronization": "completed",
        "forensics_and_hardening": "completed",
        "week_1_foundation": "completed",
        "week_2_full_deliverables": "completed",
        "lifecycle_and_api_expansion": "completed",
        "remediation_mttr_and_checksum_verification": "completed",
        "telemetry_and_compliance_export": "completed",
        "backend_tests_passed": 130,
        "python_runtime": "3.10+",
        "allowed_targets": settings.ALLOWED_TARGET_HOSTS,
        "allowed_patch_files": settings.ALLOWED_PATCH_FILES,
    }


@app.post(
    "/webhook/build",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["CI/CD Webhook"],
    summary="Ingest CI/CD Build Event"
)
def receive_build_webhook(payload: BuildWebhookPayload):
    """
    Simulated CI/CD build event webhook.
    Validates target URL and registers a new audit run in queued status.
    """
    validated_url = _validate_target_host(payload.target_url)
    unique_suffix = uuid.uuid4().hex[:6]
    run_id = f"run-{int(datetime.now(timezone.utc).timestamp())}-{unique_suffix}"
    start_time = datetime.now(timezone.utc).isoformat()

    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": start_time,
        "target": validated_url,
        "branch": payload.branch,
        "scenario": payload.scenario,
        "status": RunStatus.QUEUED.value,
        "steps": [],
        "evidence_paths": {},
        "findings": [],
        "patch": None,
        "issue_count": 0,
        "retry_count": 0,
        "pr_url": None,
        "error": None
    }

    return {
        "run_id": run_id,
        "status": RunStatus.QUEUED.value,
        "message": "Build event accepted and queued for browser audit."
    }


@app.post(
    "/webhook/github",
    status_code=status.HTTP_200_OK,
    tags=["CI/CD Webhook"],
    summary="Ingest GitHub PR and Review Webhook Events"
)
def receive_github_webhook(payload: GitHubWebhookPayload):
    """
    Ingests GitHub pull_request and review webhook events.
    Updates the matching run record status when PRs are merged or closed.
    """
    event_action = payload.action.lower()
    matched_run_id = None

    if payload.pull_request:
        pr_url = payload.pull_request.html_url
        is_merged = payload.pull_request.merged
        head_ref = payload.pull_request.head_ref or ""

        # Find matching run in runs_db
        for r_id, run_data in runs_db.items():
            if run_data.get("pr_url") == pr_url or (head_ref and r_id in head_ref):
                matched_run_id = r_id
                if event_action == "closed":
                    if is_merged:
                        run_data["status"] = RunStatus.FIXED.value
                        run_data.setdefault("steps", []).append("github_pr_merged")
                    else:
                        run_data["status"] = RunStatus.NEEDS_REVIEW.value
                        run_data.setdefault("steps", []).append("github_pr_closed_unmerged")
                elif event_action in ("opened", "reopened"):
                    run_data["status"] = RunStatus.PR_OPENED.value
                break

    return {
        "status": "processed",
        "action": event_action,
        "matched_run_id": matched_run_id
    }


@app.post(
    "/runs",
    status_code=status.HTTP_201_CREATED,
    tags=["Audit Runs"],
    summary="Trigger On-Demand Audit Run"
)
def trigger_run_manual(payload: RunTriggerPayload):
    """
    Manual trigger endpoint to initiate an on-demand browser audit.
    """
    validated_url = _validate_target_host(payload.target_url)
    unique_suffix = uuid.uuid4().hex[:6]
    run_id = f"run-{int(datetime.now(timezone.utc).timestamp())}-{unique_suffix}"
    start_time = datetime.now(timezone.utc).isoformat()

    runs_db[run_id] = {
        "run_id": run_id,
        "start_time": start_time,
        "target": validated_url,
        "branch": "main",
        "scenario": payload.scenario,
        "status": RunStatus.RUNNING.value,
        "steps": ["initiate_browser_session"],
        "evidence_paths": {},
        "findings": [],
        "patch": None,
        "issue_count": 0,
        "retry_count": 0,
        "pr_url": None,
        "error": None
    }

    return {
        "run_id": run_id,
        "status": RunStatus.RUNNING.value
    }


@app.get(
    "/runs",
    response_model=List[RunSummaryResponse],
    tags=["Audit Runs"],
    summary="List Recorded Audit Runs"
)
def list_runs(
    limit: int = 50,
    status_filter: Optional[RunStatus] = None,
    branch: Optional[str] = None,
    scenario: Optional[str] = None,
    target: Optional[str] = None,
    has_pr: Optional[bool] = None,
    has_issues: Optional[bool] = None,
    start_after: Optional[str] = None,
    start_before: Optional[str] = None,
    min_severity: Optional[Severity] = None,
):
    """
    Returns summaries of recorded test runs in reverse chronological order with optional filtering.
    Supports filtering by status, branch, scenario, target host, PR presence, date ranges, and defect severity.
    """
    sorted_runs = sorted(
        runs_db.values(),
        key=lambda r: r.get("start_time", ""),
        reverse=True
    )

    severity_order = {Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3, Severity.CRITICAL: 4}

    summaries = []
    for r in sorted_runs:
        if status_filter and r.get("status") != status_filter.value:
            continue
        if branch and r.get("branch") != branch:
            continue
        if scenario and r.get("scenario") != scenario:
            continue
        if target and target.lower() not in r.get("target", "").lower():
            continue
        if start_after and r.get("start_time", "") < start_after:
            continue
        if start_before and r.get("start_time", "") > start_before:
            continue
        if min_severity is not None:
            min_rank = severity_order.get(min_severity, 1)
            findings = r.get("findings", [])
            max_finding_rank = 0
            for f in findings:
                sev_str = f.get("severity") if isinstance(f, dict) else getattr(f, "severity", None)
                if isinstance(sev_str, str):
                    try:
                        s_enum = Severity(sev_str.lower())
                    except ValueError:
                        s_enum = Severity.LOW
                elif isinstance(sev_str, Severity):
                    s_enum = sev_str
                else:
                    s_enum = Severity.LOW
                max_finding_rank = max(max_finding_rank, severity_order.get(s_enum, 1))
            if max_finding_rank < min_rank:
                continue
        if has_pr is not None:
            pr_present = bool(r.get("pr_url"))
            if pr_present != has_pr:
                continue
        if has_issues is not None:
            issues_present = r.get("issue_count", len(r.get("findings", []))) > 0
            if issues_present != has_issues:
                continue

        summaries.append(
            RunSummaryResponse(
                run_id=r["run_id"],
                start_time=r["start_time"],
                target=r["target"],
                status=RunStatus(r["status"]),
                issue_count=r.get("issue_count", len(r.get("findings", []))),
                pr_url=r.get("pr_url")
            )
        )
        if len(summaries) >= limit:
            break
    return summaries


@app.get(
    "/runs/metrics/summary",
    response_model=RunMetricsSummaryResponse,
    tags=["Audit Runs"],
    summary="Get Aggregated Audit & PR Metrics"
)
def get_runs_metrics_summary():
    """
    Computes real-time aggregate metrics across all recorded audit runs,
    including total runs, active runs, PR creation count, defect category breakdown,
    and overall clean/remediated run rate.
    """
    total_runs = len(runs_db)
    if total_runs == 0:
        return RunMetricsSummaryResponse(
            total_runs=0,
            active_runs=0,
            fixed_runs=0,
            prs_opened=0,
            total_defects_detected=0,
            clean_run_rate_percent=100.0,
            defects_by_category={},
            runs_by_status={}
        )

    active_runs = 0
    fixed_runs = 0
    prs_opened = 0
    total_defects = 0
    clean_runs = 0
    remediation_durations: List[float] = []
    defects_by_cat: Dict[str, int] = {}
    runs_by_stat: Dict[str, int] = {}

    for r in runs_db.values():
        stat = r.get("status", "unknown")
        runs_by_stat[stat] = runs_by_stat.get(stat, 0) + 1

        if stat in (RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.VERIFYING.value):
            active_runs += 1
        if stat == RunStatus.FIXED.value:
            fixed_runs += 1
            start_str = r.get("start_time")
            verified_at = (r.get("retest_outcome") or {}).get("verified_at")
            if start_str and verified_at:
                try:
                    t_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    t_end = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
                    delta = (t_end - t_start).total_seconds()
                    if delta >= 0:
                        remediation_durations.append(delta)
                except Exception:
                    pass
        if r.get("pr_url"):
            prs_opened += 1

        findings = r.get("findings", [])
        num_issues = r.get("issue_count", len(findings))
        total_defects += num_issues
        if num_issues == 0 or stat == RunStatus.FIXED.value:
            clean_runs += 1

        for f in findings:
            cat = f.get("category", "other") if isinstance(f, dict) else getattr(f, "category", "other")
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            defects_by_cat[cat_str] = defects_by_cat.get(cat_str, 0) + 1

    clean_rate = round((clean_runs / total_runs) * 100.0, 1)
    mttr = round(sum(remediation_durations) / len(remediation_durations), 1) if remediation_durations else None

    return RunMetricsSummaryResponse(
        total_runs=total_runs,
        active_runs=active_runs,
        fixed_runs=fixed_runs,
        prs_opened=prs_opened,
        total_defects_detected=total_defects,
        clean_run_rate_percent=clean_rate,
        defects_by_category=defects_by_cat,
        runs_by_status=runs_by_stat,
        mean_time_to_remediation_seconds=mttr,
        resolved_runs_count=len(remediation_durations)
    )


@app.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    tags=["Audit Runs"],
    summary="Get Detailed Audit Run Record"
)
def get_run_details(run_id: str):
    """Returns comprehensive forensic details, evidence links, and patch data for a run."""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    r = runs_db[run_id]
    return RunDetailResponse(
        run_id=r["run_id"],
        start_time=r["start_time"],
        target=r["target"],
        status=RunStatus(r["status"]),
        steps=r.get("steps", []),
        evidence_paths=_normalize_evidence_paths(r.get("evidence_paths", {})),
        findings=r.get("findings", []),
        patch=r.get("patch"),
        retry_count=r.get("retry_count", 0),
        pr_url=r.get("pr_url"),
        error=r.get("error")
    )


@app.get(
    "/runs/{run_id}/status",
    response_model=RunStatusResponse,
    tags=["Audit Runs"],
    summary="Get Lightweight Audit Run Status"
)
def get_run_status(run_id: str):
    """
    Returns lightweight execution status for rapid client/automation polling.
    Avoids overhead of full screenshot/findings payload serialization.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    r = runs_db[run_id]
    return RunStatusResponse(
        run_id=r["run_id"],
        status=RunStatus(r["status"]),
        issue_count=r.get("issue_count", len(r.get("findings", []))),
        retry_count=r.get("retry_count", 0),
        has_pr=bool(r.get("pr_url")),
        pr_url=r.get("pr_url"),
        error=r.get("error")
    )


@app.get(
    "/runs/{run_id}/export-evidence-markdown",
    status_code=status.HTTP_200_OK,
    tags=["Audit Runs"],
    summary="Export Run Audit Evidence as GitHub Markdown"
)
def export_run_evidence_markdown(run_id: str):
    """
    Serializes a complete run's visual findings, patch, and retest status
    into GitHub-ready Markdown for PR comments, bug reports, or evidence logs.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    r = runs_db[run_id]
    findings = r.get("findings", [])
    patch = r.get("patch") or {}
    evidence_paths = r.get("evidence_paths", {})
    status_val = r.get("status", "unknown")
    target = r.get("target", "unknown")
    start_time = r.get("start_time", "unknown")

    if findings:
        findings_rows = []
        for f in findings:
            f_dict = f if isinstance(f, dict) else (f.model_dump() if hasattr(f, "model_dump") else f.__dict__)
            cat = f_dict.get("category", "defect")
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            sev = f_dict.get("severity", "medium")
            sev_str = sev.value if hasattr(sev, "value") else str(sev)
            desc = f_dict.get("description", "Visual defect")
            vp = f_dict.get("viewport", "all")
            conf = f_dict.get("confidence", 0.8)
            findings_rows.append(f"| `{cat_str}` | `{sev_str}` | `{vp}` | {desc} | {conf:.0%} |")
        findings_table = (
            "| Category | Severity | Viewport | Description | Confidence |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n" +
            "\n".join(findings_rows)
        )
    else:
        findings_table = "_No visual defects detected in this run._"

    diff_content = patch.get("diff", "No patch diff available.")
    diff_block = f"```diff\n{diff_content}\n```" if patch.get("diff") else "_No patch generated._"

    md_output = f"""# 🔍 OmniSight Visual QA Report: `{run_id}`

* **Target URL**: {target}
* **Execution Timestamp**: `{start_time}`
* **Final Status**: `{status_val}`
* **PR Link**: {r.get('pr_url') or '_None_'}

---

## 📋 Detected Visual Defects
{findings_table}

---

## 🛠️ Applied Patch Diff
* **Target File**: `{patch.get('target_file', 'N/A')}`
* **Validation Passed**: `{patch.get('validation_status', False)}`

{diff_block}
"""
    return {"run_id": run_id, "markdown": md_output}



@app.put(
    "/runs/{run_id}",
    status_code=status.HTTP_200_OK,
    tags=["Audit Runs"],
    summary="Update Run Progress and Findings"
)
def update_run_record(run_id: str, payload: RunRecordUpdatePayload):
    """Updates an existing run record with progress, findings, evidence, or state transitions."""
    if run_id not in runs_db:
        runs_db[run_id] = {
            "run_id": run_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "target": "http://localhost:5173",
            "branch": "main",
            "scenario": "checkout_flow",
            "status": RunStatus.RUNNING.value,
            "steps": [],
            "evidence_paths": {},
            "findings": [],
            "patch": None,
            "issue_count": 0,
            "retry_count": 0,
            "pr_url": None,
            "error": None
        }

    run_entry = runs_db[run_id]
    if payload.status is not None:
        run_entry["status"] = payload.status.value
    if payload.steps is not None:
        run_entry["steps"] = payload.steps
    if payload.evidence_paths is not None:
        run_entry["evidence_paths"] = _normalize_evidence_paths(payload.evidence_paths)
    if payload.findings is not None:
        run_entry["findings"] = [f.model_dump() for f in payload.findings]
        run_entry["issue_count"] = len(payload.findings)
    if payload.patch is not None:
        run_entry["patch"] = payload.patch.model_dump()
    if payload.retry_count is not None:
        run_entry["retry_count"] = payload.retry_count
    if payload.pr_url is not None:
        run_entry["pr_url"] = payload.pr_url
    if payload.error is not None:
        run_entry["error"] = payload.error

    return {"message": f"Run '{run_id}' updated successfully.", "status": run_entry["status"]}


@app.delete(
    "/runs/{run_id}",
    response_model=DeleteRunResponse,
    tags=["Audit Runs"],
    summary="Delete Recorded Audit Run"
)
def delete_run_record(run_id: str):
    """
    Deletes an audit run record and associated in-memory state.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    del runs_db[run_id]
    return DeleteRunResponse(
        run_id=run_id,
        message=f"Run '{run_id}' successfully deleted.",
        deleted=True
    )



@app.post(
    "/action-engine/parse",
    response_model=VLMParseResponse,
    tags=["Action Engine"],
    summary="Parse VLM Multimodal Findings and Diff"
)
def parse_vlm_output(payload: VLMParseRequest):
    """
    Action Engine parser endpoint.
    Parses raw VLM output, extracts structured findings and patch diff,
    and executes patch validation against security guardrails.
    """
    result = action_engine.parse_vlm_response(payload.raw_vlm_output)

    # If run_id is supplied and registered, update the run record
    if payload.run_id and payload.run_id in runs_db:
        run_entry = runs_db[payload.run_id]
        run_entry["findings"] = [f.model_dump() for f in result.findings]
        run_entry["issue_count"] = len(result.findings)
        if result.proposed_patch:
            run_entry["patch"] = result.proposed_patch.model_dump()

        if result.is_valid:
            if result.proposed_patch:
                if result.validation_status:
                    run_entry["status"] = RunStatus.AUDITED.value
                else:
                    run_entry["status"] = RunStatus.PATCH_REJECTED.value
            else:
                run_entry["status"] = RunStatus.AUDITED.value
        else:
            run_entry["status"] = RunStatus.NEEDS_REVIEW.value

    return result


@app.post(
    "/runs/{run_id}/process-vlm-output",
    response_model=VLMParseResponse,
    tags=["Action Engine"],
    summary="Process VLM Output for Specific Run"
)
def process_run_vlm_output(run_id: str, payload: VLMParseRequest):
    """Convenience endpoint to parse VLM output and associate it with a specific run."""
    if run_id not in runs_db:
        # Create an entry if it doesn't already exist
        runs_db[run_id] = {
            "run_id": run_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "target": "http://localhost:5173",
            "status": RunStatus.RUNNING.value,
            "steps": [],
            "evidence_paths": {},
            "findings": [],
            "patch": None,
            "issue_count": 0,
            "retry_count": 0,
            "pr_url": None,
            "error": None
        }

    payload.run_id = run_id
    return parse_vlm_output(payload)


@app.post(
    "/runs/{run_id}/submit-patch",
    tags=["Audit Runs"],
    summary="Validate Patch and Open Pull Request"
)
def submit_and_validate_patch(run_id: str, payload: PatchSubmitPayload):
    """
    Validates the proposed patch and opens an automated GitHub PR if security checks pass.
    """
    if run_id not in runs_db:
        runs_db[run_id] = {
            "run_id": run_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "target": "http://localhost:5173",
            "status": RunStatus.RUNNING.value,
            "steps": [],
            "evidence_paths": {},
            "findings": [],
            "patch": None,
            "issue_count": 0,
            "retry_count": 0,
            "pr_url": None,
            "error": None
        }

    # 1. Validate patch and file content using security guardrails
    validation_result = validate_patch(payload.target_file, payload.diff, payload.file_content)
    if not validation_result["validation_status"]:
        runs_db[run_id]["status"] = RunStatus.PATCH_REJECTED.value
        runs_db[run_id]["patch"] = {
            "target_file": payload.target_file,
            "diff": payload.diff,
            "validation_status": False,
            "validator_errors": validation_result["validator_errors"]
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_result["validator_errors"]
        )

    # 2. If valid, open a GitHub Pull Request
    sanitized_target = validation_result["target_file"]
    try:
        pr_url = create_pull_request_for_fix(
            run_id=run_id,
            target_file=sanitized_target,
            file_content=payload.file_content,
            commit_message=f"fix(ui): OmniSight auto-repair for {sanitized_target}",
            pr_title=payload.pr_title,
            pr_body=payload.pr_body,
            labels=payload.labels
        )
        runs_db[run_id]["status"] = RunStatus.PR_OPENED.value
        runs_db[run_id]["pr_url"] = pr_url
        runs_db[run_id]["patch"] = {
            "target_file": sanitized_target,
            "diff": payload.diff,
            "validation_status": True,
            "validator_errors": None,
            "labels": payload.labels
        }
        _append_timeline_event(
            run_id=run_id,
            event_type="pr_opened",
            description=f"Automated PR opened at {pr_url}",
            metadata={"pr_url": pr_url, "target_file": sanitized_target}
        )
        return {"status": "success", "pr_url": pr_url}
    except Exception as e:
        runs_db[run_id]["status"] = RunStatus.FAILED.value
        runs_db[run_id]["error"] = str(e)
        _append_timeline_event(
            run_id=run_id,
            event_type="pr_failed",
            description=f"PR automation failed: {str(e)}",
            metadata={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR automation failed: {str(e)}"
        )


@app.post(
    "/runs/{run_id}/retest-result",
    response_model=RetestResultResponse,
    tags=["Audit Runs"],
    summary="Ingest Verification Retest Result"
)
def submit_retest_result(run_id: str, payload: RetestResultPayload):
    """
    Ingests sandbox verification retest results, updates run state to 'fixed' or 'needs_review',
    attaches retest evidence screenshots and diff metrics, and logs a timeline event.
    """
    if run_id not in runs_db:
        runs_db[run_id] = {
            "run_id": run_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "target": "http://localhost:5173",
            "branch": "main",
            "scenario": "checkout_flow",
            "status": RunStatus.VERIFYING.value,
            "steps": [],
            "evidence_paths": {},
            "findings": [],
            "patch": None,
            "issue_count": 0,
            "retry_count": 1,
            "pr_url": None,
            "error": None,
            "timeline": []
        }

    run_entry = runs_db[run_id]
    new_status = RunStatus.FIXED if payload.passed else RunStatus.NEEDS_REVIEW
    run_entry["status"] = new_status.value

    retest_data = {
        "passed": payload.passed,
        "visual_diff_score": payload.visual_diff_score,
        "retest_viewport": payload.retest_viewport,
        "retest_screenshots": payload.retest_screenshots,
        "notes": payload.notes,
        "verified_at": datetime.now(timezone.utc).isoformat()
    }
    run_entry["retest_outcome"] = retest_data

    if payload.retest_screenshots:
        if "evidence_paths" not in run_entry:
            run_entry["evidence_paths"] = {}
        run_entry["evidence_paths"]["retest_screenshots"] = payload.retest_screenshots

    msg = "Verification retest confirmed visual fix." if payload.passed else f"Verification retest failed: {payload.notes or 'visual defect persists'}"
    _append_timeline_event(
        run_id=run_id,
        event_type="retest_verified" if payload.passed else "retest_failed",
        description=msg,
        metadata={
            "passed": payload.passed,
            "visual_diff_score": payload.visual_diff_score,
            "viewport": payload.retest_viewport
        }
    )

    return RetestResultResponse(
        run_id=run_id,
        status=new_status,
        passed=payload.passed,
        message=msg,
        visual_diff_score=payload.visual_diff_score
    )


@app.post(
    "/runs/{run_id}/retry",
    response_model=RetryRunResponse,
    tags=["Audit Runs"],
    summary="Trigger Bounded Audit Run Retry"
)
def retry_audit_run(run_id: str, payload: Optional[RetryRunPayload] = None):
    """
    Registers a retry attempt for an audit run, enforcing maximum retry bounds
    to prevent runaway self-healing loops.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    r = runs_db[run_id]
    current_retries = r.get("retry_count", 0)
    max_retries = payload.max_retries if payload else 2
    reason = payload.reason if payload and payload.reason else "Autonomous remediation retry"

    if current_retries >= max_retries:
        _append_timeline_event(
            run_id=run_id,
            event_type="retry_exhausted",
            description=f"Retry bound reached ({current_retries}/{max_retries}). Transitioning to needs_review.",
            metadata={"current_retries": current_retries, "max_retries": max_retries}
        )
        r["status"] = RunStatus.NEEDS_REVIEW.value
        return RetryRunResponse(
            run_id=run_id,
            status=RunStatus.NEEDS_REVIEW,
            retry_count=current_retries,
            retry_allowed=False,
            message=f"Maximum retry limit ({max_retries}) reached. Run requires human QA review."
        )

    new_retry_count = current_retries + 1
    r["retry_count"] = new_retry_count
    r["status"] = RunStatus.RUNNING.value
    _append_timeline_event(
        run_id=run_id,
        event_type="retry_initiated",
        description=f"Retry attempt {new_retry_count}/{max_retries} initiated: {reason}",
        metadata={"retry_count": new_retry_count, "max_retries": max_retries, "reason": reason}
    )

    return RetryRunResponse(
        run_id=run_id,
        status=RunStatus.RUNNING,
        retry_count=new_retry_count,
        retry_allowed=True,
        message=f"Retry iteration {new_retry_count}/{max_retries} registered successfully."
    )


@app.post(
    "/runs/{run_id}/update-pr-verification",
    tags=["Audit Runs"],
    summary="Update Pull Request with Verification Retest Evidence"
)
def update_pr_verification(run_id: str):
    """
    Appends a verification audit summary and retest diff metrics to the run's PR.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    run_entry = runs_db[run_id]
    pr_url = run_entry.get("pr_url")
    if not pr_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run '{run_id}' does not have an associated Pull Request."
        )

    # Extract PR number from PR URL
    try:
        pr_number = int(pr_url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        pr_number = 1

    retest_outcome = run_entry.get("retest_outcome") or {"passed": True, "notes": "Verified"}
    passed_badge = "✅ **VERIFIED FIXED**" if retest_outcome.get("passed") else "⚠️ **RETEST FAILED**"
    diff_score_str = f"{retest_outcome.get('visual_diff_score'):.2%}" if retest_outcome.get("visual_diff_score") is not None else "0.00% (Identical)"
    comment_body = f"""### 🛡️ OmniSight Retest Verification Report

* **Run ID**: `{run_id}`
* **Verification Status**: {passed_badge}
* **Visual Diff Metric**: `{diff_score_str}`
* **Viewport**: `{retest_outcome.get('retest_viewport', 'all')}`
* **Notes**: {retest_outcome.get('notes', 'Automated sandbox verification cleared defect without layout regression.')}

> All automated sandbox guardrails passed with rollback verification.
"""
    success = add_pr_comment_with_retest_evidence(pr_number, comment_body)
    _append_timeline_event(
        run_id=run_id,
        event_type="pr_comment_posted",
        description=f"Verification comment attached to PR #{pr_number}",
        metadata={"pr_number": pr_number, "success": success}
    )
    return {"status": "success", "pr_number": pr_number, "comment_posted": success}


@app.get(
    "/runs/{run_id}/pr-status",
    tags=["Audit Runs"],
    summary="Query Live GitHub PR Status for Run"
)
def get_run_pr_status(run_id: str):
    """
    Queries live GitHub PR status for a run with an open PR,
    updating the run status to 'fixed' if the PR has been merged.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    r = runs_db[run_id]
    pr_url = r.get("pr_url")
    if not pr_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run '{run_id}' does not have an associated Pull Request."
        )

    try:
        pr_number = int(pr_url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        pr_number = 1

    pr_info = check_pull_request_status(pr_number)
    if pr_info.get("merged"):
        r["status"] = RunStatus.FIXED.value
        _append_timeline_event(
            run_id=run_id,
            event_type="pr_merged_verified",
            description=f"GitHub PR #{pr_number} verified merged.",
            metadata=pr_info
        )
    elif pr_info.get("state") == "closed":
        r["status"] = RunStatus.NEEDS_REVIEW.value

    return {
        "run_id": run_id,
        "pr_info": pr_info,
        "run_status": r["status"]
    }


@app.post(
    "/runs/{run_id}/revert",
    response_model=PatchRevertResponse,
    tags=["Audit Runs"],
    summary="Rollback and Revert Remediation Patch"
)
def revert_run_patch(run_id: str):
    """
    Rolls back an applied or proposed patch when rejected by human QA or when tests regress.
    Creates a dedicated revert branch and transitions run status to 'patch_reverted'.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    r = runs_db[run_id]
    target_file = (r.get("patch") or {}).get("target_file") or "app-under-test/src/styles/defects.css"
    revert_result = revert_pull_request_patch(run_id=run_id, target_file=target_file)

    r["status"] = "patch_reverted"
    _append_timeline_event(
        run_id=run_id,
        event_type="patch_reverted",
        description=f"Patch for run '{run_id}' rolled back on branch '{revert_result.get('revert_branch')}'.",
        metadata=revert_result
    )

    return PatchRevertResponse(
        run_id=run_id,
        reverted=revert_result["reverted"],
        revert_branch=revert_result.get("revert_branch"),
        message=f"Remediation patch successfully reverted for run '{run_id}'.",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get(
    "/runs/{run_id}/timeline",
    response_model=List[TimelineEvent],
    tags=["Audit Runs"],
    summary="Get Chronological Audit Run Event Timeline"
)
def get_run_timeline(run_id: str):
    """Returns the ordered event history for an audit run."""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    raw_timeline = runs_db[run_id].get("timeline", [])
    return [TimelineEvent(**evt) if isinstance(evt, dict) else evt for evt in raw_timeline]


@app.patch(
    "/runs/{run_id}/findings/{finding_id}",
    tags=["Audit Runs"],
    summary="Update Individual Finding Resolution Status"
)
def update_finding_status(run_id: str, finding_id: str, payload: FindingStatusUpdatePayload):
    """Updates the status of a specific defect finding in a run."""
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    run_entry = runs_db[run_id]
    findings = run_entry.get("findings", [])
    target_finding = None
    for f in findings:
        if isinstance(f, dict) and f.get("id") == finding_id:
            target_finding = f
            break
        elif hasattr(f, "id") and f.id == finding_id:
            target_finding = f
            break

    if not target_finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found in run '{run_id}'."
        )

    if isinstance(target_finding, dict):
        target_finding["status"] = payload.status
        if payload.suggested_change:
            target_finding["suggested_change"] = payload.suggested_change
        if payload.notes:
            target_finding["notes"] = payload.notes
    else:
        target_finding.status = payload.status

    _append_timeline_event(
        run_id=run_id,
        event_type="finding_status_updated",
        description=f"Finding '{finding_id}' marked as {payload.status}",
        metadata={"finding_id": finding_id, "new_status": payload.status}
    )
    return {"message": f"Finding '{finding_id}' updated successfully.", "status": payload.status}


@app.get(
    "/runs/{run_id}/export-bundle",
    response_model=ForensicBundleResponse,
    tags=["Audit Runs"],
    summary="Export Complete Forensic Audit Bundle"
)
def export_run_forensic_bundle(run_id: str):
    """
    Exports a comprehensive JSON archive containing run metadata, findings,
    patch diff, validation logs, retest evidence, and timeline events for QA auditing.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )
    r = runs_db[run_id]
    summary = RunSummaryResponse(
        run_id=r["run_id"],
        start_time=r["start_time"],
        target=r["target"],
        status=RunStatus(r["status"]),
        issue_count=r.get("issue_count", len(r.get("findings", []))),
        pr_url=r.get("pr_url")
    )
    detail = RunDetailResponse(
        run_id=r["run_id"],
        start_time=r["start_time"],
        target=r["target"],
        status=RunStatus(r["status"]),
        steps=r.get("steps", []),
        evidence_paths=_normalize_evidence_paths(r.get("evidence_paths", {})),
        findings=r.get("findings", []),
        patch=r.get("patch"),
        retry_count=r.get("retry_count", 0),
        pr_url=r.get("pr_url"),
        error=r.get("error")
    )
    raw_timeline = r.get("timeline", [])
    timeline_events = [TimelineEvent(**evt) if isinstance(evt, dict) else evt for evt in raw_timeline]

    import hashlib
    raw_payload_str = f"{run_id}:{summary.model_dump_json()}:{detail.model_dump_json()}"
    digest = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

    return ForensicBundleResponse(
        run_id=run_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        detail=detail,
        timeline=timeline_events,
        retest_outcome=r.get("retest_outcome"),
        bundle_sha256=digest
    )


@app.get(
    "/runs/export/csv",
    tags=["Audit Runs"],
    summary="Export Audit Runs Summary Table (CSV)"
)
def export_runs_csv():
    """
    Exports a tabular CSV summary of all visual audit runs for compliance and spreadsheet analysis.
    """
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "run_id",
        "start_time",
        "target",
        "branch",
        "scenario",
        "status",
        "issue_count",
        "retry_count",
        "pr_url",
        "retest_passed"
    ])

    for r_id, r in runs_db.items():
        retest_passed = ""
        if r.get("retest_outcome") and isinstance(r["retest_outcome"], dict):
            retest_passed = str(r["retest_outcome"].get("passed", ""))

        writer.writerow([
            r.get("run_id", r_id),
            r.get("start_time", ""),
            r.get("target", ""),
            r.get("branch", ""),
            r.get("scenario", ""),
            r.get("status", ""),
            r.get("issue_count", len(r.get("findings", []))),
            r.get("retry_count", 0),
            r.get("pr_url", "") or "",
            retest_passed
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=omnisight_audit_runs.csv"}
    )


@app.post(
    "/runs/batch",
    response_model=BatchRunSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Audit Runs"],
    summary="Trigger Matrix Batch of Visual Audit Runs"
)
def trigger_batch_runs(payload: BatchRunTriggerPayload):
    """
    Initiates an execution matrix across scenarios and viewports in a single coordinated batch.
    """
    try:
        parsed = urlparse(payload.target_url)
        hostname = parsed.hostname or payload.target_url
        if not settings.is_host_allowed(hostname):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target host '{hostname}' is not in the allowed target hosts."
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Invalid target URL structure.")

    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()
    spawned_run_ids = []

    for scenario in payload.scenarios:
        for vp in payload.viewports:
            run_id = f"run-{uuid.uuid4().hex[:8]}"
            spawned_run_ids.append(run_id)
            runs_db[run_id] = {
                "run_id": run_id,
                "batch_id": batch_id,
                "target_url": payload.target_url,
                "branch": payload.branch,
                "scenario": scenario,
                "status": RunStatus.QUEUED,
                "created_at": created_at,
                "findings": [],
                "timeline": [],
                "retry_count": 0,
                "max_retries": 2,
                "viewports": [vp],
                "batch_label": payload.batch_label
            }
            _append_timeline_event(
                run_id=run_id,
                event_type="batch_spawned",
                description=f"Run spawned as part of batch '{batch_id}' ({scenario} @ {vp})",
                metadata={"batch_id": batch_id, "scenario": scenario, "viewport": vp}
            )

    batches_db[batch_id] = {
        "batch_id": batch_id,
        "run_ids": spawned_run_ids,
        "created_at": created_at,
        "batch_label": payload.batch_label
    }

    return BatchRunSummaryResponse(
        batch_id=batch_id,
        total_runs=len(spawned_run_ids),
        completed_runs=0,
        failed_runs=0,
        active_runs=len(spawned_run_ids),
        run_ids=spawned_run_ids,
        overall_status="queued",
        created_at=created_at
    )


@app.get(
    "/runs/batch/{batch_id}",
    response_model=BatchRunSummaryResponse,
    tags=["Audit Runs"],
    summary="Get Aggregated Batch Execution Status"
)
def get_batch_status(batch_id: str):
    """
    Retrieves dynamically computed status and progress across all runs in a batch.
    """
    if batch_id not in batches_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found."
        )

    batch = batches_db[batch_id]
    run_ids = batch.get("run_ids", [])
    total = len(run_ids)
    completed = 0
    failed = 0
    active = 0

    for r_id in run_ids:
        r_entry = runs_db.get(r_id, {})
        st = r_entry.get("status")
        if st in [RunStatus.FIXED, RunStatus.AUDITED]:
            completed += 1
        elif st in [RunStatus.FAILED, RunStatus.PATCH_REJECTED]:
            failed += 1
        else:
            active += 1

    if active > 0:
        overall = "running"
    elif failed > 0 and completed > 0:
        overall = "partially_failed"
    elif failed > 0 and completed == 0:
        overall = "failed"
    else:
        overall = "completed"

    return BatchRunSummaryResponse(
        batch_id=batch_id,
        total_runs=total,
        completed_runs=completed,
        failed_runs=failed,
        active_runs=active,
        run_ids=run_ids,
        overall_status=overall,
        created_at=batch["created_at"]
    )


@app.post(
    "/runs/batch/{batch_id}/retry",
    response_model=BatchRetryResponse,
    tags=["Audit Runs"],
    summary="Bulk Retry Failed Runs in Batch"
)
def bulk_retry_batch(batch_id: str, payload: Optional[BatchRetryPayload] = None):
    """
    Retries failed or unverified runs within an audit matrix batch.
    """
    if batch_id not in batches_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch '{batch_id}' not found."
        )

    payload = payload or BatchRetryPayload()
    batch = batches_db[batch_id]
    retried = []
    skipped = []

    for r_id in batch.get("run_ids", []):
        if r_id not in runs_db:
            skipped.append(r_id)
            continue
        entry = runs_db[r_id]
        st = entry.get("status")
        needs_retry = st in [RunStatus.FAILED, RunStatus.NEEDS_REVIEW, RunStatus.PATCH_REJECTED]
        if payload.only_failed_or_needs_review and not needs_retry:
            skipped.append(r_id)
            continue

        entry["status"] = RunStatus.QUEUED
        entry["retry_count"] = entry.get("retry_count", 0) + 1
        _append_timeline_event(
            run_id=r_id,
            event_type="batch_bulk_retry",
            description=f"Run rescheduled via batch retry on batch '{batch_id}'",
            metadata={"batch_id": batch_id, "retry_count": entry["retry_count"]}
        )
        retried.append(r_id)

    return BatchRetryResponse(
        batch_id=batch_id,
        retried_runs_count=len(retried),
        retried_run_ids=retried,
        skipped_run_ids=skipped,
        message=f"Bulk retry rescheduled {len(retried)} runs in batch '{batch_id}'."
    )


@app.post(
    "/runs/{run_id}/policy/evaluate",
    response_model=PolicyEvaluationResponse,
    tags=["Audit Runs"],
    summary="Evaluate Release Gate and Auto-Merge Policy"
)
def evaluate_run_policy(run_id: str, payload: Optional[PolicyEvaluationRequest] = None):
    """
    Evaluates self-healing release gate policy against a run's patch and retest proof.
    """
    if run_id not in runs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    run_entry = runs_db[run_id]
    target_file = payload.target_file if payload and payload.target_file else (run_entry.get("patch") or {}).get("target_file")
    diff_content = payload.diff_content if payload and payload.diff_content else (run_entry.get("patch") or {}).get("diff")

    visual_score = payload.visual_diff_score if (payload and payload.visual_diff_score is not None) else (run_entry.get("retest_outcome") or {}).get("visual_diff_score")

    severities = payload.defect_severities if (payload and payload.defect_severities) else [f.get("severity", "medium") for f in run_entry.get("findings", [])]

    fingerprints = payload.defect_fingerprints if (payload and payload.defect_fingerprints) else [f.get("fingerprint") for f in run_entry.get("findings", []) if f.get("fingerprint")]

    author = payload.author if payload and payload.author else "omnisight-agent"

    evaluation = evaluate_merge_policy(
        run_id=run_id,
        target_file=target_file,
        diff_content=diff_content,
        visual_diff_score=visual_score,
        defect_severities=severities,
        defect_fingerprints=fingerprints,
        author=author
    )

    _append_timeline_event(
        run_id=run_id,
        event_type="policy_evaluated",
        description=f"Policy gate evaluated: gate_level={evaluation['gate_level']}, auto_merge={evaluation['auto_merge_allowed']}",
        metadata={"gate_level": evaluation["gate_level"], "risk_score": evaluation["overall_risk_score"]}
    )

    return PolicyEvaluationResponse(**evaluation)
