from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ORIGIN = "http://localhost:5173"


def test_auth_setup_requires_configured_secret_and_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "setup-guard.db"))
    monkeypatch.delenv("AUTOPILOT_SETUP_TOKEN", raising=False)
    response = client.post(
        "/api/auth/setup",
        headers={"Origin": ORIGIN},
        json={"setup_token": "x" * 32, "password": "Une phrase secrète très longue"},
    )
    assert response.status_code == 403


def test_owner_setup_login_me_and_csrf_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "owner-auth.db"))
    monkeypatch.setenv("AUTOPILOT_SETUP_TOKEN", "setup-secret-" + "x" * 40)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    headers = {"Origin": ORIGIN}

    setup = client.post(
        "/api/auth/setup",
        headers=headers,
        json={
            "setup_token": "setup-secret-" + "x" * 40,
            "password": "Une phrase secrète très longue 2026!",
        },
    )
    assert setup.status_code == 200
    assert setup.json()["authenticated"] is True
    assert "autopilot_session" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    csrf = me.json()["csrf_token"]
    assert csrf

    duplicate_setup = client.post(
        "/api/auth/setup",
        headers=headers,
        json={
            "setup_token": "setup-secret-" + "x" * 40,
            "password": "Une autre phrase secrète très longue!",
        },
    )
    assert duplicate_setup.status_code == 409

    logout_without_csrf = client.post("/api/auth/logout", headers=headers)
    assert logout_without_csrf.status_code == 403

    logout = client.post(
        "/api/auth/logout",
        headers={**headers, "X-CSRF-Token": csrf},
    )
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get("/api/auth/me").status_code == 401

    login = client.post(
        "/api/auth/login",
        headers=headers,
        json={"password": "Une phrase secrète très longue 2026!"},
    )
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_login_rejects_wrong_password_and_untrusted_origin(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "login-guard.db"))
    monkeypatch.setenv("AUTOPILOT_SETUP_TOKEN", "setup-secret-" + "x" * 40)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    client.post(
        "/api/auth/setup",
        headers={"Origin": ORIGIN},
        json={
            "setup_token": "setup-secret-" + "x" * 40,
            "password": "Une phrase secrète très longue 2026!",
        },
    )
    wrong = client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"password": "Un mauvais mot de passe vraiment long"},
    )
    assert wrong.status_code == 401
    untrusted = client.post(
        "/api/auth/login",
        headers={"Origin": "https://evil.example"},
        json={"password": "Une phrase secrète très longue 2026!"},
    )
    assert untrusted.status_code == 403


def test_private_api_routes_require_owner_session_and_csrf(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "api-guard.db"))
    monkeypatch.setenv("AUTOPILOT_SETUP_TOKEN", "setup-secret-" + "z" * 40)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")

    owner = TestClient(app)
    setup = owner.post(
        "/api/auth/setup",
        headers={"Origin": ORIGIN},
        json={
            "setup_token": "setup-secret-" + "z" * 40,
            "password": "Mot de passe propriétaire long 2026!",
        },
    )
    assert setup.status_code == 200

    anonymous = TestClient(app)
    assert anonymous.get("/api/tasks").status_code == 401
    assert anonymous.post("/api/tasks", json={"title": "Sans session"}).status_code == 401

    # Read-only private routes require a session.
    assert owner.get("/api/tasks").status_code == 200

    # Mutations require both the trusted origin and the session-bound CSRF token.
    denied = owner.post(
        "/api/tasks",
        headers={"Origin": ORIGIN},
        json={"title": "Sans CSRF"},
    )
    assert denied.status_code == 403

    me = owner.get("/api/auth/me")
    csrf = me.json()["csrf_token"]
    accepted = owner.post(
        "/api/tasks",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json={"title": "Avec protection"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["item"]["title"] == "Avec protection"

    # Revoking the session blocks subsequent private reads.
    owner.post(
        "/api/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )
    assert owner.get("/api/tasks").status_code == 401


def test_production_api_fails_closed_until_owner_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "production-lock.db"))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTOPILOT_SETUP_TOKEN", raising=False)
    response = client.get("/api/tasks")
    assert response.status_code == 423
    assert client.get("/api/auth/status").status_code == 200
    assert client.get("/api/health").status_code == 200



def test_login_throttles_after_five_attempts(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import auth_routes

    auth_routes._login_attempts.clear()
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "login-throttle.db"))
    monkeypatch.setenv("AUTOPILOT_SETUP_TOKEN", "setup-secret-" + "t" * 40)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    owner = TestClient(app)
    setup = owner.post(
        "/api/auth/setup",
        headers={"Origin": ORIGIN},
        json={
            "setup_token": "setup-secret-" + "t" * 40,
            "password": "Mot de passe propriétaire long 2026!",
        },
    )
    assert setup.status_code == 200

    for _ in range(5):
        failed = owner.post(
            "/api/auth/login",
            headers={"Origin": ORIGIN},
            json={"password": "Mot de passe incorrect vraiment long"},
        )
        assert failed.status_code == 401

    blocked = owner.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"password": "Mot de passe propriétaire long 2026!"},
    )
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "900"
    auth_routes._login_attempts.clear()



def test_login_limiter_bounds_distinct_client_entries():
    from app import auth_routes

    auth_routes._login_attempts.clear()
    for index in range(auth_routes._LOGIN_MAX_CLIENTS):
        assert auth_routes._consume_login_attempt(f"192.0.2.{index}") is True

    assert auth_routes._consume_login_attempt("198.51.100.1") is False
    assert len(auth_routes._login_attempts) == auth_routes._LOGIN_MAX_CLIENTS
    auth_routes._login_attempts.clear()
