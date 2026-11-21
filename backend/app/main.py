from datetime import date, datetime, timedelta, timezone
from typing import Literal
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .database import create_task, list_tasks, update_task_status

app = FastAPI(
    title="AutoPilot AI API",
    version="0.3.0",
    description="Prototype sécurisé : organisation, échéances et suggestions fondées sur des règles, sans exécution externe.",
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


def build_reminders(tasks: list[dict], today: date, days: int = 7) -> dict:
    """Classify pending dated tasks; this only prepares reminder data."""
    horizon = today + timedelta(days=days)
    items = []
    for task in tasks:
        if task["status"] != "todo" or not task.get("due_date"):
            continue
        due = date.fromisoformat(task["due_date"])
        if due > horizon:
            continue
        if due < today:
            category = "overdue"
        elif due == today:
            category = "today"
        else:
            category = "upcoming"
        items.append({**task, "reminder_type": category})
    items.sort(key=lambda item: (item["due_date"], item["id"]))
    return {
        "items": items,
        "counts": {
            "overdue": sum(item["reminder_type"] == "overdue" for item in items),
            "today": sum(item["reminder_type"] == "today" for item in items),
            "upcoming": sum(item["reminder_type"] == "upcoming" for item in items),
        },
        "notifications_sent": False,
        "message": "Aperçu des échéances uniquement : aucune notification n'a été envoyée.",
    }



def build_next_action(tasks: list[dict], today: date) -> dict:
    """Suggest one task using transparent rules; this is not an AI model."""
    pending = [task for task in tasks if task["status"] == "todo"]
    dated = [task for task in pending if task.get("due_date")]
    overdue = sorted((t for t in dated if date.fromisoformat(t["due_date"]) < today), key=lambda t: (t["due_date"], t["id"]))
    due_today = sorted((t for t in dated if date.fromisoformat(t["due_date"]) == today), key=lambda t: (t["due_date"], t["id"]))
    upcoming = sorted((t for t in dated if date.fromisoformat(t["due_date"]) > today), key=lambda t: (t["due_date"], t["id"]))

    if overdue:
        chosen, reason, priority = overdue[0], "Cette tâche a dépassé sa date limite.", "urgent"
    elif due_today:
        chosen, reason, priority = due_today[0], "Cette tâche arrive à échéance aujourd'hui.", "high"
    elif upcoming:
        chosen, reason, priority = upcoming[0], "C'est la prochaine échéance enregistrée.", "normal"
    elif pending:
        chosen = sorted(pending, key=lambda t: (t["created_at"], t["id"]))[0]
        reason, priority = "Aucune échéance proche : commence par une tâche en attente.", "normal"
    else:
        chosen, reason, priority = None, "Aucune tâche en attente. Tu peux en ajouter une nouvelle.", "none"

    return {
        "suggestion": chosen,
        "priority": priority,
        "reason": reason,
        "method": "rules",
        "is_ai_generated": False,
        "execution_enabled": False,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "autopilot-ai-api", "version": "0.3.0"}


@app.get("/api/assistant/next-action")
def get_next_action():
    """Suggest one task using simple rules; never executes it."""
    return build_next_action(list_tasks(), date.today())


@app.get("/api/reminders")
def get_reminders(days: int = 7):
    """Return an overview of pending due dates; never sends notifications."""
    if days < 0 or days > 30:
        raise HTTPException(status_code=422, detail="La période doit être comprise entre 0 et 30 jours.")
    return build_reminders(list_tasks(), date.today(), days)


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
