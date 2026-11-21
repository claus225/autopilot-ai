"""Session lifecycle helpers for the private owner account.

Raw tokens are returned only to the caller so an HTTP layer can place them in
secure cookies. Only SHA-256 fingerprints are persisted.
"""
from datetime import datetime, timedelta, timezone

from .auth import create_secret_token, fingerprint_token, token_matches
from .database import create_auth_session, get_auth_session, revoke_auth_session


DEFAULT_SESSION_LIFETIME = timedelta(hours=12)
MAX_SESSION_LIFETIME = timedelta(hours=24)


def _utc_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La date doit inclure un fuseau horaire.")
    return value.astimezone(timezone.utc)


def create_owner_session(
    lifetime: timedelta = DEFAULT_SESSION_LIFETIME,
    now: datetime | None = None,
) -> tuple[str, str, datetime]:
    """Create a session and return raw session/CSRF tokens plus expiry."""
    if lifetime <= timedelta(0) or lifetime > MAX_SESSION_LIFETIME:
        raise ValueError("La durée de session doit être comprise entre 0 et 24 heures.")
    created = _utc_now(now)
    expires = created + lifetime
    session_token = create_secret_token()
    csrf_token = create_secret_token()
    create_auth_session(
        fingerprint_token(session_token),
        fingerprint_token(csrf_token),
        created.isoformat(),
        expires.isoformat(),
    )
    return session_token, csrf_token, expires


def get_active_owner_session(
    session_token: str,
    now: datetime | None = None,
) -> dict | None:
    """Return an active, unexpired session; invalid tokens fail closed."""
    if not isinstance(session_token, str) or not session_token:
        return None
    try:
        fingerprint = fingerprint_token(session_token)
        current = _utc_now(now)
    except (TypeError, ValueError):
        return None
    session = get_auth_session(fingerprint)
    if not session or session["revoked_at"] is not None:
        return None
    try:
        expires = datetime.fromisoformat(session["expires_at"])
        if expires.tzinfo is None or expires.utcoffset() is None:
            return None
        expires = expires.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None
    if expires <= current:
        return None
    return session


def verify_session_csrf(session: dict, csrf_token: str) -> bool:
    """Validate a CSRF token against the fingerprint bound to this session."""
    if not isinstance(session, dict):
        return False
    return token_matches(csrf_token, session.get("csrf_fingerprint", ""))


def revoke_owner_session(
    session_token: str,
    now: datetime | None = None,
) -> bool:
    """Revoke a session once; repeated revocations return False."""
    if not isinstance(session_token, str) or not session_token:
        return False
    try:
        fingerprint = fingerprint_token(session_token)
        revoked_at = _utc_now(now).isoformat()
    except (TypeError, ValueError):
        return False
    return revoke_auth_session(fingerprint, revoked_at)
