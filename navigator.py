from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 375, "height": 667})
    page.goto("file://" + os.path.abspath("index.html"))
    page.screenshot(path="mobile_checkout.png")
    browser.close()
print("Screenshot saved")