"""
FastAPI CI/CD Gateway and Action Engine API for OmniSight.
Handles build webhooks, manual audit triggers, run lifecycle, and VLM patch validation.
"""

import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
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
    RunStatus,
    PatchObject,
)
from app.services.patch_validator import validate_patch
from app.services.action_engine import action_engine
from app.services.github_service import create_pull_request_for_fix


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

# In-memory store for test runs (simulates persistence for development & demo)
runs_db: Dict[str, Dict[str, Any]] = {}


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
    "/api/milestones",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Engineering Deliverables and Security Boundaries"
)
def get_milestone_status():
    """Returns tracking status for Member 1 milestones and allowed security domains."""
    return {
        "member": "Member 1 - Backend & PR Automation",
        "foundation_scaffolding": "completed",
        "action_engine_and_security": "completed",
        "system_integration": "completed",
        "pr_automation_engine": "ready",
        "week_1_foundation": "completed",
        "week_2_action_engine": "completed",
        "week_2_day_3_integration": "completed",
        "week_3_pr_automation": "ready",
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
    status_filter: Optional[RunStatus] = None
):
    """Returns summaries of recorded test runs in reverse chronological order with optional filtering."""
    sorted_runs = sorted(
        runs_db.values(),
        key=lambda r: r.get("start_time", ""),
        reverse=True
    )

    summaries = []
    for r in sorted_runs:
        if status_filter and r.get("status") != status_filter.value:
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
        evidence_paths=r.get("evidence_paths", {}),
        findings=r.get("findings", []),
        patch=r.get("patch"),
        retry_count=r.get("retry_count", 0),
        pr_url=r.get("pr_url"),
        error=r.get("error")
    )


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
        run_entry["evidence_paths"] = payload.evidence_paths
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
        return {"status": "success", "pr_url": pr_url}
    except Exception as e:
        runs_db[run_id]["status"] = RunStatus.FAILED.value
        runs_db[run_id]["error"] = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PR automation failed: {str(e)}"
        )