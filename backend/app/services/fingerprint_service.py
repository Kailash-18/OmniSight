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


def _finding_to_dict(finding: Any) -> Dict[str, Any]:
    """Converts a finding whether dict or Pydantic model to a standard dictionary."""
    if isinstance(finding, dict):
        return dict(finding)
    if hasattr(finding, "model_dump"):
        return finding.model_dump()
    if hasattr(finding, "dict"):
        return finding.dict()
    return dict(getattr(finding, "__dict__", {}))


def generate_defect_fingerprint(
    category: Any,
    target_element: Optional[str],
    viewport: Optional[str] = None,
    suggested_change: Optional[str] = None,
    include_viewport: bool = False
) -> str:
    """
    Generates a deterministic SHA-256 fingerprint identifying a visual defect pattern.
    If include_viewport is False (default), allows grouping identical defects across viewports.
    """
    cat_val = getattr(category, "value", category) if category else "element_overlap"
    norm_category = str(cat_val).strip().lower().replace("-", "_")
    norm_selector = _normalize_selector(target_element)
    norm_prop = _extract_primary_css_property(suggested_change)

    elements = [norm_category, norm_selector, norm_prop]
    if include_viewport and viewport:
        elements.append(viewport.strip().lower())

    canonical_key = "|".join(elements)
    digest = hashlib.sha256(canonical_key.encode("utf-8")).hexdigest()[:16]
    return f"dfp-{digest}"


def compute_finding_fingerprint(finding: Any, include_viewport: bool = False) -> str:
    """Helper to compute and return a fingerprint for a finding dictionary or Pydantic model."""
    f_dict = _finding_to_dict(finding)
    return generate_defect_fingerprint(
        category=f_dict.get("category", "element_overlap"),
        target_element=f_dict.get("target_element"),
        viewport=f_dict.get("viewport"),
        suggested_change=f_dict.get("suggested_change"),
        include_viewport=include_viewport
    )


def deduplicate_findings(findings: List[Any]) -> List[Dict[str, Any]]:
    """
    Deduplicates a collection of findings by fingerprint.
    When duplicates are encountered, preserves the one with higher confidence score.
    Supports both dictionaries and Pydantic models.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for item in findings:
        f_dict = _finding_to_dict(item)
        fp = f_dict.get("fingerprint") or compute_finding_fingerprint(f_dict)
        f_dict["fingerprint"] = fp

        if fp not in seen:
            seen[fp] = f_dict
        else:
            prev_conf = float(seen[fp].get("confidence", 0.0))
            curr_conf = float(f_dict.get("confidence", 0.0))
            if curr_conf > prev_conf:
                seen[fp] = f_dict

    return list(seen.values())


def cluster_defect_findings(
    findings: List[Any],
    run_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Aggregates findings into distinct clusters based on their deterministic fingerprint.
    Tracks occurrence frequencies, affected viewports, severities, and timeline boundaries.
    Supports both dictionaries and Pydantic models.
    """
    clusters: Dict[str, Dict[str, Any]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    for raw in findings:
        item = _finding_to_dict(raw)
        fp = item.get("fingerprint") or compute_finding_fingerprint(item)
        cat = getattr(item.get("category"), "value", item.get("category", "element_overlap"))
        target = item.get("target_element")
        vp = item.get("viewport", "unknown")
        sev = getattr(item.get("severity"), "value", item.get("severity", "medium"))

        if fp not in clusters:
            clusters[fp] = {
                "fingerprint": fp,
                "category": str(cat),
                "target_element": target,
                "occurrences": 1,
                "run_ids": [run_id] if run_id else [],
                "viewports": [vp] if vp else [],
                "severities": [str(sev)] if sev else [],
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
            if sev and str(sev) not in cluster["severities"]:
                cluster["severities"].append(str(sev))
            cluster["last_seen"] = now_iso

    return list(clusters.values())
