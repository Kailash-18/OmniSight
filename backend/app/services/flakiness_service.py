# -*- coding: utf-8 -*-
"""
Visual Defect Flakiness Detection & Quarantine Manager for OmniSight.
Tracks visual defect intermittency, computes statistical flakiness ratios,
and manages defect quarantine state to prevent false-alarm release gating.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# In-memory store for defect stability records
# Structure: {fingerprint: {"fingerprint": str, "total_observations": int, "defect_occurrences": int, ...}}
_stability_store: Dict[str, Dict[str, Any]] = {}


def reset_flakiness_tracker() -> None:
    """Resets the in-memory stability and quarantine registry (primarily for test isolation)."""
    _stability_store.clear()


def calculate_flakiness_score(total_observations: int, defect_occurrences: int) -> float:
    """
    Computes statistical flakiness score between 0.0 and 1.0.
    A defect that appears 100% of the time is deterministic/stable (score = 0.0).
    A defect that appears 0% of the time is absent (score = 0.0).
    Intermittent defects appearing sporadically exhibit high flakiness (peak at 50% ratio).
    Requires at least 2 observations to calculate non-zero flakiness.
    """
    if total_observations < 2:
        return 0.0

    p = defect_occurrences / total_observations
    # Parabolic variance metric: 4 * p * (1 - p) yields 1.0 at p=0.5, 0.0 at p=0.0 or 1.0
    raw_flakiness = 4.0 * p * (1.0 - p)
    return round(max(0.0, min(1.0, raw_flakiness)), 4)


def record_defect_observation(
    fingerprint: str,
    detected: bool,
    target_element: Optional[str] = None,
    category: str = "element_overlap"
) -> Dict[str, Any]:
    """
    Records an observation of a defect in an audit run and recalculates its stability score.
    """
    if fingerprint not in _stability_store:
        _stability_store[fingerprint] = {
            "fingerprint": fingerprint,
            "target_element": target_element,
            "category": category,
            "total_observations": 1,
            "defect_occurrences": 1 if detected else 0,
            "flakiness_score": 0.0,
            "is_quarantined": False,
            "quarantined_at": None,
            "quarantine_reason": None,
        }
    else:
        record = _stability_store[fingerprint]
        record["total_observations"] += 1
        if detected:
            record["defect_occurrences"] += 1
        if target_element and not record.get("target_element"):
            record["target_element"] = target_element

        record["flakiness_score"] = calculate_flakiness_score(
            record["total_observations"],
            record["defect_occurrences"]
        )

    return dict(_stability_store[fingerprint])


def quarantine_defect(
    fingerprint: str,
    reason: str,
    quarantined_by: str = "system"
) -> Dict[str, Any]:
    """
    Places a defect into quarantine or updates its quarantine parameters.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    if fingerprint not in _stability_store:
        _stability_store[fingerprint] = {
            "fingerprint": fingerprint,
            "target_element": None,
            "category": "element_overlap",
            "total_observations": 1,
            "defect_occurrences": 1,
            "flakiness_score": 0.0,
            "is_quarantined": True,
            "quarantined_at": now_iso,
            "quarantine_reason": reason,
            "quarantined_by": quarantined_by,
        }
    else:
        record = _stability_store[fingerprint]
        record["is_quarantined"] = True
        record["quarantined_at"] = now_iso
        record["quarantine_reason"] = reason
        record["quarantined_by"] = quarantined_by

    return dict(_stability_store[fingerprint])


def unquarantine_defect(fingerprint: str) -> bool:
    """Removes a defect from quarantine. Returns True if was quarantined, False otherwise."""
    if fingerprint in _stability_store and _stability_store[fingerprint].get("is_quarantined"):
        _stability_store[fingerprint]["is_quarantined"] = False
        _stability_store[fingerprint]["quarantine_reason"] = None
        _stability_store[fingerprint]["quarantined_at"] = None
        _stability_store[fingerprint]["quarantined_by"] = None
        return True
    return False


def is_defect_quarantined(fingerprint: str) -> bool:
    """Fast check whether a defect is currently quarantined."""
    record = _stability_store.get(fingerprint)
    if record and record.get("is_quarantined"):
        return True
    return False


def get_quarantined_defects() -> List[Dict[str, Any]]:
    """Returns list of all defects currently under quarantine."""
    return [
        dict(rec) for rec in _stability_store.values()
        if rec.get("is_quarantined")
    ]


def get_flakiness_report() -> Dict[str, Any]:
    """Returns aggregated flakiness metrics across all tracked visual defects."""
    records = list(_stability_store.values())
    quarantined = [r for r in records if r.get("is_quarantined")]
    high_flakiness = [r for r in records if r.get("flakiness_score", 0.0) >= 0.5]

    return {
        "total_tracked_defects": len(records),
        "quarantined_count": len(quarantined),
        "high_flakiness_count": len(high_flakiness),
        "defects": records
    }


def bulk_quarantine_defects(
    fingerprints: List[str],
    reason: str,
    quarantined_by: str = "system"
) -> List[Dict[str, Any]]:
    """Places multiple defect fingerprints under quarantine in a single operation."""
    results = []
    for fp in fingerprints:
        clean_fp = fp.strip()
        if clean_fp:
            results.append(quarantine_defect(clean_fp, reason, quarantined_by))
    return results


def unquarantine_all_defects() -> int:
    """Releases all currently quarantined defects. Returns count of released defects."""
    count = 0
    for record in _stability_store.values():
        if record.get("is_quarantined"):
            record["is_quarantined"] = False
            record["quarantine_reason"] = None
            record["quarantined_at"] = None
            record["quarantined_by"] = None
            count += 1
    return count
