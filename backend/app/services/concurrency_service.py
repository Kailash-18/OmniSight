"""
Concurrency Control Service for managing DOM mutation leases and preventing race conditions.
"""
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from backend.app.schemas.concurrency_schema import (
    LeaseStatus, AcquireLeaseRequest, AcquireLeaseResponse,
    ReleaseLeaseRequest, ReleaseLeaseResponse, RenewLeaseRequest,
    RenewLeaseResponse, LeaseRecord, ActiveLeasesResponse
)

class ConcurrencyLeaseManager:
    def __init__(self, default_ttl: float = 60.0):
        self.default_ttl = default_ttl
        self._leases_by_key: Dict[str, LeaseRecord] = {}
        self._lease_lookup: Dict[str, str] = {}
        self._lease_timestamps: Dict[str, float] = {}

    def _clean_expired(self):
        now = time.time()
        expired_ids = [lid for lid, exp in self._lease_timestamps.items() if now > exp]
        for lid in expired_ids:
            key = self._lease_lookup.get(lid)
            if key and key in self._leases_by_key:
                rec = self._leases_by_key[key]
                rec.status = LeaseStatus.EXPIRED
                del self._leases_by_key[key]
            self._lease_lookup.pop(lid, None)
            self._lease_timestamps.pop(lid, None)

    def _make_key(self, url_path: str, selector: str) -> str:
        return f"{url_path}::{selector}"

    def acquire_lease(self, req: AcquireLeaseRequest) -> AcquireLeaseResponse:
        self._clean_expired()
        key = self._make_key(req.url_path, req.target_selector)
        now_ts = time.time()

        if key in self._leases_by_key:
            existing = self._leases_by_key[key]
            if existing.run_id != req.run_id:
                return AcquireLeaseResponse(
                    success=False,
                    lease=None,
                    rejection_reason=f"MUTATION_CONFLICT: Selector '{req.target_selector}' locked by run '{existing.run_id}' until {existing.expires_at}"
                )
            else:
                exp_ts = now_ts + req.ttl_seconds
                existing.expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat()
                existing.renewed_count += 1
                self._lease_timestamps[existing.lease_id] = exp_ts
                return AcquireLeaseResponse(success=True, lease=existing)

        lease_id = f"lease_{uuid.uuid4().hex[:12]}"
        exp_ts = now_ts + req.ttl_seconds
        acq_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()
        exp_iso = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat()

        record = LeaseRecord(
            lease_id=lease_id,
            run_id=req.run_id,
            target_selector=req.target_selector,
            url_path=req.url_path,
            status=LeaseStatus.ACTIVE,
            acquired_at=acq_iso,
            expires_at=exp_iso,
            renewed_count=0,
            requester_id=req.requester_id
        )
        self._leases_by_key[key] = record
        self._lease_lookup[lease_id] = key
        self._lease_timestamps[lease_id] = exp_ts

        return AcquireLeaseResponse(success=True, lease=record)

    def get_active_leases(self) -> ActiveLeasesResponse:
        self._clean_expired()
        active = list(self._leases_by_key.values())
        return ActiveLeasesResponse(total_active=len(active), leases=active)

concurrency_manager = ConcurrencyLeaseManager()
