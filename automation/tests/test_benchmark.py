"""Tests for EngineBenchmarkSuite."""

import pytest
from automation.benchmark import EngineBenchmarkSuite


def test_spatial_benchmark_runs():
    res = EngineBenchmarkSuite.run_spatial_benchmark(iterations=100)
    assert res["iterations"] == 100
    assert res["intersections_detected"] == 100
    assert res["average_iou"] > 0
    assert res["ops_per_sec"] > 0


def test_contrast_benchmark_runs():
    res = EngineBenchmarkSuite.run_contrast_benchmark(iterations=50)
    assert res["iterations"] == 50
    assert res["ops_per_sec"] > 0


def test_benchmark_run_all():
    summary = EngineBenchmarkSuite.run_all()
    assert summary["benchmark_status"] == "optimal"
    assert "spatial_engine" in summary
    assert "contrast_engine" in summary
