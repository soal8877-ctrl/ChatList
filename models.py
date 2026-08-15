"""Работа с нейросетями: активные модели и проверка API-ключей."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from db import Database


@dataclass(frozen=True)
class ActiveModel:
    id: int
    name: str
    api_url: str
    api_id: str
    api_key: str


class MissingApiKeyError(Exception):
    def __init__(self, model_name: str, api_id: str, hint: str = "") -> None:
        self.model_name = model_name
        self.api_id = api_id
        msg = f"Для модели «{model_name}» не задан ключ {api_id} в .env"
        if hint:
            msg = f"{msg} {hint}"
        super().__init__(msg)


def load_env(env_path: str | Path | None = None) -> Path | None:
    """Загружает .env из указанного пути, рядом с модулем или из cwd."""
    candidates: list[Path] = []
    if env_path is not None:
        candidates.append(Path(env_path))
    else:
        candidates.append(Path(__file__).resolve().parent / ".env")
        candidates.append(Path.cwd() / ".env")

    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            load_dotenv(path, override=True)
            return path
    return None


def get_active_models(db: Database) -> list[ActiveModel]:
    """Активные модели с ключами из окружения. Без ключа — MissingApiKeyError."""
    env_file = load_env()
    result: list[ActiveModel] = []
    for row in db.list_models(active_only=True):
        api_id = row["api_id"]
        key = os.getenv(api_id, "").strip()
        if not key:
            hint = (
                "Файл .env не найден или пуст. Сохраните .env и перезапустите приложение."
                if env_file is None
                else f"Проверьте переменную в файле {env_file}."
            )
            raise MissingApiKeyError(row["name"], api_id, hint)
        result.append(
            ActiveModel(
                id=int(row["id"]),
                name=row["name"],
                api_url=row["api_url"],
                api_id=api_id,
                api_key=key,
            )
        )
    return result


def validate_active_models(db: Database) -> list[str]:
    """Возвращает список ошибок по активным моделям без ключа."""
    load_env()
    errors: list[str] = []
    for row in db.list_models(active_only=True):
        api_id = row["api_id"]
        if not os.getenv(api_id, "").strip():
            errors.append(f"«{row['name']}»: нет переменной {api_id}")
    return errors
