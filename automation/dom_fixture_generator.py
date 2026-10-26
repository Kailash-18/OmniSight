"""Synthetic DOM snapshot fixture generator for offline testing and benchmarking.

Generates realistic DOM tree snapshots with configurable UI anomalies
(overlapping headings, obstructed buttons, missing alt tags) for testing engines.
"""

from __future__ import annotations

from typing import Any, Dict, List


class DOMFixtureGenerator:
    """Creates deterministic DOM tree fixtures for unit tests and benchmarks."""

    @staticmethod
    def create_ecommerce_page(
        include_overlap: bool = False,
        include_obstruction: bool = False,
        include_a11y_violations: bool = False,
    ) -> Dict[str, Any]:
        hero_y = 60 if include_overlap else 20
        banner_w = 400 if include_obstruction else 200

        button_attrs: Dict[str, Any] = {"data-testid": "submit-order"}
        if include_a11y_violations:
            button_attrs = {"data-testid": "btn-unlabeled"}

        img_attrs: Dict[str, Any] = {"src": "/hero.jpg"}
        if not include_a11y_violations:
            img_attrs["alt"] = "Everyday Mug"

        return {
            "tag": "html",
            "children": [
                {
                    "tag": "header",
                    "id": "site-header",
                    "rect": {"x": 0, "y": 0, "width": 1440, "height": 80},
                    "children": [
                        {"tag": "h1", "id": "hero-title", "rect": {"x": 40, "y": hero_y, "width": 300, "height": 60}},
                    ],
                },
                {
                    "tag": "main",
                    "id": "content",
                    "rect": {"x": 0, "y": 80, "width": 1440, "height": 800},
                    "children": [
                        {
                            "tag": "div",
                            "classes": ["promo-banner"],
                            "rect": {"x": 40, "y": 70, "width": banner_w, "height": 90},
                        },
                        {
                            "tag": "button",
                            "attributes": button_attrs,
                            "rect": {"x": 50, "y": 80, "width": 120, "height": 40},
                            "text": "" if include_a11y_violations else "Place Order",
                        },
                        {
                            "tag": "img",
                            "attributes": img_attrs,
                            "rect": {"x": 200, "y": 100, "width": 150, "height": 150},
                        },
                    ],
                },
            ],
        }
