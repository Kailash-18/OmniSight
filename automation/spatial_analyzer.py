"""
Spatial Layout Anomaly Analyzer for OmniSight (Team Lead deliverable).
Detects viewport clipping, overlapping bounding boxes, and out-of-bounds elements.
Re-exported from automation.engine for standard repository layout compliance.
"""

from automation.engine import (
    AnomalyType,
    BoundingBox,
    SpatialAnalyzer,
    SpatialAnomaly,
)

__all__ = [
    "AnomalyType",
    "BoundingBox",
    "SpatialAnalyzer",
    "SpatialAnomaly",
]
