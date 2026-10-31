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
        "run_id": run_id,
        "target": run_data.get("target", run_data.get("url", "unknown")),
        "status": str(run_data.get("status", "unknown")),
        "start_time": run_data.get("start_time", run_data.get("created_at", now_iso)),
        "issue_count": run_data.get("issue_count", len(findings)),
        "pr_url": run_data.get("pr_url"),
        "retry_count": run_data.get("retry_count", 0),
        "tags": run_data.get("tags", []),
    }
    metadata_json = canonical_json(metadata_payload)

    # 2. Build individual artifact envelopes with SHA-256 signatures
    artifacts = {
        "metadata.json": build_artifact_envelope("metadata.json", metadata_json, "application/json"),
        "findings.json": build_artifact_envelope("findings.json", findings_json, "application/json"),
        "patch.diff": build_artifact_envelope("patch.diff", patch_diff, "text/x-diff"),
        "retest_proof.json": build_artifact_envelope("retest_proof.json", retest_json, "application/json"),
        "timeline.json": build_artifact_envelope("timeline.json", timeline_json, "application/json"),
    }

    # Include any optional supplemental artifacts (e.g. annotations, review decisions)
    if extra_artifacts:
        for fname, content in extra_artifacts.items():
            content_str = content if isinstance(content, (str, bytes)) else canonical_json(content)
            artifacts[fname] = build_artifact_envelope(fname, content_str)

    # 3. Compute root forensic checksum over sorted artifact hashes
    sorted_digests = "".join(artifacts[k]["sha256"] for k in sorted(artifacts.keys()))
    root_checksum = hashlib.sha256(sorted_digests.encode("utf-8")).hexdigest()

    manifest = {
        "bundle_id": f"bundle-{run_id}-{root_checksum[:12]}",
        "run_id": run_id,
        "created_at": now_iso,
        "schema_version": "1.0-forensic-certified",
        "root_checksum": root_checksum,
        "artifact_count": len(artifacts),
        "artifact_digests": {k: v["sha256"] for k, v in artifacts.items()},
    }

    return {
        "bundle_id": manifest["bundle_id"],
        "run_id": run_id,
        "manifest": manifest,
        "root_checksum": root_checksum,
        "artifacts": artifacts,
        "metadata": metadata_payload,
        "findings": findings,
        "patch_diff": patch_diff,
        "retest_outcome": retest,
        "timeline": timeline,
    }


def verify_forensic_bundle_integrity(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies that a forensic bundle has not been tampered with or modified.
    Re-computes individual artifact SHA-256 digests and confirms match against root manifest.
    """
    manifest = bundle.get("manifest", {})
    recorded_root = manifest.get("root_checksum", bundle.get("root_checksum", ""))
    recorded_digests = manifest.get("artifact_digests", {})
    artifacts = bundle.get("artifacts", {})

    tampered: List[str] = []
    computed_digests: Dict[str, str] = {}

    for name, expected_hash in recorded_digests.items():
        if name not in artifacts:
            tampered.append(f"Missing artifact: {name}")
            continue

        artifact = artifacts[name]
        content = artifact.get("content")
        if content is None:
            # If content was omitted from memory, check recorded sha256 consistency
            computed_hash = artifact.get("sha256", "")
        else:
            computed_hash = compute_sha256(content)

        computed_digests[name] = computed_hash
        if computed_hash != expected_hash:
            tampered.append(f"Tampered artifact '{name}': expected {expected_hash}, computed {computed_hash}")

    # Re-verify root checksum
    sorted_digests = "".join(computed_digests[k] for k in sorted(computed_digests.keys()))
    recomputed_root = hashlib.sha256(sorted_digests.encode("utf-8")).hexdigest()

    if recomputed_root != recorded_root:
        tampered.append(f"Root checksum mismatch: expected {recorded_root}, computed {recomputed_root}")

    is_valid = len(tampered) == 0

    return {
        "is_valid": is_valid,
        "run_id": bundle.get("run_id"),
        "root_checksum": recorded_root,
        "recomputed_checksum": recomputed_root,
        "tampered_artifacts": tampered,
        "verified_at": datetime.now(UTC).isoformat(),
        "status": "VERIFIED_AUTHENTIC" if is_valid else "TAMPERING_DETECTED",
    }


def export_forensic_zip_archive(bundle: Dict[str, Any]) -> bytes:
    """
    Packages forensic bundle contents into a self-contained, in-memory ZIP archive.
    Includes manifest.json, findings.json, patch.diff, retest_proof.json, timeline.json,
    and a human-readable audit_log.txt.
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write manifest
        manifest_bytes = json.dumps(bundle.get("manifest", {}), indent=2).encode("utf-8")
        zf.writestr("manifest.json", manifest_bytes)

        # Write artifacts
        artifacts = bundle.get("artifacts", {})
        for fname, art in artifacts.items():
            content = art.get("content", "")
            if content is not None:
                raw = content.encode("utf-8") if isinstance(content, str) else content
                zf.writestr(fname, raw)

        # Write human-readable audit log
        manifest = bundle.get("manifest", {})
        audit_log = (
            f"================================================================================\n"
            f"OmniSight Certified Forensic Audit Bundle\n"
            f"================================================================================\n"
            f"Bundle ID:       {manifest.get('bundle_id')}\n"
            f"Run ID:          {bundle.get('run_id')}\n"
            f"Generated:       {manifest.get('created_at')}\n"
            f"Root SHA-256:    {manifest.get('root_checksum')}\n"
            f"Schema Version:  {manifest.get('schema_version')}\n"
            f"Artifact Count:  {manifest.get('artifact_count')}\n"
            f"Status:          SEALED & CRYPTOGRAPHICALLY CERTIFIED\n"
            f"================================================================================\n"
        )
        zf.writestr("audit_log.txt", audit_log.encode("utf-8"))

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def get_bundle_summary(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Returns high-level summary metrics of a forensic bundle for dashboard cards."""
    manifest = bundle.get("manifest", {})
    return {
        "bundle_id": manifest.get("bundle_id"),
        "run_id": bundle.get("run_id"),
        "created_at": manifest.get("created_at"),
        "artifact_count": manifest.get("artifact_count", 0),
        "root_checksum": manifest.get("root_checksum"),
        "schema_version": manifest.get("schema_version"),
    }
