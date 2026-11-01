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

def test_token_economics_computation():
    """Verify that cropped regions demonstrate significant token savings over full-screen."""
    opt = VLMRegionOptimizer()
    cropped = [{"crop_width": 250, "crop_height": 200}]
    report = opt.calculate_token_economics("run-opt-2", 1440, 900, cropped)

    assert report.run_id == "run-opt-2"
    assert report.full_image_tokens > report.cropped_regions_tokens
    assert report.token_savings_percent > 40.0
    assert report.latency_reduction_estimate_ms > 0
    assert report.estimated_cost_reduction_cents > 0.0

def test_crop_manifest_cache_retrieval():
    """Verify crop manifests are stored and retrieved accurately."""
    opt = VLMRegionOptimizer()
    boxes = [CropBoundingBox(x=50, y=50, width=150, height=120)]
    resp = opt.calculate_crop_regions("run-opt-3", 1280, 800, boxes)

    manifest = opt.get_crop_manifest(resp.manifest_id)
    assert manifest is not None
    assert manifest["run_id"] == "run-opt-3"
    assert manifest["image_width"] == 1280


def test_metrics_summary_efficiency_tier():
    """Verify efficiency metrics recommend appropriate model tiers."""
    opt = VLMRegionOptimizer()
    summary = opt.get_metrics_summary("run-opt-4", savings_pct=75.0)
    assert summary.efficiency_score == 0.75
    assert summary.recommended_model_tier == "gpt-4o-mini-vision"
