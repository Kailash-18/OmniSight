"""
Starts the OmniSight automation CLI as a child process for a dashboard-triggered run.
One run at a time (the retest edits defects.css in place), with a hard time limit.
"""

import logging
import os
import signal
import subprocess
import sys
import threading
from collections import deque
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
logger = logging.getLogger("omnisight.backend.run_launcher")


class RunAlreadyActive(Exception):
    pass


def _log_tail(path: Path, lines: int = 12) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            tail = "".join(deque(f, maxlen=lines)).strip()
    except OSError:
        return ""
    if not tail:
        return ""

    diagnostic = ""
    if "ConnectionRefusedError" in tail or "URLError" in tail or "not reachable" in tail:
        diagnostic = "\n[Diagnostic: Target web application is unreachable. Check port and server status.]"
    elif "TimeoutError" in tail or "timed out" in tail:
        diagnostic = "\n[Diagnostic: Browser interaction timed out. Inspect page response times.]"

    return f"\n--- last lines of runner.log ---{diagnostic}\n{tail}"


class RunLauncher:
    def __init__(self, popen=subprocess.Popen, timeout_seconds: float = 300, repo_root: Path = REPO_ROOT):
        self.popen = popen
        self.timeout_seconds = timeout_seconds
        self.repo_root = Path(repo_root)
        self.active_run_id: Optional[str] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def build_command(
        self, run_id: str, target_url: str, backend_url: str, retest: bool, auto_pr: bool = False
    ) -> list[str]:
        cmd = [sys.executable, "-m", "automation.cli", "--run-id", run_id, "--target", target_url,
               "--sync-backend", "--backend-url", backend_url]
        if not retest:
            cmd.append("--no-retest")
        if auto_pr:
            cmd.append("--auto-pr")
        return cmd

    def start(self, run_id: str, target_url: str, backend_url: str, service_token: str, retest: bool,
              on_exit: Callable[[str, Optional[str], str], None], auto_pr: bool = False) -> None:
        with self._lock:
            if self.active_run_id:
                raise RunAlreadyActive(self.active_run_id)
            log_path = self.repo_root / "artifacts" / "runs" / run_id / "runner.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log = open(log_path, "w", encoding="utf-8")
            env = {**os.environ, "OMNISIGHT_SERVICE_TOKEN": service_token, "PYTHONUNBUFFERED": "1"}
            try:
                proc = self.popen(self.build_command(run_id, target_url, backend_url, retest, auto_pr=auto_pr),
                                  cwd=str(self.repo_root), env=env, stdout=log, stderr=subprocess.STDOUT,
                                  start_new_session=True)  # own process group, so a timeout can kill Chromium too
            except Exception:
                log.close()
                raise
            self.active_run_id = run_id
        self._thread = threading.Thread(target=self._watch, args=(proc, run_id, log, log_path, on_exit), daemon=True)
        self._thread.start()

    def _watch(self, proc, run_id, log, log_path, on_exit) -> None:
        reason = None
        try:
            try:
                code = proc.wait(timeout=self.timeout_seconds)
                if code != 0:
                    reason = f"Test process exited with code {code}."
            except subprocess.TimeoutExpired:
                self._kill_tree(proc)
                proc.wait()
                reason = f"Test timed out after {self.timeout_seconds:g} seconds."
            log.close()
            try:
                on_exit(run_id, reason, _log_tail(log_path))
            except Exception:
                logger.exception("Finishing run %s failed", run_id)
        finally:
            if not log.closed:
                log.close()
            with self._lock:
                self.active_run_id = None

    @staticmethod
    def _kill_tree(proc) -> None:
        """Kill the CLI and the Playwright/Chromium processes it started (POSIX & Windows taskkill)."""
        try:
            sig = getattr(signal, "SIGKILL", getattr(signal, "SIGTERM", 9))
            os.killpg(os.getpgid(proc.pid), sig)
        except (AttributeError, OSError):
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        timeout=5
                    )
                except Exception:
                    pass
            try:
                proc.kill()
            except Exception:
                pass

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout)
