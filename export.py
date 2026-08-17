"""Экспорт выбранных результатов в Markdown и JSON."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def results_to_json(rows: Sequence[object], prompt_text: str = "") -> str:
    items = []
    for row in rows:
        items.append(
            {
                "model": getattr(row, "model_name", None)
                or (row.get("model_name") if isinstance(row, dict) else ""),
                "response": getattr(row, "response", None)
                or (row.get("response") if isinstance(row, dict) else ""),
                "prompt": getattr(row, "prompt_text", None)
                or (
                    row.get("prompt_text")
                    if isinstance(row, dict)
                    else prompt_text
                )
                or prompt_text,
            }
        )
    payload = {"exported_at": _now(), "prompt": prompt_text, "results": items}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def results_to_markdown(rows: Sequence[object], prompt_text: str = "") -> str:
    lines = [
        "# ChatList export",
        "",
        f"Exported: `{_now()}`",
        "",
    ]
    if prompt_text:
        lines.extend(["## Prompt", "", prompt_text, ""])
    lines.append("## Answers")
    lines.append("")
    for row in rows:
        if isinstance(row, dict):
            name = row.get("model_name") or ""
            response = row.get("response") or ""
            prompt = row.get("prompt_text") or prompt_text
        else:
            name = getattr(row, "model_name", "")
            response = getattr(row, "response", "")
            prompt = getattr(row, "prompt_text", "") or prompt_text
        lines.append(f"### {name}")
        lines.append("")
        if prompt and prompt != prompt_text:
            lines.append(f"*Prompt:* {prompt}")
            lines.append("")
        lines.append(response)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
