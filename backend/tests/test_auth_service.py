from datetime import datetime, timedelta, timezone

import pytest

from app.auth_service import (
    create_owner_session,
    get_active_owner_session,
    revoke_owner_session,
    verify_session_csrf,
)


def test_owner_session_is_stored_as_fingerprints_and_csrf_is_bound(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "owner-session.db"))
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)

    session_token, csrf_token, expires = create_owner_session(now=now)
    session = get_active_owner_session(session_token, now=now)

    assert session is not None
    assert expires == now + timedelta(hours=12)
    assert session["session_fingerprint"] != session_token
    assert session["csrf_fingerprint"] != csrf_token
    assert verify_session_csrf(session, csrf_token) is True
    assert verify_session_csrf(session, "incorrect-csrf-token") is False


def test_owner_session_expires_and_rejects_naive_clock(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "expiry.db"))
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    session_token, _, expires = create_owner_session(now=now)

    assert get_active_owner_session(session_token, now=expires) is None
    assert get_active_owner_session(session_token, now=datetime(2026, 11, 21, 12, 1)) is None


def test_owner_session_can_be_revoked(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "revoke.db"))
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    session_token, _, _ = create_owner_session(now=now)

    assert get_active_owner_session(session_token, now=now) is not None
    assert revoke_owner_session(session_token, now=now + timedelta(minutes=1)) is True
    assert revoke_owner_session(session_token, now=now + timedelta(minutes=2)) is False
    assert get_active_owner_session(session_token, now=now + timedelta(minutes=2)) is None


def test_session_lifetime_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "lifetime.db"))
    with pytest.raises(ValueError):
        create_owner_session(lifetime=timedelta(hours=25))
    with pytest.raises(ValueError):
        create_owner_session(lifetime=timedelta(seconds=0))
