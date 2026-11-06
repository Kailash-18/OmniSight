import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_target_hosts_endpoint_public(client):
    res = client.get("/config/target-hosts")
    assert res.status_code == 200
    data = res.json()
    assert "allowed_hosts" in data
    assert "wildcard_enabled" in data


def test_is_host_allowed_wildcard():
    # Test specific wildcard
    settings.ALLOWED_TARGET_HOSTS = ["localhost", "*.flipkart.com", "staging.internal"]
    assert settings.is_host_allowed("www.flipkart.com") is True
    assert settings.is_host_allowed("flipkart.com") is True
    assert settings.is_host_allowed("sub.shop.flipkart.com") is True
    assert settings.is_host_allowed("amazon.com") is False

    # Test full wildcard
    settings.ALLOWED_TARGET_HOSTS = ["*"]
    assert settings.is_host_allowed("www.flipkart.com") is True
    assert settings.is_host_allowed("custom-app.internal") is True

    # Cloud metadata must be blocked even when wildcard is *
    assert settings.is_host_allowed("169.254.169.254") is False
    assert settings.is_host_allowed("metadata.google.internal") is False
