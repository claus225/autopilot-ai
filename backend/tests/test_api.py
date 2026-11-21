from fastapi.testclient import TestClient
from datetime import date

from app.main import app, build_reminders

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_task_preview_never_executes():
    response = client.post(
        "/api/tasks/preview",
        json={"title": "Préparer un rappel", "description": "Exemple de test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["requires_confirmation"] is True
    assert body["execution_enabled"] is False


def test_create_and_list_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "test.db"))
    created = client.post(
        "/api/tasks",
        json={"title": "  Réviser  ", "description": "  Maths  "},
    )
    assert created.status_code == 200
    item = created.json()["item"]
    assert item["title"] == "Réviser"
    assert item["description"] == "Maths"
    assert item["status"] == "todo"
    assert item["due_date"] is None

    listed = client.get("/api/tasks")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == item["id"]


def test_task_due_date_is_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "due-date.db"))
    response = client.post(
        "/api/tasks",
        json={"title": "Préparer le devoir", "due_date": "2026-12-05"},
    )
    assert response.status_code == 200
    assert response.json()["item"]["due_date"] == "2026-12-05"


def test_task_can_be_marked_completed_without_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "status.db"))
    created = client.post("/api/tasks", json={"title": "Ranger les notes"})
    task_id = created.json()["item"]["id"]

    updated = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "completed"},
    )
    assert updated.status_code == 200
    assert updated.json()["item"]["status"] == "completed"
    assert "Aucune action externe" in updated.json()["message"]


def test_unknown_task_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "missing.db"))
    response = client.patch("/api/tasks/999/status", json={"status": "completed"})
    assert response.status_code == 404


def test_blank_task_title_is_rejected():
    response = client.post("/api/tasks", json={"title": "   "})
    assert response.status_code == 422



def test_reminder_overview_classifies_pending_tasks():
    tasks = [
        {"id": 1, "title": "En retard", "status": "todo", "due_date": "2026-11-20"},
        {"id": 2, "title": "Aujourd'hui", "status": "todo", "due_date": "2026-11-21"},
        {"id": 3, "title": "À venir", "status": "todo", "due_date": "2026-11-24"},
        {"id": 4, "title": "Terminée", "status": "completed", "due_date": "2026-11-21"},
        {"id": 5, "title": "Plus tard", "status": "todo", "due_date": "2026-12-15"},
        {"id": 6, "title": "Sans échéance", "status": "todo", "due_date": None},
    ]
    result = build_reminders(tasks, date(2026, 11, 21), days=7)
    assert result["counts"] == {"overdue": 1, "today": 1, "upcoming": 1}
    assert [item["id"] for item in result["items"]] == [1, 2, 3]
    assert result["notifications_sent"] is False


def test_reminder_endpoint_returns_preview_only(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "reminders.db"))
    client.post(
        "/api/tasks",
        json={"title": "Échéance aujourd'hui", "due_date": date.today().isoformat()},
    )
    response = client.get("/api/reminders")
    assert response.status_code == 200
    assert response.json()["counts"]["today"] == 1
    assert response.json()["notifications_sent"] is False


def test_reminder_window_is_limited():
    assert client.get("/api/reminders?days=31").status_code == 422


def test_next_action_prioritizes_overdue_task():
    from app.main import build_next_action

    tasks = [
        {"id": 1, "title": "Aujourd'hui", "status": "todo", "due_date": "2026-11-21", "created_at": "2026-11-20"},
        {"id": 2, "title": "En retard", "status": "todo", "due_date": "2026-11-19", "created_at": "2026-11-18"},
        {"id": 3, "title": "Terminée", "status": "completed", "due_date": "2026-11-18", "created_at": "2026-11-17"},
    ]
    result = build_next_action(tasks, date(2026, 11, 21))
    assert result["suggestion"]["id"] == 2
    assert result["priority"] == "urgent"
    assert result["method"] == "rules"
    assert result["is_ai_generated"] is False
    assert result["execution_enabled"] is False


def test_next_action_handles_empty_task_list():
    from app.main import build_next_action

    result = build_next_action([], date(2026, 11, 21))
    assert result["suggestion"] is None
    assert result["priority"] == "none"



def test_local_assistant_status_reports_missing_model(monkeypatch):
    from app.main import get_ollama_status
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"models": [{"name": "autre-modele:latest"}]}).encode("utf-8")

    monkeypatch.setattr("app.main.urlopen", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:0.8b")
    result = get_ollama_status()
    assert result["connected"] is False
    assert result["mode"] == "model_missing"
    assert result["model"] == "qwen3.5:0.8b"
    assert result["execution_enabled"] is False


def test_local_assistant_status_reports_ready_model(monkeypatch):
    from app.main import get_ollama_status
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"models": [{"name": "qwen3.5:0.8b"}]}).encode("utf-8")

    monkeypatch.setattr("app.main.urlopen", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:0.8b")
    result = get_ollama_status()
    assert result["connected"] is True
    assert result["mode"] == "local_ready"
    assert result["execution_enabled"] is False

def test_next_action_endpoint_is_read_only(monkeypatch):
    monkeypatch.setattr("app.main.list_tasks", lambda: [])
    response = client.get("/api/assistant/next-action")
    assert response.status_code == 200
    body = response.json()
    assert body["suggestion"] is None
    assert body["execution_enabled"] is False
    assert body["is_ai_generated"] is False


def test_local_assistant_status_is_safe_when_ollama_is_unavailable(monkeypatch):
    from app.main import get_ollama_status
    monkeypatch.setattr("app.main.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")))
    result = get_ollama_status()
    assert result["connected"] is False
    assert result["mode"] == "ollama_unavailable"
    assert result["execution_enabled"] is False


def test_local_assistant_chat_returns_reply_without_executing_actions(monkeypatch):
    monkeypatch.setattr("app.main.get_ollama_status", lambda: {
        "connected": True, "model": "qwen3.5:0.8b"
    })
    monkeypatch.setattr("app.main.generate_local_reply", lambda messages: "Bonjour !")
    response = client.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "Bonjour"}]
    })
    assert response.status_code == 200
    assert response.json()["reply"] == "Bonjour !"
    assert response.json()["execution_enabled"] is False


def test_local_assistant_chat_requires_user_last_message():
    response = client.post("/api/assistant/chat", json={
        "messages": [{"role": "assistant", "content": "Salut"}]
    })
    assert response.status_code == 422


def test_local_assistant_chat_returns_503_when_model_is_not_ready(monkeypatch):
    monkeypatch.setattr("app.main.get_ollama_status", lambda: {
        "connected": False, "model": "qwen3.5:0.8b",
        "message": "Ollama indisponible",
    })
    response = client.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "Bonjour"}]
    })
    assert response.status_code == 503
    assert response.json()["detail"] == "Ollama indisponible"



def test_security_status_defaults_to_protected_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "security-default.db"))
    response = client.get("/api/security/status")
    assert response.status_code == 200
    body = response.json()
    assert body["emergency_stop_enabled"] is False
    assert body["external_actions_enabled"] is False
    assert body["browser_automation_enabled"] is False
    assert body["local_agent_enabled"] is False
    assert body["chat_available"] is True


def test_emergency_stop_blocks_local_assistant_chat(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "security-stop.db"))
    response = client.post("/api/security/emergency-stop", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["emergency_stop_enabled"] is True

    chat = client.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "Bonjour"}]
    })
    assert chat.status_code == 423
    assert "Arrêt d’urgence activé" in chat.json()["detail"]

    response = client.post("/api/security/emergency-stop", json={"enabled": False})
    assert response.status_code == 200
    monkeypatch.setattr("app.main.get_ollama_status", lambda: {
        "connected": False, "model": "qwen3.5:0.8b", "message": "Ollama indisponible"
    })
    assert client.get("/api/security/status").json()["chat_available"] is True


def test_emergency_stop_persists_and_creates_metadata_audit_event(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_DB_PATH", str(tmp_path / "security-persist.db"))
    enabled = client.post("/api/security/emergency-stop", json={"enabled": True})
    assert enabled.status_code == 200
    assert client.get("/api/security/status").json()["emergency_stop_enabled"] is True

    events = client.get("/api/security/events")
    assert events.status_code == 200
    assert events.json()["items"][0]["event_type"] == "emergency_stop_changed"
    assert events.json()["items"][0]["enabled"] is True
    assert "content" not in events.json()["items"][0]


def test_security_events_limit_is_validated():
    assert client.get("/api/security/events?limit=51").status_code == 422
