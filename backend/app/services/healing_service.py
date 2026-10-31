"""
OmniSight Autonomous Self-Healing Decision & Dynamic PR Labeling Service.
Coordinates automated healing strategy evaluation, bounded retry guards, rollback simulation,
and contextual GitHub Pull Request label generation.
"""

from typing import Dict, Any, List, Optional
import time
from backend.app.schemas.healing_schema import (
    HealingStrategyType,
    HealingStrategyResponse,
    HealingSummaryResponse,
    PRLabelCalculationResponse,
    RollbackPreviewResponse,
)


class HealingEngine:
    """Evaluates self-healing strategies, enforces bounded retries, and computes triage labels."""

    def __init__(self):
        # In-memory storage for healing cycles: {run_id: [cycle_dict, ...]}
        self.healing_cycles_db: Dict[str, List[Dict[str, Any]]] = {}

    def evaluate_strategy(
        self,
        run_id: str,
        visual_diff_score: float,
        iteration_count: int = 1,
        max_retries: int = 2
    ) -> HealingStrategyResponse:
        """
        Evaluates current visual diff and iteration count to determine the optimal self-healing action.
        Guarantees strict bounded retry enforcement (max_retries).
        """
        if visual_diff_score <= 0.005:  # <= 0.5% mismatch is considered visually identical
            return HealingStrategyResponse(
                run_id=run_id,
                strategy=HealingStrategyType.IMMEDIATE_PATCH,
                action_rationale="Visual diff score is below 0.005 threshold. Fix is visually verified.",
                recommended_action="proceed_with_automated_pr",
                rollback_recommended=False,
                can_auto_merge=True,
            )

        if iteration_count >= max_retries:
            return HealingStrategyResponse(
                run_id=run_id,
                strategy=HealingStrategyType.HUMAN_ESCALATION,
                action_rationale=f"Iteration count {iteration_count} reached or exceeded max_retries limit of {max_retries}.",
                recommended_action="escalate_to_qa_lead",
                rollback_recommended=True,
                can_auto_merge=False,
            )

        if visual_diff_score > 0.40:  # High regression (> 40% difference)
            return HealingStrategyResponse(
                run_id=run_id,
                strategy=HealingStrategyType.ROLLBACK_REQUIRED,
                action_rationale=f"Visual diff score {visual_diff_score:.2f} indicates catastrophic layout degradation.",
                recommended_action="rollback_patch_and_halt",
                rollback_recommended=True,
                can_auto_merge=False,
            )

        # Iterative refinement for bounded minor defects (0.005 < diff <= 0.40)
        return HealingStrategyResponse(
            run_id=run_id,
            strategy=HealingStrategyType.ITERATIVE_REFINEMENT,
            action_rationale=f"Visual diff score {visual_diff_score:.3f} requires secondary prompt refinement within iteration budget.",
            recommended_action="trigger_vlm_secondary_refinement",
            rollback_recommended=False,
            can_auto_merge=False,
        )

    def compute_pr_labels(
        self,
        finding_count: int,
        max_severity: str = "medium",
        viewport_name: str = "desktop",
        is_verified: bool = True,
        defect_categories: Optional[List[str]] = None
    ) -> PRLabelCalculationResponse:
        """
        Dynamically computes contextual GitHub labels and color maps for automated PRs.
        """
        labels = ["omnisight", "automated-fix"]
        color_map = {
            "omnisight": "#0284c7",
            "automated-fix": "#059669",
        }

        # Severity triage
        sev_clean = max_severity.lower().strip()
        if sev_clean in ("critical", "high"):
            labels.append(f"severity:{sev_clean}")
            color_map[f"severity:{sev_clean}"] = "#dc2626"
            priority = "P0" if sev_clean == "critical" else "P1"
        else:
            labels.append(f"severity:{sev_clean}")
            color_map[f"severity:{sev_clean}"] = "#f59e0b"
            priority = "P2"

        # Viewport labeling
        vp_clean = viewport_name.lower().strip()
        labels.append(f"viewport:{vp_clean}")
        color_map[f"viewport:{vp_clean}"] = "#6366f1"

        # Verification tag
        if is_verified:
            labels.append("status:retest-verified")
            color_map["status:retest-verified"] = "#10b981"
        else:
            labels.append("status:unverified")
            color_map["status:unverified"] = "#ef4444"

        # Category tags
        if defect_categories:
            for cat in defect_categories[:2]:
                cat_slug = cat.lower().replace("_", "-")
                label_name = f"defect:{cat_slug}"
                if label_name not in labels:
                    labels.append(label_name)
                    color_map[label_name] = "#8b5cf6"

        return PRLabelCalculationResponse(
            labels=labels,
            color_map=color_map,
            priority_level=priority
        )
