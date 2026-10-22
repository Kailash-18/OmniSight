"""
Test configuration and fixtures for backend test suite.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend root directory is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app, runs_db


@pytest.fixture(autouse=True)
def reset_runs_db():
    """Clear in-memory database between test runs for deterministic assertions."""
    runs_db.clear()
    yield
    runs_db.clear()


@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)
