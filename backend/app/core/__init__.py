"""Core package initialization."""
import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.core.config import settings

__all__ = ["settings"]

