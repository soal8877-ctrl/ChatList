"""Модуль доступа к SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DB_PATH = Path(__file__).resolve().parent / "chatlist.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    prompt     TEXT    NOT NULL,
    tags       TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id      TEXT    NOT NULL,
    api_key_env TEXT    NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1,
    model_type  TEXT    NOT NULL DEFAULT 'openai'
);

CREATE TABLE IF NOT EXISTS results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL,
    model_id   INTEGER NOT NULL,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active   ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id  ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id   ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""

DEFAULT_SETTINGS: dict[str, str] = {
    "request_timeout": "30",
    "env_file": ".env",
    "log_requests": "0",
    "default_tags": "",
}

SEED_MODELS: list[dict[str, Any]] = [
    {
        "name": "GPT-4o",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_id": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "is_active": 0,
        "model_type": "openai",
    },
    {
        "name": "DeepSeek Chat",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "api_id": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "is_active": 0,
        "model_type": "deepseek",
    },
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        _seed_if_empty(conn)


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    settings_count = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    if settings_count == 0:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            DEFAULT_SETTINGS.items(),
        )

    models_count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    if models_count == 0:
        for model in SEED_MODELS:
            conn.execute(
                """
                INSERT INTO models (name, api_url, api_id, api_key_env, is_active, model_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    model["name"],
                    model["api_url"],
                    model["api_id"],
                    model["api_key_env"],
                    model["is_active"],
                    model["model_type"],
                ),
            )


# --- prompts ---


def add_prompt(prompt: str, tags: str | None = None) -> int:
    created_at = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (created_at, prompt, tags),
        )
        return int(cursor.lastrowid)


def list_prompts(search: str | None = None) -> list[sqlite3.Row]:
    with get_connection() as conn:
        if search:
            pattern = f"%{search}%"
            rows = conn.execute(
                """
                SELECT * FROM prompts
                WHERE prompt LIKE ? OR IFNULL(tags, '') LIKE ?
                ORDER BY created_at DESC
                """,
                (pattern, pattern),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM prompts ORDER BY created_at DESC"
            ).fetchall()
        return list(rows)


def get_prompt(prompt_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()


def delete_prompt(prompt_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))


# --- models ---


def add_model(
    name: str,
    api_url: str,
    api_id: str,
    api_key_env: str,
    is_active: bool = True,
    model_type: str = "openai",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, api_key_env, is_active, model_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, api_url, api_id, api_key_env, int(is_active), model_type),
        )
        return int(cursor.lastrowid)


def list_models(active_only: bool = False) -> list[sqlite3.Row]:
    with get_connection() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM models WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM models ORDER BY name").fetchall()
        return list(rows)


def get_model(model_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM models WHERE id = ?", (model_id,)
        ).fetchone()


def update_model(
    model_id: int,
    name: str,
    api_url: str,
    api_id: str,
    api_key_env: str,
    is_active: bool,
    model_type: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE models
            SET name = ?, api_url = ?, api_id = ?, api_key_env = ?,
                is_active = ?, model_type = ?
            WHERE id = ?
            """,
            (name, api_url, api_id, api_key_env, int(is_active), model_type, model_id),
        )


def set_model_active(model_id: int, is_active: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE models SET is_active = ? WHERE id = ?",
            (int(is_active), model_id),
        )


def delete_model(model_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM models WHERE id = ?", (model_id,))


# --- results ---


def add_result(prompt_id: int, model_id: int, response: str) -> int:
    created_at = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO results (prompt_id, model_id, response, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (prompt_id, model_id, response, created_at),
        )
        return int(cursor.lastrowid)


def list_results(search: str | None = None) -> list[sqlite3.Row]:
    with get_connection() as conn:
        if search:
            pattern = f"%{search}%"
            rows = conn.execute(
                """
                SELECT
                    r.id,
                    r.prompt_id,
                    r.model_id,
                    r.response,
                    r.created_at,
                    p.prompt AS prompt_text,
                    m.name AS model_name
                FROM results r
                JOIN prompts p ON p.id = r.prompt_id
                JOIN models m ON m.id = r.model_id
                WHERE r.response LIKE ?
                   OR p.prompt LIKE ?
                   OR m.name LIKE ?
                ORDER BY r.created_at DESC
                """,
                (pattern, pattern, pattern),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    r.id,
                    r.prompt_id,
                    r.model_id,
                    r.response,
                    r.created_at,
                    p.prompt AS prompt_text,
                    m.name AS model_name
                FROM results r
                JOIN prompts p ON p.id = r.prompt_id
                JOIN models m ON m.id = r.model_id
                ORDER BY r.created_at DESC
                """
            ).fetchall()
        return list(rows)


def delete_result(result_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM results WHERE id = ?", (result_id,))


# --- settings ---


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def list_settings() -> dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        return {row["key"]: row["value"] or "" for row in rows}
