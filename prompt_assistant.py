"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import models
import network

ASSISTANT_SYSTEM_PROMPT = """You are a prompt improvement assistant for ChatList.
Improve the user's prompt while preserving its original meaning.

Return ONLY valid JSON with this exact structure:
{
  "improved": "main improved prompt",
  "alternatives": ["alternative 1", "alternative 2", "alternative 3"],
  "adaptations": {
    "code": "prompt adapted for coding tasks",
    "analysis": "prompt adapted for analytical tasks",
    "creative": "prompt adapted for creative tasks"
  }
}

Rules:
- Write in the same language as the user's prompt.
- Provide exactly 2 or 3 items in alternatives.
- Keep adaptations concise and task-specific.
- Do not add markdown fences or extra commentary outside JSON.
"""


@dataclass
class PromptSuggestion:
    label: str
    text: str


@dataclass
class PromptImprovementResult:
    original: str
    improved: str
    alternatives: list[PromptSuggestion] = field(default_factory=list)
    adaptations: list[PromptSuggestion] = field(default_factory=list)


def build_assistant_messages(original: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Improve the following prompt and provide alternatives and adaptations:\n\n"
                f"{original.strip()}"
            ),
        },
    ]


def _extract_json_block(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _as_suggestions(
    items: list[str] | None,
    prefix: str,
) -> list[PromptSuggestion]:
    if not items:
        return []
    suggestions: list[PromptSuggestion] = []
    for index, item in enumerate(items, start=1):
        text = str(item).strip()
        if text:
            suggestions.append(PromptSuggestion(f"{prefix} {index}", text))
    return suggestions


def _as_adaptations(data: dict | None) -> list[PromptSuggestion]:
    if not isinstance(data, dict):
        return []
    labels = {
        "code": "Для кода",
        "analysis": "Для анализа",
        "creative": "Для креатива",
    }
    result: list[PromptSuggestion] = []
    for key, label in labels.items():
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(PromptSuggestion(label, text))
    return result


def parse_assistant_response(raw: str, original: str) -> PromptImprovementResult:
    try:
        payload = json.loads(_extract_json_block(raw))
    except json.JSONDecodeError:
        cleaned = raw.strip()
        return PromptImprovementResult(
            original=original,
            improved=cleaned or original,
            alternatives=[],
            adaptations=[],
        )

    improved = str(payload.get("improved", "")).strip() or original
    alternatives_raw = payload.get("alternatives", [])
    if isinstance(alternatives_raw, str):
        alternatives_raw = [alternatives_raw]
    if not isinstance(alternatives_raw, list):
        alternatives_raw = []

    return PromptImprovementResult(
        original=original,
        improved=improved,
        alternatives=_as_suggestions(alternatives_raw[:3], "Альтернатива"),
        adaptations=_as_adaptations(payload.get("adaptations")),
    )


def improve_prompt(
    text: str,
    model: models.Model,
) -> PromptImprovementResult | str:
    original = text.strip()
    if not original:
        return "Ошибка: промт пустой."

    messages = build_assistant_messages(original)
    response = network.send_chat(
        model,
        messages,
        log_status="assistant_ok",
        error_log_status="assistant_error",
    )
    if response.startswith("Ошибка"):
        return response
    return parse_assistant_response(response, original)
