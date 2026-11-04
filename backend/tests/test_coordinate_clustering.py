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
