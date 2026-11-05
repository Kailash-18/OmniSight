"""
Rollback Manifest Engine for generating atomic, reversible visual patches.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from backend.app.schemas.rollback_schema import (
    AtomicRollbackManifest, RollbackPatchItem, RollbackExecutionRequest,
    RollbackExecutionResponse, RollbackStatus
)

class RollbackManifestEngine:
    def __init__(self):
        self.manifest_store: Dict[str, AtomicRollbackManifest] = {}

    def generate_reverse_diff(self, original_css: str, patched_css: str) -> str:
        return f"--- a/patch.css\n+++ b/patch.css\n@@ -1,1 +1,1 @@\n-{patched_css}\n+{original_css}"

    def create_manifest(self, run_id: str, pr_number: Optional[int], patches: List[Dict[str, str]]) -> AtomicRollbackManifest:
        rollback_id = f"rb_{uuid.uuid4().hex[:12]}"
        items: List[RollbackPatchItem] = []
        target_files = []
        
        for p in patches:
            tf = p.get("target_file", "unknown.css")
            orig = p.get("original_css", "")
            patched = p.get("patched_css", "")
            rev_diff = self.generate_reverse_diff(orig, patched)
            chk = hashlib.sha256(rev_diff.encode("utf-8")).hexdigest()
            items.append(RollbackPatchItem(
                target_file=tf,
                original_css=orig,
                patched_css=patched,
                reverse_diff=rev_diff,
                sha256_checksum=chk
            ))
            target_files.append(tf)
            
        token_payload = f"{rollback_id}:{run_id}:{pr_number}:{datetime.now(timezone.utc).isoformat()}"
        token = hashlib.sha256(token_payload.encode("utf-8")).hexdigest()
        
        manifest = AtomicRollbackManifest(
            rollback_id=rollback_id,
            run_id=run_id,
            pr_number=pr_number,
            target_files=target_files,
            items=items,
            rollback_token=token,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=RollbackStatus.PENDING
        )
        self.manifest_store[rollback_id] = manifest
        return manifest

    def execute_rollback(self, req: RollbackExecutionRequest) -> RollbackExecutionResponse:
        if req.rollback_id not in self.manifest_store:
            raise ValueError(f"Rollback manifest {req.rollback_id} not found")
        manifest = self.manifest_store[req.rollback_id]
        if manifest.rollback_token != req.rollback_token:
            raise PermissionError("Invalid rollback token authentication")
        manifest.status = RollbackStatus.EXECUTED
        digest = hashlib.sha256(f"executed_{req.rollback_id}_{manifest.status.value}".encode()).hexdigest()
        return RollbackExecutionResponse(
            rollback_id=req.rollback_id,
            success=True,
            reverted_files_count=len(manifest.items),
            audit_log_digest=digest,
            executed_at=datetime.now(timezone.utc).isoformat()
        )
