"""Tests for GeometryTransformer and PixelRect."""

import pytest
from automation.geometry_utils import GeometryTransformer, PixelRect


def test_normalize_subpixel_box():
    raw = {"x": 10.4, "y": 20.8, "width": 100.2, "height": 50.5}
    rect = GeometryTransformer.normalize_subpixel_box(raw)
    assert rect.x == 10
    assert rect.y == 20
    assert rect.width == 101
    assert rect.height == 52


def test_scale_to_device_pixels():
    rect = PixelRect(x=10, y=20, width=100, height=50)
    scaled = GeometryTransformer.scale_to_device_pixels(rect, 2.0)
    assert scaled.x == 20
    assert scaled.y == 40
    assert scaled.width == 200
    assert scaled.height == 100
    assert scaled.to_tuple() == (20, 40, 200, 100)
