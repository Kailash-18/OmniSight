# -*- coding: utf-8 -*-
"""
Unit Test Suite for OmniSight Visual Defect Flakiness Detection & Quarantine Manager.
Verifies statistical flakiness formulas, observation recording, and quarantine lifecycles.
"""

import pytest
from app.services.flakiness_service import (
    calculate_flakiness_score,
    record_defect_observation,
    quarantine_defect,
    unquarantine_defect,
    is_defect_quarantined,
    get_quarantined_defects,
    get_flakiness_report,
    reset_flakiness_tracker,
)


@pytest.fixture(autouse=True)
def clean_flakiness_store():
    """Ensure in-memory flakiness store is clean before and after each test."""
    reset_flakiness_tracker()
    yield
    reset_flakiness_tracker()


def test_calculate_flakiness_score_boundary_conditions():
    """Verify single observation or zero observations produce zero flakiness."""
    assert calculate_flakiness_score(0, 0) == 0.0
    assert calculate_flakiness_score(1, 1) == 0.0
    assert calculate_flakiness_score(1, 0) == 0.0


def test_calculate_flakiness_deterministic_vs_flaky():
    """Verify deterministic defects score 0.0 while 50% intermittency scores 1.0."""
    # 10 detections out of 10 runs = 100% reproducible -> 0.0 flakiness
    assert calculate_flakiness_score(10, 10) == 0.0
    # 0 detections out of 10 runs = 0.0 flakiness
    assert calculate_flakiness_score(10, 0) == 0.0
    # 5 detections out of 10 runs = highly erratic -> 1.0 flakiness
    assert calculate_flakiness_score(10, 5) == 1.0
    # 8 detections out of 10 runs = slight flakiness
    score = calculate_flakiness_score(10, 8)
    assert 0.6 <= score <= 0.7


def test_record_defect_observation_lifecycle():
    """Verify progressive observation updates compute and store flakiness score."""
    fp = "dfp-test-button-overlap"
    r1 = record_defect_observation(fp, detected=True, target_element="button.primary", category="element_overlap")
    assert r1["total_observations"] == 1
    assert r1["defect_occurrences"] == 1
    assert r1["flakiness_score"] == 0.0

    # Second run: defect not detected -> flakiness jumps
    r2 = record_defect_observation(fp, detected=False)
    assert r2["total_observations"] == 2
    assert r2["defect_occurrences"] == 1
    assert r2["flakiness_score"] == 1.0


def test_quarantine_defect_flow():
    """Verify placing a defect into quarantine sets timestamp, reason, and status."""
    fp = "dfp-carousel-animation"
    assert not is_defect_quarantined(fp)

    res = quarantine_defect(fp, reason="CSS transition timing instability", quarantined_by="qa-lead")
    assert res["is_quarantined"] is True
    assert res["quarantine_reason"] == "CSS transition timing instability"
    assert is_defect_quarantined(fp) is True


def test_unquarantine_defect_flow():
    """Verify unquarantining clears the flag and returns True."""
    fp = "dfp-intermittent-banner"
    quarantine_defect(fp, reason="Font loading lag")
    assert is_defect_quarantined(fp) is True

    unquarantined = unquarantine_defect(fp)
    assert unquarantined is True
    assert is_defect_quarantined(fp) is False

    # Second call returns False because already unquarantined
    assert unquarantine_defect(fp) is False


def test_get_quarantined_defects_and_flakiness_report():
    """Verify system report correctly aggregates totals, quarantine lists, and high-flakiness counts."""
    # Setup 1 stable defect
    for _ in range(5):
        record_defect_observation("dfp-stable", detected=True)

    # Setup 1 highly flaky defect (3/6 detected)
    for i in range(6):
        record_defect_observation("dfp-flaky", detected=(i % 2 == 0))

    # Quarantine the flaky defect
    quarantine_defect("dfp-flaky", reason="Animation jitter")

    quarantined_list = get_quarantined_defects()
    assert len(quarantined_list) == 1
    assert quarantined_list[0]["fingerprint"] == "dfp-flaky"

    report = get_flakiness_report()
    assert report["total_tracked_defects"] == 2
    assert report["quarantined_count"] == 1
    assert report["high_flakiness_count"] == 1


def test_reset_flakiness_tracker():
    """Verify reset clears in-memory state completely."""
    record_defect_observation("dfp-sample", detected=True)
    quarantine_defect("dfp-sample", reason="testing")
    assert len(get_quarantined_defects()) == 1

    reset_flakiness_tracker()
    assert len(get_quarantined_defects()) == 0
    assert get_flakiness_report()["total_tracked_defects"] == 0
