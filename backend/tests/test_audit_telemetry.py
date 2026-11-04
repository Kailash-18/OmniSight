"""
Unit test suite for Audit Telemetry & Cryptographic SOC2 Compliance.
"""
import pytest
from backend.app.services.audit_telemetry_service import AuditTelemetryEngine
from backend.app.schemas.telemetry_schema import (
    AuditRunRecord,
    AnomalySeverity
)

def test_prometheus_gauge_export():
    engine = AuditTelemetryEngine()
    records = [
        AuditRunRecord(run_id="r1", timestamp="2026-11-04T10:00:00Z", visual_diff_score=0.04, tokens_saved=920, is_auto_remediated=True),
        AuditRunRecord(run_id="r2", timestamp="2026-11-04T10:30:00Z", visual_diff_score=0.12, tokens_saved=780, is_auto_remediated=True)
    ]
    gauges = engine.export_prometheus_gauges(records)
    assert len(gauges) == 3
    assert gauges[0].value == 2.0
    assert gauges[1].value == 850.0
    assert gauges[2].value == 1.0

def test_signed_audit_digest_and_tamper_detection():
    engine = AuditTelemetryEngine()
    records = [
        AuditRunRecord(run_id="r-sec-1", timestamp="2026-11-04T11:00:00Z", visual_diff_score=0.02, tokens_saved=840)
    ]
    digest = engine.generate_signed_audit_digest("Week 4 Day 2", records)
    assert len(digest.sha256_audit_seal) == 64

    records_tampered = [
        AuditRunRecord(run_id="r-sec-1", timestamp="2026-11-04T11:00:00Z", visual_diff_score=0.99, tokens_saved=840)
    ]
    digest_tampered = engine.generate_signed_audit_digest("Week 4 Day 2", records_tampered)
    assert digest.sha256_audit_seal != digest_tampered.sha256_audit_seal

def test_end_to_end_clustering_and_telemetry_pipeline():
    from backend.app.services.coordinate_cluster_service import CoordinateClusterEngine
    from backend.app.schemas.clustering_schema import ClusterBoundingBox, ClusterBoundingBoxRequest
    
    clust_engine = CoordinateClusterEngine()
    telem_engine = AuditTelemetryEngine()
    
    req = ClusterBoundingBoxRequest(
        run_id="run-e2e-cluster-1",
        viewport_width=1920,
        viewport_height=1080,
        boxes=[
            ClusterBoundingBox(id="box-nav-1", x=20, y=20, width=150, height=80),
            ClusterBoundingBox(id="box-nav-2", x=30, y=30, width=160, height=70, is_sensitive_pii=True)
        ]
    )
    clust_resp = clust_engine.cluster_and_optimize(req)
    assert clust_resp.clusters_count == 1
    assert len(clust_resp.clusters[0].redaction_masks) == 1
    
    record = AuditRunRecord(
        run_id=clust_resp.run_id,
        timestamp="2026-11-04T12:00:00Z",
        visual_diff_score=0.03,
        tokens_saved=890,
        clusters_analyzed=clust_resp.clusters_count,
        severity=telem_engine.classify_anomaly_severity(0.03, 0.05),
        is_auto_remediated=True
    )
    digest = telem_engine.generate_signed_audit_digest("Week 4 Day 2 E2E", [record])
    assert digest.total_audits == 1
    assert len(digest.sha256_audit_seal) == 64
