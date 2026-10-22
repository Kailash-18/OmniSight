"""
Headless Browser Lifecycle Manager.
Provides context-isolated browser instances and session resource cleanup.
"""

from contextlib import contextmanager
from typing import Generator, Tuple
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
from automation.config import config
from automation.viewports import ViewportSpec


@contextmanager
def launch_browser() -> Generator[Browser, None, None]:
    """
    Launches a shared Playwright Chromium instance with standardized flags.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=config.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            yield browser
        finally:
            browser.close()


@contextmanager
def create_isolated_page(
    browser: Browser, viewport: ViewportSpec
) -> Generator[Page, None, None]:
    """
    Creates an isolated browser context per viewport run to guarantee
    zero state or cookie leakage between test executions.
    """
    context = browser.new_context(
        viewport={"width": viewport.width, "height": viewport.height},
        device_scale_factor=viewport.device_scale_factor,
        is_mobile=viewport.is_mobile,
        has_touch=viewport.has_touch,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
            if viewport.is_mobile
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    )
    context.set_default_timeout(config.action_timeout_ms)
    context.set_default_navigation_timeout(config.navigation_timeout_ms)

    page = context.new_page()
    try:
        yield page
    finally:
        page.close()
        context.close()
