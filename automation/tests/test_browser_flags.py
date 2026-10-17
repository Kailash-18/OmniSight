"""Tests for BrowserFlagBuilder."""

import pytest
from automation.browser_flags import BrowserFlagBuilder


def test_default_browser_flags():
    flags = BrowserFlagBuilder.build_args(in_container=False, deterministic_fonts=True)
    assert "--no-sandbox" in flags
    assert "--disable-gpu" in flags
    assert "--font-render-hinting=none" in flags


def test_container_mode_flags():
    flags = BrowserFlagBuilder.build_args(in_container=True)
    assert "--disable-background-networking" in flags
    assert "--disable-dev-shm-usage" in flags


def test_extra_flags_deduplicated():
    flags = BrowserFlagBuilder.build_args(extra_flags=["--no-sandbox", "--custom-flag"])
    assert flags.count("--no-sandbox") == 1
    assert "--custom-flag" in flags
