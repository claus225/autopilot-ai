from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3
from collections.abc import Iterator

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "autopilot.db"


def database_path() -> Path:
    return Path(os.getenv("AUTOPILOT_DB_PATH", str(DEFAULT_DB)))


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK (status IN ('todo', 'completed')),
                created_at TEXT NOT NULL,
                due_date TEXT
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(tasks)")
        }
        if "due_date" not in columns:
            connection.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)
        connection.execute("""
            INSERT OR IGNORE INTO security_settings (setting_key, setting_value)
            VALUES ('emergency_stop_enabled', 'false')
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                created_at TEXT NOT NULL
            )
        """)


def create_task(title: str, description: str, created_at: str, due_date: str | None = None) -> dict:
    initialize_database()
    with db_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, description, created_at, due_date) VALUES (?, ?, ?, ?)",
            (title, description, created_at, due_date),
        )
        row = connection.execute(
            "SELECT id, title, description, status, created_at, due_date FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def list_tasks() -> list[dict]:
    initialize_database()
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, description, status, created_at, due_date FROM tasks ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def update_task_status(task_id: int, status: str) -> dict | None:
    initialize_database()
    with db_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, description, status, created_at, due_date FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return dict(row)


def get_emergency_stop() -> bool:
    initialize_database()
    with db_connection() as connection:
        row = connection.execute(
            "SELECT setting_value FROM security_settings WHERE setting_key = 'emergency_stop_enabled'"
        ).fetchone()
        return bool(row and row["setting_value"] == "true")


def set_emergency_stop(enabled: bool) -> None:
    from datetime import datetime, timezone

    initialize_database()
    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO security_settings (setting_key, setting_value)
            VALUES ('emergency_stop_enabled', ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """,
            ("true" if enabled else "false",),
        )
        connection.execute(
            "INSERT INTO security_events (event_type, enabled, created_at) VALUES (?, ?, ?)",
            ("emergency_stop_changed", int(enabled), datetime.now(timezone.utc).isoformat()),
        )


def list_security_events(limit: int = 20) -> list[dict]:
    initialize_database()
    safe_limit = max(1, min(limit, 50))
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT id, event_type, enabled, created_at FROM security_events ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
        return [{**dict(row), "enabled": bool(row["enabled"])} for row in rows]
