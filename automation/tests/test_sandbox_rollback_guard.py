"""
Unit Tests for Patch Sandbox Atomic Snapshot Rollback Guard.
Verifies cryptographic SHA-256 pre-patch snapshot recording and guaranteed restoration upon exit.
"""

from pathlib import Path
import threading
import time
import pytest

from automation.engine import PatchSandbox


def test_patch_sandbox_cryptographic_rollback(tmp_path: Path):
    target = tmp_path / "test_style.css"
    initial_content = ".container { width: 100px; }\n"
    target.write_text(initial_content, encoding="utf-8")

    diff = """--- a/test_style.css
+++ b/test_style.css
@@ -1,1 +1,1 @@
-.container { width: 100px; }
+.container { width: 100%; }
"""

    with PatchSandbox(target, diff, bypass_allowlist_for_testing=True) as sandbox:
        assert sandbox.is_applied is True
        assert sandbox.original_sha256 is not None
        assert "width: 100%;" in target.read_text(encoding="utf-8")
        snapshot = sandbox.snapshot_state()
        assert snapshot["is_applied"] is True

    # After context exit
    assert target.read_text(encoding="utf-8") == initial_content
    assert sandbox.is_applied is False
    assert sandbox.verify_restoration() is True


def test_patch_sandbox_rollback_on_inner_exception(tmp_path: Path):
    target = tmp_path / "broken.css"
    initial_content = "body { margin: 0; }\n"
    target.write_text(initial_content, encoding="utf-8")

    diff = """--- a/broken.css
+++ b/broken.css
@@ -1,1 +1,1 @@
-body { margin: 0; }
+body { margin: 10px; }
"""

    with pytest.raises(RuntimeError):
        with PatchSandbox(target, diff, bypass_allowlist_for_testing=True) as sandbox:
            raise RuntimeError("Simulated crash during test run")

    assert target.read_text(encoding="utf-8") == initial_content
    assert sandbox.verify_restoration() is True
