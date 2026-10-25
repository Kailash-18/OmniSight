"""
Backend Gateway Integration Client.
Enables Automation & Orchestrator to communicate with the FastAPI CI/CD Gateway,
Action Engine, and Zero-Trust Patch Validator.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from automation.config import config

logger = logging.getLogger("omnisight.backend_client")


class BackendClient:
    """
    HTTP Client for OmniSight FastAPI Backend Gateway.
    Coordinates run scheduling, lifecycle state transitions,
    VLM parsing with Action Engine, and patch validation submission.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 3.0,
        test_client: Any | None = None,
    ):
        self.base_url = (base_url or config.backend_url).rstrip("/")
        self.timeout = timeout
        self.test_client = test_client
        self._is_available: bool | None = None

    @property
    def is_available(self) -> bool | None:
        return self._is_available

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        force_probe: bool = False,
    ) -> dict[str, Any] | None:
        """
        Executes an HTTP request to the backend service.
        Supports both live network requests and in-memory FastAPI TestClient.
        Fails fast if the gateway has already been detected as offline.
        """
        if self.test_client is None and self._is_available is False and not force_probe:
            return None

        url = f"{self.base_url}{endpoint}"

        if self.test_client is not None:
            try:
                fn = getattr(self.test_client, method.lower())
                kwargs: dict[str, Any] = {}
                if json_data is not None:
                    kwargs["json"] = json_data
                if params is not None:
                    kwargs["params"] = params

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
            except Exception as e:  # noqa: BLE001
                logger.warning("TestClient error calling %s: %s", endpoint, e)
                return None

        # Live HTTP via urllib
        query_str = ""
        if params:
            query_parts = [f"{k}={v}" for k, v in params.items() if v is not None]
            if query_parts:
                query_str = "?" + "&".join(query_parts)

        full_url = f"{url}{query_str}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "OmniSight-AutomationClient/1.0",
        }
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
        """Verifies if the backend gateway is healthy and accessible with a quick probe."""
        orig_timeout = self.timeout
        try:
            self.timeout = min(orig_timeout, 1.5)
            res = self._request("GET", "/health", force_probe=True)
            healthy = res is not None and res.get("status") == "healthy"
            self._is_available = healthy
            return healthy
        finally:
            self.timeout = orig_timeout

    def register_run(
        self,
        target_url: str,
        scenario: str = "checkout_flow",
        viewports: list[str] | None = None,
    ) -> str | None:
        """
        Registers a new audit run with the backend gateway via POST /runs.
        Returns the assigned run_id.
        """
        payload = {
            "target_url": target_url,
            "scenario": scenario,
            "viewports": viewports or ["desktop_1440x900", "mobile_375x667"],
        }
        res = self._request("POST", "/runs", json_data=payload)
        return res.get("run_id") if res else None

    def update_run_state(
        self,
        run_id: str,
        status: str | None = None,
        steps: list[str] | None = None,
        evidence_paths: dict[str, Any] | None = None,
        findings: list[dict[str, Any]] | None = None,
        patch: dict[str, Any] | None = None,
        retry_count: int | None = None,
        error: str | None = None,
    ) -> bool:
        """
        Updates an existing run record on the backend with progress or state transitions.
        """
        payload: dict[str, Any] = {}
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
        if error is not None:
            payload["error"] = error

        res = self._request("PUT", f"/runs/{run_id}", json_data=payload)
        return res is not None

    def parse_with_action_engine(
        self,
        raw_vlm_output: str,
        run_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Delegates VLM response parsing and patch validation to the backend Action Engine.
        """
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
    ) -> dict[str, Any] | None:
        """
        Submits an approved patch for backend zero-trust validation and recording.
        """
        payload = {
            "target_file": target_file,
            "diff": diff,
            "file_content": file_content,
            "pr_title": pr_title,
            "pr_body": pr_body,
        }
        return self._request("POST", f"/runs/{run_id}/submit-patch", json_data=payload)

    def get_run_details(self, run_id: str) -> dict[str, Any] | None:
        """Retrieves comprehensive details for a specific run."""
        return self._request("GET", f"/runs/{run_id}")

    def get_milestones(self) -> dict[str, Any] | None:
        """Queries the team milestone tracking endpoint."""
        return self._request("GET", "/api/milestones")
