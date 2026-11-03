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

def test_token_economics_reduction():
    optimizer = VLMRegionOptimizer()
    boxes = [CropBoundingBox(x=50, y=50, width=150, height=100, padding_percent=0.10)]
    res = optimizer.calculate_crop_regions("run-b2", 1920, 1080, boxes)
    report = optimizer.calculate_token_economics("run-b2", 1920, 1080, res.cropped_regions)
    assert report.token_savings_percent > 50.0
    assert report.cropped_regions_tokens < report.full_image_tokens
