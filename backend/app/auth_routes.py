"""Private single-owner authentication endpoints.

The API remains local-only until the separate deployment security checklist is met.
"""
import hmac
import os
from datetime import datetime, timezone
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import hash_password, verify_password
from .auth_service import (
    create_owner_session,
    get_active_owner_session,
    revoke_owner_session,
    verify_session_csrf,
)
from .database import create_owner_account, get_owner_account

router = APIRouter(prefix="/api/auth", tags=["authentication"])
SESSION_COOKIE = "autopilot_session"
CSRF_COOKIE = "autopilot_csrf"

# In-process defense in depth; hosting still needs a shared proxy limiter.
_LOGIN_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_ATTEMPTS = 5
_login_attempts: dict[str, deque] = defaultdict(deque)
_login_lock = Lock()


def _consume_login_attempt(client_ip: str) -> bool:
    now = monotonic()
    key = client_ip or "unknown"
    with _login_lock:
        bucket = _login_attempts[key]
        while bucket and now - bucket[0] >= _LOGIN_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _LOGIN_MAX_ATTEMPTS:
            return False
        bucket.append(now)
        if len(_login_attempts) > 1024:
            stale = [ip for ip, attempts in _login_attempts.items()
                     if not attempts or now - attempts[-1] >= _LOGIN_WINDOW_SECONDS]
            for ip in stale:
                _login_attempts.pop(ip, None)
        return True


def _clear_login_attempts(client_ip: str) -> None:
    with _login_lock:
        _login_attempts.pop(client_ip or "unknown", None)


class SetupRequest(BaseModel):
    setup_token: str = Field(min_length=32, max_length=512)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    password: str = Field(min_length=12, max_length=1024)


def _origin_is_allowed(request: Request) -> bool:
    expected = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    origin = request.headers.get("origin", "").rstrip("/")
    return bool(origin) and hmac.compare_digest(origin, expected)


def _cookie_secure() -> bool:
    # HTTPS is the default. Set AUTH_COOKIE_SECURE=false only for local HTTP development.
    return os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true"


def _set_session_cookies(response: JSONResponse, session: str, csrf: str, expires_at: datetime) -> None:
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    common = {"max_age": max_age, "expires": expires_at, "path": "/api", "secure": _cookie_secure(), "samesite": "strict"}
    response.set_cookie(SESSION_COOKIE, session, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)


def _clear_session_cookies(response: JSONResponse) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/api", secure=_cookie_secure(), httponly=True, samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/api", secure=_cookie_secure(), httponly=False, samesite="strict")


def _session(request: Request) -> dict | None:
    return get_active_owner_session(request.cookies.get(SESSION_COOKIE, ""))


@router.get("/status")
def auth_status():
    owner_exists = get_owner_account() is not None
    setup_available = not owner_exists and len(os.getenv("AUTOPILOT_SETUP_TOKEN", "")) >= 32
    production_lock = os.getenv("APP_ENV", "development").lower() == "production"
    return {
        "owner_configured": owner_exists,
        "setup_available": setup_available,
        "access_locked": not owner_exists and (production_lock or bool(os.getenv("AUTOPILOT_SETUP_TOKEN", "").strip())),
        "session_required": True,
    }


@router.post("/setup")
def setup_owner(payload: SetupRequest, request: Request):
    if not _origin_is_allowed(request):
        raise HTTPException(status_code=403, detail="Origine refusée.")
    expected = os.getenv("AUTOPILOT_SETUP_TOKEN", "")
    if len(expected) < 32 or not hmac.compare_digest(payload.setup_token, expected):
        raise HTTPException(status_code=403, detail="Configuration initiale non autorisée.")
    if get_owner_account() is not None:
        raise HTTPException(status_code=409, detail="Le compte propriétaire existe déjà.")
    try:
        password_hash = hash_password(payload.password)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    created = create_owner_account(password_hash, datetime.now(timezone.utc).isoformat())
    if not created:
        raise HTTPException(status_code=409, detail="Le compte propriétaire existe déjà.")
    session, csrf, expires = create_owner_session()
    response = JSONResponse({"authenticated": True, "message": "Compte propriétaire créé."})
    _set_session_cookies(response, session, csrf, expires)
    return response


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    if not _origin_is_allowed(request):
        raise HTTPException(status_code=403, detail="Origine refusée.")
    client_ip = request.client.host if request.client else "unknown"
    if not _consume_login_attempt(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives de connexion. Réessaie dans 15 minutes.",
            headers={"Retry-After": "900"},
        )
    owner = get_owner_account()
    if owner is None or not verify_password(payload.password, owner["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    _clear_login_attempts(client_ip)
    session, csrf, expires = create_owner_session()
    response = JSONResponse({"authenticated": True, "expires_at": expires.isoformat()})
    _set_session_cookies(response, session, csrf, expires)
    return response


@router.get("/me")
def current_owner(request: Request):
    session = _session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    return {"authenticated": True, "csrf_token": request.cookies.get(CSRF_COOKIE, "")}


@router.post("/logout")
def logout(request: Request):
    if not _origin_is_allowed(request):
        raise HTTPException(status_code=403, detail="Origine refusée.")
    session_token = request.cookies.get(SESSION_COOKIE, "")
    session = _session(request)
    csrf = request.headers.get("x-csrf-token", "")
    if session is None or not verify_session_csrf(session, csrf):
        raise HTTPException(status_code=403, detail="Jeton CSRF invalide.")
    revoke_owner_session(session_token)
    response = JSONResponse({"authenticated": False, "message": "Session fermée."})
    _clear_session_cookies(response)
    return response
