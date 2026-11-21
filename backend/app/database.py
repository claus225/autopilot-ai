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
            CREATE TABLE IF NOT EXISTS security_permissions (
                permission_key TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1))
            )
        """)
        for permission_key in (
            "browser_automation",
            "local_pc_control",
            "social_publishing",
            "external_messages",
            "online_purchases",
        ):
            connection.execute(
                "INSERT OR IGNORE INTO security_permissions (permission_key, enabled) VALUES (?, 0)",
                (permission_key,),
            )
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                created_at TEXT NOT NULL
            )
        """)
        # One private owner only: there is deliberately no public signup table/API.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS owner_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_fingerprint TEXT PRIMARY KEY,
                csrf_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry
            ON auth_sessions(expires_at)
        """)


def create_owner_account(password_hash: str, created_at: str) -> bool:
    """Create the single owner once; never overwrite an existing credential."""
    initialize_database()
    with db_connection() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO owner_account (id, password_hash, created_at) VALUES (1, ?, ?)",
            (password_hash, created_at),
        )
        return cursor.rowcount == 1


def get_owner_account() -> dict | None:
    initialize_database()
    with db_connection() as connection:
        row = connection.execute(
            "SELECT id, password_hash, created_at FROM owner_account WHERE id = 1"
        ).fetchone()
        return dict(row) if row else None


def create_auth_session(
    session_fingerprint: str,
    csrf_fingerprint: str,
    created_at: str,
    expires_at: str,
) -> None:
    """Store only token fingerprints; raw session and CSRF tokens stay in cookies."""
    initialize_database()
    with db_connection() as connection:
        connection.execute(
            """
            INSERT INTO auth_sessions
                (session_fingerprint, csrf_fingerprint, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_fingerprint, csrf_fingerprint, created_at, expires_at),
        )


def get_auth_session(session_fingerprint: str) -> dict | None:
    initialize_database()
    with db_connection() as connection:
        row = connection.execute(
            """
            SELECT session_fingerprint, csrf_fingerprint, created_at, expires_at, revoked_at
            FROM auth_sessions WHERE session_fingerprint = ?
            """,
            (session_fingerprint,),
        ).fetchone()
        return dict(row) if row else None


def revoke_auth_session(session_fingerprint: str, revoked_at: str) -> bool:
    initialize_database()
    with db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE auth_sessions SET revoked_at = ?
            WHERE session_fingerprint = ? AND revoked_at IS NULL
            """,
            (revoked_at, session_fingerprint),
        )
        return cursor.rowcount == 1


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


def list_security_permissions() -> list[dict]:
    initialize_database()
    with db_connection() as connection:
        rows = connection.execute(
            "SELECT permission_key, enabled FROM security_permissions ORDER BY permission_key"
        ).fetchall()
        return [{"permission_key": row["permission_key"], "enabled": bool(row["enabled"])} for row in rows]


def record_permission_denial(permission_key: str) -> None:
    from datetime import datetime, timezone

    initialize_database()
    with db_connection() as connection:
        connection.execute(
            "INSERT INTO security_events (event_type, enabled, created_at) VALUES (?, 0, ?)",
            ("permission_enable_blocked:" + permission_key, datetime.now(timezone.utc).isoformat()),
        )
