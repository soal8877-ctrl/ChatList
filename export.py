"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import models


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def temp_results_to_markdown(prompt: str, items: list[models.TempResult]) -> str:
    lines = [
        "# ChatList — экспорт",
        "",
        f"**Дата:** {_utc_now_iso()}",
        "",
        "## Промт",
        "",
        prompt,
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"## {item.model_name}",
                "",
                item.response,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def temp_results_to_json(prompt: str, items: list[models.TempResult]) -> str:
    payload = {
        "exported_at": _utc_now_iso(),
        "prompt": prompt,
        "results": [
            {
                "model_name": item.model_name,
                "model_id": item.model_id,
                "response": item.response,
                "selected": item.selected,
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def saved_results_to_markdown(items: list[models.Result]) -> str:
    lines = ["# ChatList — сохранённые результаты", "", f"**Дата:** {_utc_now_iso()}", ""]
    for item in items:
        lines.extend(
            [
                f"## {item.model_name}",
                "",
                f"**Промт:** {item.prompt_text}",
                "",
                f"**Дата сохранения:** {item.created_at}",
                "",
                item.response,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def saved_results_to_json(items: list[models.Result]) -> str:
    payload = {
        "exported_at": _utc_now_iso(),
        "results": [
            {
                "id": item.id,
                "prompt_id": item.prompt_id,
                "model_id": item.model_id,
                "model_name": item.model_name,
                "prompt_text": item.prompt_text,
                "response": item.response,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
