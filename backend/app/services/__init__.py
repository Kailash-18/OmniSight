"""
OmniSight Services Package.
Exposes core business logic modules including the Action Engine,
Zero-Trust Patch Validator, GitHub Pull Request Automation Service,
Defect Fingerprinting, Flakiness Quarantine, Policy Engine, Outbound Notifications,
Audit Scheduler, Forensic Bundling, Review Engine, and Remediation Certificate Authority.
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
    validate_css_syntax_balance,
    dry_run_patch,
)
from app.services.action_engine import action_engine, ActionEngine
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
from app.services.fingerprint_service import (
    generate_defect_fingerprint,
    compute_finding_fingerprint,
    deduplicate_findings,
    cluster_defect_findings,
)
from app.services.flakiness_service import (
    calculate_flakiness_score,
    record_defect_observation,
    quarantine_defect,
    unquarantine_defect,
    is_defect_quarantined,
    get_quarantined_defects,
    get_flakiness_report,
    reset_flakiness_tracker,
    bulk_quarantine_defects,
    unquarantine_all_defects,
)
from app.services.policy_engine import evaluate_merge_policy
from app.services.notification_service import (
    sign_webhook_payload,
    build_outbound_event,
    dispatch_notification,
    get_dispatched_events,
    clear_dispatched_events,
)
from app.services.schedule_service import (
    register_schedule,
    list_schedules,
    get_schedule,
    disable_schedule,
    enable_schedule,
    delete_schedule,
    record_trigger,
)
from app.services.forensic_service import (
    compute_sha256,
    create_forensic_bundle,
    verify_forensic_bundle_integrity,
    export_forensic_zip_archive,
)
from app.services.review_engine import (
    record_review_decision,
    record_lead_override,
    get_review_trail,
    clear_reviews_db,
)
from app.services.certificate_service import (
    generate_remediation_certificate,
    export_certificate_markdown,
)

__all__ = [
    "validate_patch",
    "validate_css_safety",
    "assess_patch_risk",
    "validate_css_syntax_balance",
    "dry_run_patch",
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
    "calculate_flakiness_score",
    "record_defect_observation",
    "quarantine_defect",
    "unquarantine_defect",
    "is_defect_quarantined",
    "get_quarantined_defects",
    "get_flakiness_report",
    "reset_flakiness_tracker",
    "bulk_quarantine_defects",
    "unquarantine_all_defects",
    "evaluate_merge_policy",
    "sign_webhook_payload",
    "build_outbound_event",
    "dispatch_notification",
    "get_dispatched_events",
    "clear_dispatched_events",
    "register_schedule",
    "list_schedules",
    "get_schedule",
    "disable_schedule",
    "enable_schedule",
    "delete_schedule",
    "record_trigger",
    "compute_sha256",
    "create_forensic_bundle",
    "verify_forensic_bundle_integrity",
    "export_forensic_zip_archive",
    "record_review_decision",
    "record_lead_override",
    "get_review_trail",
    "clear_reviews_db",
    "generate_remediation_certificate",
    "export_certificate_markdown",
]

from backend.app.services.healing_service import (
    HealingEngine,
    healing_engine,
)
