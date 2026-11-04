"""
Browser Runner module for OmniSight (Team Lead Week 1 & 3 deliverable).
Provides Playwright browser automation, navigation journeys, and screenshot capture.
Re-exported from automation.engine for standard repository layout compliance.
"""

from automation.engine import (
    StoreJourney,
    attach_browser_listeners,
    check_store_health,
    create_isolated_page,
    launch_browser,
    run_visual_audit_journey,
)

__all__ = [
    "StoreJourney",
    "attach_browser_listeners",
    "check_store_health",
    "create_isolated_page",
    "launch_browser",
    "run_visual_audit_journey",
]
