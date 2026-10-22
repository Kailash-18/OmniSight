"""
Closed-Loop Agent Orchestrator.
Coordinates the Inspect -> Audit -> Patch -> Retest -> Evaluate state machine.
"""

from enum import Enum
from pathlib import Path
import re
from typing import Dict, Any, Optional, List
from automation.config import config
from automation.evidence import EvidenceCollector
from automation.browser_runner import run_visual_audit_journey
from automation.vlm_adapter import BaseVLMAdapter, MockVLMAdapter
from automation.schemas import VisualAuditReport, Finding
from automation.spatial_analyzer import SpatialAnalyzer
from automation.visual_diff import VisualComparator


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
        self.spatial_analyzer = SpatialAnalyzer()
        self.visual_comparator = VisualComparator()

    def _enrich_with_spatial_analysis(
        self,
        audit_report: VisualAuditReport,
        evidence: EvidenceCollector,
        run_results: Dict[str, Any],
    ) -> VisualAuditReport:
        """
        Grounds VLM findings with deterministic DOM spatial geometry analysis
        and creates bounding-box annotated screenshot overlays.
        """
        dom_snapshots = run_results.get("dom_snapshots", [])
        screenshots = run_results.get("screenshots", [])
        annotated_paths: List[str] = []

        existing_finding_keys = {
            (f.category, f.target_element, f.viewport) for f in audit_report.findings
        }

        for dom_path_str in dom_snapshots:
            dom_file = Path(dom_path_str)
            if not dom_file.exists():
                continue

            match = re.match(r"^(.*)_(home|cart|checkout)_dom\.json$", dom_file.name)
            if match:
                vp_name, page_name = match.group(1), match.group(2)
            else:
                vp_name, page_name = "default", "step"

            anomalies = self.spatial_analyzer.analyze_dom_file(dom_file)
            if not anomalies:
                continue

            spatial_findings = self.spatial_analyzer.to_findings(
                anomalies, viewport_name=vp_name
            )
            for sf in spatial_findings:
                key = (sf.category, sf.target_element, sf.viewport)
                if key not in existing_finding_keys:
                    audit_report.findings.append(sf)
                    existing_finding_keys.add(key)

            target_shot_name = f"{vp_name}_{page_name}.png"
            matching_shot = next((s for s in screenshots if target_shot_name in s), None)
            if matching_shot and Path(matching_shot).exists():
                annotated_path = evidence.get_annotated_path(vp_name, page_name)
                self.visual_comparator.annotate_anomalies(
                    image_path=Path(matching_shot),
                    anomalies=anomalies,
                    output_path=annotated_path,
                )
                annotated_paths.append(str(annotated_path))

        audit_report.annotated_screenshots.extend(annotated_paths)
        return audit_report

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

            audit_report = self._enrich_with_spatial_analysis(
                audit_report=audit_report,
                evidence=evidence,
                run_results=run_results,
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
                "annotated_screenshots": audit_report.annotated_screenshots,
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
