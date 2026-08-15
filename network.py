"""HTTP-запросы к OpenAI-совместимым API."""

from __future__ import annotations

import httpx

from models import ActiveModel


class NetworkError(Exception):
    """Ошибка сети или ответа API."""


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
    }
    if "openrouter.ai" in model.api_url:
        headers["HTTP-Referer"] = "https://github.com/local/ChatList"
        headers["X-Title"] = "ChatList"
    payload = {
        "model": model.name,
        "messages": [{"role": "user", "content": prompt}],
    }
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
            f"HTTP {response.status_code} от {model.name}: {detail}"
        )

    try:
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise NetworkError(
            f"Некорректный ответ API от {model.name}"
        ) from exc
