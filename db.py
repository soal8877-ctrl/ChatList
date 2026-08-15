"""Доступ к SQLite. Весь SQL только в этом модуле."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "chatlist.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    prompt     TEXT    NOT NULL,
    tags       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS models (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL UNIQUE,
    api_url   TEXT    NOT NULL,
    api_id    TEXT    NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
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
    value TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


class Database:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def close(self) -> None:
        self._conn.close()

    def init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    # --- prompts ---

    def create_prompt(self, prompt: str, tags: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (_now_iso(), prompt, tags),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_prompt(self, prompt_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM prompts WHERE id = ?", (prompt_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list_prompts(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM prompts ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def search_prompts(self, query: str) -> list[dict[str, Any]]:
        like = f"%{query}%"
        rows = self._conn.execute(
            """
            SELECT * FROM prompts
            WHERE prompt LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC
            """,
            (like, like),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_prompt(self, prompt_id: int) -> None:
        self._conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        self._conn.commit()

    def update_prompt(
        self,
        prompt_id: int,
        *,
        prompt: str | None = None,
        tags: str | None = None,
    ) -> None:
        current = self.get_prompt(prompt_id)
        if current is None:
            raise ValueError(f"Промт id={prompt_id} не найден")
        self._conn.execute(
            "UPDATE prompts SET prompt = ?, tags = ? WHERE id = ?",
            (
                prompt if prompt is not None else current["prompt"],
                tags if tags is not None else current["tags"],
                prompt_id,
            ),
        )
        self._conn.commit()

    # --- models ---

    def create_model(
        self,
        name: str,
        api_url: str,
        api_id: str,
        is_active: bool = True,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (name, api_url, api_id, 1 if is_active else 0),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_model(self, model_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM models WHERE id = ?", (model_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list_models(self, active_only: bool = False) -> list[dict[str, Any]]:
        if active_only:
            rows = self._conn.execute(
                "SELECT * FROM models WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM models ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_model(
        self,
        model_id: int,
        *,
        name: str | None = None,
        api_url: str | None = None,
        api_id: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        current = self.get_model(model_id)
        if current is None:
            raise ValueError(f"Модель id={model_id} не найдена")
        self._conn.execute(
            """
            UPDATE models
            SET name = ?, api_url = ?, api_id = ?, is_active = ?
            WHERE id = ?
            """,
            (
                name if name is not None else current["name"],
                api_url if api_url is not None else current["api_url"],
                api_id if api_id is not None else current["api_id"],
                (
                    (1 if is_active else 0)
                    if is_active is not None
                    else current["is_active"]
                ),
                model_id,
            ),
        )
        self._conn.commit()

    def delete_model(self, model_id: int) -> None:
        self._conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        self._conn.commit()

    # --- results ---

    def save_result(self, prompt_id: int, model_id: int, response: str) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO results (prompt_id, model_id, response, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (prompt_id, model_id, response, _now_iso()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_results(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT r.*, p.prompt AS prompt_text, m.name AS model_name
            FROM results r
            JOIN prompts p ON p.id = r.prompt_id
            JOIN models m ON m.id = r.model_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_result(self, result_id: int) -> None:
        self._conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
        self._conn.commit()

    # --- settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def seed_default_models(self) -> None:
        """Сиды: четыре бесплатные модели OpenRouter (:free)."""
        openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        api_id = "OPENROUTER_API_KEY"
        defaults = [
            "google/gemma-4-31b-it:free",
            "openai/gpt-oss-20b:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "liquid/lfm-2.5-2.6b:free",
        ]
        legacy = {
            "gpt-4o-mini",
            "deepseek-chat",
            "openai/gpt-4o-mini",
            "deepseek/deepseek-chat",
        }

        existing = {m["name"]: m for m in self.list_models()}

        for name, row in existing.items():
            if name in legacy:
                self.update_model(int(row["id"]), is_active=False)

        for name in defaults:
            row = existing.get(name)
            if row is None:
                self.create_model(name, openrouter_url, api_id, is_active=True)
            else:
                self.update_model(
                    int(row["id"]),
                    api_url=openrouter_url,
                    api_id=api_id,
                    is_active=True,
                )

