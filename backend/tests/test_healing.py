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
