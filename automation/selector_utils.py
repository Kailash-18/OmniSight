"""DOM selector generator and locator sanitizer for OmniSight.

Produces deterministic, resilient CSS selectors from element snapshots
prioritizing testing IDs, IDs, semantic roles, and scoped class chains.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class SelectorSanitizer:
    """Sanitizes CSS selectors and escapes invalid characters."""

    _UNSAFE_CHARS = re.compile(r"([:\[\]\(\)\.\#\/\\\$])")

    @classmethod
    def escape_identifier(cls, ident: str) -> str:
        # Standard CSS identifier escaping
        return re.sub(r"([^\w\-])", r"\\\1", ident)

    @classmethod
    def generate_resilient_selector(cls, element: Dict[str, Any]) -> str:
        attrs = element.get("attributes", {})

        # 1. Prioritize data-testid / data-cy
        for test_key in ["data-testid", "data-test", "data-cy"]:
            if test_key in attrs and attrs[test_key]:
                val = attrs[test_key]
                return f"[{test_key}='{val}']"

        # 2. Prioritize unique ID
        node_id = element.get("id") or attrs.get("id")
        if node_id and not re.match(r"^[0-9]", node_id):
            return f"#{node_id}"

        # 3. Semantic role + aria-label
        tag = (element.get("tag") or "div").lower()
        aria_label = attrs.get("aria-label")
        if aria_label:
            return f"{tag}[aria-label='{aria_label}']"

        # 4. Filtered class names
        classes = element.get("classes", [])
        if isinstance(classes, str):
            classes = classes.split()
        safe_classes = [c for c in classes if not c.startswith("_") and len(c) > 1]
        if safe_classes:
            return f"{tag}." + ".".join(safe_classes[:2])

        return tag
