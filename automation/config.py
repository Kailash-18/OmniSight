"""
Automation Engine Configuration.
Centralized settings for target URLs, viewports, timeouts, and artifact paths.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AutomationConfig:
    app_url: str = field(
        default_factory=lambda: os.getenv("APP_URL", "http://127.0.0.1:5173")
    )
    backend_url: str = field(
        default_factory=lambda: os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    )
    vlm_api_key: Optional[str] = field(
        default_factory=lambda: (
            os.getenv("VLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )
    )

    navigation_timeout_ms: int = 15000
    action_timeout_ms: int = 5000
    health_check_timeout_s: float = 3.0

    headless: bool = True
    browser_type: str = "chromium"

    workspace_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )
    artifacts_dir: Path = field(default=None)

    def __post_init__(self):
        if self.artifacts_dir is None:
            self.artifacts_dir = self.workspace_root / "artifacts" / "runs"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ViewportSpec:
    name: str
    width: int
    height: int
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    description: str = ""

    @property
    def resolution_str(self) -> str:
        return f"{self.width}x{self.height}"


STANDARD_VIEWPORTS: Dict[str, ViewportSpec] = {
    "desktop_1440x900": ViewportSpec(
        name="desktop_1440x900",
        width=1440,
        height=900,
        is_mobile=False,
        has_touch=False,
        description="Standard desktop widescreen display",
    ),
    "desktop_1280x800": ViewportSpec(
        name="desktop_1280x800",
        width=1280,
        height=800,
        is_mobile=False,
        has_touch=False,
        description="Standard laptop display resolution",
    ),
    "mobile_390x844": ViewportSpec(
        name="mobile_390x844",
        width=390,
        height=844,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        description="Modern mobile device viewport (iPhone 12/13/14)",
    ),
    "mobile_375x667": ViewportSpec(
        name="mobile_375x667",
        width=375,
        height=667,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        description="Compact mobile device viewport (iPhone SE / narrow screens)",
    ),
}


def get_viewport(name: str) -> ViewportSpec:
    if name not in STANDARD_VIEWPORTS:
        raise KeyError(
            f"Unknown viewport '{name}'. Available: {list(STANDARD_VIEWPORTS.keys())}"
        )
    return STANDARD_VIEWPORTS[name]


def get_desktop_viewports() -> List[ViewportSpec]:
    return [v for v in STANDARD_VIEWPORTS.values() if not v.is_mobile]


def get_mobile_viewports() -> List[ViewportSpec]:
    return [v for v in STANDARD_VIEWPORTS.values() if v.is_mobile]


config = AutomationConfig()

