"""
VLM Adapter Base Interface and Deterministic Mock Implementation.
Enables offline development and deterministic testing of the closed remediation loop.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from automation.schemas import (
    Finding,
    DefectCategory,
    Severity,
    ProposedPatch,
    VisualAuditReport,
)


class BaseVLMAdapter(ABC):
    @abstractmethod
    def audit_viewports(
        self,
        run_id: str,
        target_url: str,
        evidence_dir: Path,
        screenshots: List[str],
        dom_snapshots: List[str],
    ) -> VisualAuditReport:
        """Analyzes collected visual and structural evidence to identify defects."""
        pass


class MockVLMAdapter(BaseVLMAdapter):
    """
    Deterministic mock adapter implementing the Infotact baseline specification.
    Accurately identifies the seeded visual defects in app-under-test.
    """

    def audit_viewports(
        self,
        run_id: str,
        target_url: str,
        evidence_dir: Path,
        screenshots: List[str],
        dom_snapshots: List[str],
    ) -> VisualAuditReport:
        findings: List[Finding] = []

        # Analyze captured evidence names for seeded defect scenarios
        for shot_path in screenshots:
            path_str = str(shot_path).lower()

            if "desktop" in path_str and "home" in path_str:
                findings.append(
                    Finding(
                        id="defect-1-heading-overlap",
                        category=DefectCategory.ELEMENT_OVERLAP,
                        severity=Severity.HIGH,
                        description="Hero heading overlaps the top edge of the first product card.",
                        viewport="desktop_1440x900",
                        target_element=".hero-title",
                        confidence=0.95,
                        suggested_change="Remove negative bottom margin (-96px) from .hero-title.",
                        rationale="Spatial analysis reveals .hero-title bounding box intersects with .product-grid.",
                        status="detected",
                    )
                )

            if "mobile" in path_str and "cart" in path_str:
                findings.append(
                    Finding(
                        id="defect-2-checkout-button-clipped",
                        category=DefectCategory.ELEMENT_CLIPPING,
                        severity=Severity.HIGH,
                        description="Continue to checkout CTA button overflows the card boundary and is clipped.",
                        viewport="mobile_375x667",
                        target_element=".checkout-cta",
                        confidence=0.94,
                        suggested_change="Change min-width on .checkout-cta to 100% instead of 460px.",
                        rationale="Button width (460px) exceeds container card width (343px) under overflow: clip.",
                        status="detected",
                    )
                )

            if "checkout" in path_str:
                findings.append(
                    Finding(
                        id="defect-3-submit-button-obstructed",
                        category=DefectCategory.ELEMENT_OBSTRUCTION,
                        severity=Severity.CRITICAL,
                        description="Submit order button is completely obstructed by the free shipping promo banner.",
                        viewport="all",
                        target_element=".promo-banner",
                        confidence=0.98,
                        suggested_change="Remove absolute positioning and inset from .promo-banner.",
                        rationale="The promo banner is absolutely positioned with higher z-index covering the primary action.",
                        status="detected",
                    )
                )

        # Deduplicate findings by id
        unique_findings = {f.id: f for f in findings}.values()

        # Generate a clean patch for Defect 3 as the primary target
        patch_diff = (
            "--- a/app-under-test/src/styles/defects.css\n"
            "+++ b/app-under-test/src/styles/defects.css\n"
            "@@ -51,6 +51,3 @@\n"
            "-.checkout-actions {\n"
            "-  position: relative;\n"
            "-}\n"
            "-.promo-banner {\n"
            "-  position: absolute;\n"
            "-  inset: 0;\n"
            "-  z-index: 2;\n"
            "-  display: flex;\n"
            "-  align-items: center;\n"
            "-  justify-content: center;\n"
            "-  pointer-events: none;\n"
            "-}\n"
        )

        patch = ProposedPatch(
            target_file="app-under-test/src/styles/defects.css",
            diff=patch_diff,
            explanation="Removes absolute overlay on promo banner to restore visibility to Submit order button.",
        )

        return VisualAuditReport(
            run_id=run_id,
            target_url=target_url,
            findings=list(unique_findings),
            summary=f"Detected {len(unique_findings)} visual defects across evaluated viewports.",
            proposed_patch=patch,
        )
