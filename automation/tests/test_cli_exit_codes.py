"""
Unit tests for Automation CLI process exit code behavior.
Verifies that completed visual audits return 0 (success) across all audit states
and return 1 only on actual runtime failures.
"""

from unittest.mock import MagicMock, patch
import pytest

from automation.orchestrator import main


def test_cli_exit_zero_on_audited():
    with patch("automation.orchestrator.Orchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch.run_full_remediation_loop.return_value = {
            "status": "audited",
            "findings": [{"id": "f-1", "category": "element_overlap", "severity": "medium", "viewport": "desktop_1440x900", "description": "test", "suggested_change": "fix"}],
            "run_id": "test-run-1",
        }
        mock_orch_cls.return_value = mock_orch
        code = main(["--target", "http://localhost:5173", "--no-retest", "--json-output"])
        assert code == 0


def test_cli_exit_zero_on_needs_review():
    with patch("automation.orchestrator.Orchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch.run_full_remediation_loop.return_value = {
            "status": "needs_review",
            "findings": [{"id": "f-2", "category": "element_clipping", "severity": "high", "viewport": "mobile_375x667", "description": "test", "suggested_change": "fix"}],
            "run_id": "test-run-2",
        }
        mock_orch_cls.return_value = mock_orch
        code = main(["--target", "http://localhost:5173", "--no-retest", "--json-output"])
        assert code == 0


def test_cli_exit_zero_on_fixed():
    with patch("automation.orchestrator.Orchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch.run_full_remediation_loop.return_value = {
            "status": "fixed",
            "findings": [],
            "run_id": "test-run-3",
        }
        mock_orch_cls.return_value = mock_orch
        code = main(["--target", "http://localhost:5173", "--json-output"])
        assert code == 0


def test_cli_exit_one_on_failed():
    with patch("automation.orchestrator.Orchestrator") as mock_orch_cls:
        mock_orch = MagicMock()
        mock_orch.run_full_remediation_loop.return_value = {
            "status": "failed",
            "error": "Target host unreachable",
            "run_id": "test-run-4",
        }
        mock_orch_cls.return_value = mock_orch
        code = main(["--target", "http://invalid-unreachable-domain-xyz.local", "--json-output"])
        assert code == 1
