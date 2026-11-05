"""
Root pytest configuration.
Ensures both backend and automation packages are on sys.path for end-to-end integration testing.
"""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
backend_root = repo_root / "backend"

for path in [repo_root, backend_root]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "real_auth: run with the real login check (no bypass)")


@pytest.fixture(autouse=True)
def _bypass_auth(request):
    """Existing API tests predate login; they run as an authenticated user unless marked real_auth."""
    if request.node.get_closest_marker("real_auth"):
        yield
        return
    from app.core.auth import require_auth
    from app.main import app
    app.dependency_overrides[require_auth] = lambda: "test-user"
    yield
    app.dependency_overrides.pop(require_auth, None)
