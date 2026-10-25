"""
OmniSight Browser Automation & Multi-Page Journey Engine.
Coordinates headless Playwright execution, health checking, responsive viewport isolation,
runtime error listening, user journeys, and screenshot/DOM artifact generation.
"""

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple
import urllib.error
import urllib.request

from playwright.sync_api import Browser, ConsoleMessage, Page, Request, sync_playwright

from automation.config import STANDARD_VIEWPORTS, ViewportSpec, config
from automation.evidence import EvidenceCollector, extract_dom_context


def check_store_health(
    app_url: str = "http://127.0.0.1:5173", timeout: float = 1.5
) -> Tuple[bool, str, Optional[str]]:
    """
    Validates if the target URL is running and is verified as the everyday. store.

    Returns:
        (is_healthy, message, detected_url)
    """
    candidate_urls = [app_url]
    if "localhost" in app_url:
        candidate_urls.append(app_url.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in app_url:
        candidate_urls.append(app_url.replace("127.0.0.1", "localhost"))

    base_candidates = list(candidate_urls)
    for u in base_candidates:
        if "5173" in u:
            candidate_urls.extend([
                u.replace("5173", "5174"),
                u.replace("5173", "5175"),
            ])

    seen = set()
    unique_candidates = []
    for u in candidate_urls:
        if u not in seen:
            seen.add(u)
            unique_candidates.append(u)

    for url in unique_candidates:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OmniSight-HealthCheck/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    content = response.read(4096).decode("utf-8", errors="ignore")
                    if "everyday" in content.lower() or "root" in content.lower():
                        return True, f"Store verified and healthy at {url}", url
        except (urllib.error.URLError, OSError):
            continue

    return (
        False,
        f"Mock store not reachable at {app_url}. Start it with:\n  npm run dev --prefix app-under-test",
        None,
    )


@contextmanager
def launch_browser() -> Generator[Browser, None, None]:
    """Launches a shared Playwright Chromium instance with standardized flags."""
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


def attach_browser_listeners(page: Page, evidence: EvidenceCollector) -> None:
    """
    Hooks page console messages, uncaught exceptions, and network request failures
    into the evidence collection stream.
    """
    def on_console(msg: ConsoleMessage):
        if msg.type in ("error", "warning"):
            evidence.record_console_log(
                level=msg.type,
                message=msg.text,
                url=page.url
            )

    def on_page_error(exc):
        evidence.record_console_log(
            level="uncaught_exception",
            message=str(exc),
            url=page.url
        )

    def on_request_failed(request: Request):
        failure = request.failure
        evidence.record_console_log(
            level="request_failed",
            message=f"{request.method} {request.url} failed: {failure}",
            url=page.url
        )

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)


class StoreJourney:
    """Walks the standard Products -> Cart -> Checkout journey using stable data-testid selectors."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.completed_steps: List[str] = []

    def navigate_home(self) -> None:
        """Navigates to the product catalog and waits for the hero title."""
        self.page.goto(self.base_url, wait_until="networkidle")
        self.page.get_by_test_id("hero-title").wait_for(state="visible")
        self.page.get_by_test_id("product-list").wait_for(state="visible")
        self.completed_steps.append("navigate_home")

    def add_product_to_cart(self, product_id: str = "mug") -> None:
        """Adds a specific product to the cart and verifies the cart badge."""
        btn = self.page.get_by_test_id(f"add-to-cart-{product_id}")
        btn.click()
        self.page.get_by_test_id("cart-count").wait_for(state="visible")
        self.completed_steps.append(f"add_product_{product_id}")

    def navigate_to_cart(self) -> None:
        """Navigates to the shopping cart review page."""
        self.page.get_by_test_id("cart-link").click()
        self.page.get_by_test_id("cart-summary").wait_for(state="visible")
        self.completed_steps.append("navigate_to_cart")

    def continue_to_checkout(self) -> None:
        """Proceeds from the cart summary to the checkout form."""
        self.page.get_by_test_id("continue-to-checkout").click()
        self.page.get_by_test_id("checkout-form").wait_for(state="visible")
        self.completed_steps.append("continue_to_checkout")

    def fill_checkout_form(
        self,
        name: str = "Demo Tester",
        email: str = "demo@omnisight.ai",
        address: str = "100 AI Automation Way, Staging Suite 400"
    ) -> None:
        """Fills checkout details with synthetic test data."""
        self.page.get_by_test_id("input-name").fill(name)
        self.page.get_by_test_id("input-email").fill(email)
        self.page.get_by_test_id("input-address").fill(address)
        self.completed_steps.append("fill_checkout_form")


def run_visual_audit_journey(
    app_url: Optional[str] = None,
    viewports: Optional[List[str]] = None,
    evidence: Optional[EvidenceCollector] = None,
    scenario: str = "checkout_flow",
) -> Dict[str, Any]:
    """
    Executes the full e-commerce journey across all target viewports,
    capturing visual screenshots and DOM trees at every key step.
    """
    target_url = app_url or config.app_url

    healthy, msg, verified_url = check_store_health(target_url)
    if not healthy:
        raise RuntimeError(msg)

    active_url = verified_url or target_url
    collector = evidence or EvidenceCollector()

    selected_viewports: List[ViewportSpec] = []
    if viewports:
        for vp_name in viewports:
            if vp_name in STANDARD_VIEWPORTS:
                selected_viewports.append(STANDARD_VIEWPORTS[vp_name])
    if not selected_viewports:
        selected_viewports = list(STANDARD_VIEWPORTS.values())

    results: Dict[str, Any] = {
        "run_id": collector.run_id,
        "target_url": active_url,
        "scenario": scenario,
        "viewports_evaluated": [v.name for v in selected_viewports],
        "screenshots": [],
        "dom_snapshots": [],
        "steps_completed": [],
    }

    with launch_browser() as browser:
        for vp in selected_viewports:
            with create_isolated_page(browser, vp) as page:
                attach_browser_listeners(page, collector)
                journey = StoreJourney(page, active_url)

                journey.navigate_home()
                home_shot = collector.get_screenshot_path(vp.name, "home")
                page.screenshot(path=str(home_shot), full_page=False)
                collector.save_dom_snapshot(vp.name, "home", extract_dom_context(page))
                results["screenshots"].append(str(home_shot))

                journey.add_product_to_cart("mug")
                journey.navigate_to_cart()
                cart_shot = collector.get_screenshot_path(vp.name, "cart")
                page.screenshot(path=str(cart_shot), full_page=False)
                collector.save_dom_snapshot(vp.name, "cart", extract_dom_context(page))
                results["screenshots"].append(str(cart_shot))

                journey.continue_to_checkout()
                journey.fill_checkout_form()
                checkout_shot = collector.get_screenshot_path(vp.name, "checkout")
                page.screenshot(path=str(checkout_shot), full_page=False)
                collector.save_dom_snapshot(vp.name, "checkout", extract_dom_context(page))
                results["screenshots"].append(str(checkout_shot))

                results["steps_completed"] = journey.completed_steps

    collector.save_console_logs()
    collector.save_manifest(results)
    return results
