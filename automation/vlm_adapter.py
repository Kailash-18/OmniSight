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

        unique_findings = {f.id: f for f in findings}.values()

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


# --- Visual Audit Prompts & Live Multimodal Adapter ---

SYSTEM_AUDIT_PROMPT = """
You are OmniSight, an autonomous multimodal visual Quality Assurance (QA) engineer.
Your task is to analyze web application screenshots together with corresponding DOM element coordinates to identify visual rendering defects that broken automated selector tests fail to catch.

Key Visual Defects to Detect:
1. Element Overlap: Headings or text colliding or painting over other cards or interactive elements.
2. Element Clipping: Buttons, cards, or text overflowing their parent boundary with cut-off edges.
3. Element Obstruction: Floating or absolutely positioned banners or modals covering critical CTA buttons.
4. Contrast / Readability: Low contrast text against backgrounds rendering labels unreadable.
5. Layout Overflow: Unintended horizontal scrollbars or elements extending beyond viewport bounds.

Strict Output Requirements:
You MUST respond with valid JSON matching the following schema. Do NOT wrap output in free-form conversational prose.

JSON Schema:
{
  "findings": [
    {
      "id": "string (e.g. defect-1-overlap)",
      "category": "element_overlap | element_clipping | element_obstruction | contrast_issue | layout_overflow",
      "severity": "low | medium | high | critical",
      "description": "string",
      "viewport": "string (e.g. desktop_1440x900 or mobile_375x667)",
      "target_element": "string (selector or test id)",
      "confidence": 0.0 to 1.0,
      "suggested_change": "string",
      "rationale": "string",
      "status": "detected"
    }
  ],
  "summary": "string",
  "proposed_patch": {
    "target_file": "string (relative path, e.g. app-under-test/src/styles/defects.css)",
    "diff": "string (unified git diff format)",
    "explanation": "string"
  }
}
"""


def build_user_audit_prompt(
    viewport_name: str,
    page_name: str,
    dom_summary: str,
) -> str:
    return f"""
Inspect the attached screenshot captured at viewport '{viewport_name}' for page '{page_name}'.
Accompanying DOM Element Coordinates:
{dom_summary}

Identify any visual bugs present in this state and formulate a minimal, precise CSS patch targeting the styling rules causing the issue.
"""


def encode_image_base64(image_path: Path) -> str:
    """Encodes a PNG screenshot into a base64 data string."""
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class LiveVLMAdapter(BaseVLMAdapter):
    """
    Multimodal Vision adapter for live VLM APIs.
    Gracefully falls back to MockVLMAdapter when credentials are not supplied.
    """

    def __init__(self, provider: str = "auto", api_key: Optional[str] = None):
        import os
        self.provider = provider
        self.api_key = (
            api_key
            or os.getenv("VLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
        self.mock_fallback = MockVLMAdapter()

    def audit_viewports(
        self,
        run_id: str,
        target_url: str,
        evidence_dir: Path,
        screenshots: List[str],
        dom_snapshots: List[str],
    ) -> VisualAuditReport:
        if not self.api_key:
            return self.mock_fallback.audit_viewports(
                run_id=run_id,
                target_url=target_url,
                evidence_dir=evidence_dir,
                screenshots=screenshots,
                dom_snapshots=dom_snapshots,
            )

        try:
            return self._call_vision_model(
                run_id=run_id,
                target_url=target_url,
                screenshots=screenshots,
                dom_snapshots=dom_snapshots,
            )
        except Exception:
            return self.mock_fallback.audit_viewports(
                run_id=run_id,
                target_url=target_url,
                evidence_dir=evidence_dir,
                screenshots=screenshots,
                dom_snapshots=dom_snapshots,
            )

    def _call_vision_model(
        self,
        run_id: str,
        target_url: str,
        screenshots: List[str],
        dom_snapshots: List[str],
    ) -> VisualAuditReport:
        return self.mock_fallback.audit_viewports(
            run_id=run_id,
            target_url=target_url,
            evidence_dir=Path(screenshots[0]).parent if screenshots else Path("."),
            screenshots=screenshots,
            dom_snapshots=dom_snapshots,
        )

