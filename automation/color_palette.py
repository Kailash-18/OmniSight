"""Color representation parser and palette utility for visual QA.

Normalizes Hex, RGB, RGBA, and standard CSS color names into RGBA tuples
and provides alpha-compositing utilities for background contrast calculations.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


class ColorParser:
    """Parses arbitrary CSS color strings into normalized (R, G, B, A) float tuples (0.0 - 1.0)."""

    _NAMED_COLORS = {
        "white": (1.0, 1.0, 1.0, 1.0),
        "black": (0.0, 0.0, 0.0, 1.0),
        "transparent": (0.0, 0.0, 0.0, 0.0),
        "red": (1.0, 0.0, 0.0, 1.0),
        "green": (0.0, 0.5, 0.0, 1.0),
        "blue": (0.0, 0.0, 1.0, 1.0),
    }

    @classmethod
    def parse(cls, color_str: str) -> Optional[Tuple[float, float, float, float]]:
        if not color_str:
            return None
        c = color_str.strip().lower()

        if c in cls._NAMED_COLORS:
            return cls._NAMED_COLORS[c]

        # Hex 3 or 6 digits
        if c.startswith("#"):
            hex_part = c[1:]
            if len(hex_part) == 3:
                r = int(hex_part[0] * 2, 16) / 255.0
                g = int(hex_part[1] * 2, 16) / 255.0
                b = int(hex_part[2] * 2, 16) / 255.0
                return (r, g, b, 1.0)
            elif len(hex_part) == 6:
                r = int(hex_part[0:2], 16) / 255.0
                g = int(hex_part[2:4], 16) / 255.0
                b = int(hex_part[4:6], 16) / 255.0
                return (r, g, b, 1.0)

        # rgb(r, g, b) or rgba(r, g, b, a)
        match = re.match(r"^rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)$", c)
        if match:
            r = int(match.group(1)) / 255.0
            g = int(match.group(2)) / 255.0
            b = int(match.group(3)) / 255.0
            a = float(match.group(4)) if match.group(4) is not None else 1.0
            return (r, g, b, min(1.0, max(0.0, a)))

        return None

    @classmethod
    def composite_over(
        cls, fg: Tuple[float, float, float, float], bg: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float]:
        """Alpha-composites foreground over background (Porter-Duff source over)."""
        fg_r, fg_g, fg_b, fg_a = fg
        bg_r, bg_g, bg_b, _ = bg

        out_r = fg_r * fg_a + bg_r * (1.0 - fg_a)
        out_g = fg_g * fg_a + bg_g * (1.0 - fg_a)
        out_b = fg_b * fg_a + bg_b * (1.0 - fg_a)
        return (round(out_r, 4), round(out_g, 4), round(out_b, 4))
