import hashlib
import time
from backend.app.schemas.readiness_schemas import (
    ProductionReadinessChecklist, ReleaseSignOffRequest, ReleaseSignOffResponse
)

class ProductionReadinessService:
    def evaluate_readiness(self) -> ProductionReadinessChecklist:
        return ProductionReadinessChecklist()

    def record_sign_off(self, req: ReleaseSignOffRequest) -> ReleaseSignOffResponse:
        ts = time.time()
        raw = f'{req.engineer_id}:{req.approved}:{ts}'.encode('utf-8')
        manifest_hash = hashlib.sha256(raw).hexdigest()
        return ReleaseSignOffResponse(
            sign_off_id=f'sign-off-{int(ts)}',
            status='RELEASE_CERTIFIED' if req.approved else 'RELEASE_REJECTED',
            timestamp=ts,
            manifest_hash=manifest_hash
        )

readiness_service = ProductionReadinessService()
