"""Tests for SarifExporter and SARIF export endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, runs_db
from app.services.sarif_service import SarifExporter

client = TestClient(app)


def test_sarif_exporter_format():
    run_data = {
        "id": "run-sarif-test",
        "target_url": "http://localhost:5173",
        "findings": [
            {
                "category": "element_overlap",
                "severity": "high",
                "selector": ".hero-title",
                "viewport": "1440x900",
                "description": "Hero title overlaps product card",
            },
            {
                "category": "element_obstruction",
                "severity": "critical",
                "selector": ".promo-banner",
                "viewport": "375x667",
                "description": "Free shipping banner obstructs button",
            },
        ],
    }

    sarif = SarifExporter.export(run_data)
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"]) == 1
    run_sarif = sarif["runs"][0]
    assert run_sarif["tool"]["driver"]["name"] == "OmniSight"
    results = run_sarif["results"]
    assert len(results) == 2
    assert results[0]["ruleId"] == "OMNI-OVERLAP"
    assert results[0]["level"] == "error"
    assert results[1]["ruleId"] == "OMNI-OBSTRUCTION"
    assert results[1]["level"] == "error"


def test_sarif_export_api_endpoint():
    runs_db["run-sarif-api"] = {
        "id": "run-sarif-api",
        "target_url": "http://localhost:5173",
        "findings": [
            {
                "category": "element_overlap",
                "severity": "high",
                "selector": ".hero-title",
                "viewport": "1440x900",
                "description": "Overlap defect",
            }
        ],
    }

    resp = client.get("/runs/run-sarif-api/export/sarif")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    data = resp.json()
    assert data["version"] == "2.1.0"
    assert len(data["runs"][0]["results"]) == 1
