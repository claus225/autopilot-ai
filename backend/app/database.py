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
