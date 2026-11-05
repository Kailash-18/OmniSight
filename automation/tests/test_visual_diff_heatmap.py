"""
Unit Tests for Visual Diff Heatmap Overlays & Bounding Box Annotations.
Verifies pixel difference amplification and diagnostic annotation rendering.
"""

from pathlib import Path
from PIL import Image
import pytest

from automation.engine import VisualComparator


@pytest.fixture
def test_images(tmp_path: Path):
    img_a_path = tmp_path / "img_a.png"
    img_b_path = tmp_path / "img_b.png"

    img_a = Image.new("RGB", (400, 300), color=(255, 255, 255))
    img_b = Image.new("RGB", (400, 300), color=(255, 255, 255))

    # Add a modified red box on image B
    for x in range(100, 200):
        for y in range(50, 150):
            img_b.putpixel((x, y), (255, 0, 0))

    img_a.save(img_a_path)
    img_b.save(img_b_path)
    return img_a_path, img_b_path


def test_visual_comparator_generate_diff_heatmap(test_images, tmp_path: Path):
    img_a_path, img_b_path = test_images
    out_heatmap = tmp_path / "heatmap.png"

    comparator = VisualComparator()
    res_path = comparator.generate_diff_heatmap(img_a_path, img_b_path, out_heatmap)

    assert res_path.exists()
    with Image.open(res_path) as heat:
        assert heat.size == (400, 300)
        # Check that diff area has bright amplified pixel values
        pixel = heat.getpixel((150, 100))
        assert max(pixel) > 100


def test_visual_comparator_annotate_remediation_box(test_images, tmp_path: Path):
    img_a_path, _ = test_images
    out_annotated = tmp_path / "annotated.png"

    comparator = VisualComparator()
    res_path = comparator.annotate_remediation_bounding_box(
        img_a_path,
        bounding_box=(100, 50, 200, 150),
        output_path=out_annotated,
        label="Fixed Button",
    )

    assert res_path.exists()
    with Image.open(res_path) as ann:
        assert ann.size == (400, 300)
