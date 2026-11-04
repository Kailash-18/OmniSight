"""
OmniSight Automation Package.
Core browser automation, spatial layout analysis, isolated sandbox retesting, and VLM orchestration.
"""

__version__ = "0.2.0"

import sys

# Import core modules
from automation import core
from automation import engine
from automation import orchestrator

# Re-export commonly used components
from automation.core import (
    AutomationConfig,
    DefectCategory,
    EvidenceCollector,
    Finding,
    ProposedPatch,
    RetestStatus,
    RetestVerification,
    RunManifest,
    STANDARD_VIEWPORTS,
    Severity,
    ViewportSpec,
    VisualAuditReport,
    config,
    extract_dom_context,
    get_desktop_viewports,
    get_mobile_viewports,
    get_viewport,
)
from automation.engine import (
    ALLOWED_PATCH_TARGETS,
    AnomalyType,
    BaseVLMAdapter,
    BoundingBox,
    DiffResult,
    ForensicBundler,
    LiveVLMAdapter,
    MockVLMAdapter,
    PatchSandbox,
    RetestRunner,
    SpatialAnomaly,
    SpatialAnalyzer,
    StoreJourney,
    VisualComparator,
    ComponentCropper,
    CropResult,
    crop_component_region,
    apply_unified_diff,
    attach_browser_listeners,
    check_store_health,
    compute_sha256,
    create_forensic_bundle,
    create_isolated_page,
    launch_browser,
    normalize_target_path,
    run_visual_audit_journey,
    validate_patch_target,
)
from automation.orchestrator import (
    AgentState,
    BackendClient,
    Orchestrator,
    main,
)

# Backwards compatibility: register legacy submodules in sys.modules
sys.modules.setdefault("automation.config", core)
sys.modules.setdefault("automation.schemas", core)
sys.modules.setdefault("automation.evidence", core)
sys.modules.setdefault("automation.spatial_analyzer", engine)
sys.modules.setdefault("automation.visual_diff", engine)
sys.modules.setdefault("automation.browser_runner", engine)
sys.modules.setdefault("automation.vlm_adapter", engine)
sys.modules.setdefault("automation.patch_sandbox", engine)
sys.modules.setdefault("automation.forensics", engine)
sys.modules.setdefault("automation.backend_client", orchestrator)

__all__ = [
    # Core
    "AutomationConfig",
    "DefectCategory",
    "EvidenceCollector",
    "Finding",
    "ProposedPatch",
    "RetestStatus",
    "RetestVerification",
    "RunManifest",
    "STANDARD_VIEWPORTS",
    "Severity",
    "ViewportSpec",
    "VisualAuditReport",
    "config",
    "extract_dom_context",
    "get_desktop_viewports",
    "get_mobile_viewports",
    "get_viewport",
    # Engine
    "ALLOWED_PATCH_TARGETS",
    "AnomalyType",
    "BaseVLMAdapter",
    "BoundingBox",
    "DiffResult",
    "ForensicBundler",
    "LiveVLMAdapter",
    "MockVLMAdapter",
    "PatchSandbox",
    "RetestRunner",
    "SpatialAnomaly",
    "SpatialAnalyzer",
    "StoreJourney",
    "VisualComparator",
    "ComponentCropper",
    "CropResult",
    "crop_component_region",
    "apply_unified_diff",
    "attach_browser_listeners",
    "check_store_health",
    "compute_sha256",
    "create_forensic_bundle",
    "create_isolated_page",
    "launch_browser",
    "normalize_target_path",
    "run_visual_audit_journey",
    "validate_patch_target",
    # Orchestrator & CLI
    "AgentState",
    "BackendClient",
    "Orchestrator",
    "main",
]
