"""
Unit Tests for Enhanced GitHub PR Description Generation.
Verifies inclusion of accessibility badges and token optimization metrics.
"""

from app.services.github_service import generate_pr_markdown_description


def test_pr_markdown_with_accessibility_and_tokens():
    md = generate_pr_markdown_description(
        defect_title="Button clipping",
        viewport="mobile_375x667",
        target_file="defects.css",
        diff="-.btn { width: 500px; }\n+.btn { width: 100%; }",
        accessibility_score="✅ WCAG 2.1 AA Passed",
        token_savings_pct=92.5,
    )
    assert "WCAG 2.1 AA Passed" in md
    assert "92.5%" in md
    assert "Remediation Metrics & Accessibility" in md
    assert "Button clipping" in md


def test_pr_markdown_defaults_gracefully():
    md = generate_pr_markdown_description(
        defect_title="Header overlap",
        viewport="desktop_1440x900",
        target_file="defects.css",
        diff="-.h1 { margin-top: -20px; }\n+.h1 { margin-top: 10px; }",
    )
    assert "WCAG 2.1 AA Compliant" in md
    assert "N/A" in md
    assert "Zero-trust Verified" in md
