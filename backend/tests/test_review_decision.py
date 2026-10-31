# -*- coding: utf-8 -*-
"""
Unit tests for Human-in-the-Loop QA Review Decision Engine.
Verifies approval, rejection, changes requested, lead override, and audit trail persistence.
"""

import pytest

from backend.app.services.review_engine import (
    record_review_decision,
    record_lead_override,
    get_review_trail,
    clear_reviews_db,
)


@pytest.fixture(autouse=True)
def setup_review_tests():
    clear_reviews_db()


def test_record_review_decision_approval():
    runs_db = {
        "run-rev-01": {"run_id": "run-rev-01", "status": "needs_review", "timeline": []}
    }

    record = record_review_decision(
        run_id="run-rev-01",
        reviewer_id="qa-engineer-alice",
        decision="approved",
        comments="Visual fix verified on mobile and desktop viewports.",
        auto_merge_authorized=True,
        runs_db=runs_db
    )

    assert record["decision_id"].startswith("rev-")
    assert record["decision"] == "approved"
    assert record["auto_merge_authorized"] is True
    assert runs_db["run-rev-01"]["status"] == "fixed"
    assert runs_db["run-rev-01"]["review_status"] == "approved"


def test_record_review_decision_rejection():
    runs_db = {
        "run-rev-02": {"run_id": "run-rev-02", "status": "audited", "timeline": []}
    }

    record = record_review_decision(
        run_id="run-rev-02",
        reviewer_id="qa-lead-bob",
        decision="rejected",
        comments="Button fix introduces secondary overlap on tablet viewport.",
        runs_db=runs_db
    )

    assert record["decision"] == "rejected"
    assert runs_db["run-rev-02"]["status"] == "failed"
    assert runs_db["run-rev-02"]["review_status"] == "rejected"


def test_record_review_decision_changes_requested():
    runs_db = {
        "run-rev-03": {"run_id": "run-rev-03", "status": "audited", "timeline": []}
    }

    record = record_review_decision(
        run_id="run-rev-03",
        reviewer_id="qa-reviewer-carol",
        decision="changes_requested",
        comments="Please increase margin-bottom to 16px instead of 8px.",
        runs_db=runs_db
    )

    assert record["decision"] == "changes_requested"
    assert runs_db["run-rev-03"]["status"] == "needs_review"


def test_record_lead_override():
    runs_db = {
        "run-rev-04": {"run_id": "run-rev-04", "status": "needs_review", "timeline": []}
    }

    record = record_lead_override(
        run_id="run-rev-04",
        lead_reviewer_id="qa-director-dan",
        override_reason="Expediting checkout release hotfix ahead of flash sale.",
        acknowledged_risks=["large_diff", "quarantined_defect"],
        runs_db=runs_db
    )

    assert record["decision"] == "override"
    assert record["auto_merge_authorized"] is True
    assert "large_diff" in record["risk_acknowledgement"]
    assert runs_db["run-rev-04"]["status"] == "fixed"
    assert runs_db["run-rev-04"]["review_status"] == "lead_override"


def test_invalid_decision_raises():
    with pytest.raises(ValueError, match="Invalid decision"):
        record_review_decision(
            run_id="r1",
            reviewer_id="user1",
            decision="unsupported_decision",
            comments="Valid comments here."
        )


def test_short_comments_raises():
    with pytest.raises(ValueError, match="at least 5 characters"):
        record_review_decision(
            run_id="r1",
            reviewer_id="user1",
            decision="approved",
            comments="ok"
        )


def test_empty_reviewer_raises():
    with pytest.raises(ValueError, match="Reviewer ID cannot be empty"):
        record_review_decision(
            run_id="r1",
            reviewer_id="   ",
            decision="approved",
            comments="Valid comment here."
        )


def test_get_review_trail_ordering():
    runs_db = {"r-trail": {"run_id": "r-trail", "timeline": []}}

    record_review_decision("r-trail", "rev1", "changes_requested", "Change margin to 12px", runs_db=runs_db)
    record_review_decision("r-trail", "rev2", "approved", "Updated patch verified perfectly", runs_db=runs_db)

    trail = get_review_trail("r-trail")
    assert len(trail) == 2
    assert trail[0]["decision"] == "changes_requested"
    assert trail[1]["decision"] == "approved"


def test_get_review_by_id_and_counts():
    from backend.app.services.review_engine import get_review_by_id, count_reviews_by_decision

    runs_db = {"r-stat": {"run_id": "r-stat", "timeline": []}}
    r1 = record_review_decision("r-stat", "rev1", "changes_requested", "Change padding", runs_db=runs_db)
    r2 = record_review_decision("r-stat", "rev2", "approved", "Approved now", runs_db=runs_db)

    found = get_review_by_id("r-stat", r1["decision_id"])
    assert found is not None
    assert found["decision"] == "changes_requested"

    not_found = get_review_by_id("r-stat", "nonexistent-id")
    assert not_found is None

    counts = count_reviews_by_decision("r-stat")
    assert counts["changes_requested"] == 1
    assert counts["approved"] == 1
