"""
Cross-Viewport Canary Verification Engine.
Evaluates patches across mobile, tablet, and desktop viewports to certify responsive layout invariants.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from backend.app.schemas.canary_schema import (
    CanaryVerificationRequest, CanaryVerificationReport,
    ViewportStabilityResult, ViewportProfile
)
from backend.app.schemas.regression_guard_schema import SpatialDriftMetric

class CanaryVerificationEngine:
    def __init__(self):
        self._cached_reports: Dict[str, CanaryVerificationReport] = {}
        self._latest_csi: float = 100.0

    def verify_canary_patch(self, req: CanaryVerificationRequest) -> CanaryVerificationReport:
        viewport_results: List[ViewportStabilityResult] = []
        breaking_viewports: List[str] = []
        scores: List[float] = []

        for vp in req.viewports:
            drifts = req.per_viewport_drift.get(vp.name, [])
            violations = sum(1 for d in drifts if not d.is_invariant_preserved)
            total = len(drifts)
            score = round(max(0.0, 1.0 - (violations / max(1, total))), 3) if total > 0 else 1.0
            is_acceptable = (score >= vp.min_acceptable_stability) and (violations == 0)

            if not is_acceptable:
                breaking_viewports.append(vp.name)

            scores.append(score)
            viewport_results.append(ViewportStabilityResult(
                viewport=vp.name,
                width=vp.width,
                height=vp.height,
                stability_score=score,
                violations_count=violations,
                is_acceptable=is_acceptable,
                details=drifts
            ))

        csi = round((sum(scores) / max(1, len(scores))) * 100.0, 2)
        self._latest_csi = csi
        overall_passed = len(breaking_viewports) == 0

        report = CanaryVerificationReport(
            run_id=req.run_id,
            patch_id=req.patch_id,
            overall_canary_passed=overall_passed,
            canary_stability_index=csi,
            breaking_viewports=breaking_viewports,
            viewport_results=viewport_results,
            quarantine_recommended=not overall_passed,
            certified_at=datetime.now(timezone.utc).isoformat()
        )
        self._cached_reports[req.run_id] = report
        return report

    def get_report(self, run_id: str) -> Optional[CanaryVerificationReport]:
        return self._cached_reports.get(run_id)

    def export_prometheus_canary_metrics(self) -> str:
        return (
            f"# HELP omnisight_canary_stability_index Cross-viewport canary stability index score (0-100%)\n"
            f"# TYPE omnisight_canary_stability_index gauge\n"
            f"omnisight_canary_stability_index {self._latest_csi}\n"
        )

canary_engine = CanaryVerificationEngine()
