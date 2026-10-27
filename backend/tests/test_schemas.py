"""
Unit tests for OmniSight Pydantic schemas, validators, and enums.
Verifies schema constraints, default values, confidence normalization, and error handling.
"""

import pytest
from pydantic import ValidationError

from app.schemas.run_schema import (
    RunStatus,
    DefectCategory,
    Severity,
    FindingSchema,
    PatchObject,
    BuildWebhookPayload,
    RunTriggerPayload,
    HealthCheckResponse,
)


def test_run_status_enum_values():
    """Verify all lifecycle run statuses are properly enumerated."""
    expected_statuses = {
        "queued",
        "running",
        "audited",
        "patch_rejected",
        "verifying",
        "fixed",
        "needs_review",
        "pr_opened",
        "failed",
    }
    actual_statuses = {s.value for s in RunStatus}
    assert expected_statuses.issubset(actual_statuses)


def test_defect_category_enum_values():
    """Verify visual defect categories cover core UI anomaly types."""
    assert DefectCategory.ELEMENT_OVERLAP.value == "element_overlap"
    assert DefectCategory.ELEMENT_CLIPPING.value == "element_clipping"
    assert DefectCategory.CONTRAST_ISSUE.value == "contrast_issue"
    assert DefectCategory.LAYOUT_OVERFLOW.value == "layout_overflow"


def test_severity_levels():
    """Verify standard severity ranking."""
    assert Severity.LOW.value == "low"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.HIGH.value == "high"
    assert Severity.CRITICAL.value == "critical"


def test_finding_schema_valid_creation():
    """Verify valid FindingSchema instantiation and normalization."""
    finding = FindingSchema(
        id="defect-test-1",
        category=DefectCategory.ELEMENT_CLIPPING,
        severity=Severity.HIGH,
        description="Checkout CTA clipped on mobile viewport",
        viewport="mobile_375x667",
        confidence=0.92,
        suggested_change="width: 100%;",
        rationale="Button exceeds viewport boundary"
    )
    assert finding.id == "defect-test-1"
    assert finding.confidence == 0.92
    assert finding.status == "detected"


def test_finding_schema_confidence_percentage_string():
    """Verify string percentages like '95%' or '90' are normalized to float."""
    finding = FindingSchema(
        id="defect-test-2",
        category=DefectCategory.ELEMENT_OVERLAP,
        severity=Severity.MEDIUM,
        description="Text overlaps badge",
        viewport="desktop_1440x900",
        confidence="95%",
        suggested_change="margin-top: 10px;",
        rationale="Bounding box collision"
    )
    assert finding.confidence == 0.95


def test_finding_schema_category_case_insensitivity():
    """Verify category normalizer handles uppercase and hyphens gracefully."""
    finding = FindingSchema(
        id="defect-test-3",
        category="ELEMENT-CLIPPING",
        severity=Severity.LOW,
        description="Minor icon clipping",
        viewport="desktop_1440x900",
        confidence=0.8,
        suggested_change="overflow: visible;",
        rationale="Edge boundary clipped"
    )
    assert finding.category == DefectCategory.ELEMENT_CLIPPING


def test_patch_object_defaults():
    """Verify PatchObject model default fields and serialization."""
    patch = PatchObject(
        target_file="app-under-test/src/styles/defects.css",
        diff="-.btn { width: 500px; }\n+.btn { width: 100%; }",
        explanation="Make checkout button responsive"
    )
    assert patch.target_file == "app-under-test/src/styles/defects.css"
    assert patch.validation_status is None
    assert patch.validator_errors is None


def test_build_webhook_payload_defaults():
    """Verify BuildWebhookPayload default values."""
    payload = BuildWebhookPayload(target_url="http://localhost:5173")
    assert payload.target_url == "http://localhost:5173"
    assert payload.branch == "main"
    assert payload.scenario == "checkout_flow"
    assert payload.commit_sha is None


def test_health_check_response_schema():
    """Verify HealthCheckResponse serialization."""
    resp = HealthCheckResponse(
        status="healthy",
        timestamp="2026-10-19T20:00:00Z",
        version="1.0.0"
    )
    data = resp.model_dump()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_finding_schema_rationale_preserved():
    """Verify rationale field is stored and serialized in FindingSchema."""
    finding = FindingSchema(
        id="defect-rationale-test",
        category=DefectCategory.ELEMENT_OBSTRUCTION,
        severity=Severity.HIGH,
        description="Checkout CTA is occluded by modal backdrop",
        viewport="desktop_1440x900",
        confidence=0.97,
        suggested_change="z-index: 100;",
        rationale="Backdrop element covers primary button with higher z-index",
        status="detected"
    )
    assert finding.rationale == "Backdrop element covers primary button with higher z-index"
    dumped = finding.model_dump()
    assert dumped["rationale"] == "Backdrop element covers primary button with higher z-index"


def test_enum_resilience_missing_values():
    """Verify enums handle non-standard casing and unknown values gracefully."""
    # RunStatus
    assert RunStatus("RUNNING") == RunStatus.RUNNING
    assert RunStatus("Queued") == RunStatus.QUEUED
    assert RunStatus("non_existent_status") == RunStatus.FAILED

    # DefectCategory
    assert DefectCategory("ELEMENT_CLIPPING") == DefectCategory.ELEMENT_CLIPPING
    assert DefectCategory("element-clipping") == DefectCategory.ELEMENT_CLIPPING
    assert DefectCategory("unknown_category") == DefectCategory.ELEMENT_OVERLAP

    # Severity
    assert Severity("CRITICAL") == Severity.CRITICAL
    assert Severity("Low") == Severity.LOW
    assert Severity("extreme") == Severity.MEDIUM


def test_settings_allowlist_helpers():
    """Verify Settings is_host_allowed and is_path_allowed normalizations."""
    from app.core.config import settings

    # Host checks including bracketed IPv6
    assert settings.is_host_allowed("localhost") is True
    assert settings.is_host_allowed("127.0.0.1") is True
    assert settings.is_host_allowed("::1") is True
    assert settings.is_host_allowed("[::1]") is True
    assert settings.is_host_allowed("evil.attacker.com") is False

    # Path checks including leading relative and git diff prefixes
    assert settings.is_path_allowed("b/app-under-test/src/styles/defects.css") is True
    assert settings.is_path_allowed("backend/app/main.py") is False


def test_patch_submit_payload_validation():
    """Verify PatchSubmitPayload defaults and required fields."""
    from app.schemas.run_schema import PatchSubmitPayload

    payload = PatchSubmitPayload(
        target_file="app-under-test/src/styles/defects.css",
        diff="-.old { margin: 0; }\n+.old { margin: 10px; }",
        file_content=".old { margin: 10px; }"
    )
    assert payload.target_file == "app-under-test/src/styles/defects.css"
    assert "OmniSight Automated Visual Defect Fix" in payload.pr_title
    assert payload.pr_body == ""


def test_run_detail_response_serialization():
    """Verify RunDetailResponse model serialization with findings and evidence paths."""
    from app.schemas.run_schema import RunDetailResponse, RunStatus

    detail = RunDetailResponse(
        run_id="run-test-detail-1",
        start_time="2026-10-22T20:00:00Z",
        target="http://localhost:5173",
        status=RunStatus.AUDITED,
        steps=["nav", "audit"],
        evidence_paths={"screenshots": ["desktop.png"]}
    )
    data = detail.model_dump()
    assert data["run_id"] == "run-test-detail-1"
    assert data["status"] == "audited"
    assert "screenshots" in data["evidence_paths"]
    assert "before_screenshots" in data["evidence_paths"]
    assert data["evidence_paths"]["before_screenshots"] == ["desktop.png"]

    # Verify reverse alias: before_screenshots populates screenshots
    detail_alias = RunDetailResponse(
        run_id="run-test-detail-2",
        start_time="2026-10-22T20:00:00Z",
        target="http://localhost:5173",
        status=RunStatus.AUDITED,
        steps=["nav", "audit"],
        evidence_paths={"before_screenshots": ["mobile.png"]}
    )
    alias_data = detail_alias.model_dump()
    assert alias_data["evidence_paths"]["screenshots"] == ["mobile.png"]


def test_retest_result_payload_validation():
    """Verify RetestResultPayload constraints and defaults."""
    from app.schemas.run_schema import RetestResultPayload

    payload = RetestResultPayload(
        passed=True,
        visual_diff_score=0.02,
        retest_viewport="mobile_375x667",
        retest_screenshots={"after": "artifacts/retest.png"},
        notes="Visual mismatch resolved"
    )
    assert payload.passed is True
    assert payload.visual_diff_score == 0.02
    assert payload.retest_viewport == "mobile_375x667"
    assert "after" in payload.retest_screenshots


def test_timeline_event_schema_serialization():
    """Verify TimelineEvent creation and dictionary dump."""
    from app.schemas.run_schema import TimelineEvent

    event = TimelineEvent(
        event_id="evt-101",
        timestamp="2026-10-25T11:00:00Z",
        event_type="retest_verified",
        description="Sandbox visual verification passed",
        metadata={"diff_score": 0.0}
    )
    dumped = event.model_dump()
    assert dumped["event_id"] == "evt-101"
    assert dumped["event_type"] == "retest_verified"
    assert dumped["metadata"]["diff_score"] == 0.0


def test_finding_status_update_payload():
    """Verify FindingStatusUpdatePayload validation."""
    from app.schemas.run_schema import FindingStatusUpdatePayload

    update = FindingStatusUpdatePayload(
        status="verified",
        suggested_change="padding: 12px;",
        notes="Verified against mobile viewport"
    )
    assert update.status == "verified"
    assert update.suggested_change == "padding: 12px;"


def test_metrics_summary_schema_with_mttr():
    """Verify RunMetricsSummaryResponse accepts and serializes MTTR fields."""
    from app.schemas.run_schema import RunMetricsSummaryResponse

    metrics = RunMetricsSummaryResponse(
        total_runs=10,
        active_runs=2,
        fixed_runs=8,
        prs_opened=5,
        total_defects_detected=12,
        clean_run_rate_percent=80.0,
        defects_by_category={"element_clipping": 8, "contrast_issue": 4},
        runs_by_status={"fixed": 8, "running": 2},
        mean_time_to_remediation_seconds=145.5,
        resolved_runs_count=8
    )
    dumped = metrics.model_dump()
    assert dumped["mean_time_to_remediation_seconds"] == 145.5
    assert dumped["resolved_runs_count"] == 8
    assert dumped["clean_run_rate_percent"] == 80.0
