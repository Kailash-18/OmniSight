"""
Regression Guard Engine for validating DOM spatial stability and visual invariants.
"""
import math
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from backend.app.schemas.regression_guard_schema import (
    VisualInvariantCheckRequest, VisualInvariantCheckResponse,
    SpatialDriftMetric, DriftSeverity
)

class RegressionGuardEngine:
    def __init__(self, default_max_shift_px: float = 2.0):
        self.default_max_shift_px = default_max_shift_px

    def calculate_drift(self, b_node, p_node, max_shift: float, max_area_pct: float) -> SpatialDriftMetric:
        dx = p_node.x - b_node.x
        dy = p_node.y - b_node.y
        dw = p_node.width - b_node.width
        dh = p_node.height - b_node.height
        euclidean = math.sqrt(dx * dx + dy * dy)
        base_area = max(1, b_node.width * b_node.height)
        patch_area = max(1, p_node.width * p_node.height)
        area_delta_pct = abs(patch_area - base_area) / base_area * 100.0
        
        is_preserved = (euclidean <= max_shift) and (area_delta_pct <= max_area_pct)
        if is_preserved:
            severity = DriftSeverity.STABLE if euclidean == 0 else DriftSeverity.MINOR_SHIFT
        else:
            severity = DriftSeverity.REGRESSION_VIOLATION
            
        return SpatialDriftMetric(
            node_id=b_node.node_id,
            selector=b_node.selector,
            dx=dx,
            dy=dy,
            d_width=dw,
            d_height=dh,
            euclidean_shift=round(euclidean, 2),
            area_delta_pct=round(area_delta_pct, 2),
            is_invariant_preserved=is_preserved,
            severity=severity
        )

    def verify_spatial_invariants(self, req: VisualInvariantCheckRequest) -> VisualInvariantCheckResponse:
        p_map = {n.node_id: n for n in req.patched_nodes}
        drift_list: List[SpatialDriftMetric] = []
        violations = 0
        
        for b in req.baseline_nodes:
            # Skip evaluating the intentionally modified target element
            if b.selector == req.target_selector:
                continue
            if b.node_id in p_map:
                p = p_map[b.node_id]
                d = self.calculate_drift(b, p, req.max_allowed_shift_px, req.max_allowed_area_change_pct)
                drift_list.append(d)
                if not d.is_invariant_preserved:
                    violations += 1
                    
        total_evaluated = len(drift_list)
        stability = round(max(0.0, 1.0 - (violations / max(1, total_evaluated))), 3)
        
        return VisualInvariantCheckResponse(
            run_id=req.run_id,
            total_nodes_evaluated=total_evaluated,
            invariant_preserved=(violations == 0),
            layout_stability_score=stability,
            violations_detected=violations,
            drift_details=drift_list,
            evaluated_at=datetime.now(timezone.utc).isoformat()
        )
