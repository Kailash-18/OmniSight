"""
Visual Defect Diff and Screenshot Annotation Engine.
Provides pixel delta comparisons between before/after captures and produces
highlighted bounding-box overlays for audit reports and pull requests.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageChops


@dataclass
class DiffResult:
    total_pixels: int
    diff_pixels: int
    mismatch_percentage: float
    is_identical: bool
    diff_image_path: Optional[str] = None
    bounding_box_changes: Optional[Tuple[int, int, int, int]] = None


class VisualComparator:
    """
    Performs visual comparison and diagnostic image annotation
    for OmniSight verification runs.
    """

    def __init__(self, tolerance: int = 15):
        """
        :param tolerance: Per-channel threshold (0-255) below which pixel variance is ignored.
        """
        self.tolerance = tolerance

    def annotate_defects(
        self,
        image_path: Path,
        bounding_boxes: List[Dict[str, Any]],
        output_path: Path,
        stroke_color: str = "#FF3366",
        stroke_width: int = 3,
    ) -> Path:
        """
        Draws defect bounding boxes and warning labels onto a target screenshot.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Source screenshot not found: {image_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(image_path).convert("RGBA") as base_img:
            overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            for item in bounding_boxes:
                box = item.get("box", {})
                x = int(box.get("x", 0))
                y = int(box.get("y", 0))
                w = int(box.get("width", 0))
                h = int(box.get("height", 0))

                if w <= 0 or h <= 0:
                    continue

                x1, y1 = x, y
                x2, y2 = x + w, y + h

                draw.rectangle([x1, y1, x2, y2], outline=stroke_color, width=stroke_width)
                draw.rectangle([x1, y1, x2, y2], fill=(255, 51, 102, 35))

            composite = Image.alpha_composite(base_img, overlay)
            composite.convert("RGB").save(output_path, "PNG")

        return output_path

    def annotate_anomalies(
        self,
        image_path: Path,
        anomalies: List[Any],
        output_path: Path,
        stroke_color: str = "#FF3366",
        stroke_width: int = 3,
    ) -> Path:
        """
        Draws defect bounding boxes directly from detected SpatialAnomaly objects.
        """
        boxes: List[Dict[str, Any]] = []
        for a in anomalies:
            if getattr(a, "intersection_box", None):
                ib = a.intersection_box
                boxes.append({"box": {"x": ib.x, "y": ib.y, "width": ib.width, "height": ib.height}})
            elif getattr(a, "primary_element", None) and "box" in a.primary_element:
                boxes.append({"box": a.primary_element["box"]})
        return self.annotate_defects(image_path, boxes, output_path, stroke_color, stroke_width)

    def compare_images(
        self,
        image_a_path: Path,
        image_b_path: Path,
        diff_output_path: Optional[Path] = None,
    ) -> DiffResult:
        """
        Calculates pixel-level diff between two screenshots (e.g. before vs after patch).
        Produces a highlighted diff image showing changed layout regions.
        """
        if not image_a_path.exists():
            raise FileNotFoundError(f"Base image not found: {image_a_path}")
        if not image_b_path.exists():
            raise FileNotFoundError(f"Comparison image not found: {image_b_path}")

        with Image.open(image_a_path).convert("RGB") as img_a, Image.open(image_b_path).convert("RGB") as img_b:
            max_w = max(img_a.width, img_b.width)
            max_h = max(img_a.height, img_b.height)

            if img_a.size != (max_w, max_h):
                canvas_a = Image.new("RGB", (max_w, max_h), (255, 255, 255))
                canvas_a.paste(img_a, (0, 0))
                img_a = canvas_a

            if img_b.size != (max_w, max_h):
                canvas_b = Image.new("RGB", (max_w, max_h), (255, 255, 255))
                canvas_b.paste(img_b, (0, 0))
                img_b = canvas_b

            diff = ImageChops.difference(img_a, img_b)
            diff_box = diff.getbbox()

            total_pixels = max_w * max_h
            if diff_box is None:
                saved_path: Optional[str] = None
                if diff_output_path:
                    diff_output_path.parent.mkdir(parents=True, exist_ok=True)
                    img_a.save(diff_output_path, "PNG")
                    saved_path = str(diff_output_path)
                return DiffResult(
                    total_pixels=total_pixels,
                    diff_pixels=0,
                    mismatch_percentage=0.0,
                    is_identical=True,
                    diff_image_path=saved_path,
                )

            diff_gray = diff.convert("L")
            point_table = [0 if i < self.tolerance else 255 for i in range(256)]
            diff_mask = diff_gray.point(point_table)

            diff_pixels = diff_mask.getcolors()
            changed_count = 0
            for count, val in diff_pixels:
                if val > 0:
                    changed_count += count

            mismatch_pct = round((changed_count / total_pixels) * 100, 3)

            saved_path: Optional[str] = None
            if diff_output_path:
                diff_output_path.parent.mkdir(parents=True, exist_ok=True)
                dimmed = Image.blend(img_a, Image.new("RGB", img_a.size, (0, 0, 0)), 0.35)
                magenta_mask = Image.new("RGB", img_a.size, (255, 0, 128))
                highlighted = Image.composite(magenta_mask, dimmed, diff_mask)
                highlighted.save(diff_output_path, "PNG")
                saved_path = str(diff_output_path)

            return DiffResult(
                total_pixels=total_pixels,
                diff_pixels=changed_count,
                mismatch_percentage=mismatch_pct,
                is_identical=(changed_count == 0),
                diff_image_path=saved_path,
                bounding_box_changes=diff_box,
            )
