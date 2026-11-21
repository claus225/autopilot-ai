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
