"""SARIF (Static Analysis Results Interchange Format) exporter for OmniSight.

Generates standard SARIF v2.1.0 JSON reports from OmniSight visual audit runs,
enabling native integration with GitHub Code Scanning, SonarQube, and CI security tabs.
"""

from __future__ import annotations

from typing import Any, Dict, List


class SarifExporter:
    """Converts OmniSight audit runs and findings to SARIF v2.1.0 format."""

    SEVERITY_TO_SARIF_LEVEL = {
        "CRITICAL": "error",
        "HIGH": "error",
        "MEDIUM": "warning",
        "LOW": "note",
    }

    @classmethod
    def export(cls, run_data: Dict[str, Any]) -> Dict[str, Any]:
        run_id = run_data.get("id", "unknown-run")
        target_url = run_data.get("target_url", "")
        findings = run_data.get("findings", [])

        rules: List[Dict[str, Any]] = [
            {
                "id": "OMNI-OVERLAP",
                "name": "ElementOverlap",
                "shortDescription": {"text": "Visual UI element collision or overlapping bounding box."},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "OMNI-OBSTRUCTION",
                "name": "ElementObstruction",
                "shortDescription": {"text": "Interactive UI control occluded or obstructed by another element."},
                "defaultConfiguration": {"level": "error"},
            },
            {
                "id": "OMNI-A11Y-CONTRAST",
                "name": "ContrastRatioViolation",
                "shortDescription": {"text": "Text contrast ratio fails WCAG 2.1 AA 4.5:1 threshold."},
                "defaultConfiguration": {"level": "warning"},
            },
            {
                "id": "OMNI-A11Y-ACCESSIBLE-NAME",
                "name": "MissingAccessibleName",
                "shortDescription": {"text": "Interactive element lacks accessible name or label."},
                "defaultConfiguration": {"level": "warning"},
            },
            {
                "id": "OMNI-GENERAL",
                "name": "GeneralVisualDefect",
                "shortDescription": {"text": "Visual UI anomaly detected by OmniSight multimodal engine."},
                "defaultConfiguration": {"level": "note"},
            },
        ]

        sarif_results: List[Dict[str, Any]] = []

        for f in findings:
            cat = str(f.get("category", "")).upper()
            sev = str(f.get("severity", "MEDIUM")).upper()
            desc = f.get("description") or "Visual defect detected"
            selector = f.get("selector") or "body"
            viewport = f.get("viewport") or "default"

            rule_id = "OMNI-GENERAL"
            if "OVERLAP" in cat:
                rule_id = "OMNI-OVERLAP"
            elif "OBSTRUCT" in cat:
                rule_id = "OMNI-OBSTRUCTION"
            elif "CONTRAST" in cat or "CONTRAST" in desc.upper():
                rule_id = "OMNI-A11Y-CONTRAST"
            elif "ACCESSIBLE" in cat or "NAME" in cat:
                rule_id = "OMNI-A11Y-ACCESSIBLE-NAME"

            level = cls.SEVERITY_TO_SARIF_LEVEL.get(sev, "warning")

            sarif_results.append({
                "ruleId": rule_id,
                "level": level,
                "message": {
                    "text": f"[{viewport}] {desc} (selector: '{selector}')"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": target_url or "app-under-test/src/styles/defects.css",
                            },
                        }
                    }
                ],
                "properties": {
                    "selector": selector,
                    "viewport": viewport,
                    "runId": run_id,
                },
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "OmniSight",
                            "version": "1.0.0",
                            "informationUri": "https://github.com/Kailash-18/OmniSight",
                            "rules": rules,
                        }
                    },
                    "results": sarif_results,
                }
            ],
        }
