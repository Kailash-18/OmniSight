# -*- coding: utf-8 -*-
"""
Visual Defect Fingerprinting & Deduplication Service for OmniSight.
Enables deterministic visual defect signature generation, cross-viewport clustering,
and duplicate alert mitigation.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def _extract_primary_css_property(suggested_change: Optional[str]) -> str:
    """Extracts the primary CSS property key from a suggested CSS rule correction."""
    if not suggested_change:
        return "layout"
    clean = suggested_change.strip()
    match = re.search(r"([a-z\-]+)\s*:", clean, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return "layout"


def _normalize_selector(selector: Optional[str]) -> str:
    """Normalizes a CSS selector by stripping whitespace and standardizing quotes."""
    if not selector:
        return "body"
    norm = re.sub(r"\s+", " ", selector.strip().lower())
    norm = norm.replace("'", '"')
    return norm


def generate_defect_fingerprint(
    category: str,
    target_element: Optional[str],
    viewport: Optional[str] = None,
    suggested_change: Optional[str] = None,
    include_viewport: bool = False
) -> str:
    """
    Generates a deterministic SHA-256 fingerprint identifying a visual defect pattern.
    If include_viewport is False (default), allows grouping identical defects across viewports.
    """
    norm_category = (category or "element_overlap").strip().lower().replace("-", "_")
    norm_selector = _normalize_selector(target_element)
    norm_prop = _extract_primary_css_property(suggested_change)

    elements = [norm_category, norm_selector, norm_prop]
    if include_viewport and viewport:
        elements.append(viewport.strip().lower())

    canonical_key = "|".join(elements)
    digest = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]
    return f"dfp-{digest}"


def compute_finding_fingerprint(finding: Dict[str, Any], include_viewport: bool = False) -> str:
    """Helper to compute and return a fingerprint for a finding dictionary."""
    return generate_defect_fingerprint(
        category=finding.get("category", "element_overlap"),
        target_element=finding.get("target_element"),
        viewport=finding.get("viewport"),
        suggested_change=finding.get("suggested_change"),
        include_viewport=include_viewport
    )


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates a collection of findings by fingerprint.
    When duplicates are encountered, preserves the one with higher confidence score.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for f in findings:
        fp = f.get("fingerprint") or compute_finding_fingerprint(f)
        f_copy = dict(f)
        f_copy["fingerprint"] = fp

        if fp not in seen:
            seen[fp] = f_copy
        else:
            prev_conf = float(seen[fp].get("confidence", 0.0))
            curr_conf = float(f.get("confidence", 0.0))
            if curr_conf > prev_conf:
                seen[fp] = f_copy

    return list(seen.values())


def cluster_defect_findings(
    findings: List[Dict[str, Any]],
    run_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Aggregates findings into distinct clusters based on their deterministic fingerprint.
    Tracks occurrence frequencies, affected viewports, severities, and timeline boundaries.
    """
    clusters: Dict[str, Dict[str, Any]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in findings:
        fp = item.get("fingerprint") or compute_finding_fingerprint(item)
        cat = item.get("category", "element_overlap")
        target = item.get("target_element")
        vp = item.get("viewport", "unknown")
        sev = item.get("severity", "medium")

        if fp not in clusters:
            clusters[fp] = {
                "fingerprint": fp,
                "category": cat,
                "target_element": target,
                "occurrences": 1,
                "run_ids": [run_id] if run_id else [],
                "viewports": [vp] if vp else [],
                "severities": [sev] if sev else [],
                "first_seen": now_iso,
                "last_seen": now_iso
            }
        else:
            cluster = clusters[fp]
            cluster["occurrences"] += 1
            if run_id and run_id not in cluster["run_ids"]:
                cluster["run_ids"].append(run_id)
            if vp and vp not in cluster["viewports"]:
                cluster["viewports"].append(vp)
            if sev and sev not in cluster["severities"]:
                cluster["severities"].append(sev)
            cluster["last_seen"] = now_iso

    return list(clusters.values())
