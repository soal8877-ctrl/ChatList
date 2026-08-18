"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

from adapters import extra_headers, parse_chat_content
from models import ActiveModel

SYSTEM_PROMPT = """\
You are a prompt-engineering assistant. The user will give you their original prompt.
Return ONLY a valid JSON object (no markdown fences, no extra text) with these keys:
- "improved": a single improved version of the prompt (same language as original).
- "alternatives": a JSON array of 2–3 alternative rephrasings (same language).
- "adaptations": a JSON object with keys "code", "analysis", "creative" — \
each value is the prompt adapted for that task type (same language). \
If a task type is not applicable, set the value to an empty string.
Do NOT wrap the JSON in ```json fences. Return raw JSON only.\
"""


@dataclass
class ImproveResult:
    improved: str = ""
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)
    raw: str = ""


def _parse_result(text: str) -> ImproveResult:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1 and text.endswith("```"):
            text = text[first_nl + 1 : -3].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ImproveResult(improved=text, raw=text)

    improved = data.get("improved", "")
    alternatives = data.get("alternatives", [])
    if not isinstance(alternatives, list):
        alternatives = []
    alternatives = [str(a) for a in alternatives if a]

    adaptations = data.get("adaptations", {})
    if not isinstance(adaptations, dict):
        adaptations = {}
    adaptations = {str(k): str(v) for k, v in adaptations.items() if v}

    return ImproveResult(
        improved=str(improved),
        alternatives=alternatives,
        adaptations=adaptations,
        raw=text,
    )


def improve_prompt(
    model: ActiveModel,
    prompt: str,
    *,
    timeout_sec: float = 90.0,
) -> ImproveResult:
    """Отправляет промт в модель и возвращает улучшенные варианты."""
    headers = {
        "Authorization": f"Bearer {model.api_key}",
        "Content-Type": "application/json",
        **extra_headers(model.api_url),
    }
    payload = {
        "model": model.name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }

    with httpx.Client(timeout=timeout_sec) as client:
        response = client.post(model.api_url, headers=headers, json=payload)

    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")

    content = parse_chat_content(response.json())
    return _parse_result(content)
