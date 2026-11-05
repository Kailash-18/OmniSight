"""
Unit tests for RollbackManifestEngine.
"""
import pytest
from backend.app.services.rollback_manifest_service import RollbackManifestEngine
from backend.app.schemas.rollback_schema import RollbackExecutionRequest, RollbackStatus

def test_generate_rollback_manifest():
    engine = RollbackManifestEngine()
    manifest = engine.create_manifest(
        run_id="run_rb_01",
        pr_number=42,
        patches=[
            {
                "target_file": "styles/globals.css",
                "original_css": "color: red;",
                "patched_css": "color: blue;"
            }
        ]
    )
    assert manifest.run_id == "run_rb_01"
    assert len(manifest.items) == 1
    assert manifest.items[0].target_file == "styles/globals.css"
    assert len(manifest.rollback_token) == 64
    assert manifest.status == RollbackStatus.PENDING

def test_execute_rollback_with_token():
    engine = RollbackManifestEngine()
    manifest = engine.create_manifest(
        run_id="run_rb_02",
        pr_number=43,
        patches=[{"target_file": "app.css", "original_css": "margin: 0;", "patched_css": "margin: 10px;"}]
    )
    req = RollbackExecutionRequest(
        rollback_id=manifest.rollback_id,
        rollback_token=manifest.rollback_token
    )
    res = engine.execute_rollback(req)
    assert res.success is True
    assert res.reverted_files_count == 1
