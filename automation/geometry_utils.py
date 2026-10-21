"""Layout coordinate transformer and subpixel bounding box normalizer.

Converts between CSS logical coordinates and device hardware pixel coordinates,
ensuring consistent boundary arithmetic across high-DPI displays.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class PixelRect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


class GeometryTransformer:
    """Transforms and normalizes bounding boxes across device pixel ratios."""

    @staticmethod
    def normalize_subpixel_box(raw_box: Dict[str, Any]) -> PixelRect:
        """Rounds subpixel coordinates to outer bounding integers (floor start, ceil dimensions)."""
        x = float(raw_box.get("x", 0.0))
        y = float(raw_box.get("y", 0.0))
        w = float(raw_box.get("width", 0.0))
        h = float(raw_box.get("height", 0.0))

        int_x = math.floor(x)
        int_y = math.floor(y)
        int_w = math.ceil(x + w) - int_x
        int_h = math.ceil(y + h) - int_y

        return PixelRect(x=int_x, y=int_y, width=max(0, int_w), height=max(0, int_h))

    @staticmethod
    def scale_to_device_pixels(rect: PixelRect, scale_factor: float) -> PixelRect:
        """Scales a logical CSS pixel rectangle to physical device pixels."""
        if scale_factor <= 0.0:
            scale_factor = 1.0
        return PixelRect(
            x=math.floor(rect.x * scale_factor),
            y=math.floor(rect.y * scale_factor),
            width=math.ceil(rect.width * scale_factor),
            height=math.ceil(rect.height * scale_factor),
        )
