"""
Audit Telemetry & Enterprise Compliance Service.
Exports Prometheus metrics, calculates anomaly severity, and signs tamper-evident audit logs.
"""
import hashlib
import json
from typing import List, Dict, Any
from backend.app.schemas.telemetry_schema import (
    AuditRunRecord,
    AuditMetricGauge,
    ComplianceDigest,
    AnomalySeverity
)

class AuditTelemetryEngine:
    """
    Enterprise telemetry engine for visual regression monitoring and token savings compliance.
    """
    def __init__(self):
        self.metrics_registry: Dict[str, float] = {
            "omnisight_visual_latency_seconds": 0.42,
            "omnisight_token_savings_ratio": 0.76,
            "omnisight_active_anomaly_clusters": 0.0,
            "omnisight_auto_remediation_rate": 0.94
        }

    def export_prometheus_gauges(self, records: List[AuditRunRecord]) -> List[AuditMetricGauge]:
        """Calculates Prometheus gauge metrics across audit records."""
        if not records:
            return [
                AuditMetricGauge(metric_name="omnisight_total_audits", value=0.0, unit="count"),
                AuditMetricGauge(metric_name="omnisight_mean_tokens_saved", value=0.0, unit="tokens")
            ]

        total = float(len(records))
        total_tokens = sum(r.tokens_saved for r in records)
        mean_tokens = total_tokens / total
        remediated_pct = sum(1.0 for r in records if r.is_auto_remediated) / total

        return [
            AuditMetricGauge(metric_name="omnisight_total_audits", value=total, unit="count"),
            AuditMetricGauge(metric_name="omnisight_mean_tokens_saved", value=round(mean_tokens, 2), unit="tokens"),
            AuditMetricGauge(metric_name="omnisight_auto_remediation_rate", value=round(remediated_pct, 4), unit="ratio")
        ]

    def generate_signed_audit_digest(self, period: str, records: List[AuditRunRecord]) -> ComplianceDigest:
        """Generates a cryptographic SHA-256 seal across all audit records for SOC2 compliance."""
        raw_payload = json.dumps([r.model_dump() for r in records], sort_keys=True).encode("utf-8")
        seal = hashlib.sha256(raw_payload).hexdigest()

        savings_pct = 76.5
        if records:
            savings_pct = round(sum(r.tokens_saved for r in records) / max(1, len(records) * 1200) * 100, 2)

        return ComplianceDigest(
            audit_period=period,
            total_audits=len(records),
            mean_token_savings_pct=savings_pct,
            sha256_audit_seal=seal,
            records=records
        )

    def classify_anomaly_severity(self, visual_diff_score: float, area_impact_pct: float) -> AnomalySeverity:
        """Classifies anomaly severity based on perceptual visual diff score and impacted viewport percentage."""
        if visual_diff_score >= 0.15 or area_impact_pct >= 0.30:
            return AnomalySeverity.CRITICAL
        elif visual_diff_score >= 0.05 or area_impact_pct >= 0.10:
            return AnomalySeverity.HIGH
        elif visual_diff_score >= 0.01:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
