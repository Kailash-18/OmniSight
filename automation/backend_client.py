"""
OmniSight Backend Gateway Client (Team Lead Automation Deliverable).
High-performance HTTP client for orchestrator state synchronization,
Action Engine integration, automated PR dispatch, and forensic verification.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("omnisight.automation.backend_client")


class BackendClient:
    """
    Robust HTTP Client for OmniSight FastAPI Backend Gateway.
    Handles service token and admin session authentication, run lifecycle updates,
    VLM parsing with the Action Engine, patch validation, and forensics.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 4.0,
        test_client: Optional[Any] = None,
        token: Optional[str] = None,
    ):
        raw_url = base_url or os.environ.get("OMNISIGHT_BACKEND_URL", "http://127.0.0.1:8000")
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self.test_client = test_client
        self._token = token
        self._is_available: Optional[bool] = None

    @property
    def is_available(self) -> Optional[bool]:
        return self._is_available

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional[str]:
        """
        Authenticate against backend gateway to obtain an authorized session bearer token.
        Defaults to admin/admin credentials or backend/.env configuration.
        """
        user = username or os.environ.get("OMNISIGHT_USERNAME", "admin")
        pwd = password or os.environ.get("OMNISIGHT_PASSWORD", "admin")

        res = self._request(
            "POST",
            "/auth/login",
            json_data={"username": user, "password": pwd},
            skip_auth=True,
            force_probe=True,
        )
        if res and "token" in res:
            self._token = res["token"]
            return self._token
        return None

    def _get_auth_header(self) -> Optional[str]:
        # 1. Runner service token set by launcher
        svc_token = os.environ.get("OMNISIGHT_SERVICE_TOKEN")
        if svc_token:
            return f"Bearer {svc_token}"

        # 2. Explicit or cached session token
        if self._token:
            return f"Bearer {self._token}"

        # 3. Opportunistic auto-login for standalone CLI runs
        auto_token = self.login()
        if auto_token:
            return f"Bearer {auto_token}"

        return None

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        force_probe: bool = False,
        skip_auth: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if self.test_client is None and self._is_available is False and not force_probe:
            return None

        # Execute via FastAPI TestClient when injected (for test suite execution)
        if self.test_client is not None:
            try:
                fn = getattr(self.test_client, method.lower())
                kwargs: Dict[str, Any] = {}
                if json_data is not None:
                    kwargs["json"] = json_data
                if params is not None:
                    kwargs["params"] = params

                if not skip_auth:
                    auth_header = self._get_auth_header()
                    if auth_header:
                        kwargs["headers"] = {"Authorization": auth_header}

                response = fn(endpoint, **kwargs)
                if response.status_code in (200, 201, 202):
                    self._is_available = True
                    return response.json()
                logger.warning(
                    "Backend error %d from %s: %s",
                    response.status_code,
                    endpoint,
                    response.text,
                )
                return None
            except Exception as e:
                logger.warning("TestClient error calling %s: %s", endpoint, e)
                return None

        # Standard live HTTP execution via urllib
        query_str = ""
        if params:
            query_parts = [f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if v is not None]
            if query_parts:
                query_str = "?" + "&".join(query_parts)

        full_url = f"{self.base_url}{endpoint}{query_str}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "OmniSight-AutomationClient/1.0",
        }

        if not skip_auth:
            auth_header = self._get_auth_header()
            if auth_header:
                headers["Authorization"] = auth_header

        body_bytes = None
        if json_data is not None:
            headers["Content-Type"] = "application/json"
            body_bytes = json.dumps(json_data).encode("utf-8")

        req = urllib.request.Request(
            full_url, data=body_bytes, headers=headers, method=method.upper()
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status in (200, 201, 202):
                    self._is_available = True
                    content = resp.read().decode("utf-8")
                    return json.loads(content) if content else {}
                return None
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as e:
            self._is_available = False
            logger.debug("Backend request failed for %s %s: %s", method, full_url, e)
            return None

    def check_health(self) -> bool:
        """Ping backend health check endpoint to verify readiness."""
        orig_timeout = self.timeout
        try:
            self.timeout = min(orig_timeout, 2.0)
            res = self._request("GET", "/health", force_probe=True, skip_auth=True)
            healthy = res is not None and res.get("status") == "healthy"
            self._is_available = healthy
            return healthy
        finally:
            self.timeout = orig_timeout

    def get_target_hosts(self) -> Optional[Dict[str, Any]]:
        """Retrieve allowed audit hosts and wildcard configuration."""
        return self._request("GET", "/config/target-hosts", skip_auth=True)

    def register_run(
        self,
        target_url: str,
        scenario: str = "checkout_flow",
        viewports: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Trigger or register a new browser audit run."""
        payload = {
            "target_url": target_url,
            "scenario": scenario,
            "viewports": viewports or ["desktop_1440x900", "mobile_375x667"],
            "launch": False,
        }
        res = self._request("POST", "/runs", json_data=payload)
        return res.get("run_id") if res else None

    def update_run_state(
        self,
        run_id: str,
        status: Optional[str] = None,
        steps: Optional[List[str]] = None,
        evidence_paths: Optional[Dict[str, Any]] = None,
        findings: Optional[List[Dict[str, Any]]] = None,
        patch: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        retest_outcome: Optional[Dict[str, Any]] = None,
        pr_url: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update lifecycle state and forensic metadata for an active run."""
        payload: Dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if steps is not None:
            payload["steps"] = steps
        if evidence_paths is not None:
            payload["evidence_paths"] = evidence_paths
        if findings is not None:
            payload["findings"] = findings
        if patch is not None:
            payload["patch"] = patch
        if retry_count is not None:
            payload["retry_count"] = retry_count
        if retest_outcome is not None:
            payload["retest_outcome"] = retest_outcome
        if pr_url is not None:
            payload["pr_url"] = pr_url
        if error is not None:
            payload["error"] = error

        res = self._request("PUT", f"/runs/{run_id}", json_data=payload)
        return res is not None

    def parse_with_action_engine(
        self,
        raw_vlm_output: str,
        run_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Dispatch raw VLM output to backend Action Engine for structured parsing."""
        payload = {"raw_vlm_output": raw_vlm_output}
        if run_id:
            payload["run_id"] = run_id
        return self._request("POST", "/action-engine/parse", json_data=payload)

    def submit_patch(
        self,
        run_id: str,
        target_file: str,
        diff: str,
        file_content: str,
        pr_title: str = "OmniSight Automated Visual Defect Fix",
        pr_body: str = "Automated visual QA patch verified by sandbox re-test.",
        auto_create_pr: bool = False,
        labels: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Submit proposed CSS fix to backend validator for security allowlist verification."""
        payload: Dict[str, Any] = {
            "target_file": target_file,
            "diff": diff,
            "file_content": file_content,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "auto_create_pr": auto_create_pr,
        }
        if labels is not None:
            payload["labels"] = labels
        return self._request("POST", f"/runs/{run_id}/submit-patch", json_data=payload)

    def get_run_details(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full forensic run report including risk scores and evidence."""
        return self._request("GET", f"/runs/{run_id}")

    def list_runs(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recorded test runs from backend store."""
        params = {"status_filter": status_filter} if status_filter else None
        res = self._request("GET", "/runs", params=params)
        return res if isinstance(res, list) else []

    def get_milestones(self) -> Optional[Dict[str, Any]]:
        """Retrieve team milestone delivery metrics."""
        return self._request("GET", "/api/milestones")

    def create_pull_request(
        self,
        run_id: str,
        pr_title: Optional[str] = None,
        pr_body: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Trigger automated GitHub Pull Request creation for verified runs."""
        payload: Dict[str, Any] = {}
        if pr_title:
            payload["pr_title"] = pr_title
        if pr_body:
            payload["pr_body"] = pr_body
        if labels:
            payload["labels"] = labels
        return self._request("POST", f"/runs/{run_id}/create-pr", json_data=payload)

    def update_pr_verification(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Publish re-test verification comments and visual diff evidence to GitHub PR."""
        return self._request("POST", f"/runs/{run_id}/update-pr-verification")

    def get_forensics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Fetch forensic bundle metadata and SHA-256 manifests."""
        return self._request("GET", f"/runs/{run_id}/forensics")

    def generate_forensics(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Compile an immutable forensic ZIP archive for a completed run."""
        return self._request("POST", f"/runs/{run_id}/forensics")

    def verify_forensic_bundle(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Validate cryptographic SHA-256 hashes of all artifacts inside a forensic bundle."""
        return self._request("GET", f"/runs/{run_id}/verify-bundle")

    def get_telemetry_summary(self) -> Optional[Dict[str, Any]]:
        """Retrieve aggregated QA metrics and remediation success rates."""
        return self._request("GET", "/runs/metrics/summary")


def main() -> int:
    """CLI utility for probing backend connectivity and inspecting runs."""
    parser = argparse.ArgumentParser(description="OmniSight Backend Gateway Diagnostic Client")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--health", action="store_true", help="Check backend health")
    parser.add_argument("--login", action="store_true", help="Authenticate with admin credentials")
    parser.add_argument("--target-hosts", action="store_true", help="List allowed audit target hosts")
    parser.add_argument("--list-runs", action="store_true", help="List recorded audit runs")
    parser.add_argument("--telemetry", action="store_true", help="Show quality telemetry summary")
    parser.add_argument("--verify-bundle", type=str, metavar="RUN_ID", help="Verify forensic bundle integrity")

    args = parser.parse_args()
    client = BackendClient(base_url=args.url)

    if args.health or len(sys.argv) == 1:
        healthy = client.check_health()
        print(f"Backend Health ({args.url}): {'HEALTHY' if healthy else 'OFFLINE'}")
        if not healthy:
            return 1

    if args.login:
        token = client.login()
        if token:
            print("Authentication: SUCCESS (admin)")
            print(f"Token: {token[:24]}...")
        else:
            print("Authentication: FAILED")
            return 1

    if args.target_hosts:
        hosts = client.get_target_hosts()
        print("Target Hosts:", json.dumps(hosts, indent=2))

    if args.list_runs:
        runs = client.list_runs()
        print(f"Recorded Runs ({len(runs)}):")
        for r in runs[:10]:
            print(f"  - [{r.get('status')}] {r.get('run_id')} -> {r.get('target')}")

    if args.telemetry:
        tel = client.get_telemetry_summary()
        print("Quality Telemetry:", json.dumps(tel, indent=2))

    if args.verify_bundle:
        res = client.verify_forensic_bundle(args.verify_bundle)
        print(f"Bundle Verification ({args.verify_bundle}):", json.dumps(res, indent=2))

    return 0


__all__ = ["BackendClient", "main"]

if __name__ == "__main__":
    sys.exit(main())
