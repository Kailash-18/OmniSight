from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class SystemDiagnosticCheck(BaseModel):
    component: str = Field(..., description="Subsystem or engine under diagnostic evaluation")
    status: Literal["PASS", "WARN", "FAIL"] = Field(..., description="Evaluation outcome status")
    latency_ms: float = Field(..., description="Diagnostic execution latency in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Component-specific telemetry details")
    checked_at: str = Field(..., description="ISO 8601 evaluation timestamp")

class FullSystemDiagnosticsReport(BaseModel):
    overall_status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY"] = Field(..., description="Aggregate system health state")
    system_readiness_score: float = Field(..., description="System health index from 0.0 to 100.0")
    components_checked: int = Field(..., description="Total component diagnostics executed")
    passed_checks: int = Field(..., description="Count of passed checks")
    warnings: int = Field(..., description="Count of warning checks")
    failures: int = Field(..., description="Count of failed checks")
    checks: List[SystemDiagnosticCheck] = Field(default_factory=list, description="List of granular component checks")
    audit_digest: str = Field(..., description="SHA-256 cryptographic digest of diagnostic report")
    generated_at: str = Field(..., description="ISO 8601 report generation timestamp")
