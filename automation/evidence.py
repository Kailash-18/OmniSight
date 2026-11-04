"""
Evidence Collection and Run Artifacts module for OmniSight (Team Lead deliverable).
Re-exported from automation.core for standard repository layout compliance.
"""

from automation.core import (
    EvidenceCollector,
    Finding,
    ProposedPatch,
    RunManifest,
    VisualAuditReport,
    extract_dom_context,
)

__all__ = [
    "EvidenceCollector",
    "Finding",
    "ProposedPatch",
    "RunManifest",
    "VisualAuditReport",
    "extract_dom_context",
]
