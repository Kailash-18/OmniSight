"""
Tests for Webhook Security:
1. Shared secret protection for /webhook/build (WEBHOOK_SECRET).
2. Exemption from user login and X-Hub-Signature-256 HMAC verification for /webhook/github/pull-request.
"""

import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app, runs_db


@pytest.fixture
def client():
    return TestClient(app)


def test_build_webhook_protected_by_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", "super-secret-ci-key")
    payload = {
        "target_url": "http://localhost:5173",
        "branch": "main",
        "scenario": "checkout_flow"
    }

    # 1. No secret header -> 401
    res = client.post("/webhook/build", json=payload)
    assert res.status_code == 401
    assert "Invalid or missing webhook secret" in res.json()["detail"]

    # 2. Wrong secret header -> 401
    res = client.post("/webhook/build", json=payload, headers={"X-Webhook-Secret": "wrong-secret"})
    assert res.status_code == 401

    # 3. Correct X-Webhook-Secret header -> 202
    res = client.post("/webhook/build", json=payload, headers={"X-Webhook-Secret": "super-secret-ci-key"})
    assert res.status_code == 202
    assert res.json()["status"] == "queued"

    # 4. Correct Bearer token -> 202
    res = client.post("/webhook/build", json=payload, headers={"Authorization": "Bearer super-secret-ci-key"})
    assert res.status_code == 202


@pytest.mark.real_auth
def test_github_webhook_exempt_from_login_and_validates_signature(client, monkeypatch):
    secret = "my-github-webhook-secret"
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", secret)

    # Register dummy run
    run_id = "test-gh-webhook-run"
    runs_db[run_id] = {
        "run_id": run_id,
        "status": "pr_opened",
        "steps": [],
        "pr_url": None,
    }

    payload_dict = {
        "action": "closed",
        "pull_request": {
            "number": 101,
            "html_url": "https://github.com/Kailash-18/OmniSight/pull/101",
            "merged": True,
            "head": {"ref": f"omnisight-fix-{run_id}"}
        }
    }
    raw_payload = json.dumps(payload_dict).encode("utf-8")

    # 1. Without signature header -> 401 (not login error, but signature error)
    res = client.post(
        "/webhook/github/pull-request",
        content=raw_payload,
        headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 401
    assert "Missing or invalid X-Hub-Signature-256" in res.json()["detail"]

    # 2. With wrong signature -> 401
    res = client.post(
        "/webhook/github/pull-request",
        content=raw_payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=invalidhex"}
    )
    assert res.status_code == 401
    assert "Invalid GitHub webhook signature" in res.json()["detail"]

    # 3. With valid signature -> 200 OK
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).hexdigest()
    res = client.post(
        "/webhook/github/pull-request",
        content=raw_payload,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "processed"
    assert runs_db[run_id]["status"] == "fixed"
    assert runs_db[run_id]["merged"] is True
