"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

import models


def load_env(env_file: str = ".env") -> None:
    path = Path(env_file)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    load_dotenv(path, override=False)


def get_api_key(env_var: str, env_file: str | None = None) -> str | None:
    if env_file:
        load_env(env_file)
    else:
        load_env(models.get_env_file())
    value = os.getenv(env_var)
    if value is None or not value.strip():
        return None
    return value.strip()


def _build_openai_payload(model: models.Model, prompt: str) -> dict:
    return {
        "model": model.api_id,
        "messages": [{"role": "user", "content": prompt}],
    }


def _parse_openai_response(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise ValueError(f"Неожиданный формат ответа API: {data}") from exc


def send_openai_compatible(
    model: models.Model,
    prompt: str,
    timeout: int,
    env_file: str | None = None,
) -> str:
    api_key = get_api_key(model.api_key_env, env_file)
    if not api_key:
        return f"Ошибка: переменная {model.api_key_env} не найдена или пуста в .env"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_openai_payload(model, prompt)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(model.api_url, headers=headers, json=payload)
            response.raise_for_status()
            return _parse_openai_response(response.json())
    except httpx.TimeoutException:
        return f"Ошибка: превышен таймаут ({timeout} с) для модели {model.name}"
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        if len(detail) > 300:
            detail = detail[:300] + "..."
        return f"Ошибка HTTP {exc.response.status_code}: {detail or exc.response.reason_phrase}"
    except httpx.RequestError as exc:
        return f"Ошибка сети: {exc}"
    except ValueError as exc:
        return str(exc)


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

    # OpenAI, DeepSeek, Groq используют совместимый формат chat/completions.
    if model.model_type in {"openai", "deepseek", "groq"}:
        return send_openai_compatible(model, prompt, timeout, env_file)

    return send_openai_compatible(model, prompt, timeout, env_file)


def send_prompt_to_all(
    model_list: list[models.Model],
    prompt: str,
    session: models.ChatSession,
    timeout: int | None = None,
    env_file: str | None = None,
    parallel: bool = True,
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
