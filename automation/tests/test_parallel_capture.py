"""
Unit Tests for Asynchronous Parallel Multi-Viewport Capture.
Verifies thread-pool parallelization, viewport filtering, and multi-shot aggregation.
"""

from unittest.mock import MagicMock, patch
from automation.engine import run_parallel_viewports
from automation.core import EvidenceCollector


def test_parallel_viewports_mocked_execution(tmp_path):
    collector = EvidenceCollector(run_id="test-parallel-run")

    with patch("automation.engine.check_store_health", return_value=(True, "OK", "http://127.0.0.1:5173")), \
         patch("automation.engine.launch_browser") as mock_launch, \
         patch("automation.engine.create_isolated_page") as mock_page, \
         patch("automation.engine.attach_browser_listeners"), \
         patch("automation.engine.StoreJourney") as mock_journey_cls, \
         patch("automation.engine.extract_dom_context", return_value=[]), \
         patch.object(collector, "save_console_logs"), \
         patch.object(collector, "save_manifest"), \
         patch.object(collector, "save_dom_snapshot"):

        mock_page_inst = MagicMock()
        mock_page.return_value.__enter__.return_value = mock_page_inst
        mock_journey_inst = MagicMock()
        mock_journey_cls.return_value = mock_journey_inst

        results = run_parallel_viewports(
            app_url="http://127.0.0.1:5173",
            viewports=["desktop_1440x900", "mobile_375x667"],
            evidence=collector,
            max_workers=2,
        )

        assert results["parallel_execution"] is True
        assert "desktop_1440x900" in results["viewports_evaluated"]
        assert "mobile_375x667" in results["viewports_evaluated"]
        assert len(results["screenshots"]) == 6
