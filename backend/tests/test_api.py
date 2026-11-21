from fastapi.testclient import TestClient
from app.main import app

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

    listed = client.get("/api/tasks")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["items"][0]["id"] == item["id"]


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
