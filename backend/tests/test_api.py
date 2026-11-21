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


def test_assistant_status_defaults_to_rules_only(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    response = client.get("/api/assistant/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["mode"] == "rules_only"
    assert response.json()["api_key_present"] is False


def test_assistant_status_never_claims_unimplemented_provider_is_connected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "example")
    monkeypatch.setenv("AI_API_KEY", "test-placeholder")
    response = client.get("/api/assistant/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["mode"] == "not_implemented"
