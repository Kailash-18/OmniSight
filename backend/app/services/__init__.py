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

from app.services.patch_validator import (
    validate_patch,
    validate_css_safety,
    assess_patch_risk,
)
from app.services.action_engine import action_engine, ActionEngine
from app.services.fingerprint_service import (
    generate_defect_fingerprint,
    compute_finding_fingerprint,
    deduplicate_findings,
    cluster_defect_findings,
)
from app.services.github_service import (
    create_pull_request_for_fix,
    generate_pr_markdown_description,
    add_pr_comment_with_retest_evidence,
    update_pull_request_verification_proof,
    sanitize_git_branch_name,
    check_pull_request_status,
    close_pull_request,
    revert_pull_request_patch,
)

__all__ = [
    "validate_patch",
    "validate_css_safety",
    "assess_patch_risk",
    "action_engine",
    "ActionEngine",
    "create_pull_request_for_fix",
    "generate_pr_markdown_description",
    "add_pr_comment_with_retest_evidence",
    "update_pull_request_verification_proof",
    "sanitize_git_branch_name",
    "check_pull_request_status",
    "close_pull_request",
    "revert_pull_request_patch",
    "generate_defect_fingerprint",
    "compute_finding_fingerprint",
    "deduplicate_findings",
    "cluster_defect_findings",
]


