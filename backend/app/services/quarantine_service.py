from typing import Dict, List, Optional
import time
from backend.app.schemas.quarantine_schemas import (
    QuarantineRecord, QuarantineRequest, QuarantineClusterStatus
)

class ClusterQuarantineService:
    def __init__(self, default_cluster_size: int = 10):
        self.default_cluster_size = default_cluster_size
        self._quarantined: Dict[str, QuarantineRecord] = {}

    def clear(self) -> None:
        self._quarantined.clear()

    def isolate_node(self, req: QuarantineRequest) -> QuarantineRecord:
        rec = QuarantineRecord(
            node_id=req.node_id,
            reason=req.reason,
            consecutive_failures=req.consecutive_failures,
            isolated_at=time.time(),
            quarantine_status='ISOLATED',
            probe_attempts=0
        )
        self._quarantined[req.node_id] = rec
        return rec

    def probe_node(self, node_id: str) -> QuarantineRecord:
        if node_id not in self._quarantined:
            raise KeyError(f'Node {node_id} is not in quarantine')
        rec = self._quarantined[node_id]
        rec.probe_attempts += 1
        rec.quarantine_status = 'PROBATION'
        return rec

    def release_node(self, node_id: str) -> QuarantineRecord:
        if node_id not in self._quarantined:
            raise KeyError(f'Node {node_id} is not in quarantine')
        rec = self._quarantined[node_id]
        rec.quarantine_status = 'RELEASED'
        return rec

    def is_isolated(self, node_id: str) -> bool:
        rec = self._quarantined.get(node_id)
        return bool(rec and rec.quarantine_status in ('ISOLATED', 'PROBATION'))

    def get_cluster_status(self) -> QuarantineClusterStatus:
        active_quarantine = [r for r in self._quarantined.values() if r.quarantine_status != 'RELEASED']
        q_count = len(active_quarantine)
        healthy = max(0, self.default_cluster_size - q_count)
        return QuarantineClusterStatus(
            total_nodes=self.default_cluster_size,
            healthy_nodes=healthy,
            quarantined_nodes=q_count,
            records=list(self._quarantined.values())
        )

cluster_quarantine = ClusterQuarantineService()
