"""
Spatial Geometry and Layout Overlap Analysis Engine.
Computes axis-aligned bounding box (AABB) intersections, viewport clipping,
and z-index occlusion matrices from extracted DOM snapshots to ground VLM findings.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

from automation.schemas import Finding, DefectCategory, Severity


class AnomalyType(str, Enum):
    VIEWPORT_CLIPPING = "viewport_clipping"
    ELEMENT_COLLISION = "element_collision"
    ACTION_OCCLUSION = "action_occlusion"


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def intersects(self, other: "BoundingBox") -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )

    def intersection(self, other: "BoundingBox") -> Optional["BoundingBox"]:
        if not self.intersects(other):
            return None

        inter_left = max(self.left, other.left)
        inter_top = max(self.top, other.top)
        inter_right = min(self.right, other.right)
        inter_bottom = min(self.bottom, other.bottom)

        return BoundingBox(
            x=inter_left,
            y=inter_top,
            width=inter_right - inter_left,
            height=inter_bottom - inter_top,
        )

    def iou(self, other: "BoundingBox") -> float:
        inter = self.intersection(other)
        if not inter or self.area == 0 or other.area == 0:
            return 0.0
        union_area = self.area + other.area - inter.area
        return inter.area / union_area if union_area > 0 else 0.0


@dataclass
class SpatialAnomaly:
    anomaly_type: AnomalyType
    severity: str
    primary_element: Dict[str, Any]
    secondary_element: Optional[Dict[str, Any]] = None
    intersection_box: Optional[BoundingBox] = None
    overlap_percentage: float = 0.0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpatialAnalyzer:
    """
    Analyzes DOM element geometry to identify visual layout anomalies
    such as clipping outside viewport bounds or overlapping interactive elements.
    """

    def __init__(self, min_overlap_ratio: float = 0.08):
        self.min_overlap_ratio = min_overlap_ratio

    def parse_box(self, raw_box: Dict[str, Any]) -> BoundingBox:
        return BoundingBox(
            x=int(raw_box.get("x", 0)),
            y=int(raw_box.get("y", 0)),
            width=int(raw_box.get("width", 0)),
            height=int(raw_box.get("height", 0)),
        )

    def analyze_dom_snapshot(self, snapshot: Dict[str, Any]) -> List[SpatialAnomaly]:
        """
        Runs geometric inspection over a serialized DOM snapshot.
        Checks for viewport boundary overflow and pairwise element occlusion.
        """
        anomalies: List[SpatialAnomaly] = []
        viewport = snapshot.get("viewport", {})
        vp_width = viewport.get("width", 0)
        vp_height = viewport.get("height", 0)
        elements = snapshot.get("elements", [])

        if not elements or vp_width <= 0 or vp_height <= 0:
            return anomalies

        for el in elements:
            box = self.parse_box(el.get("box", {}))
            if box.width <= 0 or box.height <= 0:
                continue

            overflow_right = box.right - vp_width
            if overflow_right > 10:
                anomalies.append(
                    SpatialAnomaly(
                        anomaly_type=AnomalyType.VIEWPORT_CLIPPING,
                        severity="high",
                        primary_element=el,
                        overlap_percentage=round((overflow_right / box.width) * 100, 2),
                        description=(
                            f"Element <{el.get('tag')}> with test-id '{el.get('test_id')}' overflows "
                            f"viewport width ({vp_width}px) by {overflow_right}px."
                        ),
                        metadata={"overflow_axis": "x", "overflow_pixels": overflow_right},
                    )
                )

        num_elements = len(elements)
        for i in range(num_elements):
            el_a = elements[i]
            box_a = self.parse_box(el_a.get("box", {}))
            if box_a.area <= 0:
                continue

            for j in range(i + 1, num_elements):
                el_b = elements[j]
                box_b = self.parse_box(el_b.get("box", {}))
                if box_b.area <= 0:
                    continue

                if not box_a.intersects(box_b):
                    continue

                inter = box_a.intersection(box_b)
                if not inter:
                    continue

                smaller_area = min(box_a.area, box_b.area)
                overlap_ratio = inter.area / smaller_area if smaller_area > 0 else 0.0

                if overlap_ratio >= self.min_overlap_ratio:
                    anomaly = self._classify_collision(el_a, box_a, el_b, box_b, inter, overlap_ratio)
                    if anomaly:
                        anomalies.append(anomaly)

        return anomalies

    def _classify_collision(
        self,
        el_a: Dict[str, Any],
        box_a: BoundingBox,
        el_b: Dict[str, Any],
        box_b: BoundingBox,
        inter: BoundingBox,
        overlap_ratio: float,
    ) -> Optional[SpatialAnomaly]:
        """Classifies the nature of the collision between two elements."""
        tag_a = el_a.get("tag", "")
        tag_b = el_b.get("tag", "")
        test_id_a = el_a.get("test_id") or ""
        test_id_b = el_b.get("test_id") or ""
        comp_a = el_a.get("computed", {})
        comp_b = el_b.get("computed", {})

        is_action_a = tag_a in ("button", "a", "input") or "button" in test_id_a or "submit" in test_id_a
        is_action_b = tag_b in ("button", "a", "input") or "button" in test_id_b or "submit" in test_id_b

        if (is_action_a or is_action_b) and overlap_ratio > 0.5:
            action_el = el_a if is_action_a else el_b
            occluder_el = el_b if is_action_a else el_a

            return SpatialAnomaly(
                anomaly_type=AnomalyType.ACTION_OCCLUSION,
                severity="critical",
                primary_element=action_el,
                secondary_element=occluder_el,
                intersection_box=inter,
                overlap_percentage=round(overlap_ratio * 100, 2),
                description=(
                    f"Actionable element <{action_el.get('tag')}> ('{action_el.get('test_id')}') is "
                    f"occluded ({round(overlap_ratio * 100)}%) by <{occluder_el.get('tag')}>."
                ),
                metadata={
                    "action_test_id": action_el.get("test_id"),
                    "occluder_test_id": occluder_el.get("test_id"),
                },
            )

        is_heading_a = tag_a in ("h1", "h2", "h3") or "hero-title" in el_a.get("classes", [])
        is_heading_b = tag_b in ("h1", "h2", "h3") or "hero-title" in el_b.get("classes", [])

        if is_heading_a or is_heading_b:
            heading_el = el_a if is_heading_a else el_b
            other_el = el_b if is_heading_a else el_a

            return SpatialAnomaly(
                anomaly_type=AnomalyType.ELEMENT_COLLISION,
                severity="high",
                primary_element=heading_el,
                secondary_element=other_el,
                intersection_box=inter,
                overlap_percentage=round(overlap_ratio * 100, 2),
                description=(
                    f"Heading <{heading_el.get('tag')}> overlaps with <{other_el.get('tag')}> "
                    f"('{other_el.get('test_id')}') by {inter.height}px vertically."
                ),
                metadata={"vertical_overlap_px": inter.height},
            )

        return None

    def analyze_dom_file(self, json_path: Union[Path, str]) -> List[SpatialAnomaly]:
        """Loads and inspects a saved DOM JSON snapshot file."""
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"DOM snapshot not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        return self.analyze_dom_snapshot(snapshot)

    def to_findings(
        self, anomalies: List[SpatialAnomaly], viewport_name: str = "all"
    ) -> List[Finding]:
        """
        Translates detected spatial anomalies into standardized OmniSight Finding schemas.
        """
        findings: List[Finding] = []
        for idx, a in enumerate(anomalies, 1):
            target_sel = (
                f"[data-testid='{a.primary_element.get('test_id')}']"
                if a.primary_element.get("test_id")
                else a.primary_element.get("tag", "element")
            )

            if a.anomaly_type == AnomalyType.VIEWPORT_CLIPPING:
                category = DefectCategory.ELEMENT_CLIPPING
                sev = Severity.HIGH
                suggested = "Adjust responsive CSS (e.g. max-width: 100% or overflow handling) to fit within viewport."
                rationale = f"Element geometry extends {a.metadata.get('overflow_pixels', 0)}px past viewport edge."
            elif a.anomaly_type == AnomalyType.ACTION_OCCLUSION:
                category = DefectCategory.ELEMENT_OBSTRUCTION
                sev = Severity.CRITICAL
                occluder = (
                    a.secondary_element.get("test_id")
                    or a.secondary_element.get("tag")
                    or "overlay"
                ) if a.secondary_element else "overlay"
                suggested = f"Remove overlay positioning, reduce z-index, or reposition '{occluder}' to reveal primary action."
                rationale = f"Primary actionable control is occluded ({a.overlap_percentage}%) by '{occluder}'."
            else:
                category = DefectCategory.ELEMENT_OVERLAP
                sev = Severity.HIGH
                suggested = "Adjust margin, padding, or layout flow to avoid element overlap."
                rationale = f"Elements collide with {a.metadata.get('vertical_overlap_px', 0)}px vertical overlap."

            findings.append(
                Finding(
                    id=f"spatial-{a.anomaly_type.value}-{idx}",
                    category=category,
                    severity=sev,
                    description=a.description,
                    viewport=viewport_name,
                    target_element=target_sel,
                    confidence=0.96,
                    suggested_change=suggested,
                    rationale=rationale,
                    status="detected",
                )
            )
        return findings
