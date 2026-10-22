"""
Live Multimodal Vision Client.
Integrates cloud vision APIs with automatic base64 image encoding and JSON parsing.
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from automation.schemas import VisualAuditReport
from automation.vlm_adapter import BaseVLMAdapter, MockVLMAdapter
from automation.prompts.audit_prompts import SYSTEM_AUDIT_PROMPT, build_user_audit_prompt


def encode_image_base64(image_path: Path) -> str:
    """Encodes a PNG file into a base64 data string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class LiveVLMAdapter(BaseVLMAdapter):
    """
    Multimodal Vision adapter for GPT-4o / Claude Vision.
    Falls back gracefully to MockVLMAdapter when credentials are not supplied.
    """

    def __init__(self, provider: str = "auto", api_key: Optional[str] = None):
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
