"""
Unit Tests for Focused Screenshot Analysis & Component Cropper (Week 4 optimization).
Verifies region cropping around UI anomalies, boundary clamping, and token reduction metrics.
"""

from pathlib import Path
from PIL import Image
import pytest

from automation.engine import (
    BoundingBox,
    ComponentCropper,
    CropResult,
    crop_component_region,
)


@pytest.fixture
def sample_test_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "test_screenshot.png"
    img = Image.new("RGB", (1440, 900), color=(240, 240, 245))
    img.save(img_path)
    return img_path


def test_component_cropper_basic(sample_test_image: Path, tmp_path: Path):
    out_path = tmp_path / "crop.png"
    cropper = ComponentCropper(padding=20)
    box = BoundingBox(x=100, y=150, width=200, height=80)

    result = cropper.crop_region(sample_test_image, box, out_path)

    assert isinstance(result, CropResult)
    assert out_path.exists()
    assert result.original_dimensions == (1440, 900)
    assert result.cropped_dimensions == (240, 120)  # 200+40, 80+40
    assert result.area_reduction_percentage > 90.0
    assert result.estimated_token_savings_percentage > 85.0


def test_component_cropper_boundary_clamping(sample_test_image: Path, tmp_path: Path):
    out_path = tmp_path / "edge_crop.png"
    # Near top-left boundary
    box = {"x": 5, "y": 5, "width": 50, "height": 50}

    result = crop_component_region(sample_test_image, box, out_path, padding=30)
    assert out_path.exists()
    x1, y1, x2, y2 = result.bounding_box
    assert x1 >= 0
    assert y1 >= 0
    assert x2 <= 1440
    assert y2 <= 900


def test_component_cropper_missing_source_raises(tmp_path: Path):
    cropper = ComponentCropper()
    with pytest.raises(FileNotFoundError):
        cropper.crop_region(tmp_path / "non_existent.png", (0, 0, 50, 50), tmp_path / "out.png")
