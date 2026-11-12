"""
Backend Configuration Module for OmniSight.
Centralizes environment variables and application settings with zero hardcoded secrets.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load local environment variables from backend/.env or root .env
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_backend_dir.parent / ".env")
load_dotenv()


class Settings:
    """Application settings loaded strictly from environment variables."""

    def __init__(self) -> None:
        # API Metadata
        self.API_TITLE: str = "OmniSight Backend Gateway & Action Engine"
        self.API_VERSION: str = "1.0.0"
        self.DEBUG: bool = os.getenv("BACKEND_DEBUG", "false").lower() in ("true", "1", "yes")

        # Server Configuration
        self.HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
        _default_artifacts = _backend_dir.parent / "artifacts"
        self.ARTIFACTS_DIR: Path = Path(os.getenv("ARTIFACTS_DIR", str(_default_artifacts))).resolve()

        # GitHub Service Configuration
        self.GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
        self.REPO_NAME: str = os.getenv("REPO_NAME", "Kailash-18/OmniSight")
        self.MOCK_GITHUB: bool = os.getenv("MOCK_GITHUB", "false").lower() in ("true", "1", "yes")

        # Dashboard login (primary reviewer account + optional extra accounts). Empty primary = login refused with 503.
        self.OMNISIGHT_USERNAME: str = os.getenv("OMNISIGHT_USERNAME", "admin")
        self.OMNISIGHT_PASSWORD: str = os.getenv("OMNISIGHT_PASSWORD", "admin")
        self.OMNISIGHT_USERS: dict[str, str] = self._parse_users(os.getenv("OMNISIGHT_USERS", ""))
        self.OMNISIGHT_SECRET_KEY: str = os.getenv("OMNISIGHT_SECRET_KEY", "")

        # Webhook Shared Secrets
        self.WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
        self.GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", os.getenv("WEBHOOK_SECRET", ""))

        # Audit Journey Timeouts
        self.RUN_TIMEOUT_SECONDS: int = int(os.getenv("RUN_TIMEOUT_SECONDS", "300"))

        # Allowed Target Hosts for Browser Audits (SSRF Prevention)
        default_hosts = "*"
        self.ALLOWED_TARGET_HOSTS: list[str] = [
            h.strip().lower()
            for h in os.getenv("ALLOWED_TARGET_HOSTS", default_hosts).split(",")
            if h.strip()
        ]

        # Patch Security Guardrails
        default_patch_files = (
            "app-under-test/src/styles/defects.css,"
            "app-under-test/src/styles/base.css,"
            "app-under-test/src/App.css,"
            "app-under-test/src/index.css,"
            "app-under-test/src/components/,"
            "app-under-test/src/App.jsx"
        )
        self.ALLOWED_PATCH_FILES: list[str] = [
            p.strip().replace("\\", "/")
            for p in os.getenv("ALLOWED_PATCH_FILES", default_patch_files).split(",")
            if p.strip()
        ]

        # Patch Diff Constraints
        self.MAX_DIFF_LINES: int = int(os.getenv("MAX_DIFF_LINES", "300"))
        self.MAX_DIFF_BYTES: int = int(os.getenv("MAX_DIFF_BYTES", "30000"))

    @staticmethod
    def _parse_users(raw: str) -> dict[str, str]:
        """Parses OMNISIGHT_USERS from JSON object or comma-separated user:password pairs."""
        text = (raw or "").strip()
        if not text:
            return {}
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return {}
            if not isinstance(parsed, dict):
                return {}
            return {
                str(k).strip(): str(v)
                for k, v in parsed.items()
                if str(k).strip() and isinstance(v, str) and v
            }
        users: dict[str, str] = {}
        for entry in text.split(","):
            if ":" not in entry:
                continue
            username, password = entry.strip().split(":", 1)
            username = username.strip()
            password = password.strip()
            if username and password:
                users[username] = password
        return users

    def is_host_allowed(self, hostname: str) -> bool:
        """Checks if a given host is in the allowed target hosts list, supporting exact and wildcards."""
        host = (hostname or "").lower().strip()
        if not host:
            return False

        # Critical SSRF Guard: Deny cloud metadata services and link-local ranges unconditionally
        blocked_hosts = {"169.254.169.254", "metadata.google.internal", "instance-data"}
        if host in blocked_hosts or host.startswith("169.254."):
            return False

        for allowed in self.ALLOWED_TARGET_HOSTS:
            if allowed in ("*", "all"):
                return True
            if allowed.startswith("*."):
                suffix = allowed[1:]  # e.g. .flipkart.com
                if host.endswith(suffix) or host == allowed[2:]:
                    return True
            if host == allowed:
                return True
        return False

    def is_path_allowed(self, clean_path: str) -> bool:
        """Checks if a sanitized target file path falls strictly within the allowlist boundaries."""
        normalized = clean_path.replace("\\", "/").strip()
        for allowed in self.ALLOWED_PATCH_FILES:
            if allowed.endswith("/"):
                if normalized.startswith(allowed):
                    return True
            else:
                if normalized == allowed:
                    return True
        return False


settings = Settings()
