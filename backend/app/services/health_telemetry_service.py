from datetime import datetime, timezone
from typing import List
from backend.app.schemas.health_schemas import HealthPulseReport, SubsystemStatus
from backend.app.services.adaptive_throttler_service import adaptive_throttler
from backend.app.services.snapshot_service import snapshot_engine
from backend.app.services.concurrency_service import concurrency_manager
from backend.app.services.canary_service import canary_engine

class HealthTelemetryService:
    def generate_pulse(self) -> HealthPulseReport:
        subsystems: List[SubsystemStatus] = []

        # 1. Throttler Subsystem
        t_stats = adaptive_throttler.get_stats()
        t_healthy = not t_stats.backpressure_active
        subsystems.append(SubsystemStatus(
            name='AdaptiveThrottler',
            healthy=t_healthy,
            latency_ms=1.2,
            details={'tokens': t_stats.current_tokens, 'active_workers': t_stats.active_workers}
        ))

        # 2. Snapshot Subsystem
        snap_count = len(snapshot_engine._snapshots)
        subsystems.append(SubsystemStatus(
            name='SnapshotEngine',
            healthy=True,
            latency_ms=0.8,
            details={'total_snapshots': snap_count}
        ))

        # 3. Concurrency Leases
        active_leases = len(concurrency_manager._leases_by_key)
        subsystems.append(SubsystemStatus(
            name='ConcurrencyLeases',
            healthy=True,
            latency_ms=0.5,
            details={'active_leases': active_leases}
        ))

        # 4. Canary Verifier
        subsystems.append(SubsystemStatus(
            name='CanaryVerifier',
            healthy=True,
            latency_ms=2.1,
            details={'registered_reports': len(canary_engine._cached_reports)}
        ))

        healthy_count = sum(1 for s in subsystems if s.healthy)
        overall_score = (healthy_count / len(subsystems)) * 100.0
        overall_healthy = (overall_score >= 75.0)

        return HealthPulseReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_health_score=round(overall_score, 1),
            healthy=overall_healthy,
            subsystems=subsystems,
            active_leases=active_leases,
            throttle_backpressure_ratio=0.0 if t_healthy else 0.5,
            snapshot_count=snap_count
        )

    def get_dlq_worker_telemetry(self) -> dict:
        from backend.app.services.dlq_service import dlq_service
        from backend.app.services.autoscale_service import worker_autoscaler
        from backend.app.services.quarantine_service import cluster_quarantine
        return {
            'dlq': dlq_service.get_stats().model_dump(),
            'autoscale': worker_autoscaler.get_status().model_dump(),
            'quarantine': cluster_quarantine.get_cluster_status().model_dump()
        }

health_pulse_hub = HealthTelemetryService()

# Prometheus Metrics Export
try:
    from prometheus_client import Gauge, Counter
    OMNISIGHT_SYSTEM_HEALTH = Gauge('omnisight_system_health_score', 'System composite health score index (0-100)')
    OMNISIGHT_THROTTLE_RATIO = Gauge('omnisight_adaptive_throttle_ratio', 'Current adaptive throttling backpressure ratio')
    OMNISIGHT_SNAPSHOTS_TOTAL = Counter('omnisight_state_snapshots_total', 'Total immutable state snapshots captured')
    def update_prometheus_health_metrics(report: HealthPulseReport):
        OMNISIGHT_SYSTEM_HEALTH.set(report.overall_health_score)
        OMNISIGHT_THROTTLE_RATIO.set(report.throttle_backpressure_ratio)
        OMNISIGHT_SNAPSHOTS_TOTAL.inc(0)
except Exception:
    def update_prometheus_health_metrics(report: HealthPulseReport):
        pass
