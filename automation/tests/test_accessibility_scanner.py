"""
Unit Tests for Lightweight Accessibility & Contrast Scanner (Week 3 enhancement).
Verifies detection of missing accessible names, missing image alt attributes, and small touch targets.
"""

from automation.engine import (
    AccessibilityFinding,
    AccessibilityScanner,
    audit_dom_accessibility,
)


def test_accessibility_detects_unlabeled_button():
    dom = [
        {
            "tag": "button",
            "test_id": "btn-icon-cart",
            "text": "",
            "aria_label": "",
            "box": {"width": 32, "height": 32},
        }
    ]
    findings = AccessibilityScanner.audit_element_tree(dom)
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, AccessibilityFinding)
    assert f.issue_type == "missing_accessible_name"
    assert f.severity == "high"
    assert "4.1.2" in f.wcag_criterion


def test_accessibility_detects_missing_image_alt():
    dom = [
        {
            "tag": "img",
            "test_id": "product-hero",
            "alt": None,
            "box": {"width": 300, "height": 300},
        }
    ]
    findings = audit_dom_accessibility(dom)
    assert len(findings) == 1
    assert findings[0].issue_type == "missing_alt_text"
    assert "1.1.1" in findings[0].wcag_criterion


def test_accessibility_detects_substandard_touch_target():
    dom = [
        {
            "tag": "button",
            "test_id": "btn-tiny",
            "text": "X",
            "box": {"width": 16, "height": 16},
        }
    ]
    findings = audit_dom_accessibility(dom)
    assert len(findings) == 1
    assert findings[0].issue_type == "substandard_target_size"
    assert findings[0].severity == "low"
