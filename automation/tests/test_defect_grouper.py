"""Tests for DefectGrouper."""

import pytest
from automation.defect_grouper import DefectGrouper


def test_defect_grouper_clusters_duplicate_selectors():
    findings = [
        {
            "selector": ".hero-title",
            "category": "ELEMENT_OVERLAP",
            "severity": "MEDIUM",
            "viewport": "desktop_1440x900",
            "description": "Hero text overlaps header on desktop",
        },
        {
            "selector": ".hero-title",
            "category": "ELEMENT_OVERLAP",
            "severity": "HIGH",
            "viewport": "mobile_375x667",
            "description": "Hero text overlaps product card on mobile",
        },
        {
            "selector": ".promo-banner",
            "category": "ELEMENT_OBSTRUCTION",
            "severity": "CRITICAL",
            "viewport": "desktop_1440x900",
            "description": "Banner obstructs checkout button",
        },
    ]

    clusters = DefectGrouper.group_findings(findings)
    assert len(clusters) == 2

    # First cluster should be highest severity (CRITICAL)
    assert clusters[0].category == "ELEMENT_OBSTRUCTION"
    assert clusters[0].highest_severity == "CRITICAL"
    assert len(clusters[0].raw_findings) == 1

    # Second cluster should be .hero-title with upgraded severity (HIGH) across both viewports
    assert clusters[1].primary_selector == ".hero-title"
    assert clusters[1].highest_severity == "HIGH"
    assert len(clusters[1].raw_findings) == 2
    assert "desktop_1440x900" in clusters[1].affected_viewports
    assert "mobile_375x667" in clusters[1].affected_viewports
    assert len(clusters[1].descriptions) == 2

    d = clusters[1].to_dict()
    assert d["occurrences"] == 2
    assert d["severity"] == "HIGH"
