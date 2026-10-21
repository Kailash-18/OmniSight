"""
Run Metadata and Manifest Serializer.
Produces standardized run.json artifacts for backend ingestion and QA dashboard inspection.
"""

import os
import sys
import platform
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class RunManifest:
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
