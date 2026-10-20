"""
Automation Engine Configuration.
Centralized settings for target URLs, viewports, timeouts, and artifact paths.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class AutomationConfig:
    # Target Application
    app_url: str = field(
        default_factory=lambda: os.getenv("APP_URL", "http://localhost:5173")
    )
    backend_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_URL", "http://localhost:8000")
    )

    # Timeouts (milliseconds)
    navigation_timeout_ms: int = 15000
    action_timeout_ms: int = 5000
    health_check_timeout_s: float = 3.0

    # Browser Execution
    headless: bool = True
    browser_type: str = "chromium"

    # Artifact Storage
    workspace_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )
    artifacts_dir: Path = field(default=None)

    def __post_init__(self):
        if self.artifacts_dir is None:
            self.artifacts_dir = self.workspace_root / "artifacts" / "runs"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = AutomationConfig()
