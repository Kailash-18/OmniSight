"""Evidence metadata formatting and artifact integrity verification.

Generates machine-readable metadata records for captured screenshots,
DOM trees, and network logs attached to audit runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ScreenshotRecord:
    filename: str
    viewport: str
    page_name: str
    stage: str  # 'before', 'after', 'diff'
    width: int
    height: int
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "viewport": self.viewport,
            "page": self.page_name,
            "stage": self.stage,
            "dimensions": f"{self.width}x{self.height}",
            "captured_at": self.captured_at,
        }


class EvidenceMetadataManager:
    """Manages collection and validation of audit run evidence records."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.screenshots: List[ScreenshotRecord] = []

    def register_screenshot(
        self, filename: str, viewport: str, page_name: str, stage: str, width: int, height: int
    ) -> ScreenshotRecord:
        record = ScreenshotRecord(
            filename=filename,
            viewport=viewport,
            page_name=page_name,
            stage=stage,
            width=width,
            height=height,
        )
        self.screenshots.append(record)
        return record

    def compile_manifest(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_screenshots": len(self.screenshots),
            "viewports_covered": sorted(list({s.viewport for s in self.screenshots})),
            "stages_covered": sorted(list({s.stage for s in self.screenshots})),
            "screenshots": [s.to_dict() for s in self.screenshots],
        }
