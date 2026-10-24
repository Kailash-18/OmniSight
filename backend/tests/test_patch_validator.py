"""
Unit Tests for Patch Security Validator (Member 1).
Verifies path traversal protection, file allowlist, extension boundaries, and code injection defenses.
"""

from app.services.patch_validator import validate_patch


def test_valid_css_patch_accepted():
    target = "app-under-test/src/styles/defects.css"
    diff = """--- a/app-under-test/src/styles/defects.css
+++ b/app-under-test/src/styles/defects.css
@@ -10,3 +10,3 @@
-.promo-banner { position: absolute; }
+.promo-banner { position: static; }
"""
    result = validate_patch(target, diff)
    assert result["validation_status"] is True
    assert result["validator_errors"] is None
    assert result["target_file"] == target


def test_valid_component_patch_accepted():
    target = "app-under-test/src/components/Checkout.jsx"
    diff = """--- a/app-under-test/src/components/Checkout.jsx
+++ b/app-under-test/src/components/Checkout.jsx
@@ -15,1 +15,1 @@
-  <div className="btn-clipped">
+  <div className="btn-responsive">
"""
    result = validate_patch(target, diff)
    assert result["validation_status"] is True
    assert result["validator_errors"] is None


def test_reject_path_traversal():
    traversal_targets = [
        "../backend/app/main.py",
        "app-under-test/src/../../backend/.env",
        "../../etc/passwd",
        "app-under-test/src/styles/../../../passwords.txt",
        "app-under-test/src/%2e%2e/backend/app/main.py",
        "app-under-test/src/styles/%2e%2e%2fdefects.css",
    ]
    diff = "-old\n+new"
    for target in traversal_targets:
        res = validate_patch(target, diff)
        assert res["validation_status"] is False
        assert "Security violation" in res["validator_errors"]


def test_reject_null_bytes():
    bad_target = "app-under-test/src/styles/\x00defects.css"
    res = validate_patch(bad_target, "-old\n+new")
    assert res["validation_status"] is False
    assert "Null byte detected" in res["validator_errors"]

    bad_diff = "-old\n+\x00malicious"
    res2 = validate_patch("app-under-test/src/styles/defects.css", bad_diff)
    assert res2["validation_status"] is False
    assert "Null byte detected" in res2["validator_errors"]


def test_reject_absolute_paths():
    absolute_targets = [
        "/etc/passwd",
        "/var/log/app.log",
        "C:/Windows/System32/cmd.exe",
        "D:\\projects\\secret.key",
    ]
    diff = "-old\n+new"
    for target in absolute_targets:
        res = validate_patch(target, diff)
        assert res["validation_status"] is False
        assert "Security violation" in res["validator_errors"]


def test_reject_unapproved_files():
    unapproved = [
        "backend/app/main.py",
        "package.json",
        "README.md",
        "automation/browser_runner.py",
    ]
    diff = "-old\n+new"
    for target in unapproved:
        res = validate_patch(target, diff)
        assert res["validation_status"] is False
        assert "not in the approved allowlist" in res["validator_errors"]


def test_reject_disallowed_extensions():
    bad_ext_targets = [
        "app-under-test/src/components/script.py",
        "app-under-test/src/components/run.sh",
        "app-under-test/src/components/binary.exe",
    ]
    diff = "-old\n+new"
    for target in bad_ext_targets:
        res = validate_patch(target, diff)
        assert res["validation_status"] is False
        assert "File extension" in res["validator_errors"]


def test_reject_empty_diff():
    target = "app-under-test/src/styles/defects.css"
    for empty in ["", "   ", "\n\n"]:
        res = validate_patch(target, empty)
        assert res["validation_status"] is False
        assert "Provided patch diff is empty" in res["validator_errors"]


def test_reject_script_injection_in_css():
    target = "app-under-test/src/styles/defects.css"
    dangerous_diffs = [
        ".promo { background: url('javascript:alert(1)'); }",
        ".promo { behavior: expression(alert(1)); }",
        "<script>window.location='http://evil.com'</script>",
        ".promo { background: red; } /* eval('test') */",
    ]
    for bad_diff in dangerous_diffs:
        res = validate_patch(target, bad_diff)
        assert res["validation_status"] is False
        assert "injection pattern detected" in res["validator_errors"]


def test_target_path_prefix_normalization():
    diff = "-old\n+new"
    for prefixed in [
        "./app-under-test/src/styles/defects.css",
        "a/app-under-test/src/styles/defects.css",
        "b/app-under-test/src/styles/defects.css",
        "./app-under-test/src/App.css",
        "a/app-under-test/src/index.css",
    ]:
        res = validate_patch(prefixed, diff)
        assert res["validation_status"] is True
        assert res["validator_errors"] is None


def test_validate_patch_with_file_content():
    target = "app-under-test/src/styles/defects.css"
    diff = "-old\n+new"

    # Valid file content
    good_content = ".container { display: flex; }"
    res = validate_patch(target, diff, file_content=good_content)
    assert res["validation_status"] is True

    # Malicious file content
    bad_content = ".container { display: flex; } <script>alert(1)</script>"
    res_bad = validate_patch(target, diff, file_content=bad_content)
    assert res_bad["validation_status"] is False
    assert "injection pattern detected in file content" in res_bad["validator_errors"]

    # Null byte in file content
    null_content = ".container { \x00 display: flex; }"
    res_null = validate_patch(target, diff, file_content=null_content)
    assert res_null["validation_status"] is False
    assert "Null byte detected" in res_null["validator_errors"]

