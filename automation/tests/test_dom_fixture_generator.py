"""Tests for DOMFixtureGenerator."""

import pytest
from automation.dom_fixture_generator import DOMFixtureGenerator


def test_clean_fixture_generation():
    dom = DOMFixtureGenerator.create_ecommerce_page(
        include_overlap=False, include_obstruction=False, include_a11y_violations=False
    )
    assert dom["tag"] == "html"
    assert len(dom["children"]) == 2
    header = dom["children"][0]
    assert header["id"] == "site-header"
    h1 = header["children"][0]
    assert h1["rect"]["y"] == 20


def test_anomalous_fixture_generation():
    dom = DOMFixtureGenerator.create_ecommerce_page(
        include_overlap=True, include_obstruction=True, include_a11y_violations=True
    )
    header = dom["children"][0]
    assert header["children"][0]["rect"]["y"] == 60
    main = dom["children"][1]
    banner = main["children"][0]
    assert banner["rect"]["width"] == 400
    button = main["children"][1]
    assert button["attributes"]["data-testid"] == "btn-unlabeled"
    img = main["children"][2]
    assert "alt" not in img["attributes"]
