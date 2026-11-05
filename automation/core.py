"""
OmniSight Automation Core Module.
Contains centralized configuration, standard viewports, Pydantic schemas,
and evidence artifact collection for browser visual audit runs.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import platform
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


# ---------------------------------------------------------------------------
# Configuration & Viewports
# ---------------------------------------------------------------------------

@dataclass
class AutomationConfig:
    """Centralized runtime configuration for browser runner and backend integration."""
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
    artifacts_dir: Optional[Path] = field(default=None)

    def __post_init__(self):
        if self.artifacts_dir is None:
            self.artifacts_dir = self.workspace_root / "artifacts" / "runs"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ViewportSpec:
    """Specification for responsive browser viewport simulation."""
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
    """Retrieves a standard viewport specification by name."""
    if name not in STANDARD_VIEWPORTS:
        raise KeyError(
            f"Unknown viewport '{name}'. Available: {list(STANDARD_VIEWPORTS.keys())}"
        )
    return STANDARD_VIEWPORTS[name]


def get_desktop_viewports() -> List[ViewportSpec]:
    """Returns desktop viewport specifications."""
    return [v for v in STANDARD_VIEWPORTS.values() if not v.is_mobile]


def get_mobile_viewports() -> List[ViewportSpec]:
    """Returns mobile viewport specifications."""
    return [v for v in STANDARD_VIEWPORTS.values() if v.is_mobile]


config = AutomationConfig()


# ---------------------------------------------------------------------------
# Data Schemas & Models
# ---------------------------------------------------------------------------

class DefectCategory(str, Enum):
    ELEMENT_OVERLAP = "element_overlap"
    ELEMENT_CLIPPING = "element_clipping"
    ELEMENT_OBSTRUCTION = "element_obstruction"
    CONTRAST_ISSUE = "contrast_issue"
    LAYOUT_OVERFLOW = "layout_overflow"
    BROKEN_LINK = "broken_link"
    CLICK_ERROR = "click_error"
    NO_EFFECT = "no_effect"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    id: str = Field(description="Unique defect identifier")
    category: DefectCategory = Field(description="Classification of the visual bug")
    severity: Severity = Field(description="Impact on user journey")
    description: str = Field(description="Clear explanation of the visual flaw")
    viewport: str = Field(description="Viewport(s) where defect is observable")
    target_element: Optional[str] = Field(default=None, description="CSS selector or test ID")
    confidence: float = Field(ge=0.0, le=1.0, description="VLM model confidence score")
    suggested_change: str = Field(description="Proposed CSS/layout rule correction")
    rationale: str = Field(description="Multimodal visual reasoning justification")
    status: str = Field(default="detected", description="Remediation status")


class ProposedPatch(BaseModel):
    target_file: str = Field(description="Allowlisted relative path to file")
    diff: str = Field(description="Unified git diff representing the fix")
    explanation: str = Field(description="Why this patch repairs the visual defect")


class RetestStatus(str, Enum):
    FIXED = "fixed"
    UNRESOLVED = "unresolved"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class RetestVerification(BaseModel):
    status: RetestStatus = Field(description="Verification evaluation result")
    target_viewport: str = Field(description="Viewport verified under retest")
    before_screenshot: str = Field(description="Path to baseline defect screenshot")
    after_screenshot: str = Field(description="Path to post-repair screenshot")
    diff_screenshot: Optional[str] = Field(default=None, description="Visual diff overlay path")
    mismatch_percentage: float = Field(default=0.0, description="Pixel mismatch delta percentage")
    resolved_findings: List[str] = Field(default_factory=list, description="IDs of cleared defects")
    remaining_findings: List[str] = Field(default_factory=list, description="IDs of lingering defects")
    notes: str = Field(default="", description="Verification summary notes")


class VisualAuditReport(BaseModel):
    run_id: str
    target_url: str
    findings: List[Finding]
    summary: str
    proposed_patch: Optional[ProposedPatch] = None
    annotated_screenshots: List[str] = Field(
        default_factory=list, description="Screenshots with visual defect annotations"
    )
    retest_verification: Optional[RetestVerification] = Field(
        default=None, description="Sandboxed retest verification result"
    )


# ---------------------------------------------------------------------------
# Evidence Collector & DOM Extraction
# ---------------------------------------------------------------------------

@dataclass
class RunManifest:
    """Standardized run.json artifact for backend ingestion and QA inspection."""
    run_id: str
    target_url: str
    status: str
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    end_time: Optional[str] = None
    viewports: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    dom_snapshots: List[str] = field(default_factory=list)
    issue_count: int = 0
    environment: Dict[str, str] = field(
        default_factory=lambda: {
            "os": platform.system(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
    )

    def finalize(self, status: str = "audited", issue_count: int = 0) -> None:
        self.status = status
        self.issue_count = issue_count
        self.end_time = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_dom_context(page: Any) -> Dict[str, Any]:
    """
    Evaluates key interactive and visual elements in the current page,
    returning structured geometry and semantic identifiers.
    """
    script = """
    () => {
        const elements = [];
        const targets = document.querySelectorAll(
            '[data-testid], h1, h2, h3, button, a, form, input, textarea, .promo-banner, .hero-title, .cart-summary'
        );

        targets.forEach((el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            
            if (rect.width > 0 || rect.height > 0) {
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    test_id: el.getAttribute('data-testid') || null,
                    classes: Array.from(el.classList),
                    text: (el.innerText || el.textContent || '').trim().slice(0, 100),
                    box: {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    },
                    computed: {
                        display: style.display,
                        position: style.position,
                        zIndex: style.zIndex,
                        overflow: style.overflow,
                        visibility: style.visibility,
                        pointerEvents: style.pointerEvents
                    }
                });
            }
        });

        return {
            url: window.location.href,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            element_count: elements.length,
            elements: elements
        };
    }
    """
    try:
        return page.evaluate(script)
    except Exception as e:
        return {
            "url": getattr(page, "url", ""),
            "error": f"Failed to extract DOM context: {str(e)}",
            "elements": []
        }


class EvidenceCollector:
    """Manages run directory structure and persists screenshots, logs, and manifests."""

    def __init__(self, run_id: Optional[str] = None):
        if run_id is None:
            self.run_id = f"run-{int(time.time())}"
        else:
            self.run_id = run_id

        self.run_dir = config.artifacts_dir / self.run_id
        self.screenshots_dir = self.run_dir / "screenshots"
        self.dom_dir = self.run_dir / "dom"
        self.logs_dir = self.run_dir / "logs"
        self.annotated_dir = self.run_dir / "annotated"
        self.retest_dir = self.run_dir / "retest"

        for directory in [
            self.run_dir,
            self.screenshots_dir,
            self.dom_dir,
            self.logs_dir,
            self.annotated_dir,
            self.retest_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        self.recorded_screenshots: List[str] = []
        self.recorded_dom_snapshots: List[str] = []
        self.recorded_annotated: List[str] = []
        self.console_logs: List[Dict[str, Any]] = []

    def get_screenshot_path(self, viewport_name: str, page_name: str) -> Path:
        filename = f"{viewport_name}_{page_name}.png"
        path = self.screenshots_dir / filename
        path_str = str(path)
        if path_str not in self.recorded_screenshots:
            self.recorded_screenshots.append(path_str)
        return path

    def get_annotated_path(self, viewport_name: str, page_name: str) -> Path:
        filename = f"{viewport_name}_{page_name}_annotated.png"
        path = self.annotated_dir / filename
        path_str = str(path)
        if path_str not in self.recorded_annotated:
            self.recorded_annotated.append(path_str)
        return path

    def get_retest_path(self, filename: str) -> Path:
        return self.retest_dir / filename

    def save_dom_snapshot(
        self, viewport_name: str, page_name: str, dom_data: Dict[str, Any]
    ) -> Path:
        filename = f"{viewport_name}_{page_name}_dom.json"
        path = self.dom_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dom_data, f, indent=2)
        path_str = str(path)
        if path_str not in self.recorded_dom_snapshots:
            self.recorded_dom_snapshots.append(path_str)
        return path

    def record_console_log(self, level: str, message: str, url: str):
        self.console_logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "url": url,
        })

    def save_console_logs(self) -> Path:
        log_file = self.logs_dir / "console.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self.console_logs, f, indent=2)
        return log_file

    def save_manifest(self, manifest_data: Dict[str, Any]) -> Path:
        manifest_file = self.run_dir / "run.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        return manifest_file
