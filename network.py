"""HTTP-запросы к OpenRouter (только бесплатные модели)."""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import httpx
from dotenv import dotenv_values, load_dotenv

import db
import logger
import models

OPENROUTER_API_URL = db.OPENROUTER_API_URL
OPENROUTER_API_KEY_ENV = db.OPENROUTER_API_KEY_ENV
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 502, 503, 504}

AdapterFunc = Callable[[models.Model, str, int, str | None], str]


def resolve_env_path(env_file: str) -> Path:
    path = Path(env_file)
    if path.is_absolute():
        return path

    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / env_file)
    candidates.extend(
        [
            Path(__file__).resolve().parent / env_file,
            Path.cwd() / env_file,
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_env(env_file: str = ".env") -> Path:
    path = resolve_env_path(env_file)
    if path.exists():
        load_dotenv(path, override=True, encoding="utf-8")
    return path


def get_api_key(env_var: str | None = None, env_file: str | None = None) -> str | None:
    env_name = env_var or OPENROUTER_API_KEY_ENV
    target_file = env_file or models.get_env_file()
    path = load_env(target_file)

    value = os.getenv(env_name)
    if value and value.strip():
        return value.strip()

    if path.exists():
        file_values = dotenv_values(path, encoding="utf-8")
        file_value = file_values.get(env_name)
        if file_value and file_value.strip():
            os.environ[env_name] = file_value.strip()
            return file_value.strip()

    return None


def format_auth_error(env_var: str, env_file: str | None = None) -> str:
    target_file = env_file or models.get_env_file()
    path = resolve_env_path(target_file)
    if not path.exists():
        return (
            f"Ошибка: файл {path} не найден. "
            f"Сохраните .env рядом с программой и укажите {env_var}."
        )

    keys = [key for key in dotenv_values(path, encoding="utf-8") if key]
    keys_hint = ", ".join(keys) if keys else "переменные не найдены"
    return (
        f"Ошибка: переменная {env_var} не найдена или пуста в {path}. "
        f"Найдены ключи: {keys_hint}. Сохраните файл .env (Ctrl+S)."
    )


def is_free_openrouter_model(api_id: str) -> bool:
    api_id = api_id.strip()
    return api_id == "openrouter/free" or api_id.endswith(":free")


def validate_model(model: models.Model) -> str | None:
    if "openrouter.ai" not in model.api_url:
        return (
            f"Ошибка: поддерживается только OpenRouter ({OPENROUTER_API_URL}). "
            f"Указано: {model.api_url}"
        )
    if not is_free_openrouter_model(model.api_id):
        return (
            "Ошибка: разрешены только бесплатные модели OpenRouter "
            f"(openrouter/free или id с суффиксом :free). Указано: {model.api_id}"
        )
    return None


def _build_openrouter_payload(model: models.Model, prompt: str) -> dict:
    return {
        "model": model.api_id,
        "messages": [{"role": "user", "content": prompt}],
    }


def _parse_openrouter_response(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise ValueError(f"Неожиданный формат ответа OpenRouter: {data}") from exc


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 15.0)
        except ValueError:
            pass
    return min(2.0 ** attempt, 8.0)


def _format_http_error(model: models.Model, exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    if status == 429:
        return (
            f"Модель «{model.name}» временно недоступна: превышен лимит бесплатного "
            f"доступа OpenRouter. Повторите запрос через 1–2 минуты или выберите "
            f"другую модель в меню «Модели»."
        )
    detail = exc.response.text.strip()
    if len(detail) > 300:
        detail = detail[:300] + "..."
    return f"Ошибка HTTP {status}: {detail or exc.response.reason_phrase}"


def send_openrouter(
    model: models.Model,
    prompt: str,
    timeout: int,
    env_file: str | None = None,
) -> str:
    validation_error = validate_model(model)
    if validation_error:
        logger.log_request(model.name, model.api_id, prompt, "validation_error", validation_error)
        return validation_error

    api_key = get_api_key(model.api_key_env or OPENROUTER_API_KEY_ENV, env_file)
    if not api_key:
        env_name = model.api_key_env or OPENROUTER_API_KEY_ENV
        message = format_auth_error(env_name, env_file)
        logger.log_request(model.name, model.api_id, prompt, "auth_error", message)
        return message

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ChatList",
        "X-Title": "ChatList",
    }
    payload = _build_openrouter_payload(model, prompt)
    api_url = model.api_url if model.api_url else OPENROUTER_API_URL
    start = time.perf_counter()

    try:
        with httpx.Client(timeout=timeout) as client:
            for attempt in range(MAX_RETRIES):
                response = client.post(api_url, headers=headers, json=payload)
                if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES - 1:
                    time.sleep(_retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                text = _parse_openrouter_response(response.json())
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.log_request(model.name, model.api_id, prompt, "ok", duration_ms=duration_ms)
                return text
    except httpx.TimeoutException:
        message = f"Ошибка: превышен таймаут ({timeout} с) для модели {model.name}"
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.log_request(model.name, model.api_id, prompt, "timeout", message, duration_ms)
        return message
    except httpx.HTTPStatusError as exc:
        message = _format_http_error(model, exc)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.log_request(model.name, model.api_id, prompt, "http_error", message, duration_ms)
        return message
    except httpx.RequestError as exc:
        message = f"Ошибка сети: {exc}"
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.log_request(model.name, model.api_id, prompt, "network_error", message, duration_ms)
        return message
    except ValueError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.log_request(model.name, model.api_id, prompt, "parse_error", str(exc), duration_ms)
        return str(exc)


ADAPTERS: dict[str, AdapterFunc] = {
    "openrouter": send_openrouter,
}


def send_prompt(
    model: models.Model,
    prompt: str,
    timeout: int | None = None,
    env_file: str | None = None,
) -> str:
    if timeout is None:
        timeout = models.get_request_timeout()
    if env_file is None:
        env_file = models.get_env_file()

    load_env(env_file)
    adapter = ADAPTERS.get(model.model_type, send_openrouter)
    return adapter(model, prompt, timeout, env_file)


def send_prompt_to_all(
    model_list: list[models.Model],
    prompt: str,
    session: models.ChatSession,
    timeout: int | None = None,
    env_file: str | None = None,
    parallel: bool = False,
) -> list[models.TempResult]:
    if timeout is None:
        timeout = models.get_request_timeout()
    if env_file is None:
        env_file = models.get_env_file()

    session.clear_temp_results()

    if not model_list:
        return []

    def _send_one(model: models.Model) -> models.TempResult:
        response = send_prompt(model, prompt, timeout, env_file)
        return models.TempResult(
            model_name=model.name,
            model_id=model.id,
            prompt_id=session.current_prompt_id,
            prompt_text=session.current_prompt_text,
            response=response,
            selected=False,
        )

    results: list[models.TempResult] = []

    if parallel and len(model_list) > 1:
        with ThreadPoolExecutor(max_workers=min(len(model_list), 8)) as executor:
            futures = {executor.submit(_send_one, model): model for model in model_list}
            for future in as_completed(futures):
                item = future.result()
                session.add_temp_result(
                    item.model_name,
                    item.model_id,
                    item.response,
                    item.selected,
                )
                results.append(item)
    else:
        for model in model_list:
            item = _send_one(model)
            session.add_temp_result(
                item.model_name,
                item.model_id,
                item.response,
                item.selected,
            )
            results.append(item)

    return results
