"""
Unit & Integration Tests for GitHub Pull Request Automation Service (Member 1).
Verifies mock fallback, markdown formatting, evidence injection, and PR parameter handling.
"""

import pytest
from app.core.config import settings
from app.services.github_service import (
    generate_pr_markdown_description,
    create_pull_request_for_fix,
)


def test_mock_github_fallback_when_mock_enabled(monkeypatch):
    """Verify create_pull_request_for_fix falls back to simulated PR URL in mock mode."""
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)
    monkeypatch.setattr(settings, "REPO_NAME", "Kailash-18/OmniSight")

    pr_url = create_pull_request_for_fix(
        run_id="run-test-1001",
        target_file="app-under-test/src/styles/defects.css",
        file_content=".btn { width: 100%; }"
    )
    assert pr_url.startswith("https://github.com/Kailash-18/OmniSight/pull/")
    assert pr_url.split("/")[-1].isdigit()


def test_generate_pr_markdown_description_with_all_evidence():
    """Verify PR body markdown generation renders evidence screenshots and custom status."""
    body = generate_pr_markdown_description(
        defect_title="Banner Overflow",
        viewport="desktop_1280x800",
        target_file="app-under-test/src/styles/defects.css",
        diff="-.banner { height: 800px; }\n+.banner { height: auto; }",
        verification_status="Verified in Isolated Headless Browser",
        before_screenshot_url="http://storage.internal/evidence/before.png",
        after_screenshot_url="http://storage.internal/evidence/after.png",
        limitations="Restricted to presentation styling; functional logic untouched."
    )

    assert "Banner Overflow" in body
    assert "`desktop_1280x800`" in body
    assert "`app-under-test/src/styles/defects.css`" in body
    assert "Verified in Isolated Headless Browser" in body
    assert "![Before Fix](http://storage.internal/evidence/before.png)" in body
    assert "![After Fix](http://storage.internal/evidence/after.png)" in body
    assert "Restricted to presentation styling" in body


def test_generate_pr_markdown_fallback_when_screenshots_omitted():
    """Verify fallback text is rendered when screenshots are not provided."""
    body = generate_pr_markdown_description(
        defect_title="Misaligned Cart Icon",
        viewport="mobile_375x667",
        target_file="app-under-test/src/styles/defects.css",
        diff="-.cart-icon { margin-left: -50px; }\n+.cart-icon { margin-left: 0; }"
    )
    assert "_Evidence captured in local run artifacts._" in body
    assert "_Retest screenshot recorded in local run artifacts._" in body


def test_create_pull_request_deterministic_mock_url(monkeypatch):
    """Verify mock PR URL is deterministic for the same run ID."""
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)
    run_id = "run-fixed-seed-42"
    url1 = create_pull_request_for_fix(run_id, "app-under-test/src/App.css", "body {}")
    url2 = create_pull_request_for_fix(run_id, "app-under-test/src/App.css", "body {}")
    assert url1 == url2


def test_create_pull_request_with_custom_labels(monkeypatch, caplog):
    """Verify create_pull_request_for_fix logs and accepts custom labels."""
    monkeypatch.setattr(settings, "MOCK_GITHUB", True)
    run_id = "run-label-test-55"
    custom_labels = ["omnisight", "viewport:mobile", "high-priority"]

    with caplog.at_level("INFO"):
        pr_url = create_pull_request_for_fix(
            run_id=run_id,
            target_file="app-under-test/src/styles/defects.css",
            file_content=".checkout { display: block; }",
            labels=custom_labels
        )

    assert pr_url.startswith("https://github.com/Kailash-18/OmniSight/pull/")
    assert "viewport:mobile" in caplog.text
    assert "high-priority" in caplog.text


def test_create_pull_request_live_mock_adds_labels(monkeypatch):
    """Verify that when token is present, add_to_labels is called on the created PR object."""
    monkeypatch.setattr(settings, "MOCK_GITHUB", False)
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_valid_mock_token_123456789")
    monkeypatch.setattr(settings, "REPO_NAME", "Kailash-18/OmniSight")

    applied_labels = []

    class MockPR:
        html_url = "https://github.com/Kailash-18/OmniSight/pull/42"
        def add_to_labels(self, *labels):
            applied_labels.extend(labels)

    class MockCommit:
        sha = "abc1234def5678"

    class MockBranch:
        commit = MockCommit()

    class MockRepo:
        default_branch = "main"
        owner = type("Owner", (), {"login": "Kailash-18"})()
        def get_branch(self, name):
            return MockBranch()
        def create_git_ref(self, ref, sha):
            return None
        def get_contents(self, path, ref=None):
            return type("Content", (), {"sha": "sha999"})()
        def update_file(self, path, message, content, sha, branch):
            return None
        def create_pull(self, title, body, head, base):
            return MockPR()

    class MockGithub:
        def __init__(self, token):
            pass
        def get_repo(self, repo_name):
            return MockRepo()

    monkeypatch.setattr("app.services.github_service.Github", MockGithub)

    url = create_pull_request_for_fix(
        run_id="run-live-test",
        target_file="app-under-test/src/styles/defects.css",
        file_content="/* fix */",
        labels=["omnisight-bot", "visual-qa"]
    )
    assert url == "https://github.com/Kailash-18/OmniSight/pull/42"
    assert "omnisight-bot" in applied_labels
    assert "visual-qa" in applied_labels

