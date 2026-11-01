"""
OmniSight Spatial Region Optimization & VLM Token Economics Schemas.
Defines data models for image chunking, bounding box context cropping, and token savings analytics.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class CropBoundingBox(BaseModel):
    """Normalized bounding coordinates for a visual UI component."""
    x: int = Field(..., description="Top-left X coordinate in pixels", ge=0)
    y: int = Field(..., description="Top-left Y coordinate in pixels", ge=0)
    width: int = Field(..., description="Box width in pixels", gt=0)
    height: int = Field(..., description="Box height in pixels", gt=0)
    padding_percent: float = Field(default=0.15, description="Context margin padding ratio", ge=0.0, le=0.5)


class CropRegionRequest(BaseModel):
    """Request payload to compute focused crop regions around anomalous UI elements."""
    run_id: str = Field(..., description="Unique audit run identifier", min_length=3)
    image_width: int = Field(default=1440, description="Full screenshot width in pixels", gt=0)
    image_height: int = Field(default=900, description="Full screenshot height in pixels", gt=0)
    bounding_boxes: List[CropBoundingBox] = Field(..., description="List of defect element bounding boxes", min_length=1)
    target_defect_id: Optional[str] = Field(default=None, description="Optional defect ID to isolate")

class CropRegionResponse(BaseModel):
    """Calculated cropped viewport coordinate matrices for focused VLM reasoning."""
    run_id: str = Field(..., description="Audit run identifier")
    manifest_id: str = Field(..., description="Unique crop manifest identifier")
    cropped_regions: List[Dict[str, Any]] = Field(..., description="Calculated crop regions with padded boundaries")
    total_regions: int = Field(..., description="Total count of optimized image chunks", ge=1)
    aspect_ratios: List[float] = Field(default_factory=list, description="Aspect ratios of resulting crop tiles")


class CropManifestRegistration(BaseModel):
    """Registration payload for a pre-computed crop manifest."""
    manifest_id: str = Field(..., description="Unique crop manifest identifier")
    run_id: str = Field(..., description="Audit run identifier")
    regions_count: int = Field(..., description="Count of stored image regions", ge=1)
    is_cached: bool = Field(default=True, description="Whether regions are hot-cached in memory")

class TokenEconomicsReport(BaseModel):
    """Detailed token consumption and latency reduction analysis for visual inference."""
    run_id: str = Field(..., description="Audit run identifier")
    full_image_tokens: int = Field(..., description="Estimated tokens required for full viewport image", gt=0)
    cropped_regions_tokens: int = Field(..., description="Actual tokens required for cropped focus tiles", gt=0)
    token_savings_count: int = Field(..., description="Total tokens saved per visual audit inference")
    token_savings_percent: float = Field(..., description="Percentage reduction in prompt token consumption", ge=0.0, le=100.0)
    latency_reduction_estimate_ms: int = Field(..., description="Estimated inference latency savings in milliseconds", ge=0)
    estimated_cost_reduction_cents: float = Field(..., description="Estimated API expense reduction per 1,000 runs", ge=0.0)
