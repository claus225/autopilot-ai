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
