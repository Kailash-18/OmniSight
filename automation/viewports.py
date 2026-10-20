"""
Viewport Specifications and Device Matrix Models.
Defines team standard resolutions for responsive visual regression audits.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ViewportSpec:
    name: str
    width: int
    height: int
    device_scale_factor: float = 1.0
    is_mobile: bool = False
    has_touch: bool = False
    description: str = ""

    @property
    def resolution_str(self) -> str:
        return f"{self.width}x{self.height}"


# Team Standard Viewports (Infotact SOP / OmniSight Specs)
STANDARD_VIEWPORTS: Dict[str, ViewportSpec] = {
    "desktop_1440x900": ViewportSpec(
        name="desktop_1440x900",
        width=1440,
        height=900,
        is_mobile=False,
        has_touch=False,
        description="Standard desktop widescreen display",
    ),
    "desktop_1280x800": ViewportSpec(
        name="desktop_1280x800",
        width=1280,
        height=800,
        is_mobile=False,
        has_touch=False,
        description="Standard laptop display resolution",
    ),
    "mobile_390x844": ViewportSpec(
        name="mobile_390x844",
        width=390,
        height=844,
        device_scale_factor=3.0,
        is_mobile=True,
        has_touch=True,
        description="Modern mobile device viewport (iPhone 12/13/14)",
    ),
    "mobile_375x667": ViewportSpec(
        name="mobile_375x667",
        width=375,
        height=667,
        device_scale_factor=2.0,
        is_mobile=True,
        has_touch=True,
        description="Compact mobile device viewport (iPhone SE / narrow screens)",
    ),
}


def get_viewport(name: str) -> ViewportSpec:
    if name not in STANDARD_VIEWPORTS:
        raise KeyError(
            f"Unknown viewport '{name}'. Available: {list(STANDARD_VIEWPORTS.keys())}"
        )
    return STANDARD_VIEWPORTS[name]


def get_desktop_viewports() -> List[ViewportSpec]:
    return [v for v in STANDARD_VIEWPORTS.values() if not v.is_mobile]


def get_mobile_viewports() -> List[ViewportSpec]:
    return [v for v in STANDARD_VIEWPORTS.values() if v.is_mobile]
