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


class ReleaseCertificationManifest(BaseModel):
    release_version: str = Field(default="1.0.0-final", description="Semantic release version tag")
    certification_timestamp: str = Field(..., description="ISO 8601 certification timestamp")
    compliance_seal: str = Field(..., description="HMAC-SHA256 signature sealing release integrity")
    certified_by: str = Field(default="Sri Khyathi", description="Lead system architect & engineer")
    environment: str = Field(default="production", description="Certified runtime deployment target")
    test_summary: Dict[str, Any] = Field(default_factory=dict, description="Test suite execution summary")
    subsystem_status: Dict[str, str] = Field(default_factory=dict, description="Subsystem operational status")
    audit_pass: bool = Field(default=True, description="Whether all compliance gates passed")

class VerifyCertificateRequest(BaseModel):
    certificate_id: str = Field(..., description="Certificate identifier or release version")
    compliance_seal: str = Field(..., description="Cryptographic seal to verify")

class VerifyCertificateResponse(BaseModel):
    valid: bool = Field(..., description="Whether cryptographic seal is authentic")
    certificate_id: str = Field(..., description="Target certificate identifier")
    message: str = Field(..., description="Verification result message")
    verified_at: str = Field(..., description="ISO 8601 verification timestamp")
