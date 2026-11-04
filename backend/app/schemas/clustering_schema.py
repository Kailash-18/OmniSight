"""
Pydantic v2 schemas for VLM coordinate clustering and spatial optimization.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ClusterBoundingBox(BaseModel):
    id: str = Field(..., description="Unique identifier for the bounding box")
    x: int = Field(..., ge=0, description="X coordinate of top-left corner")
    y: int = Field(..., ge=0, description="Y coordinate of top-left corner")
    width: int = Field(..., gt=0, description="Width of bounding box in pixels")
    height: int = Field(..., gt=0, description="Height of bounding box in pixels")
    dom_selector: Optional[str] = Field(default=None, description="DOM element selector")
    z_index: int = Field(default=0, description="DOM stacking z-index")
    is_sensitive_pii: bool = Field(default=False, description="Flag for credential/PII inputs")

class ClusterRegion(BaseModel):
    cluster_id: str
    bounding_box: Dict[str, int]
    included_box_ids: List[str]
    area_pixels: int
    hardware_aligned_box: Dict[str, int]
    redaction_masks: List[Dict[str, int]] = []

class ClusterBoundingBoxRequest(BaseModel):
    run_id: str
    viewport_width: int = Field(default=1920, gt=0)
    viewport_height: int = Field(default=1080, gt=0)
    boxes: List[ClusterBoundingBox]
    iou_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    padding_percent: float = Field(default=0.15, ge=0.0, le=0.5)

class ClusterBoundingBoxResponse(BaseModel):
    run_id: str
    clusters_count: int
    clusters: List[ClusterRegion]
    original_boxes_count: int
    compression_ratio: float
