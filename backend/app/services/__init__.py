"""
OmniSight Services Package.
Exposes core business logic modules including the Action Engine,
Zero-Trust Patch Validator, and GitHub Pull Request Automation Service.
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.services.patch_validator import validate_patch, validate_css_safety
from app.services.action_engine import action_engine, ActionEngine
from app.services.github_service import (
    create_pull_request_for_fix,
    generate_pr_markdown_description,
    add_pr_comment_with_retest_evidence,
    update_pull_request_verification_proof,
    sanitize_git_branch_name,
)

__all__ = [
    "validate_patch",
    "validate_css_safety",
    "action_engine",
    "ActionEngine",
    "create_pull_request_for_fix",
    "generate_pr_markdown_description",
    "add_pr_comment_with_retest_evidence",
    "update_pull_request_verification_proof",
    "sanitize_git_branch_name",
]

