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
