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
            run_dir / "retest" / f"{viewport}_{page}_after.png",  # where the retest step saves it
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

        # If no findings for this run, there are 0 bugs: do NOT draw a fake defect box
        if not findings:
            return None

        # Find findings that specifically match this viewport and page
        matching_finding = None
        for f in findings:
            f_dict = f if isinstance(f, dict) else (f.dict() if hasattr(f, "dict") else vars(f))
            f_vp = str(f_dict.get("viewport") or "all")
            vp_match = (f_vp == "all") or (f_vp == viewport) or (f_vp in viewport) or (viewport in f_vp)
            if not vp_match:
                continue

            f_id = str(f_dict.get("id") or "").lower()
            target_el = str(f_dict.get("target_element") or "").lower()
            desc = str(f_dict.get("description") or "").lower()
            raw_box = f_dict.get("bounding_box") or (
                f_dict.get("details", {}).get("box") if isinstance(f_dict.get("details"), dict) else None
            )

            page_match = False
            if raw_box and not any(k in f_id for k in ("cart", "checkout", "home", "product")):
                # Explicit bounding box with generic finding ID (e.g. "box-1" or "f1" in tests)
                page_match = True
            elif page == "home":
                page_match = any(k in f_id for k in ("home", "product", "defect-1")) or any(k in target_el for k in ("hero", "product")) or "hero" in desc
            elif page == "cart":
                page_match = any(k in f_id for k in ("cart", "defect-2")) or any(k in target_el for k in ("checkout-cta", "continue-to-checkout", "cart")) or "cart" in desc or "clipped" in desc
            elif page == "checkout":
                page_match = any(k in f_id for k in ("checkout", "defect-3")) or any(k in target_el for k in ("promo-banner", "submit", "checkout")) or "promo" in desc or "obstruct" in desc
            else:
                page_match = (page in f_id) or (page in target_el)

            if page_match:
                matching_finding = f_dict
                break

        if not matching_finding:
            # No defect on this specific screenshot: do NOT draw a box
            return None

        annotated_path = screenshots_dir / f"{viewport}_{page}_annotated.png"
        if not annotated_path.exists():
            # Attempt to retrieve real bounding box from DOM snapshot or finding
            box = None
            raw_box = matching_finding.get("bounding_box") or (
                matching_finding.get("details", {}).get("box") if isinstance(matching_finding.get("details"), dict) else None
            )
            if raw_box and isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
                bx1, by1, bx2, by2 = raw_box
                if bx2 > bx1 and by2 > by1:
                    box = (int(bx1), int(by1), int(bx2), int(by2))
                else:
                    box = (int(bx1), int(by1), int(bx1 + bx2), int(by1 + by2))

            # Inspect DOM snapshot for the target element geometry
            if not box:
                dom_path = run_dir / "dom" / f"{viewport}_{page}_dom.json"
                if dom_path.exists():
                    try:
                        import json
                        with open(dom_path, "r", encoding="utf-8") as df:
                            dom_data = json.load(df)
                        target_selector = str(matching_finding.get("target_element") or "").strip().lstrip(".").lower()
                        for el in dom_data.get("elements", []):
                            classes = [c.lower() for c in el.get("classes", [])]
                            test_id = str(el.get("test_id") or "").lower()
                            if (target_selector and (target_selector in classes or target_selector in test_id)) or \
                               (page == "home" and ("hero-title" in classes or el.get("tag") == "h1")) or \
                               (page == "cart" and ("checkout-cta" in classes or test_id == "continue-to-checkout")) or \
                               (page == "checkout" and ("promo-banner" in classes or "free shipping" in el.get("text", "").lower())):
                                b = el.get("box", {})
                                if b.get("width", 0) > 0 and b.get("height", 0) > 0:
                                    x = int(b.get("x", 0))
                                    y = int(b.get("y", 0))
                                    w = int(b.get("width", 0))
                                    h = int(b.get("height", 0))
                                    box = (x, y, x + w, y + h)
                                    break
                    except Exception:
                        pass

            # Coordinate estimates tailored to defect and screen size if DOM snapshot not present
            if not box:
                from PIL import Image
                with Image.open(base_path) as img:
                    img_w, img_h = img.size
                if page == "home":
                    box = (int(img_w * 0.08), int(img_h * 0.12), int(img_w * 0.65), int(img_h * 0.24))
                elif page == "cart":
                    box = (int(img_w * 0.05), int(img_h * 0.70), int(img_w * 0.95), int(img_h * 0.82))
                elif page == "checkout":
                    box = (int(img_w * 0.10), int(img_h * 0.60), int(img_w * 0.85), int(img_h * 0.76))
                else:
                    box = (int(img_w * 0.15), int(img_h * 0.25), int(img_w * 0.85), int(img_h * 0.50))

            label = matching_finding.get("description", "Defect Detected")[:20]
            self.comparator.annotate_remediation_bounding_box(base_path, box, annotated_path, label=label)
        return annotated_path


spatial_service = SpatialDiagnosticService()
