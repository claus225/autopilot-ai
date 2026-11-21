from datetime import date, datetime, timedelta, timezone
from typing import Literal
import os
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .telegram import get_telegram_status

from .database import (
    create_task, list_tasks, update_task_status, get_emergency_stop,
    set_emergency_stop as persist_emergency_stop, list_security_events,
    list_security_permissions, record_permission_denial,
)

app = FastAPI(
    title="AutoPilot AI API",
    version="0.3.0",
    description="Prototype sécurisé : organisation, échéances et suggestions fondées sur des règles, sans exécution externe.",
)

# Local-only guard, lightweight per-IP rate limit, and baseline response headers.
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_REQUESTS = 60
_rate_buckets: dict[str, deque] = defaultdict(deque)
_rate_lock = Lock()


def security_headers(response: JSONResponse | object):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.middleware("http")
async def protect_api(request: FastAPIRequest, call_next):
    client_host = request.client.host if request.client else ""
    # Starlette's in-process test client is allowed for automated tests only.
    is_test_client = client_host == "testclient"
    is_loopback = client_host in {"127.0.0.1", "::1", "localhost"}
    if not (is_loopback or is_test_client):
        return security_headers(JSONResponse(
            status_code=403,
            content={"detail": "API locale : les connexions distantes sont refusées."},
        ))

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 65536:
                return security_headers(JSONResponse(status_code=413, content={"detail": "Requête trop volumineuse."}))
        except ValueError:
            return security_headers(JSONResponse(status_code=400, content={"detail": "En-tête Content-Length invalide."}))

    now = monotonic()
    with _rate_lock:
        bucket = _rate_buckets[client_host]
        while bucket and now - bucket[0] >= _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _RATE_MAX_REQUESTS:
            return security_headers(JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Réessaie dans une minute."},
                headers={"Retry-After": "60"},
            ))
        bucket.append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


allowed_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


class EmergencyStopUpdate(BaseModel):
    enabled: bool


class PermissionUpdate(BaseModel):
    enabled: bool


PERMISSION_LABELS = {
    "browser_automation": "Automatisation du navigateur",
    "local_pc_control": "Contrôle de l’ordinateur",
    "social_publishing": "Publication sur les réseaux sociaux",
    "external_messages": "Envoi de messages externes",
    "online_purchases": "Achats en ligne",
}


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



class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=12)

    @field_validator("messages")
    @classmethod
    def last_message_must_be_user(cls, value: list[ChatTurn]) -> list[ChatTurn]:
        if value[-1].role != "user":
            raise ValueError("Le dernier message doit venir de l'utilisateur.")
        return value




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


@app.get("/api/telegram/status")
def telegram_status():
    """Check Telegram bot credentials without exposing the token or sending messages."""
    if get_emergency_stop():
        return {
            "configured": bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip()),
            "connected": False,
            "bot": None,
            "mode": "emergency_stop",
            "message": "Arrêt d’urgence activé : la connexion Telegram est suspendue.",
            "sending_enabled": False,
        }
    return get_telegram_status()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "autopilot-ai-api", "version": "0.3.0"}




def get_ollama_status() -> dict:
    """Check only the local Ollama service and configured model."""
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:0.8b")
    request = Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        installed = [item.get("name", "") for item in payload.get("models", [])]
        ready = model in installed
        return {
            "connected": ready, "provider": "Ollama local", "model": model,
            "mode": "local_ready" if ready else "model_missing",
            "message": "Assistant local prêt. Les messages restent sur cet ordinateur." if ready else "Ollama fonctionne, mais le modèle " + model + " n'est pas installé.",
            "installed_models": installed, "execution_enabled": False,
        }
    except (URLError, TimeoutError, OSError, ValueError):
        return {
            "connected": False, "provider": "Ollama local", "model": model,
            "mode": "ollama_unavailable",
            "message": "Ollama n'est pas démarré ou n'est pas installé sur cet ordinateur.",
            "installed_models": [], "execution_enabled": False,
        }


def generate_local_reply(messages: list[dict]) -> str:
    """Send chat text only to the Ollama service on this computer."""
    model = os.getenv("OLLAMA_MODEL", "qwen3.5:0.8b")
    system_message = {
        "role": "system",
        "content": "Tu es l’assistant d’organisation AutoPilot AI. Réponds clairement en français. Aide à comprendre, planifier et rédiger. Tu n’as aucun outil, aucun accès au système, au navigateur ou aux comptes. Ne prétends jamais avoir exécuté une action. Demande une confirmation humaine pour toute action externe.",
    }
    body = json.dumps({
        "model": model,
        "messages": [system_message, *messages],
        "stream": False,
        "keep_alive": "5m",
        "options": {"num_predict": 400, "temperature": 0.5},
    }).encode("utf-8")
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload.get("message", {}).get("content", "").strip()
        if not content:
            raise HTTPException(status_code=502, detail="Le modèle local n'a pas renvoyé de réponse.")
        return content
    except HTTPError as error:
        if error.code == 404:
            raise HTTPException(status_code=503, detail="Modèle local absent. Installe le modèle indiqué dans le guide.")
        raise HTTPException(status_code=502, detail="Le service IA local a renvoyé une erreur.")
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(status_code=503, detail="Ollama est indisponible. Vérifie qu'il est démarré sur cet ordinateur.")


@app.get("/api/security/status")
def security_status():
    return {
        "emergency_stop_enabled": get_emergency_stop(),
        "external_actions_enabled": False,
        "browser_automation_enabled": False,
        "local_agent_enabled": False,
        "chat_available": not get_emergency_stop(),
        "permissions": [
            {**item, "label": PERMISSION_LABELS[item["permission_key"]]}
            for item in list_security_permissions()
        ],
        "message": (
            "Arrêt d’urgence activé : le chat IA est suspendu."
            if get_emergency_stop()
            else "Mode protégé : aucune action externe ni automatisation n’est activée."
        ),
    }


@app.post("/api/security/emergency-stop")
def set_emergency_stop(update: EmergencyStopUpdate):
    persist_emergency_stop(update.enabled)
    return security_status()


@app.get("/api/security/permissions")
def security_permissions():
    return {
        "items": [
            {**item, "label": PERMISSION_LABELS[item["permission_key"]]}
            for item in list_security_permissions()
        ],
        "policy": "default_deny",
        "message": "Toutes les capacités externes restent désactivées dans cette version.",
    }


@app.patch("/api/security/permissions/{permission_key}")
def update_security_permission(permission_key: str, update: PermissionUpdate):
    if permission_key not in PERMISSION_LABELS:
        raise HTTPException(status_code=404, detail="Permission inconnue.")
    if update.enabled:
        record_permission_denial(permission_key)
        raise HTTPException(
            status_code=403,
            detail="Cette capacité n’est pas implémentée et ne peut pas être activée.",
        )
    return {
        "permission_key": permission_key,
        "enabled": False,
        "message": "Permission maintenue désactivée.",
    }


@app.get("/api/security/events")
def get_security_events(limit: int = 20):
    """Return metadata-only security events; message contents are never logged."""
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=422, detail="La limite doit être comprise entre 1 et 50.")
    return {"items": list_security_events(limit)}




@app.get("/api/assistant/status")
def assistant_status():
    return get_ollama_status()


@app.post("/api/assistant/chat")
def assistant_chat(chat: ChatRequest):
    if get_emergency_stop():
        raise HTTPException(status_code=423, detail="Arrêt d’urgence activé : le chat IA est suspendu.")
    status = get_ollama_status()
    if not status["connected"]:
        raise HTTPException(status_code=503, detail=status["message"])
    messages = [turn.model_dump() for turn in chat.messages]
    return {
        "reply": generate_local_reply(messages),
        "provider": "Ollama local",
        "model": status["model"],
        "execution_enabled": False,
    }


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


# Private owner authentication endpoints (route-level checks).
from .auth_routes import router as auth_router
app.include_router(auth_router)
