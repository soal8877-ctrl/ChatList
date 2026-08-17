"""Провайдеры API: OpenRouter, OpenAI, DeepSeek, Groq и совместимые."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    api_url: str
    api_id: str


PROVIDERS: dict[str, Provider] = {
    "openrouter": Provider(
        key="openrouter",
        label="OpenRouter",
        api_url="https://openrouter.ai/api/v1/chat/completions",
        api_id="OPENROUTER_API_KEY",
    ),
    "openai": Provider(
        key="openai",
        label="OpenAI",
        api_url="https://api.openai.com/v1/chat/completions",
        api_id="OPENAI_API_KEY",
    ),
    "deepseek": Provider(
        key="deepseek",
        label="DeepSeek",
        api_url="https://api.deepseek.com/chat/completions",
        api_id="DEEPSEEK_API_KEY",
    ),
    "groq": Provider(
        key="groq",
        label="Groq",
        api_url="https://api.groq.com/openai/v1/chat/completions",
        api_id="GROQ_API_KEY",
    ),
}


def detect_provider(api_url: str) -> str:
    url = (api_url or "").lower()
    if "openrouter.ai" in url:
        return "openrouter"
    if "deepseek.com" in url:
        return "deepseek"
    if "groq.com" in url:
        return "groq"
    if "openai.com" in url:
        return "openai"
    return "openai_compatible"


def extra_headers(api_url: str) -> dict[str, str]:
    provider = detect_provider(api_url)
    if provider == "openrouter":
        return {
            "HTTP-Referer": "https://github.com/local/ChatList",
            "X-Title": "ChatList",
        }
    return {}


def chat_payload(model_name: str, prompt: str) -> dict:
    """OpenAI-совместимый chat/completions payload (OpenAI, DeepSeek, Groq, OpenRouter)."""
    return {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
    }


def parse_chat_content(data: object) -> str:
    if not isinstance(data, dict):
        raise ValueError("response is not an object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("no message")
    content = message.get("content")
    if content is None:
        raise ValueError("no content")
    return str(content).strip()
