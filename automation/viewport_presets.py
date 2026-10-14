"""Standard device viewport presets and orientation scaling for OmniSight.

Provides comprehensive mobile, tablet, laptop, and desktop viewport specifications
compliant with standard device pixel ratios and responsive testing guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DevicePreset:
    name: str
    width: int
    height: int
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool
    category: str  # 'mobile', 'tablet', 'laptop', 'desktop'

    def to_viewport_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "deviceScaleFactor": self.device_scale_factor,
            "isMobile": self.is_mobile,
            "hasTouch": self.has_touch,
            "category": self.category,
        }


DEVICE_CATALOG: Dict[str, DevicePreset] = {
    "desktop_1440x900": DevicePreset(
        name="desktop_1440x900",
        width=1440,
        height=900,
        device_scale_factor=1.0,
        is_mobile=False,
        has_touch=False,
        category="desktop",
    ),
    "laptop_1280x800": DevicePreset(
        name="laptop_1280x800",
        width=1280,
        height=800,
        device_scale_factor=1.0,
        is_mobile=False,
        has_touch=False,
        category="laptop",
    ),
    "tablet_768x1024": DevicePreset(
        name="tablet_768x1024",
        width=768,
        height=1024,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        category="tablet",
    ),
    "mobile_375x667": DevicePreset(
        name="mobile_375x667",
        width=375,
        height=667,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        category="mobile",
    ),
    "mobile_390x844": DevicePreset(
        name="mobile_390x844",
        width=390,
        height=844,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        category="mobile",
    ),
}


class ViewportCatalog:
    """Helper for resolving viewport presets and device configurations."""

    @staticmethod
    def get_preset(name: str) -> Optional[DevicePreset]:
        return DEVICE_CATALOG.get(name.lower().strip())

    @staticmethod
    def list_presets_by_category(category: str) -> List[DevicePreset]:
        cat_clean = category.lower().strip()
        return [p for p in DEVICE_CATALOG.values() if p.category == cat_clean]

    @staticmethod
    def get_all_names() -> List[str]:
        return list(DEVICE_CATALOG.keys())
