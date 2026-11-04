"""
Coordinate Clustering & Spatial Tensor Optimization Service.
Merges overlapping anomaly viewports, aligns to hardware tensor grids, and generates PII redactions.
"""
from typing import List, Dict, Any, Tuple
from backend.app.schemas.clustering_schema import (
    ClusterBoundingBox,
    ClusterRegion,
    ClusterBoundingBoxRequest,
    ClusterBoundingBoxResponse
)

class CoordinateClusterEngine:
    """
    Hierarchical spatial clustering engine for VLM vision payloads.
    Reduces redundant VLM tile processing by merging localized bounding box clusters.
    """
    def __init__(self, hardware_tile_alignment: int = 64):
        self.hardware_tile_alignment = hardware_tile_alignment

    @staticmethod
    def calculate_iou(box_a: Dict[str, int], box_b: Dict[str, int]) -> float:
        """Calculates Intersection-over-Union (IoU) between two bounding boxes."""
        ax1, ay1 = box_a["x"], box_a["y"]
        ax2, ay2 = ax1 + box_a["width"], ay1 + box_a["height"]
        bx1, by1 = box_b["x"], box_b["y"]
        bx2, by2 = bx1 + box_b["width"], by1 + box_b["height"]

        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        intersection_area = iw * ih

        area_a = box_a["width"] * box_a["height"]
        area_b = box_b["width"] * box_b["height"]
        union_area = area_a + area_b - intersection_area

        if union_area <= 0:
            return 0.0
        return float(intersection_area / union_area)
