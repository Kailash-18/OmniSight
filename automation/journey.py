"""
E-Commerce Journey Automation.
Walks the standard Products -> Cart -> Checkout journey using stable data-testid selectors.
"""

from typing import Dict, Any, List
from playwright.sync_api import Page


class StoreJourney:
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
