"""Логирование запросов ChatList."""

from __future__ import annotations

import logging
from pathlib import Path

import db

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "chatlist.log"


def setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("chatlist")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def is_logging_enabled() -> bool:
    return db.get_setting("log_requests", "0") == "1"


def log_request(
    model_name: str,
    api_id: str,
    prompt: str,
    status: str,
    detail: str = "",
    duration_ms: int | None = None,
) -> None:
    if not is_logging_enabled():
        return

    prompt_preview = prompt.replace("\n", " ")[:120]
    parts = [
        f"model={model_name}",
        f"api_id={api_id}",
        f"status={status}",
        f'prompt="{prompt_preview}"',
    ]
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms}")
    if detail:
        parts.append(f"detail={detail[:200]}")

    setup_logger().info(" | ".join(parts))
