import sys
import urllib.request

from playwright.sync_api import sync_playwright

# Mock store from app-under-test/ (start it with: npm run dev --prefix app-under-test)
APP_URL = "http://localhost:5173"
VIEWPORTS = {
    "desktop_1440x900": (1440, 900),
    "desktop_1280x800": (1280, 800),
    "mobile_390x844": (390, 844),
    "mobile_375x667": (375, 667),
}

# Fail fast with a clear message instead of a Playwright timeout when the store isn't running.
try:
    urllib.request.urlopen(APP_URL, timeout=3)
except OSError:
    print(f"Store not reachable at {APP_URL}. Start it first with:\n  npm run dev --prefix app-under-test")
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for name, (width, height) in VIEWPORTS.items():
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(APP_URL)
        page.get_by_test_id("add-to-cart-mug").click()
        page.get_by_test_id("cart-link").click()
        page.get_by_test_id("continue-to-checkout").click()
        page.get_by_test_id("checkout-form").wait_for()
        page.screenshot(path=f"{name}_checkout.png")
        page.close()
        print(f"Screenshot saved: {name}_checkout.png")
    browser.close()
