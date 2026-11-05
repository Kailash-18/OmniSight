from types import SimpleNamespace

import pytest

from app import main
from app.services.github_service import pr_number_from_url, summarize_check_runs


def runs(*pairs):
    return [SimpleNamespace(status=s, conclusion=c) for s, c in pairs]


def test_summarize_check_runs():
    assert summarize_check_runs([])["state"] == "pending"
    assert summarize_check_runs(runs(("completed", "success"), ("completed", "skipped")))["state"] == "passed"
    s = summarize_check_runs(runs(("completed", "success"), ("completed", "failure"), ("in_progress", None)))
    assert s == {"state": "failed", "total": 3, "passed": 1, "failed": 1, "running": 1}
    assert summarize_check_runs(runs(("completed", "success"), ("queued", None)))["state"] == "running"


def test_pr_number_from_url():
    assert pr_number_from_url("https://github.com/Kailash-18/OmniSight/pull/42") == 42
    assert pr_number_from_url("https://github.com/Kailash-18/OmniSight/pull/42/checks") == 42
    assert pr_number_from_url("not a url") is None


def test_checks_endpoint_states(client, monkeypatch):
    main.runs_db["r1"] = {"run_id": "r1", "pr_url": None}
    assert client.get("/runs/r1/checks").json()["state"] == "none"
    main.runs_db["r1"]["pr_url"] = "https://github.com/Kailash-18/OmniSight/pull/7"
    monkeypatch.setattr(main, "get_pull_request_checks", lambda url: {"state": "passed", "total": 4, "passed": 4, "failed": 0, "running": 0})
    body = client.get("/runs/r1/checks").json()
    assert body["state"] == "passed" and body["checks_url"] == "https://github.com/Kailash-18/OmniSight/pull/7/checks"
    assert client.get("/runs/missing/checks").status_code == 404


def test_checks_unavailable_without_token(monkeypatch):
    from app.services import github_service
    monkeypatch.setattr(github_service.settings, "GITHUB_TOKEN", "")
    assert github_service.get_pull_request_checks("https://github.com/Kailash-18/OmniSight/pull/7")["state"] == "unavailable"
