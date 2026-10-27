"""Tests for SeverityClassifier."""

import pytest
from automation.severity_classifier import SeverityClassifier


def test_classify_critical_obstruction():
    sev = SeverityClassifier.classify(
        category="ELEMENT_OBSTRUCTION", is_interactive=True, overlap_ratio=0.8
    )
    assert sev == "CRITICAL"


def test_classify_high_interactive_overlap():
    sev = SeverityClassifier.classify(
        category="ELEMENT_OVERLAP", is_interactive=True, overlap_ratio=0.25
    )
    assert sev == "HIGH"


def test_classify_medium_non_interactive():
    sev = SeverityClassifier.classify(
        category="ELEMENT_OVERLAP", is_interactive=False, overlap_ratio=0.1
    )
    assert sev == "MEDIUM"


def test_classify_low_minor_defect():
    sev = SeverityClassifier.classify(
        category="ALIGNMENT_SHIFT", is_interactive=False, overlap_ratio=0.01
    )
    assert sev == "LOW"
