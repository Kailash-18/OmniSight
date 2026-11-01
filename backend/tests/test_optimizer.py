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
