"""Tests for SelectorSanitizer."""

import pytest
from automation.selector_utils import SelectorSanitizer


def test_prioritizes_data_testid():
    elem = {
        "tag": "button",
        "id": "btn-123",
        "attributes": {"data-testid": "submit-order-button"},
    }
    sel = SelectorSanitizer.generate_resilient_selector(elem)
    assert sel == "[data-testid='submit-order-button']"


def test_uses_id_when_no_testid():
    elem = {
        "tag": "div",
        "id": "hero-section",
        "attributes": {},
    }
    sel = SelectorSanitizer.generate_resilient_selector(elem)
    assert sel == "#hero-section"


def test_uses_aria_label():
    elem = {
        "tag": "a",
        "attributes": {"aria-label": "Close Modal"},
    }
    sel = SelectorSanitizer.generate_resilient_selector(elem)
    assert sel == "a[aria-label='Close Modal']"


def test_uses_classes():
    elem = {
        "tag": "div",
        "classes": ["card", "product-item"],
        "attributes": {},
    }
    sel = SelectorSanitizer.generate_resilient_selector(elem)
    assert sel == "div.card.product-item"
