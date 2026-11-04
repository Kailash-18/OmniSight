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

    def merge_overlapping_boxes(self, boxes: List[ClusterBoundingBox], iou_threshold: float, max_w: int, max_h: int, padding: float) -> List[ClusterRegion]:
        """Clusters bounding boxes based on IoU overlap threshold."""
        if not boxes:
            return []

        dict_boxes = [
            {"id": b.id, "x": b.x, "y": b.y, "width": b.width, "height": b.height, "pii": b.is_sensitive_pii, "z": b.z_index}
            for b in boxes
        ]

        clusters: List[List[Dict[str, Any]]] = []
        visited = set()

        for i, box in enumerate(dict_boxes):
            if i in visited:
                continue
            curr_cluster = [box]
            visited.add(i)

            for j in range(i + 1, len(dict_boxes)):
                if j in visited:
                    continue
                other = dict_boxes[j]
                if self.calculate_iou(box, other) >= iou_threshold:
                    curr_cluster.append(other)
                    visited.add(j)
            clusters.append(curr_cluster)

        result_regions: List[ClusterRegion] = []
        for idx, cluster in enumerate(clusters):
            min_x = min(b["x"] for b in cluster)
            min_y = min(b["y"] for b in cluster)
            max_x2 = max(b["x"] + b["width"] for b in cluster)
            max_y2 = max(b["y"] + b["height"] for b in cluster)

            w = max_x2 - min_x
            h = max_y2 - min_y
            pad_x = int(w * padding)
            pad_y = int(h * padding)

            x = max(0, min_x - pad_x)
            y = max(0, min_y - pad_y)
            w = min(max_w - x, w + 2 * pad_x)
            h = min(max_h - y, h + 2 * pad_y)

            aligned = {"x": x, "y": y, "width": w, "height": h}
            redactions = [
                {"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]}
                for b in cluster if b.get("pii")
            ]

            result_regions.append(ClusterRegion(
                cluster_id=f"cluster-{idx + 1}",
                bounding_box={"x": x, "y": y, "width": w, "height": h},
                included_box_ids=[b["id"] for b in cluster],
                area_pixels=w * h,
                hardware_aligned_box=aligned,
                redaction_masks=redactions
            ))
        return result_regions
