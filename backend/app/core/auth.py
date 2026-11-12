"""
Dashboard login for OmniSight: signed bearer tokens (stdlib HMAC, no database),
one reviewer account from env, and a per-process service token for launched test runs.
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time

from fastapi import HTTPException, Request, status

from app.core.config import settings

TOKEN_TTL_SECONDS = 8 * 60 * 60
PUBLIC_PATHS = {"/health", "/health/liveness", "/health/readiness", "/api/system/concurrency", "/auth/login", "/config/target-hosts", "/webhook/build", "/webhook/github/pull-request", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}

# Handed only to test processes this backend starts, so they can report progress.
SERVICE_TOKEN = secrets.token_urlsafe(32)
# What a launched test process may call: its run record and sub-routes, plus the Action Engine.
# Not listing runs, starting runs, or anything account-related.
SERVICE_PATHS = re.compile(r"^/runs/(?!active$|metrics(?:/|$))[^/]+(?:/.*)?$|^/action-engine/parse$|^/api/milestones$")
# ponytail: random key when unset means tokens die on restart (users sign in again); set OMNISIGHT_SECRET_KEY to keep them.
_SECRET = (settings.OMNISIGHT_SECRET_KEY or secrets.token_urlsafe(32)).encode()


class LoginNotConfigured(Exception):
    pass


def _sign(body: str) -> str:
    return hmac.new(_SECRET, body.encode(), hashlib.sha256).hexdigest()


def create_token(username: str, now: float | None = None) -> tuple[str, int]:
    exp = int((time.time() if now is None else now) + TOKEN_TTL_SECONDS)
    body = base64.urlsafe_b64encode(json.dumps({"u": username, "exp": exp}).encode()).decode()
    return f"{body}.{_sign(body)}", exp


def verify_token(token: str, now: float | None = None) -> str | None:
    body, _, sig = token.rpartition(".")
    if not body or not hmac.compare_digest(sig.encode(), _sign(body).encode()):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(body.encode()))
    except ValueError:
        return None
    if data.get("exp", 0) < (time.time() if now is None else now):
        return None
    return data.get("u") or None


def _configured_accounts() -> dict[str, str]:
    """Returns configured login accounts; empty when primary login is unconfigured."""
    if not settings.OMNISIGHT_USERNAME or not settings.OMNISIGHT_PASSWORD:
        return {}
    accounts: dict[str, str] = {}
    for username, password in getattr(settings, "OMNISIGHT_USERS", {}).items():
        if username and password:
            accounts[username] = password
    accounts[settings.OMNISIGHT_USERNAME] = settings.OMNISIGHT_PASSWORD
    return accounts


def check_credentials(username: str, password: str) -> bool:
    accounts = _configured_accounts()
    if not accounts:
        raise LoginNotConfigured()
    matched = False
    for expected_user, expected_pass in accounts.items():
        user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
        pass_ok = hmac.compare_digest(password.encode(), expected_pass.encode())
        matched |= user_ok and pass_ok
    return matched


def require_auth(request: Request) -> str | None:
    """App-wide dependency: every route except PUBLIC_PATHS needs a user token or the service token."""
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS or request.url.path.startswith("/health"): 
        return None
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if token and hmac.compare_digest(token.encode(), SERVICE_TOKEN.encode()):
        if SERVICE_PATHS.match(request.url.path):
            return "omnisight-runner"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not allowed for the test runner",
                            headers={"WWW-Authenticate": "Bearer"})
    user = verify_token(token) if token else None
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
