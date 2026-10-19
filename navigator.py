from playwright.sync_api import sync_playwright

# Mock store from app-under-test/ (start it with: npm run dev --prefix app-under-test)
APP_URL = "http://localhost:5173"
VIEWPORTS = {"desktop": (1280, 800), "mobile": (375, 667)}

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
