"""
Automated unit tests for OmniSight Forensic Bundling Engine.
Verifies artifact consolidation, cryptographic SHA-256 calculation, and ZIP packaging.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
import pytest

from automation.forensics import ForensicBundler, compute_sha256, create_forensic_bundle


def test_compute_sha256(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    content = b"OmniSight Forensic Verification Evidence 2026"
    test_file.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert compute_sha256(test_file) == expected


def test_forensic_bundler_packaging(tmp_path: Path):
    run_id = "run-test-forensics-101"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    # Populate sample artifacts
    (run_dir / "screenshots").mkdir()
    (run_dir / "screenshots" / "desktop_1440x900_home.png").write_bytes(b"\x89PNG\r\n\x1a\nfakeimage")
    (run_dir / "dom").mkdir()
    (run_dir / "dom" / "home_dom.json").write_text(json.dumps({"elements": 42}))
    (run_dir / "logs").mkdir()
    (run_dir / "logs" / "console.json").write_text(json.dumps([{"msg": "console test"}]))

    bundler = ForensicBundler(artifacts_base_dir=tmp_path)
    result = bundler.bundle_run(
        run_id=run_id,
        run_dir=run_dir,
        run_data={"target": "http://localhost:5173", "status": "fixed"}
    )

    assert result["run_id"] == run_id
    assert result["bundle_name"] == f"forensic_bundle_{run_id}.zip"
    assert len(result["sha256"]) == 64
    assert result["size_bytes"] > 0
    assert result["artifact_count"] >= 5

    # Verify physical zip file content
    zip_path = Path(result["bundle_file"])
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert f"{run_id}/checksums.sha256" in namelist
        assert f"{run_id}/forensic_manifest.json" in namelist
        assert f"{run_id}/screenshots/desktop_1440x900_home.png" in namelist
        assert f"{run_id}/dom/home_dom.json" in namelist

        # Validate checksum file matches extracted content
        checksums_bytes = zf.read(f"{run_id}/checksums.sha256").decode("utf-8")
        assert "desktop_1440x900_home.png" in checksums_bytes


def test_forensic_bundler_tamper_evidence(tmp_path: Path):
    run_id = "run-tamper-check"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    evidence_file = run_dir / "evidence.txt"
    evidence_file.write_text("original content")

    result1 = create_forensic_bundle(run_id=run_id, run_dir=run_dir)
    original_hash = result1["sha256"]

    # Tamper with evidence file
    evidence_file.write_text("tampered content")
    result2 = create_forensic_bundle(run_id=run_id, run_dir=run_dir)
    tampered_hash = result2["sha256"]

    assert original_hash != tampered_hash
