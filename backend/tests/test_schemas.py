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

