"""Временная таблица результатов в памяти (не SQLite)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TempResultRow:
    model_id: int
    model_name: str
    response: str
    selected: bool = False
    prompt_id: int | None = None
    prompt_text: str = ""


@dataclass
class TempResultsTable:
    rows: list[TempResultRow] = field(default_factory=list)

    def clear(self) -> None:
        self.rows.clear()

    def reset(self) -> None:
        """Полный сброс перед новым промтом."""
        self.clear()

    def create_from_responses(
        self,
        *,
        prompt_text: str,
        prompt_id: int | None,
        items: list[tuple[int, str, str]],
    ) -> None:
        """
        Создать таблицу после ответов моделей.
        items: список (model_id, model_name, response).
        """
        self.reset()
        for model_id, model_name, response in items:
            self.rows.append(
                TempResultRow(
                    model_id=model_id,
                    model_name=model_name,
                    response=response,
                    selected=False,
                    prompt_id=prompt_id,
                    prompt_text=prompt_text,
                )
            )

    def selected_rows(self) -> list[TempResultRow]:
        return [r for r in self.rows if r.selected]

    def set_selected(self, index: int, selected: bool) -> None:
        self.rows[index].selected = selected

    def set_selected_by_model_id(self, model_id: int, selected: bool) -> None:
        for row in self.rows:
            if row.model_id == model_id:
                row.selected = selected
                return
