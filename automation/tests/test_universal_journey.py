from pathlib import Path
from PIL import Image
import pytest

from automation.engine import (
    MockVLMAdapter,
    UniversalWebJourney,
    _capture_journey_screenshot,
    check_store_health,
    create_journey,
    is_mock_store,
)
from automation.interaction_check import store_pages


def test_is_mock_store_detection():
    assert is_mock_store("http://localhost:5173") is True
    assert is_mock_store("http://127.0.0.1:5174/store") is True
    assert is_mock_store("https://www.flipkart.com/") is False
    assert is_mock_store("https://staging.acme.corp/app") is False


def test_create_journey_factory(monkeypatch):
    class DummyPage:
        pass

    page = DummyPage()
    mock_j = create_journey(page, "http://localhost:5173")
    assert mock_j.__class__.__name__ == "StoreJourney"

    univ_j = create_journey(page, "https://www.flipkart.com")
    assert univ_j.__class__.__name__ == "UniversalWebJourney"


def test_universal_web_journey_steps():
    class FakePage:
        def __init__(self):
            self.calls = []

        def goto(self, url, **kw):
            self.calls.append(("goto", url))

        def wait_for_timeout(self, ms):
            self.calls.append(("wait", ms))

        def evaluate(self, script):
            self.calls.append(("eval", script))

    page = FakePage()
    journey = UniversalWebJourney(page, "https://example.com")
    journey.navigate_home()
    journey.add_product_to_cart()
    journey.navigate_to_cart()
    journey.continue_to_checkout()
    journey.fill_checkout_form()

    assert len(journey.completed_steps) == 5
    assert journey.completed_steps[0] == "navigate_home"


def test_external_site_skips_mock_store_defects_and_duplicate_pages():
    report = MockVLMAdapter().audit_viewports(
        run_id="run-ext",
        target_url="https://www.youtube.com/",
        evidence_dir=Path("."),
        screenshots=["desktop_1440x900_home.png", "mobile_375x667_checkout.png"],
        dom_snapshots=[],
    )
    assert report.findings == []
    assert report.proposed_patch is None
    pages = store_pages("https://www.youtube.com/")
    assert [name for name, _ in pages] == ["home"]


def test_universal_web_journey_retries_transient_error_and_rejects_blank_error_page():
    class FlakyThenOkPage:
        def __init__(self):
            self.attempts = 0
            self.url = "about:blank"

        def goto(self, url, **kw):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("net::ERR_NETWORK_CHANGED")
            self.url = url

        def wait_for_timeout(self, ms):
            pass

        def evaluate(self, script):
            return []

    ok_page = FlakyThenOkPage()
    journey = UniversalWebJourney(ok_page, "https://example.com")
    journey.navigate_home()
    assert ok_page.attempts == 2
    assert journey.completed_steps == ["navigate_home"]

    class AlwaysErrorPage:
        def __init__(self):
            self.attempts = 0
            self.url = "chrome-error://chromewebdata/"

        def goto(self, url, **kw):
            self.attempts += 1
            self.url = "chrome-error://chromewebdata/"

        def wait_for_timeout(self, ms):
            pass

    err_page = AlwaysErrorPage()
    failing_journey = UniversalWebJourney(err_page, "https://example.com")
    with pytest.raises(RuntimeError, match="Failed to load target website"):
        failing_journey.navigate_home()
    assert err_page.attempts == 3


def test_capture_journey_screenshot_recaptures_blank_white_external_page(tmp_path: Path):
    class PaintOnSecondShotPage:
        def __init__(self):
            self.url = "https://example.com/"
            self.shot_calls = 0

        def screenshot(self, path, **kw):
            self.shot_calls += 1
            color = (255, 255, 255) if self.shot_calls == 1 else (30, 80, 160)
            Image.new("RGB", (64, 64), color).save(path, "PNG")

        def wait_for_timeout(self, ms):
            pass

        def evaluate(self, script):
            pass

    page = PaintOnSecondShotPage()
    shot_path = tmp_path / "desktop_1440x900_home.png"
    _capture_journey_screenshot(page, shot_path, {"full_page": False}, True, "https://example.com/")
    assert page.shot_calls == 2
    with Image.open(shot_path) as img:
        assert img.getpixel((10, 10)) == (30, 80, 160)
