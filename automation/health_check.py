"""
Store Connectivity and Health Check Validator.
Ensures target server is reachable, active, and verified as the OmniSight mock store.
"""

import urllib.request
import urllib.error
from typing import Tuple, Optional


def check_store_health(
    app_url: str = "http://localhost:5173", timeout: float = 3.0
) -> Tuple[bool, str, Optional[str]]:
    """
    Validates if the target URL is running and is verified as the everyday. store.

    Returns:
        (is_healthy, message, detected_url)
    """
    candidate_urls = [app_url]
    # If using default 5173, also check Vite fallback ports 5174 and 5175
    if "5173" in app_url:
        candidate_urls.extend([
            app_url.replace("5173", "5174"),
            app_url.replace("5173", "5175"),
        ])

    for url in candidate_urls:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "OmniSight-HealthCheck/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    content = response.read(4096).decode("utf-8", errors="ignore")
                    # Verify content matches mock store
                    if "everyday" in content.lower() or "root" in content.lower():
                        return True, f"Store verified and healthy at {url}", url
        except (urllib.error.URLError, OSError):
            continue

    return (
        False,
        f"Mock store not reachable at {app_url}. Start it with:\n  npm run dev --prefix app-under-test",
        None,
    )
