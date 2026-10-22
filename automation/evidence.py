"""
Evidence Collector and Artifact Directory Manager.
Stores structured visual proof, DOM trees, and run metadata per audit session.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from automation.config import config


class EvidenceCollector:
    def __init__(self, run_id: Optional[str] = None):
        if run_id is None:
            self.run_id = f"run-{int(time.time())}"
        else:
            self.run_id = run_id

        self.run_dir = config.artifacts_dir / self.run_id
        self.screenshots_dir = self.run_dir / "screenshots"
        self.dom_dir = self.run_dir / "dom"
        self.logs_dir = self.run_dir / "logs"

        for directory in [self.run_dir, self.screenshots_dir, self.dom_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.recorded_screenshots: List[str] = []
        self.recorded_dom_snapshots: List[str] = []
        self.console_logs: List[Dict[str, Any]] = []

    def get_screenshot_path(self, viewport_name: str, page_name: str) -> Path:
        filename = f"{viewport_name}_{page_name}.png"
        path = self.screenshots_dir / filename
        self.recorded_screenshots.append(str(path))
        return path

    def save_dom_snapshot(
        self, viewport_name: str, page_name: str, dom_data: Dict[str, Any]
    ) -> Path:
        filename = f"{viewport_name}_{page_name}_dom.json"
        path = self.dom_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dom_data, f, indent=2)
        self.recorded_dom_snapshots.append(str(path))
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
