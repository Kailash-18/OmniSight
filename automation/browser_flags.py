"""Headless Chromium browser launch flag builder for OmniSight.

Constructs safe container flags, memory optimization arguments, and deterministic
font antialiasing settings for reproducible multi-viewport visual audits.
"""

from __future__ import annotations

from typing import List


class BrowserFlagBuilder:
    """Configures Chromium command-line switches for headless visual QA."""

    DEFAULT_SECURITY_FLAGS: List[str] = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]

    DETERMINISTIC_RENDERING_FLAGS: List[str] = [
        "--font-render-hinting=none",
        "--disable-skia-runtime-opts",
        "--disable-font-subpixel-positioning",
        "--disable-lcd-text",
        "--disable-smooth-scrolling",
    ]

    @classmethod
    def build_args(
        cls,
        in_container: bool = False,
        deterministic_fonts: bool = True,
        extra_flags: List[str] | None = None,
    ) -> List[str]:
        args = list(cls.DEFAULT_SECURITY_FLAGS)
        if in_container:
            args.extend(["--disable-background-networking", "--disable-breakpad"])
        if deterministic_fonts:
            args.extend(cls.DETERMINISTIC_RENDERING_FLAGS)
        if extra_flags:
            args.extend(extra_flags)
        # Deduplicate while preserving order
        seen = set()
        out = []
        for a in args:
            if a not in seen:
                seen.add(a)
                out.append(a)
        return out
