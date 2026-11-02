"""Run comparison service for OmniSight.

Compares two audit runs (e.g. baseline run vs candidate/retest run) to compute
defect deltas, resolved issues, new regressions, and overall improvement scores.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Union


class RunComparator:
    """Compares two audit runs and produces a structured delta report."""

    @staticmethod
    def compare_runs(
        baseline: Union[Dict[str, Any], Any],
        candidate: Union[Dict[str, Any], Any],
    ) -> Dict[str, Any]:
        """Compares baseline and candidate runs."""
        base_id = baseline.get("id") if isinstance(baseline, dict) else getattr(baseline, "id", "")
        cand_id = candidate.get("id") if isinstance(candidate, dict) else getattr(candidate, "id", "")

        base_findings = baseline.get("findings", []) if isinstance(baseline, dict) else (getattr(baseline, "findings", None) or [])
        cand_findings = candidate.get("findings", []) if isinstance(candidate, dict) else (getattr(candidate, "findings", None) or [])

        def _finding_fingerprint(f: Any) -> str:
            if isinstance(f, dict):
                cat = str(f.get("category", "")).lower()
                sel = str(f.get("selector", "")).strip().lower()
                vp = str(f.get("viewport", "")).strip().lower()
                return f"{cat}::{sel}::{vp}"
            cat = getattr(f, "category", "")
            if hasattr(cat, "value"):
                cat = cat.value
            sel = str(getattr(f, "selector", "")).strip().lower()
            vp = str(getattr(f, "viewport", "")).strip().lower()
            return f"{str(cat).lower()}::{sel}::{vp}"

        base_keys: Set[str] = {_finding_fingerprint(f) for f in base_findings if f}
        cand_keys: Set[str] = {_finding_fingerprint(f) for f in cand_findings if f}

        resolved_count = len(base_keys - cand_keys)
        regression_count = len(cand_keys - base_keys)
        persisting_count = len(base_keys & cand_keys)

        total_base = len(base_keys)
        improvement_pct = 0.0
        if total_base > 0:
            improvement_pct = round(((resolved_count - regression_count) / total_base) * 100.0, 1)

        return {
            "baseline_run_id": base_id,
            "candidate_run_id": cand_id,
            "baseline_defect_count": len(base_findings),
            "candidate_defect_count": len(cand_findings),
            "resolved_defects_count": resolved_count,
            "new_regressions_count": regression_count,
            "persisting_defects_count": persisting_count,
            "net_improvement_percentage": improvement_pct,
            "is_improved": resolved_count > regression_count,
            "has_new_regressions": regression_count > 0,
        }
