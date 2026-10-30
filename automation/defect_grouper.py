"""Multi-viewport defect deduplication and root-cause clustering.

Groups related visual defect findings across viewports (e.g. desktop and mobile)
sharing identical selectors or defect categories into unified defect clusters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class DefectCluster:
    cluster_id: str
    primary_selector: str
    category: str
    highest_severity: str
    affected_viewports: Set[str] = field(default_factory=set)
    descriptions: List[str] = field(default_factory=list)
    raw_findings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "selector": self.primary_selector,
            "category": self.category,
            "severity": self.highest_severity,
            "viewports": sorted(list(self.affected_viewports)),
            "occurrences": len(self.raw_findings),
            "descriptions": self.descriptions,
        }


SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


class DefectGrouper:
    """Clusters and deduplicates defect findings by selector and category."""

    @classmethod
    def group_findings(
        cls, findings: List[Dict[str, Any]]
    ) -> List[DefectCluster]:
        clusters: Dict[str, DefectCluster] = {}

        for item in findings:
            selector = item.get("selector") or item.get("element_selector") or "general"
            category = item.get("category") or item.get("type") or "UNKNOWN"
            severity = (item.get("severity") or "MEDIUM").upper()
            viewport = item.get("viewport") or "default"
            desc = item.get("description") or ""

            cluster_key = f"{category}::{selector.strip().lower()}"

            if cluster_key not in clusters:
                clusters[cluster_key] = DefectCluster(
                    cluster_id=f"cluster-{len(clusters) + 1}",
                    primary_selector=selector,
                    category=category,
                    highest_severity=severity,
                    affected_viewports={viewport},
                    descriptions=[desc] if desc else [],
                    raw_findings=[item],
                )
            else:
                cluster = clusters[cluster_key]
                cluster.affected_viewports.add(viewport)
                if desc and desc not in cluster.descriptions:
                    cluster.descriptions.append(desc)
                cluster.raw_findings.append(item)

                # Upgrade severity if higher
                if SEVERITY_WEIGHTS.get(severity, 1) > SEVERITY_WEIGHTS.get(
                    cluster.highest_severity, 1
                ):
                    cluster.highest_severity = severity

        # Return sorted by highest severity first
        return sorted(
            clusters.values(),
            key=lambda c: SEVERITY_WEIGHTS.get(c.highest_severity, 1),
            reverse=True,
        )
