"""Tests for ViewportCatalog and DevicePreset."""

import pytest
from automation.viewport_presets import ViewportCatalog, DevicePreset


def test_viewport_catalog_lookup():
    preset = ViewportCatalog.get_preset("desktop_1440x900")
    assert preset is not None
    assert preset.width == 1440
    assert preset.height == 900
    assert preset.category == "desktop"
    assert preset.is_mobile is False

    mobile = ViewportCatalog.get_preset("mobile_375x667")
    assert mobile is not None
    assert mobile.is_mobile is True
    assert mobile.has_touch is True


def test_viewport_catalog_categories():
    mobiles = ViewportCatalog.list_presets_by_category("mobile")
    assert len(mobiles) >= 2
    assert all(m.category == "mobile" for m in mobiles)

    d = mobiles[0].to_viewport_dict()
    assert "deviceScaleFactor" in d
