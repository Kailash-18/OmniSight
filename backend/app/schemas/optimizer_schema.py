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
