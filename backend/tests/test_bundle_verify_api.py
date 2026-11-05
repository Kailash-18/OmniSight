"""
Unit & Integration Tests for Forensic Bundle Cryptographic Verification.
Verifies SHA-256 integrity validation and tampering detection.
"""

from fastapi.testclient import TestClient
from pathlib import Path
from app.services.forensics_service import compile_forensic_bundle, verify_forensic_bundle_integrity


def test_verify_bundle_integrity_clean(tmp_path: Path):
    run_id = "test-verify-run"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "test.txt").write_text("Hello Forensic World", encoding="utf-8")

    compile_forensic_bundle(run_id=run_id, run_data={"run_id": run_id, "status": "fixed"}, artifacts_base_dir=tmp_path)
    res = verify_forensic_bundle_integrity(run_id=run_id, artifacts_base_dir=tmp_path)
    assert res["is_valid"] is True
    assert res["verified_files_count"] >= 1
    assert len(res["discrepancies"]) == 0


def test_verify_bundle_detects_tampering(tmp_path: Path):
    run_id = "test-tamper-run"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    art = run_dir / "target.txt"
    art.write_text("Original content", encoding="utf-8")

    compile_forensic_bundle(run_id=run_id, run_data={"run_id": run_id, "status": "fixed"}, artifacts_base_dir=tmp_path)

    # Tamper with the file
    art.write_text("Maliciously altered content", encoding="utf-8")

    res = verify_forensic_bundle_integrity(run_id=run_id, artifacts_base_dir=tmp_path)
    assert res["is_valid"] is False
    assert len(res["discrepancies"]) > 0
    assert "Hash mismatch" in res["discrepancies"][0]


def test_verify_bundle_endpoint(client: TestClient):
    # Queue a run
    payload = {
        "target_url": "http://localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow",
    }
    r = client.post("/webhook/build", json=payload)
    run_id = r.json()["run_id"]

    # Compile bundle first
    client.post(f"/runs/{run_id}/forensics")

    # Verify endpoint
    res = client.get(f"/runs/{run_id}/forensics/verify")
    assert res.status_code == 200
    assert res.json()["is_valid"] is True
