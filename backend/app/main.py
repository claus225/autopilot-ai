from datetime import date, datetime, timezone
from typing import Literal
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .database import create_task, list_tasks, update_task_status

app = FastAPI(
    title="AutoPilot AI API",
    version="0.3.0",
    description="Prototype sécurisé : organisation et planification simple de tâches, sans exécution externe.",
)

allowed_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


class TaskDraft(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Le titre ne peut pas être vide.")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return value.strip()


class TaskStatusUpdate(BaseModel):
    status: Literal["todo", "completed"]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "autopilot-ai-api", "version": "0.3.0"}


@app.post("/api/tasks/preview")
def preview_task(task: TaskDraft):
    """Return a non-executable task proposal. No external action occurs."""
    return {
        "status": "draft",
        "requires_confirmation": True,
        "execution_enabled": False,
        "task": task.model_dump(mode="json"),
        "message": "Proposition créée. Aucune action n'a été exécutée.",
    }


@app.get("/api/tasks")
def get_tasks():
    """Return locally stored task notes, newest first."""
    return {"items": list_tasks()}


@app.post("/api/tasks")
def add_task(task: TaskDraft):
    """Save a task note locally. Saving a note does not execute it."""
    created_at = datetime.now(timezone.utc).isoformat()
    due_date = task.due_date.isoformat() if task.due_date else None
    item = create_task(task.title, task.description, created_at, due_date)
    return {"item": item, "message": "Tâche enregistrée. Aucune action externe n'a été exécutée."}


@app.patch("/api/tasks/{task_id}/status")
def change_task_status(task_id: int, update: TaskStatusUpdate):
    """Mark a task note as todo or completed; this never runs the task."""
    item = update_task_status(task_id, update.status)
    if item is None:
        raise HTTPException(status_code=404, detail="Tâche introuvable.")
    return {"item": item, "message": "Statut mis à jour. Aucune action externe n'a été exécutée."}
