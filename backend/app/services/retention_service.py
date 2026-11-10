"""Audit run retention and storage lifecycle management for OmniSight.

Manages run pruning policies (maximum retained runs, TTL expiration, artifact cleanup)
to maintain predictable disk usage on containerized production hosts.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


class RunRetentionService:
    """Prunes stale audit run metadata and artifact directories."""

    @staticmethod
    def cleanup_runs(
        runs_db: Dict[str, Any],
        artifacts_dir: Optional[Path] = None,
        max_runs_to_keep: int = 50,
        preserve_fixed: bool = True,
    ) -> Dict[str, Any]:
        """Prunes oldest runs exceeding max_runs_to_keep threshold."""
        if len(runs_db) <= max_runs_to_keep:
            return {
                "total_runs_before": len(runs_db),
                "total_runs_after": len(runs_db),
                "pruned_run_ids": [],
            }

        # Order runs by created_at or insertion order
        sorted_run_ids = list(runs_db.keys())

        # Determine candidates for deletion (oldest first)
        candidates_to_prune: List[str] = []
        for rid in sorted_run_ids:
            if len(runs_db) - len(candidates_to_prune) <= max_runs_to_keep:
                break
            record = runs_db.get(rid, {})
            # If preserve_fixed is enabled and run is verified fixed, give it lower priority to prune
            if preserve_fixed and record.get("status") == "fixed":
                continue
            candidates_to_prune.append(rid)

        # If still above limit, prune oldest regardless
        if len(runs_db) - len(candidates_to_prune) > max_runs_to_keep:
            for rid in sorted_run_ids:
                if len(runs_db) - len(candidates_to_prune) <= max_runs_to_keep:
                    break
                if rid not in candidates_to_prune:
                    candidates_to_prune.append(rid)

        # Delete metadata and artifact directories
        pruned_ids: List[str] = []
        for rid in candidates_to_prune:
            if rid in runs_db:
                del runs_db[rid]
                pruned_ids.append(rid)

            if artifacts_dir:
                run_dir = artifacts_dir / "runs" / rid
                if run_dir.exists() and run_dir.is_dir():
                    try:
                        shutil.rmtree(run_dir, ignore_errors=True)
                    except OSError:
                        pass

        return {
            "total_runs_before": len(runs_db) + len(pruned_ids),
            "total_runs_after": len(runs_db),
            "pruned_run_ids": pruned_ids,
        }
