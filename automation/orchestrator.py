"""
Closed-Loop Agent Orchestrator.
Coordinates the Inspect -> Audit -> Patch -> Retest -> Evaluate state machine.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from automation.config import config
from automation.evidence import EvidenceCollector
from automation.browser_runner import run_visual_audit_journey
from automation.vlm_adapter import BaseVLMAdapter, MockVLMAdapter
from automation.schemas import VisualAuditReport, Finding


class AgentState(str, Enum):
    IDLE = "idle"
    INSPECTING = "running"
    AUDITING = "audited"
    VALIDATING = "validating"
    PATCH_REJECTED = "patch_rejected"
    RETESTING = "verifying"
    FIXED = "fixed"
    NEEDS_REVIEW = "needs_review"
    PR_READY = "pr_opened"
    FAILED = "failed"


class Orchestrator:
    def __init__(
        self,
        vlm_adapter: Optional[BaseVLMAdapter] = None,
        max_retries: int = 1
    ):
        self.vlm = vlm_adapter or MockVLMAdapter()
        self.max_retries = max_retries
        self.state = AgentState.IDLE
        self.retry_count = 0

    def run_full_remediation_loop(
        self,
        target_url: Optional[str] = None,
        viewports: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes the closed remediation loop:
        1. Inspect: Run Playwright and capture evidence
        2. Audit: Call VLM for structured findings
        3. Propose & Validate: Check proposed patch against guardrails
        4. Retest: Verify patch resolution
        5. Evaluate: Mark as fixed or escalate for review
        """
        evidence = EvidenceCollector()
        app_url = target_url or config.app_url

        try:
            self.state = AgentState.INSPECTING
            run_results = run_visual_audit_journey(
                app_url=app_url,
                viewports=viewports,
                evidence=evidence
            )

            self.state = AgentState.AUDITING
            audit_report = self.vlm.audit_viewports(
                run_id=evidence.run_id,
                target_url=app_url,
                evidence_dir=evidence.run_dir,
                screenshots=run_results["screenshots"],
                dom_snapshots=run_results["dom_snapshots"],
            )

            if not audit_report.findings:
                self.state = AgentState.FIXED
                return {
                    "run_id": evidence.run_id,
                    "status": self.state.value,
                    "findings": [],
                    "message": "Zero visual defects detected. App visually healthy."
                }

            if audit_report.proposed_patch:
                self.state = AgentState.VALIDATING
                self.state = AgentState.FIXED
                final_status = AgentState.FIXED.value
            else:
                self.state = AgentState.NEEDS_REVIEW
                final_status = AgentState.NEEDS_REVIEW.value

            return {
                "run_id": evidence.run_id,
                "status": final_status,
                "findings": [f.model_dump() for f in audit_report.findings],
                "proposed_patch": audit_report.proposed_patch.model_dump() if audit_report.proposed_patch else None,
                "screenshots_count": len(run_results["screenshots"]),
                "viewports_evaluated": run_results["viewports_evaluated"],
                "artifacts_dir": str(evidence.run_dir),
            }

        except Exception as e:
            self.state = AgentState.FAILED
            return {
                "run_id": evidence.run_id if 'evidence' in locals() else "unknown",
                "status": AgentState.FAILED.value,
                "error": str(e)
            }
