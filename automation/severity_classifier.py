"""Defect severity classifier and heuristic risk scorer for visual findings.

Calculates impact severity (CRITICAL, HIGH, MEDIUM, LOW) based on element interactivity,
viewport obstruction ratio, and accessibility compliance.
"""

from __future__ import annotations

from typing import Any, Dict


class SeverityClassifier:
    """Classifies visual UI defects according to functional impact."""

    @staticmethod
    def classify(
        category: str,
        is_interactive: bool = False,
        overlap_ratio: float = 0.0,
        is_wcag_violation: bool = False,
    ) -> str:
        cat_upper = category.upper()

        # Critical: Interactive control fully obstructed or major checkout blocker
        if "OBSTRUCT" in cat_upper and is_interactive and overlap_ratio >= 0.5:
            return "CRITICAL"

        # High: Any interactive element overlap or severe WCAG violation
        if is_interactive and overlap_ratio > 0.15:
            return "HIGH"
        if is_wcag_violation and "CONTRAST" not in cat_upper:
            return "HIGH"

        # Medium: Visual overlap on non-interactive elements or text contrast
        if overlap_ratio > 0.05 or "OVERLAP" in cat_upper or is_wcag_violation:
            return "MEDIUM"

        return "LOW"
