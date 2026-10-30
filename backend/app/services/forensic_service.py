# -*- coding: utf-8 -*-
"""
Forensic Audit Bundling & Cryptographic Verification Service for OmniSight.
Consolidates audit run evidence, DOM states, VLM findings, and sandbox retests
into tamper-evident forensic packages with SHA-256 digital verification seals.
"""

import io
import json
import hashlib
import zipfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

UTC = timezone.utc


def compute_sha256(content: str | bytes) -> str:
    """Computes a hexadecimal SHA-256 cryptographic digest for string or byte input."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def canonical_json(data: Any) -> str:
    """Serializes data to canonical, sorted, deterministic JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def build_artifact_envelope(filename: str, content: str | bytes, mime_type: str = "application/json") -> Dict[str, Any]:
    """Wraps raw artifact content in a metadata envelope with byte size and SHA-256 digest."""
    raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return {
        "filename": filename,
        "byte_size": len(raw_bytes),
        "sha256": digest,
        "mime_type": mime_type,
        "content": content if isinstance(content, str) else None,
    }


def create_forensic_bundle(
    run_id: str,
    run_data: Dict[str, Any],
    extra_artifacts: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates an immutable, tamper-evident forensic audit bundle for an audit run.
    Aggregates run metadata, visual findings, unified patch diff, verification retests,
    and execution timeline into a cryptographically sealed package.
    """
    now_iso = datetime.now(UTC).isoformat()
    findings = run_data.get("findings") or []
    patch = run_data.get("patch")
    retest = run_data.get("retest_outcome")
    timeline = run_data.get("timeline") or []

    # 1. Prepare discrete artifact payloads
    findings_json = canonical_json(findings)
    patch_diff = ""
    if isinstance(patch, dict):
        patch_diff = patch.get("diff") or ""
    elif hasattr(patch, "diff"):
        patch_diff = getattr(patch, "diff") or ""

    retest_json = canonical_json(retest if retest is not None else {})
    timeline_json = canonical_json(timeline)

    metadata_payload = {
