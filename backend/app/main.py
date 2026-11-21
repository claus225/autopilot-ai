from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

app = FastAPI(
    title="AutoPilot AI API",
    version="0.1.0",
    description="Prototype sécurisé : préparation de tâches, sans exécution externe.",
)

allowed_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class TaskDraft(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "autopilot-ai-api", "version": "0.1.0"}


@app.post("/api/tasks/preview")
def preview_task(task: TaskDraft):
    """Create a non-executable task proposal. No browser or system action occurs."""
    return {
        "status": "draft",
        "requires_confirmation": True,
        "execution_enabled": False,
        "task": task.model_dump(),
        "message": "Proposition créée. Aucune action n'a été exécutée.",
    }
