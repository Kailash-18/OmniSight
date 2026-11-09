import hmac
import hashlib
import time
from typing import Dict
from backend.app.schemas.tenant_schemas import (
    TenantSession, TenantCreateRequest, TenantValidateResponse
)

class TenantIsolationService:
    def __init__(self, secret_key: str = 'omnisight-tenant-crypto-key'):
        self.secret_key = secret_key.encode('utf-8')
        self._tenants: Dict[str, TenantSession] = {}

    def create_tenant(self, req: TenantCreateRequest) -> TenantSession:
        token_data = f'{req.tenant_id}:{time.time()}'.encode('utf-8')
        token = hmac.new(self.secret_key, token_data, hashlib.sha256).hexdigest()
        session = TenantSession(
            tenant_id=req.tenant_id,
            session_token=token,
            max_parallel_runs=req.max_parallel_runs,
            active_runs=0,
            rate_limit_per_min=req.rate_limit_per_min,
            created_at=time.time()
        )
        self._tenants[req.tenant_id] = session
        return session

    def validate_session(self, tenant_id: str, session_token: str) -> TenantValidateResponse:
        session = self._tenants.get(tenant_id)
        if not session or session.session_token != session_token:
            return TenantValidateResponse(
                valid=False,
                tenant_id=tenant_id,
                quota_remaining=0,
                message='Invalid tenant identifier or unauthorized session token'
            )
        quota_left = max(0, session.max_parallel_runs - session.active_runs)
        return TenantValidateResponse(
            valid=True,
            tenant_id=tenant_id,
            quota_remaining=quota_left,
            message='Tenant session valid and authorized'
        )

    def acquire_run_slot(self, tenant_id: str) -> bool:
        session = self._tenants.get(tenant_id)
        if not session:
            return False
        if session.active_runs >= session.max_parallel_runs:
            return False
        session.active_runs += 1
        return True

    def release_run_slot(self, tenant_id: str):
        session = self._tenants.get(tenant_id)
        if session and session.active_runs > 0:
            session.active_runs -= 1

tenant_service = TenantIsolationService()
