"""
OmniSight Services Package.
Exposes core business logic modules including the Action Engine,
Zero-Trust Patch Validator, and GitHub Pull Request Automation Service.
"""

from app.services.patch_validator import validate_patch
from app.services.action_engine import action_engine, ActionEngine
from app.services.github_service import (
    create_pull_request_for_fix,
    generate_pr_markdown_description,
    add_pr_comment_with_retest_evidence,
    update_pull_request_verification_proof,
)

__all__ = [
    "validate_patch",
    "action_engine",
    "ActionEngine",
    "create_pull_request_for_fix",
    "generate_pr_markdown_description",
    "add_pr_comment_with_retest_evidence",
    "update_pull_request_verification_proof",
]

