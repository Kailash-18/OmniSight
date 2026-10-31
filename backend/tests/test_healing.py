"""
Unit and Integration Tests for Autonomous Self-Healing Decision Engine and PR Labeling.
"""

import pytest
from backend.app.schemas.healing_schema import (
    HealingStrategyType,
    HealingStrategyRequest,
    HealingStrategyResponse,
    PRLabelCalculationRequest,
    RollbackPreviewRequest,
)
from backend.app.services.healing_service import HealingEngine, healing_engine


def test_immediate_patch_strategy_on_zero_diff():
    """Verify that diff score <= 0.005 immediately yields IMMEDIATE_PATCH strategy."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-101", visual_diff_score=0.002, iteration_count=1)
    assert resp.strategy == HealingStrategyType.IMMEDIATE_PATCH
    assert resp.can_auto_merge is True
    assert resp.rollback_recommended is False
    assert "visually verified" in resp.action_rationale.lower()

def test_human_escalation_on_exceeded_max_retries():
    """Verify that exceeding max_retries escalates to human review with rollback recommendation."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-102", visual_diff_score=0.15, iteration_count=2, max_retries=2)
    assert resp.strategy == HealingStrategyType.HUMAN_ESCALATION
    assert resp.can_auto_merge is False
    assert resp.rollback_recommended is True
    assert "max_retries" in resp.action_rationale


def test_catastrophic_regression_triggers_rollback():
    """Verify that visual diff score > 0.40 triggers ROLLBACK_REQUIRED strategy."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-103", visual_diff_score=0.55, iteration_count=1, max_retries=3)
    assert resp.strategy == HealingStrategyType.ROLLBACK_REQUIRED
    assert resp.rollback_recommended is True
    assert "catastrophic" in resp.action_rationale.lower()


def test_iterative_refinement_within_budget():
    """Verify that minor diff within retry budget triggers ITERATIVE_REFINEMENT."""
    engine = HealingEngine()
    resp = engine.evaluate_strategy("run-104", visual_diff_score=0.08, iteration_count=1, max_retries=3)
    assert resp.strategy == HealingStrategyType.ITERATIVE_REFINEMENT
    assert resp.can_auto_merge is False
    assert resp.rollback_recommended is False
