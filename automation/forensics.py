"""
Forensic Audit Bundling Engine for OmniSight.
Consolidates run logs, DOM snapshots, visual diffs, and verification proof
into an immutable, tamper-evident forensic bundle with SHA-256 cryptographic manifests.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import zipfile

from automation.config import config

logger = logging.getLogger("omnisight.automation.forensics")


def compute_sha256(file_path: Path) -> str:
    """Calculates SHA-256 cryptographic hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


class ForensicBundler:
    """
    Consolidates audit artifacts, generates cryptographic checksum manifests,
    and packages an immutable forensic ZIP archive for compliance and QA review.
    """

    def __init__(self, artifacts_base_dir: Optional[Path] = None):
        self.artifacts_base = artifacts_base_dir or config.artifacts_dir

    def bundle_run(
        self,
        run_id: str,
        run_dir: Optional[Path] = None,
        run_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Gathers all artifacts in run_dir, generates SHA-256 manifest and checksums,
        and packages a forensic archive.
        """
        target_dir = run_dir or (self.artifacts_base / run_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Ensure run.json exists if run_data was provided
        manifest_file = target_dir / "run.json"
        if run_data and not manifest_file.exists():
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(run_data, f, indent=2)

        # 2. Discover all artifact files inside run directory (exclude preexisting bundles)
        artifacts_to_bundle: List[Path] = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                if (
                    file.startswith("forensic_bundle_")
                    or file.endswith(".sha256")
                    or file == "forensic_manifest.json"
                ):
                    continue
                file_path = Path(root) / file
                artifacts_to_bundle.append(file_path)

        # 3. Compute checksums and structured manifest
        file_checksums: Dict[str, str] = {}
        file_records: List[Dict[str, Any]] = []
        checksum_lines: List[str] = []

        for p in sorted(artifacts_to_bundle):
            rel_path = p.relative_to(target_dir).as_posix()
            file_hash = compute_sha256(p)
            file_size = p.stat().st_size
            file_checksums[rel_path] = file_hash
            checksum_lines.append(f"{file_hash}  {rel_path}")
            file_records.append({
                "path": rel_path,
                "sha256": file_hash,
                "size_bytes": file_size,
            })

        # Save checksums.sha256
        checksums_path = target_dir / "checksums.sha256"
        checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

        # Save forensic_manifest.json
        manifest_content = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_artifacts": len(artifacts_to_bundle),
            "files": file_records,
            "audit_metadata": run_data or {},
            "specification": "OmniSight-Forensic-Audit-v1.0",
        }
        forensic_manifest_path = target_dir / "forensic_manifest.json"
        forensic_manifest_path.write_text(json.dumps(manifest_content, indent=2), encoding="utf-8")

        # 4. Package all files into forensic zip archive
        zip_filename = f"forensic_bundle_{run_id}.zip"
        zip_path = target_dir / zip_filename

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write all artifact files
            for p in artifacts_to_bundle:
                rel_path = p.relative_to(target_dir).as_posix()
                zf.write(p, arcname=f"{run_id}/{rel_path}")

            # Write checksums and forensic manifest
            zf.write(checksums_path, arcname=f"{run_id}/checksums.sha256")
            zf.write(forensic_manifest_path, arcname=f"{run_id}/forensic_manifest.json")

        # 5. Compute the hash of the bundle itself
        bundle_hash = compute_sha256(zip_path)
        bundle_size = zip_path.stat().st_size

        logger.info(
            f"Created forensic bundle for run {run_id}: {zip_path.name} "
            f"({bundle_size} bytes, SHA256: {bundle_hash[:12]}...)"
        )

        return {
            "run_id": run_id,
            "bundle_file": str(zip_path),
            "bundle_name": zip_filename,
            "sha256": bundle_hash,
            "size_bytes": bundle_size,
            "artifact_count": len(artifacts_to_bundle) + 2,
            "manifest": manifest_content,
        }


def create_forensic_bundle(
    run_id: str,
    run_dir: Optional[Path] = None,
    run_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper function to compile and package an immutable forensic bundle."""
    bundler = ForensicBundler()
    return bundler.bundle_run(run_id=run_id, run_dir=run_dir, run_data=run_data)
