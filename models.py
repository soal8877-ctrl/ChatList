"""Бизнес-логика: промты, модели, временные и сохранённые результаты."""

from __future__ import annotations

from dataclasses import dataclass, field

import db


@dataclass
class Prompt:
    id: int
    created_at: str
    prompt: str
    tags: str | None = None


@dataclass
class Model:
    id: int
    name: str
    api_url: str
    api_id: str
    api_key_env: str
    is_active: bool
    model_type: str = "openrouter"


@dataclass
class Result:
    id: int
    prompt_id: int
    model_id: int
    response: str
    created_at: str
    prompt_text: str = ""
    model_name: str = ""


@dataclass
class TempResult:
    model_name: str
    model_id: int
    prompt_id: int | None
    prompt_text: str
    response: str
    selected: bool = False


@dataclass
class ChatSession:
    """Состояние текущего запроса и временной таблицы результатов."""

    current_prompt_id: int | None = None
    current_prompt_text: str = ""
    current_tags: str | None = None
    _temp_results: list[TempResult] = field(default_factory=list)

    def set_current_prompt(
        self,
        text: str,
        prompt_id: int | None = None,
        tags: str | None = None,
    ) -> None:
        self.current_prompt_text = text.strip()
        self.current_prompt_id = prompt_id
        self.current_tags = tags

    def clear_temp_results(self) -> None:
        self._temp_results.clear()

    def add_temp_result(
        self,
        model_name: str,
        model_id: int,
        response: str,
        selected: bool = False,
    ) -> None:
        self._temp_results.append(
            TempResult(
                model_name=model_name,
                model_id=model_id,
                prompt_id=self.current_prompt_id,
                prompt_text=self.current_prompt_text,
                response=response,
                selected=selected,
            )
        )

    def get_temp_results(self) -> list[TempResult]:
        return list(self._temp_results)

    def get_selected_temp_results(self) -> list[TempResult]:
        return [item for item in self._temp_results if item.selected]

    def set_temp_result_selected(self, index: int, selected: bool) -> None:
        if 0 <= index < len(self._temp_results):
            self._temp_results[index].selected = selected

    def sort_temp_results(self, *, by_model: bool = False, by_response: bool = False) -> None:
        if by_model:
            self._temp_results.sort(key=lambda item: item.model_name.lower())
        elif by_response:
            self._temp_results.sort(key=lambda item: item.response.lower())

    def reset_for_new_request(self) -> None:
        self.current_prompt_id = None
        self.current_prompt_text = ""
        self.current_tags = None
        self.clear_temp_results()


def row_to_prompt(row) -> Prompt:
    return Prompt(
        id=row["id"],
        created_at=row["created_at"],
        prompt=row["prompt"],
        tags=row["tags"],
    )


def row_to_model(row) -> Model:
    return Model(
        id=row["id"],
        name=row["name"],
        api_url=row["api_url"],
        api_id=row["api_id"],
        api_key_env=row["api_key_env"],
        is_active=bool(row["is_active"]),
        model_type=row["model_type"],
    )


def row_to_result(row) -> Result:
    return Result(
        id=row["id"],
        prompt_id=row["prompt_id"],
        model_id=row["model_id"],
        response=row["response"],
        created_at=row["created_at"],
        prompt_text=row["prompt_text"] if "prompt_text" in row.keys() else "",
        model_name=row["model_name"] if "model_name" in row.keys() else "",
    )


def get_active_models() -> list[Model]:
    return [row_to_model(row) for row in db.list_models(active_only=True)]


def get_all_models() -> list[Model]:
    return [row_to_model(row) for row in db.list_models(active_only=False)]


def save_prompt(text: str, tags: str | None = None) -> Prompt:
    prompt_id = db.add_prompt(text, tags)
    row = db.get_prompt(prompt_id)
    assert row is not None
    return row_to_prompt(row)


def load_prompts(search: str | None = None) -> list[Prompt]:
    return [row_to_prompt(row) for row in db.list_prompts(search)]


def delete_prompt(prompt_id: int) -> None:
    db.delete_prompt(prompt_id)


def add_model(
    name: str,
    api_url: str,
    api_id: str,
    api_key_env: str,
    is_active: bool = True,
    model_type: str = "openrouter",
) -> Model:
    model_id = db.add_model(name, api_url, api_id, api_key_env, is_active, model_type)
    row = db.get_model(model_id)
    assert row is not None
    return row_to_model(row)


def update_model(model: Model) -> None:
    db.update_model(
        model.id,
        model.name,
        model.api_url,
        model.api_id,
        model.api_key_env,
        model.is_active,
        model.model_type,
    )


def set_model_active(model_id: int, is_active: bool) -> None:
    db.set_model_active(model_id, is_active)


def delete_model(model_id: int) -> None:
    db.delete_model(model_id)


def load_results(search: str | None = None) -> list[Result]:
    return [row_to_result(row) for row in db.list_results(search)]


def save_selected_results(session: ChatSession, save_prompt_if_new: bool = False) -> int:
    """Сохраняет отмеченные строки в БД. Возвращает количество сохранённых."""
    selected = session.get_selected_temp_results()
    if not selected:
        return 0

    if not session.current_prompt_text:
        return 0

    prompt_id = session.current_prompt_id
    if prompt_id is None and save_prompt_if_new:
        prompt = save_prompt(session.current_prompt_text, session.current_tags)
        prompt_id = prompt.id
        session.current_prompt_id = prompt_id
    elif prompt_id is None:
        prompt = save_prompt(session.current_prompt_text, session.current_tags)
        prompt_id = prompt.id
        session.current_prompt_id = prompt_id

    saved_count = 0
    for item in selected:
        db.add_result(prompt_id, item.model_id, item.response)
        saved_count += 1

    session.clear_temp_results()
    return saved_count


def get_settings() -> dict[str, str]:
    return db.list_settings()


def save_settings(settings: dict[str, str]) -> None:
    for key, value in settings.items():
        db.set_setting(key, value)


def get_request_timeout() -> int:
    value = db.get_setting("request_timeout", "30")
    try:
        return max(1, int(value or "30"))
    except ValueError:
        return 30


def get_env_file() -> str:
    return db.get_setting("env_file", ".env") or ".env"
