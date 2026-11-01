"""
Unit and Integration Tests for VLM Spatial Region Optimization & Token Economics Engine.
"""

import pytest
from backend.app.schemas.optimizer_schema import CropBoundingBox, CropRegionRequest
from backend.app.services.optimizer_service import VLMRegionOptimizer, vlm_optimizer


def test_calculate_crop_regions_basic_box():
    """Verify crop region calculation applies padding and returns valid dimensions."""
    opt = VLMRegionOptimizer()
    boxes = [CropBoundingBox(x=100, y=150, width=200, height=100, padding_percent=0.15)]
    res = opt.calculate_crop_regions("run-opt-1", 1440, 900, boxes)

    assert res.run_id == "run-opt-1"
    assert res.total_regions == 1
    assert "MANIFEST-OPT-" in res.manifest_id

    reg = res.cropped_regions[0]
    # 200 * 0.15 = 30px padding
    assert reg["crop_x"] <= 100
    assert reg["crop_width"] >= 200

def test_clamp_coordinates_at_edge_boundaries():
    """Verify that coordinates near canvas edges are safely clamped to [0, max]."""
    opt = VLMRegionOptimizer()
    clamped = opt.clamp_coordinates(x=-20, y=890, width=300, height=200, max_w=1440, max_h=900)
    assert clamped["x"] == 0
    assert clamped["y"] + clamped["height"] <= 900
    assert clamped["width"] >= 50
