import time

import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import settings
from app.main import app

pytestmark = pytest.mark.real_auth


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "OMNISIGHT_USERNAME", "reviewer")
    monkeypatch.setattr(settings, "OMNISIGHT_PASSWORD", "s3cret-pass")


@pytest.fixture
def client():
    return TestClient(app)


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_runs_require_token(client):
    assert client.get("/runs").status_code == 401


def test_login_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "OMNISIGHT_USERNAME", "")
    monkeypatch.setattr(settings, "OMNISIGHT_PASSWORD", "")
    res = client.post("/auth/login", json={"username": "a", "password": "b"})
    assert res.status_code == 503


def test_wrong_password_401(client, configured):
    res = client.post("/auth/login", json={"username": "reviewer", "password": "nope"})
    assert res.status_code == 401


def test_login_then_me_and_runs(client, configured):
    res = client.post("/auth/login", json={"username": "reviewer", "password": "s3cret-pass"})
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "reviewer" and body["token"] and body["expires_at"]
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/auth/me", headers=headers).json() == {"username": "reviewer"}
    assert client.get("/runs", headers=headers).status_code == 200


def test_tampered_and_expired_tokens_rejected(client):
    token, _ = auth.create_token("reviewer")
    assert client.get("/runs", headers={"Authorization": f"Bearer {token[:-2]}xx"}).status_code == 401
    old, _ = auth.create_token("reviewer", now=time.time() - 9 * 3600)
    assert client.get("/runs", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    assert auth.verify_token("garbage") is None


def test_service_token_accepted_on_run_updates(client):
    h = {"Authorization": f"Bearer {auth.SERVICE_TOKEN}"}
    assert client.put("/runs/r1", json={"status": "running"}, headers=h).status_code == 200
    assert client.get("/runs/r1", headers=h).status_code == 200
    assert client.post("/action-engine/parse", json={"raw_vlm_output": "{}"}, headers=h).status_code != 401


def test_service_token_cannot_launch_or_list_runs(client):
    h = {"Authorization": f"Bearer {auth.SERVICE_TOKEN}"}
    assert client.get("/runs", headers=h).status_code == 401
    assert client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True}, headers=h).status_code == 401
    assert client.get("/runs/active", headers=h).status_code == 401
    assert client.get("/auth/me", headers=h).status_code == 401


def test_artifacts_require_token(client, tmp_path, monkeypatch):
    # Evidence files (screenshots, forensic zips, runner logs) must be behind login like the API.
    res = client.get("/artifacts/runs/any/forensic_bundle_any.zip")
    assert res.status_code == 401


def test_artifacts_served_with_token_and_no_traversal(client, tmp_path, monkeypatch):
    from app import main
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "shot.png").write_bytes(b"png")
    (tmp_path.parent / "secret.txt").write_text("nope")
    monkeypatch.setattr(main, "artifacts_path", tmp_path.resolve())
    token, _ = auth.create_token("reviewer")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/artifacts/runs/shot.png", headers=headers).content == b"png"
    assert client.get("/artifacts/..%2Fsecret.txt", headers=headers).status_code == 404
    assert client.get("/artifacts/runs/missing.png", headers=headers).status_code == 404


def test_admin_credentials_accepted(client):
    res = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    assert res.json()["username"] == "admin"
    assert "token" in res.json()


def test_admin_cannot_bypass_when_custom_account_configured(client, configured):
    res = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 401

