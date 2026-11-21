"""Minimal, read-only Telegram Bot API connection check.

The bot token is read only from the server environment and is never returned.
No messages are sent and no chat settings are changed by this module.
"""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def get_telegram_status() -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {
            "configured": False,
            "connected": False,
            "bot": None,
            "mode": "not_configured",
            "message": "Ajoute TELEGRAM_BOT_TOKEN dans les variables d’environnement du serveur.",
            "sending_enabled": False,
        }

    request = Request(
        f"https://api.telegram.org/bot{token}/getMe",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok") or not isinstance(payload.get("result"), dict):
            return {
                "configured": True,
                "connected": False,
                "bot": None,
                "mode": "telegram_rejected_token",
                "message": "Telegram n’a pas validé le token. Vérifie sa configuration côté serveur.",
                "sending_enabled": False,
            }
        bot = payload["result"]
        return {
            "configured": True,
            "connected": True,
            "bot": {
                "id": bot.get("id"),
                "username": bot.get("username"),
                "first_name": bot.get("first_name"),
                "can_join_groups": bot.get("can_join_groups"),
                "can_read_all_group_messages": bot.get("can_read_all_group_messages"),
            },
            "mode": "connected_read_only",
            "message": "Bot connecté. Les publications et modifications restent désactivées.",
            "sending_enabled": False,
        }
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return {
            "configured": True,
            "connected": False,
            "bot": None,
            "mode": "telegram_unavailable",
            "message": "Impossible de vérifier le bot auprès de Telegram pour le moment.",
            "sending_enabled": False,
        }
