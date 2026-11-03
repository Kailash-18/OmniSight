"""Visual regression tolerance profiles and threshold configurations.

Defines customizable sensitivity profiles (STRICT, BALANCED, PERMISSIVE)
controlling pixel-delta thresholds, bounding box cluster filtering, and antialias tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class SensitivityProfile(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    PERMISSIVE = "permissive"


@dataclass
class VisualThresholdConfig:
    profile: SensitivityProfile = SensitivityProfile.BALANCED
    pixel_delta_threshold: int = 15          # RGB channel delta 0-255
    min_cluster_area_px: int = 36             # Ignore anomalies smaller than 6x6
    max_acceptable_diff_percent: float = 0.05 # 0.05% threshold for clean retest
    ignore_antialiasing: bool = True

    @classmethod
    def from_profile(cls, profile: SensitivityProfile | str) -> VisualThresholdConfig:
        if isinstance(profile, str):
            profile = SensitivityProfile(profile.lower())

        if profile == SensitivityProfile.STRICT:
            return cls(
                profile=profile,
                pixel_delta_threshold=8,
                min_cluster_area_px=16,
                max_acceptable_diff_percent=0.01,
                ignore_antialiasing=False,
            )
        elif profile == SensitivityProfile.PERMISSIVE:
            return cls(
                profile=profile,
                pixel_delta_threshold=30,
                min_cluster_area_px=100,
                max_acceptable_diff_percent=0.20,
                ignore_antialiasing=True,
            )
        # BALANCED default
        return cls(
            profile=SensitivityProfile.BALANCED,
            pixel_delta_threshold=15,
            min_cluster_area_px=36,
            max_acceptable_diff_percent=0.05,
            ignore_antialiasing=True,
        )

    def is_diff_acceptable(self, diff_percent: float) -> bool:
        return diff_percent <= self.max_acceptable_diff_percent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "pixel_delta_threshold": self.pixel_delta_threshold,
            "min_cluster_area_px": self.min_cluster_area_px,
            "max_acceptable_diff_percent": self.max_acceptable_diff_percent,
            "ignore_antialiasing": self.ignore_antialiasing,
        }
