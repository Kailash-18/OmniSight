"""
Unit test suite for Coordinate Clustering and IoU Spatial Optimization.
"""
import pytest
from backend.app.services.coordinate_cluster_service import CoordinateClusterEngine
from backend.app.schemas.clustering_schema import (
    ClusterBoundingBox,
    ClusterBoundingBoxRequest
)

def test_iou_calculation_exact_and_disjoint():
    engine = CoordinateClusterEngine()
    box_a = {"x": 100, "y": 100, "width": 200, "height": 200}
    box_b = {"x": 100, "y": 100, "width": 200, "height": 200}
    assert engine.calculate_iou(box_a, box_b) == 1.0

    disjoint_box = {"x": 500, "y": 500, "width": 100, "height": 100}
    assert engine.calculate_iou(box_a, disjoint_box) == 0.0

def test_multi_element_box_merging():
    engine = CoordinateClusterEngine()
    boxes = [
        ClusterBoundingBox(id="b1", x=100, y=100, width=150, height=150),
        ClusterBoundingBox(id="b2", x=120, y=120, width=140, height=140),
        ClusterBoundingBox(id="b3", x=800, y=600, width=100, height=100)
    ]
    regions = engine.merge_overlapping_boxes(boxes, iou_threshold=0.20, max_w=1920, max_h=1080, padding=0.10)
    assert len(regions) == 2
    assert "b1" in regions[0].included_box_ids
    assert "b2" in regions[0].included_box_ids
    assert "b3" in regions[1].included_box_ids

def test_hardware_grid_alignment():
    engine = CoordinateClusterEngine(hardware_tile_alignment=64)
    res = engine.align_to_hardware_grid(x=73, y=129, width=195, height=210, max_w=1920, max_h=1080)
    assert res["x"] % 64 == 0
    assert res["y"] % 64 == 0
    assert res["width"] >= 195
    assert res["height"] >= 210
