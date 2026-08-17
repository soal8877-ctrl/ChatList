"""HTTP-запросы к OpenAI-совместимым API (OpenRouter, OpenAI, DeepSeek, Groq)."""

from __future__ import annotations

import httpx

from adapters import chat_payload, extra_headers, parse_chat_content
from models import ActiveModel


class NetworkError(Exception):
    """Ошибка сети или ответа API."""

    def __init__(self, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


def send_prompt(
    model: ActiveModel,
    prompt: str,
    *,
    timeout_sec: float = 60.0,
) -> str:
    """Отправляет промт в модель. Возвращает текст ответа."""
    headers = {
        "Authorization": f"Bearer {model.api_key}",
        "Content-Type": "application/json",
        **extra_headers(model.api_url),
    }
    payload = chat_payload(model.name, prompt)
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.post(model.api_url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise NetworkError(f"Таймаут при запросе к {model.name}") from exc
    except httpx.RequestError as exc:
        raise NetworkError(f"Сеть: {model.name}: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:500]
        raise NetworkError(
            f"HTTP {response.status_code} от {model.name}: {detail}",
            http_status=response.status_code,
        )

    try:
        return parse_chat_content(response.json())
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise NetworkError(
            f"Некорректный ответ API от {model.name}",
            http_status=response.status_code,
        ) from exc
