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


def test_accept_app_css_and_index_css():
    diff = "-.root { margin: 0; }\n+.root { margin: 4px; }"
    for target in ["app-under-test/src/App.css", "app-under-test/src/index.css"]:
        res = validate_patch(target, diff)
        assert res["validation_status"] is True
        assert res["validator_errors"] is None


def test_accept_leading_dot_slash():
    diff = "-.btn { width: 500px; }\n+.btn { width: 100%; }"
    res = validate_patch("./app-under-test/src/styles/defects.css", diff)
    assert res["validation_status"] is True
    assert res["target_file"] == "app-under-test/src/styles/defects.css"


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


def test_reject_script_injection_in_file_content():
    target = "app-under-test/src/styles/defects.css"
    diff = "-.btn { width: 500px; }\n+.btn { width: 100%; }"
    bad_content = ".btn { width: 100%; } <script>evil()</script>"
    res = validate_patch(target, diff, file_content=bad_content)
    assert res["validation_status"] is False
    assert "Malicious script injection" in res["validator_errors"]


def test_reject_null_byte_in_file_content():
    target = "app-under-test/src/styles/defects.css"
    diff = "-.btn { width: 500px; }\n+.btn { width: 100%; }"
    bad_content = ".btn { width: 100%; }\x00/* hidden payload */"
    res = validate_patch(target, diff, file_content=bad_content)
    assert res["validation_status"] is False
    assert "Null byte detected in file content payload" in res["validator_errors"]


def test_patch_validator_whitespace_tolerance():
    """Verify patch validator gracefully handles surrounding whitespace and newlines."""
    target = "  app-under-test/src/styles/defects.css  \n"
    diff = "  \n\n -.btn { width: 500px; }\n+.btn { width: 100%; }\n\n  "
    res = validate_patch(target, diff)
    assert res["validation_status"] is True
    assert res["target_file"] == "app-under-test/src/styles/defects.css"


def test_reject_css_import_directive():
    """Verify @import directives in CSS diff or file content are strictly rejected."""
    target = "app-under-test/src/styles/defects.css"
    diff = "+@import url('https://evil.attacker.com/leak.css');\n+.btn { width: 100%; }"
    res = validate_patch(target, diff)
    assert res["validation_status"] is False
    assert "@import" in res["validator_errors"]


def test_reject_css_behavior_directive():
    """Verify behavior: property in CSS diff or file content is rejected."""
    target = "app-under-test/src/styles/defects.css"
    diff = "+.banner { behavior: url(evil.htc); }"
    res = validate_patch(target, diff)
    assert res["validation_status"] is False
    assert "behavior" in res["validator_errors"]


def test_reject_css_moz_binding_directive():
    """Verify -moz-binding property in CSS is rejected."""
    target = "app-under-test/src/styles/defects.css"
    diff = "+.banner { -moz-binding: url(evil.xml#xss); }"
    res = validate_patch(target, diff)
    assert res["validation_status"] is False
    assert "-moz-binding" in res["validator_errors"]


def test_accept_valid_responsive_css_media_queries():
    """Verify valid CSS with @media queries and standard layout rules passes validation."""
    target = "app-under-test/src/styles/defects.css"
    diff = """
+@media (max-width: 600px) {
+  .checkout-container {
+    display: flex;
+    flex-direction: column;
+    width: 100%;
+  }
+}
"""
    res = validate_patch(target, diff)
    assert res["validation_status"] is True
    assert res["validator_errors"] is None


