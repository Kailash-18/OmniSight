from automation.engine import UniversalWebJourney, check_store_health, create_journey, is_mock_store


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
