from fastapi import FastAPI, HTTPException, status
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.services.patch_validator import validate_patch
from app.services.github_service import create_pull_request_for_fix

app = FastAPI(title="OmniSight Backend API", version="1.0.0")

# In-memory database simulation for local development
fake_runs_db = {}

class BuildWebhookPayload(BaseModel):
    target_url: str
    branch: str
    scenario: str
    commit_sha: Optional[str] = None
    event_id: Optional[str] = None

class PatchSubmitPayload(BaseModel):
    target_file: str
    diff: str
    file_content: str
    pr_title: str
    pr_body: str

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy"}

@app.post("/webhook/build", status_code=status.HTTP_202_ACCEPTED)
def receive_build_webhook(payload: BuildWebhookPayload):
    run_id = f"run-{int(datetime.utcnow().timestamp())}"
    
    fake_runs_db[run_id] = {
        "run_id": run_id,
        "start_time": datetime.utcnow().isoformat(),
        "target": payload.target_url,
        "branch": payload.branch,
        "scenario": payload.scenario,
        "status": "queued",
        "issue_count": 0,
        "pr_url": None
    }

    return {
        "run_id": run_id,
        "status": "queued",
        "message": "Build event accepted and queued for browser audit."
    }

@app.get("/runs")
def list_runs():
    return list(fake_runs_db.values())

@app.get("/runs/{run_id}")
def get_run_details(run_id: str):
    if run_id not in fake_runs_db:
        raise HTTPException(status_code=404, detail="Run not found.")
    return fake_runs_db[run_id]

@app.post("/runs/{run_id}/submit-patch")
def submit_and_validate_patch(run_id: str, payload: PatchSubmitPayload):
    if run_id not in fake_runs_db:
        fake_runs_db[run_id] = {"run_id": run_id, "status": "running"}

    # 1. Validate patch using security guardrails
    validation_result = validate_patch(payload.target_file, payload.diff)
    if not validation_result["validation_status"]:
        fake_runs_db[run_id]["status"] = "patch_rejected"
        raise HTTPException(status_code=400, detail=validation_result["validator_errors"])

    # 2. If valid, open a GitHub Pull Request
    try:
        pr_url = create_pull_request_for_fix(
            run_id=run_id,
            target_file=payload.target_file,
            file_content=payload.file_content,
            commit_message=f"OmniSight Auto-fix for UI defect in {payload.target_file}",
            pr_title=payload.pr_title,
            pr_body=payload.pr_body
        )
        fake_runs_db[run_id]["status"] = "pr_opened"
        fake_runs_db[run_id]["pr_url"] = pr_url
        return {"status": "success", "pr_url": pr_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))