from app.database import (
    create_auth_session,
    create_owner_account,
    get_auth_session,
    get_owner_account,
    revoke_auth_session,
)


def test_owner_account_can_only_be_created_once(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "auth.db"))

    assert create_owner_account("$argon2id$first-hash", "2026-11-21T00:00:00+00:00") is True
    assert create_owner_account("$argon2id$replacement-hash", "2026-11-22T00:00:00+00:00") is False

    owner = get_owner_account()
    assert owner is not None
    assert owner["id"] == 1
    assert owner["password_hash"] == "$argon2id$first-hash"


def test_auth_session_stores_fingerprints_and_can_be_revoked(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "sessions.db"))
    session_fingerprint = "a" * 64
    csrf_fingerprint = "b" * 64

    create_auth_session(
        session_fingerprint,
        csrf_fingerprint,
        "2026-11-21T10:00:00+00:00",
        "2026-11-21T11:00:00+00:00",
    )

    session = get_auth_session(session_fingerprint)
    assert session is not None
    assert session["session_fingerprint"] == session_fingerprint
    assert session["csrf_fingerprint"] == csrf_fingerprint
    assert session["revoked_at"] is None

    assert revoke_auth_session(session_fingerprint, "2026-11-21T10:30:00+00:00") is True
    assert revoke_auth_session(session_fingerprint, "2026-11-21T10:31:00+00:00") is False
    assert get_auth_session(session_fingerprint)["revoked_at"] == "2026-11-21T10:30:00+00:00"


def test_unknown_auth_session_cannot_be_revoked(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "unknown.db"))
    assert get_auth_session("c" * 64) is None
    assert revoke_auth_session("c" * 64, "2026-11-21T10:00:00+00:00") is False
