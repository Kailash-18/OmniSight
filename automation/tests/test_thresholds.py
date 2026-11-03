"""Tests for VisualThresholdConfig and SensitivityProfile."""

import pytest
from automation.thresholds import SensitivityProfile, VisualThresholdConfig


def test_threshold_profiles():
    strict = VisualThresholdConfig.from_profile("strict")
    assert strict.profile == SensitivityProfile.STRICT
    assert strict.pixel_delta_threshold == 8
    assert strict.is_diff_acceptable(0.005) is True
    assert strict.is_diff_acceptable(0.02) is False

    balanced = VisualThresholdConfig.from_profile("balanced")
    assert balanced.profile == SensitivityProfile.BALANCED
    assert balanced.pixel_delta_threshold == 15
    assert balanced.is_diff_acceptable(0.04) is True
    assert balanced.is_diff_acceptable(0.08) is False

    permissive = VisualThresholdConfig.from_profile("permissive")
    assert permissive.profile == SensitivityProfile.PERMISSIVE
    assert permissive.pixel_delta_threshold == 30
    assert permissive.is_diff_acceptable(0.15) is True
    assert permissive.is_diff_acceptable(0.25) is False


def test_threshold_dict_serialization():
    cfg = VisualThresholdConfig.from_profile("balanced")
    d = cfg.to_dict()
    assert d["profile"] == "balanced"
    assert "pixel_delta_threshold" in d
    assert "max_acceptable_diff_percent" in d
