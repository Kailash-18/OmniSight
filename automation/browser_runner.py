"""
Multi-Page Responsive Screenshot Capture Engine.
Coordinates viewport matrices, browser journeys, and artifact generation.
"""

from typing import Dict, Any, List, Optional
from automation.config import config
from automation.viewports import STANDARD_VIEWPORTS, ViewportSpec
from automation.health_check import check_store_health
from automation.browser import launch_browser, create_isolated_page
from automation.logger import attach_browser_listeners
from automation.journey import StoreJourney
from automation.dom_extractor import extract_dom_context
from automation.evidence import EvidenceCollector


def run_visual_audit_journey(
    app_url: Optional[str] = None,
    viewports: Optional[List[str]] = None,
    evidence: Optional[EvidenceCollector] = None,
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
