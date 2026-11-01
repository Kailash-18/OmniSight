"""
OmniSight Spatial Region Optimization & VLM Token Economics Service.
Implements intelligent bounding box cropping, contextual margin padding, boundary clamping,
and token/latency economics computation.
"""

from typing import Dict, Any, List, Optional
import math
import hashlib
from backend.app.schemas.optimizer_schema import (
    CropBoundingBox,
    CropRegionResponse,
    TokenEconomicsReport,
    CropMetricsSummary,
)


class VLMRegionOptimizer:
    """Calculates focused image regions and computes token reduction metrics for multimodal VLMs."""

    def __init__(self):
        # In-memory storage for crop manifests: {manifest_id: manifest_dict}
        self.crop_manifests_db: Dict[str, Dict[str, Any]] = {}
