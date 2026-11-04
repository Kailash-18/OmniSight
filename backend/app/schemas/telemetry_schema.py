"""
Pydantic v2 schemas for enterprise visual audit telemetry and Prometheus reporting.
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class AnomalySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AuditRunRecord(BaseModel):
    run_id: str
    timestamp: str
    visual_diff_score: float = Field(..., ge=0.0, le=1.0)
    tokens_saved: int = Field(default=0, ge=0)
    clusters_analyzed: int = Field(default=0, ge=0)
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    is_auto_remediated: bool = Field(default=False)

class AuditMetricGauge(BaseModel):
    metric_name: str
    value: float
    unit: str
    labels: Dict[str, str] = {}

class ComplianceDigest(BaseModel):
    audit_period: str
    total_audits: int
    mean_token_savings_pct: float
    sha256_audit_seal: str
    records: List[AuditRunRecord]
