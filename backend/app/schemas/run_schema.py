from pydantic import BaseModel
from typing import Optional

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