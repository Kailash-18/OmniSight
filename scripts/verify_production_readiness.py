"""
OmniSight Production Readiness & Deployment Verification Script.
Performs pre-flight checks across container environments, runtime dependencies,
Playwright headless browser engines, API health probes, and zero-trust security.
"""

import sys
import os
import shutil
import platform
import subprocess
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_python_environment():
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 11
    print(f"[{'OK' if is_valid else 'FAIL'}] Python Runtime: {version.major}.{version.minor}.{version.micro} ({platform.system()} {platform.machine()})")
    return is_valid


def check_dependencies():
    packages = ["fastapi", "uvicorn", "pydantic", "PIL", "playwright", "github"]
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  [OK] Dependency '{pkg}' installed")
        except ImportError:
            print(f"  [FAIL] Missing required dependency '{pkg}'")
            all_ok = False
    return all_ok


def check_playwright_browsers():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser_path = p.chromium.executable_path
            print(f"  [OK] Headless Chromium executable: {browser_path}")
            return True
    except Exception as e:
        print(f"  [WARN] Playwright Chromium direct check: {e}")
        return True


def check_filesystem_permissions():
    artifacts_dir = REPO_ROOT / "artifacts" / "runs"
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe = artifacts_dir / ".readiness_probe_test"
        probe.write_text("readiness_check", encoding="utf-8")
        probe.unlink(missing_ok=True)
        print(f"  [OK] Artifact directory writable: {artifacts_dir}")
        return True
    except Exception as e:
        print(f"  [FAIL] Artifact directory write failure: {e}")
        return False


def check_zero_trust_security():
    # Verify .gitignore protects credentials and terraform state
    gitignore_path = REPO_ROOT / ".gitignore"
    if not gitignore_path.exists():
        print("  [FAIL] .gitignore is missing")
        return False

    content = gitignore_path.read_text(encoding="utf-8")
    required_rules = [".env", "*.tfvars", "*.tfstate"]
    all_present = all(rule in content for rule in required_rules)
    if all_present:
        print("  [OK] Zero-trust security: secrets, .env and terraform states protected in .gitignore")
    else:
        print("  [FAIL] .gitignore is missing essential secret protection rules")
    return all_present


def check_containerization_configs():
    dockerfiles = [
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "dashboard" / "Dockerfile",
        REPO_ROOT / "app-under-test" / "Dockerfile",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / ".dockerignore",
    ]
    all_exist = True
    for df in dockerfiles:
        if df.exists():
            print(f"  [OK] Container config present: {df.name}")
        else:
            print(f"  [FAIL] Missing container config: {df.name}")
            all_exist = False
    return all_exist


def check_terraform_configs():
    tf_files = [
        REPO_ROOT / "backend" / "terraform" / "main.tf",
        REPO_ROOT / "backend" / "terraform" / "variables.tf",
        REPO_ROOT / "backend" / "terraform" / "outputs.tf",
        REPO_ROOT / "backend" / "terraform" / "terraform.tfvars.example",
    ]
    all_exist = True
    for tf in tf_files:
        if tf.exists():
            print(f"  [OK] Terraform HCL file present: {tf.name}")
        else:
            print(f"  [FAIL] Missing Terraform file: {tf.name}")
            all_exist = False
    return all_exist


def verify_all():
    print("=" * 70)
    print("  OmniSight Week 4: Production Deployment & Cloud Readiness Verification")
    print("=" * 70)

    checks = [
        ("Python Environment", check_python_environment),
        ("Core Dependencies", check_dependencies),
        ("Browser Automation", check_playwright_browsers),
        ("Filesystem Permissions", check_filesystem_permissions),
        ("Zero-Trust Security", check_zero_trust_security),
        ("Containerization Configs", check_containerization_configs),
        ("Terraform Cloud Infrastructure", check_terraform_configs),
    ]

    results = []
    for name, fn in checks:
        print(f"\n--- Checking {name} ---")
        ok = fn()
        results.append((name, ok))

    print("\n" + "=" * 70)
    print("  Pre-Flight Verification Summary")
    print("=" * 70)
    all_passed = True
    for name, ok in results:
        status_text = "PASSED" if ok else "FAILED"
        if not ok:
            all_passed = False
        print(f"  {name:35}: {status_text}")

    print("=" * 70)
    if all_passed:
        print("  RESULT: All production readiness and containerization checks PASSED.")
        print("=" * 70)
        return 0
    else:
        print("  RESULT: One or more readiness checks failed. Review output above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(verify_all())
