"""
Pydantic v2 schemas for cross-viewport canary verification.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.regression_guard_schema import SpatialDriftMetric

class ViewportProfile(BaseModel):
    name: str = "desktop_1920x1080"
    width: int = 1920
    height: int = 1080
    min_acceptable_stability: float = Field(default=0.90, ge=0.5, le=1.0)

class ViewportStabilityResult(BaseModel):
    viewport: str
    width: int
    height: int
    stability_score: float
    violations_count: int
    is_acceptable: bool
    details: List[SpatialDriftMetric] = []

class CanaryVerificationRequest(BaseModel):
    run_id: str
    patch_id: str
    target_selector: str
    viewports: List[ViewportProfile] = Field(default_factory=lambda: [
        ViewportProfile(name="mobile_375x667", width=375, height=667, min_acceptable_stability=0.85),
        ViewportProfile(name="tablet_768x1024", width=768, height=1024, min_acceptable_stability=0.90),
        ViewportProfile(name="desktop_1920x1080", width=1920, height=1080, min_acceptable_stability=0.95),
    ])
    per_viewport_drift: Dict[str, List[SpatialDriftMetric]] = Field(default_factory=dict)

class CanaryVerificationReport(BaseModel):
    run_id: str
    patch_id: str
    overall_canary_passed: bool
    canary_stability_index: float
    breaking_viewports: List[str]
    viewport_results: List[ViewportStabilityResult]
    quarantine_recommended: bool
    certified_at: str
