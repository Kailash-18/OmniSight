"""
Backend Configuration Module for OmniSight.
Centralizes environment variables and application settings with zero hardcoded secrets.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load local environment variables from backend/.env or root .env
load_dotenv()


class Settings:
    """Application settings loaded strictly from environment variables."""

    # API Metadata
    API_TITLE: str = "OmniSight Backend Gateway & Action Engine"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("BACKEND_DEBUG", "false").lower() in ("true", "1", "yes")

    # Server Configuration
    HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # GitHub Service Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    REPO_NAME: str = os.getenv("REPO_NAME", "Kailash-18/OmniSight")
    MOCK_GITHUB: bool = os.getenv("MOCK_GITHUB", "false").lower() in ("true", "1", "yes")

    # Allowed Target Hosts for Browser Audits (SSRF Prevention)
    _default_hosts = "localhost,127.0.0.1,0.0.0.0,staging.internal"
    ALLOWED_TARGET_HOSTS: List[str] = [
        h.strip()
        for h in os.getenv("ALLOWED_TARGET_HOSTS", _default_hosts).split(",")
        if h.strip()
    ]

    # Patch Security Guardrails
    _default_patch_files = (
        "app-under-test/src/styles/defects.css,"
        "app-under-test/src/styles/base.css,"
        "app-under-test/src/components/,"
        "app-under-test/src/App.jsx"
    )
    ALLOWED_PATCH_FILES: List[str] = [
        p.strip()
        for p in os.getenv("ALLOWED_PATCH_FILES", _default_patch_files).split(",")
        if p.strip()
    ]

    # Patch Diff Constraints
    MAX_DIFF_LINES: int = int(os.getenv("MAX_DIFF_LINES", "300"))
    MAX_DIFF_BYTES: int = int(os.getenv("MAX_DIFF_BYTES", "30000"))


settings = Settings()
