# -*- coding: utf-8 -*-
"""
Unit Test Suite for OmniSight Visual Defect Fingerprinting & Clustering Service.
Verifies deterministic hashing, deduplication logic, and multi-viewport aggregation.
"""

import pytest
from app.services.fingerprint_service import (
    generate_defect_fingerprint,
    compute_finding_fingerprint,
    deduplicate_findings,
    cluster_defect_findings,
)


def test_generate_defect_fingerprint_deterministic():
    """Verify identical defect inputs produce identical deterministic fingerprints."""
    fp1 = generate_defect_fingerprint(
        category="element_overlap",
        target_element="div.checkout-modal",
        viewport="desktop_1440x900",
        suggested_change="margin-top: 20px;"
    )
    fp2 = generate_defect_fingerprint(
        category="element_overlap",
        target_element="div.checkout-modal",
        viewport="mobile_375x667",
        suggested_change="margin-top: 20px;"
    )
    assert fp1.startswith("dfp-")
    assert fp1 == fp2  # Viewport agnostic by default for clustering


def test_defect_fingerprint_whitespace_and_case_insensitive():
    """Verify whitespace, single/double quotes, and casing do not alter fingerprint."""
    fp1 = generate_defect_fingerprint(
        category="ELEMENT_CLIPPING",
        target_element="button[data-testid='submit-btn']",
        suggested_change="width: 100%;"
    )
    fp2 = generate_defect_fingerprint(
        category="element-clipping",
        target_element="  button[data-testid=\"submit-btn\"]  ",
        suggested_change="  width : 100% ; "
    )
    assert fp1 == fp2


def test_defect_fingerprint_property_extraction():
    """Verify primary CSS property is accurately extracted and affects the digest."""
    fp_width = generate_defect_fingerprint(
        category="layout_overflow",
        target_element="div.container",
        suggested_change="max-width: 500px;"
    )
    fp_height = generate_defect_fingerprint(
        category="layout_overflow",
        target_element="div.container",
        suggested_change="height: auto;"
    )
    assert fp_width != fp_height


def test_compute_finding_fingerprint():
    """Verify helper extracts dict fields and computes valid fingerprint."""
    finding = {
        "id": "defect-1",
        "category": "contrast_issue",
        "target_element": "p.caption-text",
        "viewport": "desktop_1440x900",
        "suggested_change": "color: #333333;",
        "confidence": 0.92
    }
    fp = compute_finding_fingerprint(finding)
    assert fp.startswith("dfp-")
    assert len(fp) > 10


def test_deduplicate_findings_preserves_highest_confidence():
    """Verify duplicate findings are collapsed and higher confidence instance is preserved."""
    findings = [
        {
            "id": "defect-1",
            "category": "element_overlap",
            "target_element": "header.navbar",
            "suggested_change": "z-index: 10;",
            "confidence": 0.70
        },
        {
            "id": "defect-2",
            "category": "element_overlap",
            "target_element": "header.navbar",
            "suggested_change": "z-index: 10;",
            "confidence": 0.95
        },
        {
            "id": "defect-3",
            "category": "contrast_issue",
            "target_element": "footer.bottom-bar",
            "suggested_change": "color: #000;",
            "confidence": 0.85
        }
    ]
    deduped = deduplicate_findings(findings)
    assert len(deduped) == 2
    # Verify the preserved instance of header.navbar has 0.95 confidence
    navbar_finding = next(f for f in deduped if "navbar" in f["target_element"])
    assert navbar_finding["confidence"] == 0.95
    assert navbar_finding["id"] == "defect-2"


def test_cluster_defect_findings_aggregates_metrics():
    """Verify clustering aggregates occurrence counts, viewports, and run identifiers."""
    findings = [
        {
            "category": "element_clipping",
            "target_element": "button.checkout",
            "viewport": "mobile_375x667",
            "suggested_change": "overflow: visible;",
            "severity": "high"
        },
        {
            "category": "element_clipping",
            "target_element": "button.checkout",
            "viewport": "tablet_768x1024",
            "suggested_change": "overflow: visible;",
            "severity": "medium"
        }
    ]
    clusters = cluster_defect_findings(findings, run_id="run-101")
    assert len(clusters) == 1
    c = clusters[0]
    assert c["occurrences"] == 2
    assert "run-101" in c["run_ids"]
    assert "mobile_375x667" in c["viewports"]
    assert "tablet_768x1024" in c["viewports"]
    assert "high" in c["severities"]
    assert "medium" in c["severities"]


def test_fingerprint_with_viewport_distinguishes_screens():
    """Verify include_viewport flag produces distinct fingerprints across screen sizes."""
    fp_desk = generate_defect_fingerprint(
        category="element_overlap",
        target_element="div.hero",
        viewport="desktop_1440x900",
        include_viewport=True
    )
    fp_mob = generate_defect_fingerprint(
        category="element_overlap",
        target_element="div.hero",
        viewport="mobile_375x667",
        include_viewport=True
    )
    assert fp_desk != fp_mob


def test_fingerprint_with_pydantic_finding_schema():
    """Verify compute_finding_fingerprint, deduplicate_findings, and cluster_defect_findings support Pydantic models."""
    from app.schemas.run_schema import FindingSchema, DefectCategory, Severity

    f1 = FindingSchema(
        id="f-1",
        category=DefectCategory.ELEMENT_OVERLAP,
        severity=Severity.HIGH,
        description="Overlapping text block",
        viewport="mobile_375x667",
        target_element="header .title",
        confidence=0.92,
        suggested_change="margin-bottom: 1rem;",
        rationale="Collision detected"
    )
    f2 = FindingSchema(
        id="f-2",
        category=DefectCategory.ELEMENT_OVERLAP,
        severity=Severity.MEDIUM,
        description="Overlapping text block duplicate",
        viewport="mobile_375x667",
        target_element="header .title",
        confidence=0.85,
        suggested_change="margin-bottom: 1rem;",
        rationale="Collision detected duplicate"
    )

    fp = compute_finding_fingerprint(f1)
    assert fp.startswith("dfp-")

    deduped = deduplicate_findings([f1, f2])
    assert len(deduped) == 1
    assert deduped[0]["id"] == "f-1"
    assert deduped[0]["confidence"] == 0.92

    clusters = cluster_defect_findings([f1, f2], run_id="run-pydantic")
    assert len(clusters) == 1
    assert clusters[0]["occurrences"] == 2
    assert "run-pydantic" in clusters[0]["run_ids"]
