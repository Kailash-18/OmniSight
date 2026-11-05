import io
import json
import urllib.request

from automation import orchestrator
from automation.orchestrator import BackendClient


class Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_cli_passes_run_id(monkeypatch, capsys):
    seen = {}

    def fake_loop(self, **kw):
        seen.update(kw)
        return {"run_id": kw.get("run_id"), "status": "audited", "findings": []}

    monkeypatch.setattr(orchestrator.Orchestrator, "run_full_remediation_loop", fake_loop)
    orchestrator.main(["--run-id", "run-abc", "--json-output", "--no-interaction-check"])
    assert seen["run_id"] == "run-abc"
    assert json.loads(capsys.readouterr().out)["run_id"] == "run-abc"


def test_backend_client_sends_service_token(monkeypatch):
    monkeypatch.setenv("OMNISIGHT_SERVICE_TOKEN", "tok-123")
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["auth"] = req.get_header("Authorization")
        return Resp(b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    BackendClient(base_url="http://127.0.0.1:8000").update_run_state("r1", status="running")
    assert captured["auth"] == "Bearer tok-123"


def test_backend_client_no_header_without_env(monkeypatch):
    monkeypatch.delenv("OMNISIGHT_SERVICE_TOKEN", raising=False)
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["auth"] = req.get_header("Authorization")
        return Resp(b"{}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    BackendClient(base_url="http://127.0.0.1:8000").update_run_state("r1", status="running")
    assert captured["auth"] is None
