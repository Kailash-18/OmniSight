"""
Unit test suite for ConcurrencyLeaseManager and DOM mutation locks.
"""
import time
import pytest
from backend.app.schemas.concurrency_schema import AcquireLeaseRequest
from backend.app.services.concurrency_service import ConcurrencyLeaseManager

@pytest.fixture
def manager():
    return ConcurrencyLeaseManager(default_ttl=5.0)

def test_acquire_and_release_lease(manager):
    req = AcquireLeaseRequest(run_id="run_101", target_selector=".hero-cta", url_path="/checkout", ttl_seconds=10.0)
    res = manager.acquire_lease(req)
    assert res.success is True
    assert res.lease is not None
    assert res.lease.run_id == "run_101"
    assert res.lease.target_selector == ".hero-cta"

    rel = manager.release_lease(res.lease.lease_id, "run_101")
    assert rel.released is True
    assert manager.get_active_leases().total_active == 0

def test_lease_ttl_expiration(manager):
    req = AcquireLeaseRequest(run_id="run_exp", target_selector=".badge", url_path="/", ttl_seconds=0.05)
    res = manager.acquire_lease(req)
    assert res.success is True
    time.sleep(0.1)
    active = manager.get_active_leases()
    assert active.total_active == 0
