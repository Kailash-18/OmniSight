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

    def calculate_crop_regions(
        self,
        run_id: str,
        image_width: int,
        image_height: int,
        bounding_boxes: List[CropBoundingBox]
    ) -> CropRegionResponse:
        """
        Calculates optimized crop tiles around bounding boxes with context padding.
        Clamps all coordinates safely to [0, width] and [0, height].
        """
        regions = []
        aspect_ratios = []

        for idx, box in enumerate(bounding_boxes):
            pad_x = int(box.width * box.padding_percent)
            pad_y = int(box.height * box.padding_percent)

            # Apply padding and clamp
            x1 = max(0, box.x - pad_x)
            y1 = max(0, box.y - pad_y)
            x2 = min(image_width, box.x + box.width + pad_x)
            y2 = min(image_height, box.y + box.height + pad_y)

            crop_w = max(100, x2 - x1)  # enforce minimum tile width
            crop_h = max(100, y2 - y1)  # enforce minimum tile height

            aspect = round(crop_w / crop_h, 3)
            aspect_ratios.append(aspect)

            regions.append({
                "region_index": idx,
                "crop_x": x1,
                "crop_y": y1,
                "crop_width": crop_w,
                "crop_height": crop_h,
                "aspect_ratio": aspect,
                "area_pixels": crop_w * crop_h,
            })

        # Generate deterministic manifest ID
        hash_seed = f"{run_id}-{image_width}x{image_height}-{len(bounding_boxes)}"
        manifest_id = f"MANIFEST-OPT-{hashlib.sha256(hash_seed.encode()).hexdigest()[:8].upper()}"

        manifest = {
            "manifest_id": manifest_id,
            "run_id": run_id,
            "image_width": image_width,
            "image_height": image_height,
            "regions": regions,
            "total_regions": len(regions),
        }
        self.crop_manifests_db[manifest_id] = manifest

        return CropRegionResponse(
            run_id=run_id,
            manifest_id=manifest_id,
            cropped_regions=regions,
            total_regions=len(regions),
            aspect_ratios=aspect_ratios,
        )

    def clamp_coordinates(self, x: int, y: int, width: int, height: int, max_w: int, max_h: int) -> Dict[str, int]:
        """Safely clamps arbitrary bounding box dimensions within pixel viewport boundaries."""
        cx = max(0, min(x, max_w - 50))
        cy = max(0, min(y, max_h - 50))
        cw = min(width, max_w - cx)
        ch = min(height, max_h - cy)
        return {"x": cx, "y": cy, "width": max(50, cw), "height": max(50, ch)}

    def calculate_token_economics(
        self,
        run_id: str,
        image_width: int,
        image_height: int,
        cropped_regions: List[Dict[str, Any]]
    ) -> TokenEconomicsReport:
        """
        Estimates multimodal visual token usage comparing full-resolution vs cropped tiles.
        Standard vision models: 85 base tokens + 170 tokens per 512x512 tile.
        """
        # Full viewport tiles (e.g. 1440x900 ~ 6 tiles)
        full_tiles_x = math.ceil(image_width / 512)
        full_tiles_y = math.ceil(image_height / 512)
        full_tokens = 85 + (full_tiles_x * full_tiles_y * 170)

        # Cropped regions tiles
        cropped_tokens = 0
        for reg in cropped_regions:
            w = reg.get("crop_width", 300)
            h = reg.get("crop_height", 250)
            tx = math.ceil(w / 512)
            ty = math.ceil(h / 512)
            cropped_tokens += 85 + (tx * ty * 170)

        if not cropped_regions:
            cropped_tokens = full_tokens

        saved_tokens = max(0, full_tokens - cropped_tokens)
        savings_pct = round((saved_tokens / full_tokens) * 100.0, 2)
        latency_saved_ms = int(saved_tokens * 1.8)  # ~1.8ms per token generation speedup
        cost_saved_cents = round(saved_tokens * 0.00025 * 1000, 2)  # ~$0.0025 per 1k tokens

        return TokenEconomicsReport(
            run_id=run_id,
            full_image_tokens=full_tokens,
            cropped_regions_tokens=cropped_tokens,
            token_savings_count=saved_tokens,
            token_savings_percent=savings_pct,
            latency_reduction_estimate_ms=latency_saved_ms,
            estimated_cost_reduction_cents=cost_saved_cents,
        )

    def get_crop_manifest(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached crop manifest by ID."""
        return self.crop_manifests_db.get(manifest_id)

    def get_metrics_summary(self, run_id: str, savings_pct: float) -> CropMetricsSummary:
        """Returns compact efficiency score for dashboard telemetry."""
        efficiency = min(1.0, max(0.0, savings_pct / 100.0))
        tier = "gpt-4o-mini-vision" if efficiency > 0.50 else "claude-3-5-sonnet-vision"
        return CropMetricsSummary(
            run_id=run_id,
            optimization_applied=True,
            efficiency_score=round(efficiency, 3),
            recommended_model_tier=tier,
        )


# Global singleton instance
vlm_optimizer = VLMRegionOptimizer()
