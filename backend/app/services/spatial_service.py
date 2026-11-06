"""
Spatial and Visual Diff Diagnostic Service for OmniSight Backend.
Generates pixel-difference heatmaps and bounding box annotations for QA review.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure repository root is on sys.path for automation module imports
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from automation.engine import VisualComparator


class SpatialDiagnosticService:
    def __init__(self, artifacts_dir: Path = Path("artifacts")):
        self.artifacts_dir = Path(artifacts_dir).resolve()
        self.comparator = VisualComparator()

    def get_or_generate_heatmap(
        self, run_id: str, viewport: str = "desktop_1440x900", page: str = "home"
    ) -> Optional[Path]:
        run_dir = self.artifacts_dir / "runs" / run_id
        screenshots_dir = run_dir / "screenshots"

        before_candidates = [
            screenshots_dir / f"{viewport}_{page}.png",
            screenshots_dir / f"{viewport}_{page}_before.png",
        ]
        after_candidates = [
            screenshots_dir / f"{viewport}_{page}_after.png",
        ]

        before_path = next((p for p in before_candidates if p.exists()), None)
        after_path = next((p for p in after_candidates if p.exists()), None)

        if not before_path or not after_path:
            return None

        heatmap_path = screenshots_dir / f"{viewport}_{page}_heatmap.png"
        if not heatmap_path.exists():
            self.comparator.generate_diff_heatmap(before_path, after_path, heatmap_path)
        return heatmap_path

    def get_or_generate_annotated(
        self, run_id: str, viewport: str = "desktop_1440x900", page: str = "home",
        findings: Optional[list] = None
    ) -> Optional[Path]:
        run_dir = self.artifacts_dir / "runs" / run_id
        screenshots_dir = run_dir / "screenshots"
        base_path = screenshots_dir / f"{viewport}_{page}.png"

        if not base_path.exists():
            return None

        annotated_path = screenshots_dir / f"{viewport}_{page}_annotated.png"
        if not annotated_path.exists():
            # If findings with bounding boxes exist, annotate the primary box
            box = (40, 40, 200, 100)
            if findings:
                for f in findings:
                    raw_box = f.get("bounding_box") or (f.get("details", {}).get("box") if isinstance(f, dict) else None)
                    if raw_box and isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
                        box = tuple(raw_box)
                        break
            self.comparator.annotate_remediation_bounding_box(base_path, box, annotated_path, label="Defect Detected")
        return annotated_path


spatial_service = SpatialDiagnosticService()
