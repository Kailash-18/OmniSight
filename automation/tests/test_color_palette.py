"""Tests for ColorParser."""

import pytest
from automation.color_palette import ColorParser


def test_parse_hex_colors():
    white = ColorParser.parse("#ffffff")
    assert white == (1.0, 1.0, 1.0, 1.0)

    black = ColorParser.parse("#000")
    assert black == (0.0, 0.0, 0.0, 1.0)


def test_parse_rgb_rgba():
    rgb = ColorParser.parse("rgb(255, 0, 0)")
    assert rgb == (1.0, 0.0, 0.0, 1.0)

    rgba = ColorParser.parse("rgba(0, 255, 0, 0.5)")
    assert rgba == (0.0, 1.0, 0.0, 0.5)


def test_alpha_compositing():
    # 50% black over 100% white -> 50% grey
    fg = (0.0, 0.0, 0.0, 0.5)
    bg = (1.0, 1.0, 1.0, 1.0)
    res = ColorParser.composite_over(fg, bg)
    assert res == (0.5, 0.5, 0.5)
