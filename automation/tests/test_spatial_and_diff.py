"""
Tests for Spatial Geometry Analyzer and Visual Comparator.
Verifies collision detection, viewport clipping, and pixel delta calculations.
"""

from pathlib import Path
import json
import pytest
from PIL import Image

from automation.spatial_analyzer import (
    BoundingBox,
    SpatialAnalyzer,
    SpatialAnomaly,
    AnomalyType,
)
from automation.visual_diff import VisualComparator
from automation.schemas import DefectCategory, Severity


def test_bounding_box_geometry():
    box_a = BoundingBox(x=10, y=10, width=100, height=50)
    box_b = BoundingBox(x=60, y=30, width=100, height=50)
    box_disjoint = BoundingBox(x=200, y=200, width=50, height=50)

    assert box_a.area == 5000
    assert box_a.right == 110
    assert box_a.bottom == 60

    assert box_a.intersects(box_b) is True
    assert box_a.intersects(box_disjoint) is False

    inter = box_a.intersection(box_b)
    assert inter is not None
    assert inter.x == 60
    assert inter.y == 30
    assert inter.width == 50
    assert inter.height == 30

    assert box_a.iou(box_b) > 0.1
    assert box_a.iou(box_disjoint) == 0.0


def test_spatial_analyzer_viewport_clipping():
    analyzer = SpatialAnalyzer()
    snapshot = {
        "viewport": {"width": 375, "height": 667},
        "elements": [
            {
                "tag": "button",
                "test_id": "continue-to-checkout",
                "box": {"x": 20, "y": 400, "width": 460, "height": 48},
            }
        ],
    }

    anomalies = analyzer.analyze_dom_snapshot(snapshot)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.VIEWPORT_CLIPPING
    assert anomalies[0].metadata["overflow_pixels"] == 105


def test_spatial_analyzer_action_occlusion():
    analyzer = SpatialAnalyzer()
    snapshot = {
        "viewport": {"width": 1280, "height": 800},
        "elements": [
            {
                "tag": "button",
                "test_id": "submit-order",
                "box": {"x": 100, "y": 200, "width": 200, "height": 50},
            },
            {
                "tag": "div",
                "test_id": "promo-banner",
                "box": {"x": 100, "y": 200, "width": 200, "height": 50},
            },
        ],
    }

    anomalies = analyzer.analyze_dom_snapshot(snapshot)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.ACTION_OCCLUSION
    assert anomalies[0].severity == "critical"
    assert anomalies[0].metadata["action_test_id"] == "submit-order"


def test_spatial_analyzer_heading_collision():
    analyzer = SpatialAnalyzer()
    snapshot = {
        "viewport": {"width": 1440, "height": 900},
        "elements": [
            {
                "tag": "h1",
                "test_id": "hero-title",
                "classes": ["hero-title"],
                "box": {"x": 100, "y": 50, "width": 600, "height": 100},
            },
            {
                "tag": "div",
                "test_id": "product-card-1",
                "classes": ["product-card"],
                "box": {"x": 100, "y": 110, "width": 300, "height": 200},
            },
        ],
    }

    anomalies = analyzer.analyze_dom_snapshot(snapshot)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.ELEMENT_COLLISION
    assert anomalies[0].metadata["vertical_overlap_px"] == 40


def test_visual_comparator_identical_and_different(tmp_path: Path):
    comparator = VisualComparator(tolerance=10)

    img_a_path = tmp_path / "img_a.png"
    img_b_path = tmp_path / "img_b.png"
    diff_path = tmp_path / "diff.png"

    img_a = Image.new("RGB", (200, 200), (255, 255, 255))
    img_a.save(img_a_path)

    identical_result = comparator.compare_images(img_a_path, img_a_path)
    assert identical_result.is_identical is True
    assert identical_result.diff_pixels == 0

    img_b = Image.new("RGB", (200, 200), (255, 255, 255))
    for x in range(50, 100):
        for y in range(50, 100):
            img_b.putpixel((x, y), (0, 0, 0))
    img_b.save(img_b_path)

    diff_result = comparator.compare_images(img_a_path, img_b_path, diff_output_path=diff_path)
    assert diff_result.is_identical is False
    assert diff_result.diff_pixels == 2500
    assert diff_result.mismatch_percentage > 0
    assert diff_path.exists()


def test_visual_comparator_annotation(tmp_path: Path):
    comparator = VisualComparator()
    base_img_path = tmp_path / "screenshot.png"
    annotated_path = tmp_path / "annotated.png"

    img = Image.new("RGB", (400, 400), (240, 240, 240))
    img.save(base_img_path)

    boxes = [{"box": {"x": 50, "y": 50, "width": 100, "height": 50}}]
    out = comparator.annotate_defects(base_img_path, boxes, annotated_path)

    assert out.exists()
    with Image.open(out) as res:
        assert res.size == (400, 400)


def test_spatial_analyzer_dom_file_and_to_findings(tmp_path: Path):
    analyzer = SpatialAnalyzer()
    dom_file = tmp_path / "desktop_1440x900_home_dom.json"

    dom_data = {
        "viewport": {"width": 1440, "height": 900},
        "elements": [
            {
                "tag": "h1",
                "test_id": "hero-title",
                "classes": ["hero-title"],
                "box": {"x": 100, "y": 50, "width": 600, "height": 100},
            },
            {
                "tag": "div",
                "test_id": "product-card-1",
                "classes": ["product-card"],
                "box": {"x": 100, "y": 110, "width": 300, "height": 200},
            },
        ],
    }

    with open(dom_file, "w", encoding="utf-8") as f:
        json.dump(dom_data, f)

    anomalies = analyzer.analyze_dom_file(dom_file)
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == AnomalyType.ELEMENT_COLLISION

    findings = analyzer.to_findings(anomalies, viewport_name="desktop_1440x900")
    assert len(findings) == 1
    assert findings[0].category == DefectCategory.ELEMENT_OVERLAP
    assert findings[0].severity == Severity.HIGH
    assert findings[0].viewport == "desktop_1440x900"
    assert "hero-title" in findings[0].target_element


def test_visual_comparator_annotate_anomalies(tmp_path: Path):
    comparator = VisualComparator()
    base_img_path = tmp_path / "screenshot.png"
    annotated_path = tmp_path / "annotated.png"

    img = Image.new("RGB", (500, 500), (245, 245, 245))
    img.save(base_img_path)

    anomaly = SpatialAnomaly(
        anomaly_type=AnomalyType.ELEMENT_COLLISION,
        severity="high",
        primary_element={"tag": "h1", "test_id": "hero-title"},
        intersection_box=BoundingBox(x=50, y=50, width=150, height=80),
        overlap_percentage=45.0,
        description="Collision detected",
    )

    out = comparator.annotate_anomalies(base_img_path, [anomaly], annotated_path)
    assert out.exists()
    with Image.open(out) as res:
        assert res.size == (500, 500)


def test_orchestrator_enrich_with_spatial_analysis(tmp_path: Path):
    from automation.orchestrator import Orchestrator
    from automation.evidence import EvidenceCollector
    from automation.schemas import VisualAuditReport

    orchestrator = Orchestrator()
    evidence = EvidenceCollector(run_id="test-spatial-enrich")
    evidence.run_dir = tmp_path
    evidence.annotated_dir = tmp_path / "annotated"
    evidence.annotated_dir.mkdir(parents=True, exist_ok=True)

    shot_path = tmp_path / "mobile_375x667_cart.png"
    img = Image.new("RGB", (375, 667), (255, 255, 255))
    img.save(shot_path)

    dom_path = tmp_path / "mobile_375x667_cart_dom.json"
    dom_data = {
        "viewport": {"width": 375, "height": 667},
        "elements": [
            {
                "tag": "button",
                "test_id": "continue-to-checkout",
                "box": {"x": 20, "y": 400, "width": 460, "height": 48},
            }
        ],
    }
    with open(dom_path, "w", encoding="utf-8") as f:
        json.dump(dom_data, f)

    audit_report = VisualAuditReport(
        run_id="test-spatial-enrich",
        target_url="http://127.0.0.1:5173",
        findings=[],
        summary="Initial audit",
    )

    run_results = {
        "screenshots": [str(shot_path)],
        "dom_snapshots": [str(dom_path)],
    }

    enriched = orchestrator._enrich_with_spatial_analysis(
        audit_report=audit_report,
        evidence=evidence,
        run_results=run_results,
    )

    assert len(enriched.findings) >= 1
    assert any(f.category == DefectCategory.ELEMENT_CLIPPING for f in enriched.findings)
    assert len(enriched.annotated_screenshots) == 1
    assert Path(enriched.annotated_screenshots[0]).exists()

