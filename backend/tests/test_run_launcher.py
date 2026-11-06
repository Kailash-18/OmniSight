import subprocess
import threading

import pytest

from app import main
from app.services.run_launcher import RunAlreadyActive, RunLauncher


@pytest.fixture(autouse=True)
def _never_kill_real_processes(monkeypatch):
    """FakeProc pids are made up; make sure no test can signal a real process group."""
    import app.services.run_launcher as rl

    def refuse(*a):
        raise OSError("test: real killpg disabled")

    monkeypatch.setattr(rl.os, "killpg", refuse, raising=False)
    monkeypatch.setattr(rl.os, "getpgid", lambda pid: pid, raising=False)


class FakeProc:
    pid = 4242

    def __init__(self, code=0, hang=False, gate=None):
        self.returncode, self.hang, self.gate, self.killed = code, hang, gate, False

    def wait(self, timeout=None):
        if self.gate is not None:
            self.gate.wait(5)
        if self.hang and not self.killed:
            raise subprocess.TimeoutExpired("automation.cli", timeout)
        return self.returncode

    def kill(self):
        self.killed, self.returncode = True, -9


def make(tmp_path, proc, timeout=300):
    calls = []

    def popen(cmd, **kw):
        calls.append((cmd, kw))
        return proc

    return RunLauncher(popen=popen, timeout_seconds=timeout, repo_root=tmp_path), calls


def test_start_builds_cli_command_and_clears_slot(tmp_path):
    launcher, calls = make(tmp_path, FakeProc(0))
    done = []
    launcher.start("run-1", "http://localhost:5173", "http://127.0.0.1:8000", "svc", True, lambda r, reason, tail="": done.append((r, reason)))
    launcher.join(2)
    cmd, kw = calls[0]
    assert cmd[1:4] == ["-m", "automation.cli", "--run-id"] and "run-1" in cmd
    assert "--sync-backend" in cmd and "--no-retest" not in cmd
    assert kw["env"]["OMNISIGHT_SERVICE_TOKEN"] == "svc" and kw["cwd"] == str(tmp_path)
    assert done == [("run-1", None)] and launcher.active_run_id is None
    assert (tmp_path / "artifacts/runs/run-1/runner.log").exists()


def test_retest_false_adds_flag(tmp_path):
    launcher, calls = make(tmp_path, FakeProc(0))
    launcher.start("r", "http://localhost:5173", "http://x", "svc", False, lambda *a: None)
    launcher.join(2)
    assert "--no-retest" in calls[0][0]


def test_second_start_while_active_raises(tmp_path):
    gate = threading.Event()
    launcher, _ = make(tmp_path, FakeProc(0, gate=gate))
    launcher.start("a", "http://localhost:5173", "http://x", "svc", True, lambda *a: None)
    with pytest.raises(RunAlreadyActive):
        launcher.start("b", "http://localhost:5173", "http://x", "svc", True, lambda *a: None)
    gate.set()
    launcher.join(2)
    assert launcher.active_run_id is None


def test_timeout_kills_and_reports(tmp_path):
    proc = FakeProc(0, hang=True)
    launcher, _ = make(tmp_path, proc, timeout=0.01)
    done = []
    launcher.start("t", "http://localhost:5173", "http://x", "svc", True, lambda r, reason, tail="": done.append(reason))
    launcher.join(2)
    assert proc.killed and "timed out" in done[0]


# --- API -------------------------------------------------------------------

@pytest.fixture
def api_launcher(tmp_path, monkeypatch):
    gate = threading.Event()
    holder = {"proc": FakeProc(0, gate=gate)}
    calls = []

    def popen(cmd, **kw):
        calls.append(cmd)
        return holder["proc"]

    launcher = RunLauncher(popen=popen, timeout_seconds=300, repo_root=tmp_path)
    monkeypatch.setattr(main, "run_launcher", launcher)
    yield launcher, calls, gate, holder
    gate.set()
    launcher.join(2)


def test_launch_starts_run_and_reports_active(client, api_launcher):
    launcher, calls, gate, _ = api_launcher
    res = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True})
    assert res.status_code == 201
    run_id = res.json()["run_id"]
    assert calls and run_id in calls[0]
    assert client.get("/runs/active").json() == {"run_id": run_id}
    again = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True})
    assert again.status_code == 409 and run_id in again.json()["detail"]
    gate.set()
    launcher.join(2)
    assert client.get("/runs/active").json() == {"run_id": None}


def test_launch_rejects_disallowed_host_without_spawning(client, api_launcher):
    _, calls, _, _ = api_launcher
    res = client.post("/runs", json={"target_url": "  http://evil.example.com ", "launch": True})
    assert res.status_code == 400
    assert calls == []


def test_launch_nonzero_exit_marks_failed_and_frees_slot(client, api_launcher, tmp_path):
    launcher, _, gate, holder = api_launcher
    holder["proc"] = FakeProc(2)
    gate.set()
    res = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True})
    run_id = res.json()["run_id"]
    launcher.join(2)
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "failed" and "exited with code 2" in run["error"]
    assert client.get("/runs/active").json() == {"run_id": None}


def test_register_only_does_not_spawn(client, api_launcher):
    _, calls, _, _ = api_launcher
    res = client.post("/runs", json={"target_url": "http://localhost:5173"})
    assert res.status_code == 201 and calls == []


@pytest.mark.parametrize("url", [
    "http://evil.com\\@localhost:5173/",      # urlparse sees localhost, browsers see evil.com
    "http://user@localhost:5173/",             # userinfo
    "http://local host:5173/",                 # whitespace inside
])
def test_launch_rejects_ambiguous_urls(client, api_launcher, url):
    _, calls, _, _ = api_launcher
    res = client.post("/runs", json={"target_url": url, "launch": True})
    assert res.status_code == 400
    assert calls == []


def test_launch_passes_normalized_url(client, api_launcher):
    launcher, calls, gate, _ = api_launcher
    res = client.post("/runs", json={"target_url": "  localhost:5173/shop?x=1 ", "launch": True})
    assert res.status_code == 201
    cmd = calls[0]
    assert cmd[cmd.index("--target") + 1] == "http://localhost:5173/shop?x=1"


def test_clean_exit_without_final_status_marks_failed(client, api_launcher):
    launcher, _, gate, holder = api_launcher
    holder["proc"] = FakeProc(0)
    gate.set()
    run_id = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True}).json()["run_id"]
    launcher.join(2)
    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "failed" and "without reporting a result" in run["error"]


def test_crash_after_cli_reported_failed_appends_log_tail(client, api_launcher, tmp_path):
    launcher, _, gate, holder = api_launcher

    class ReportingProc(FakeProc):
        def wait(self, timeout=None):
            from app.main import runs_db
            rid = next(iter(runs_db))
            runs_db[rid].update(status="failed", error="Store not reachable")
            (tmp_path / "artifacts/runs" / rid / "runner.log").write_text("Traceback...\nRuntimeError: store down\n")
            return 1

    holder["proc"] = ReportingProc()
    run_id = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True}).json()["run_id"]
    launcher.join(2)
    err = client.get(f"/runs/{run_id}").json()["error"]
    assert err.startswith("Store not reachable") and "RuntimeError: store down" in err


def test_child_runs_in_its_own_process_group(tmp_path):
    launcher, calls = make(tmp_path, FakeProc(0))
    launcher.start("g", "http://localhost:5173", "http://x", "svc", True, lambda *a: None)
    launcher.join(2)
    assert calls[0][1]["start_new_session"] is True


def test_timeout_kills_whole_process_group(tmp_path, monkeypatch):
    import app.services.run_launcher as rl
    killed = []
    monkeypatch.setattr(rl.os, "killpg", lambda pgid, sig: killed.append((pgid, sig)), raising=False)
    monkeypatch.setattr(rl.os, "getpgid", lambda pid: pid, raising=False)
    proc = FakeProc(0, hang=True)
    proc.kill = lambda: None  # only the group kill should be relied on
    proc.wait_calls = 0
    real_wait = proc.wait

    def wait(timeout=None):
        if killed:
            return -9
        return real_wait(timeout)

    proc.wait = wait
    launcher, _ = make(tmp_path, proc, timeout=0.01)
    launcher.start("k", "http://localhost:5173", "http://x", "svc", True, lambda *a: None)
    launcher.join(2)
    assert killed and killed[0][0] == 4242


def test_any_startup_error_marks_run_failed(client, monkeypatch, tmp_path):
    def broken_popen(cmd, **kw):
        raise RuntimeError("bad interpreter")

    monkeypatch.setattr(main, "run_launcher", RunLauncher(popen=broken_popen, repo_root=tmp_path))
    res = client.post("/runs", json={"target_url": "http://localhost:5173", "launch": True})
    assert res.status_code == 500 and "bad interpreter" in res.json()["detail"]
    run = client.get("/runs").json()[0]
    assert run["status"] == "failed"
    assert main.run_launcher.active_run_id is None
