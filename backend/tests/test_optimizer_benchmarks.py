"""
Unit and benchmark tests for VLM Spatial Optimization & Token Economics.
"""
import pytest
from backend.app.services.optimizer_service import VLMRegionOptimizer
from backend.app.schemas.optimizer_schema import CropBoundingBox

def test_spatial_crop_boundary_expansion():
    optimizer = VLMRegionOptimizer()
    boxes = [CropBoundingBox(x=100, y=100, width=200, height=150, padding_percent=0.15)]
    res = optimizer.calculate_crop_regions("run-b1", 1280, 720, boxes)
    assert len(res.cropped_regions) == 1
    region = res.cropped_regions[0]
    assert region["crop_width"] >= 200
    assert region["crop_height"] >= 150
    assert region["crop_x"] <= 100
