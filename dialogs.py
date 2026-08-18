"""Диалоги управления данными: модели, промты, результаты, настройки, логи."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from adapters import PROVIDERS
from db import Database
from export import results_to_json, results_to_markdown


def configure_table(table: QTableWidget) -> None:
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)


def apply_table_filter(table: QTableWidget, query: str) -> None:
    q = query.strip().lower()
    for row in range(table.rowCount()):
        if not q:
            table.setRowHidden(row, False)
            continue
        parts: list[str] = []
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                parts.append(item.text().lower())
        table.setRowHidden(row, q not in " ".join(parts))


def make_search_box(placeholder: str, on_change) -> QLineEdit:
    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    search.textChanged.connect(on_change)
    return search


def id_item(value: int) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setData(Qt.ItemDataRole.DisplayRole, value)
    return item


def export_rows(parent, rows: list, prompt_text: str = "") -> None:
    if not rows:
        QMessageBox.information(parent, "Экспорт", "Нет строк для экспорта.")
        return
    path, selected = QFileDialog.getSaveFileName(
        parent,
        "Экспорт результатов",
        "chatlist-export.md",
        "Markdown (*.md);;JSON (*.json)",
    )
    if not path:
        return
    out = Path(path)
    if "json" in selected.lower() or out.suffix.lower() == ".json":
        out.write_text(results_to_json(rows, prompt_text), encoding="utf-8")
    else:
        if out.suffix.lower() not in {".md", ".markdown"}:
            out = out.with_suffix(".md")
        out.write_text(results_to_markdown(rows, prompt_text), encoding="utf-8")
    QMessageBox.information(parent, "Экспорт", f"Сохранено: {out}")


def normalize_markdown(text: str) -> str:
    """If the whole reply is a ```markdown fence, unwrap it for rendering."""
    s = (text or "").strip()
    if not s.startswith("```"):
        return text or ""
    first_nl = s.find("\n")
    if first_nl == -1 or not s.endswith("```"):
        return s
    lang = s[3:first_nl].strip().lower()
    if lang not in ("", "markdown", "md"):
        return s
    inner = s[first_nl + 1 :]
    if inner.endswith("```"):
        inner = inner[:-3]
    return inner.strip()


class MarkdownViewDialog(QDialog):
    def __init__(self, title: str, markdown: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 640)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(normalize_markdown(markdown))

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(browser)
        layout.addLayout(row)


class ModelEditDialog(QDialog):
    def __init__(self, parent=None, data: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Модель" if data else "Новая модель")
        self.resize(560, 240)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Другой / вручную", None)
        for key, provider in PROVIDERS.items():
            self.provider_combo.addItem(provider.label, key)

        self.name_edit = QLineEdit(data["name"] if data else "")
        self.url_edit = QLineEdit(
            data["api_url"]
            if data
            else PROVIDERS["openrouter"].api_url
        )
        self.api_id_edit = QLineEdit(
            data["api_id"] if data else PROVIDERS["openrouter"].api_id
        )
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(
            bool(data["is_active"]) if data else True
        )

        if data:
            url = (data.get("api_url") or "").lower()
            for i in range(self.provider_combo.count()):
                key = self.provider_combo.itemData(i)
                if key and PROVIDERS[key].api_url.lower() in url:
                    self.provider_combo.setCurrentIndex(i)
                    break

        form = QFormLayout()
        form.addRow("Провайдер:", self.provider_combo)
        form.addRow("Имя (id модели):", self.name_edit)
        form.addRow("API URL:", self.url_edit)
        form.addRow("api_id (.env):", self.api_id_edit)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.provider_combo.currentIndexChanged.connect(self._on_provider)

    def _on_provider(self, _index: int) -> None:
        key = self.provider_combo.currentData()
        if not key:
            return
        provider = PROVIDERS[key]
        self.url_edit.setText(provider.api_url)
        self.api_id_edit.setText(provider.api_id)

    def values(self) -> tuple[str, str, str, bool]:
        return (
            self.name_edit.text().strip(),
            self.url_edit.text().strip(),
            self.api_id_edit.text().strip(),
            self.active_check.isChecked(),
        )


class ModelsDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Модели")
        self.resize(800, 420)

        self.search = make_search_box(
            "Поиск по имени, URL, api_id…",
            lambda text: apply_table_filter(self.table, text),
        )
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "API URL", "api_id", "Активна"]
        )
        configure_table(self.table)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 280)

        add_btn = QPushButton("Добавить")
        edit_btn = QPushButton("Изменить")
        del_btn = QPushButton("Удалить")
        close_btn = QPushButton("Закрыть")

        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(edit_btn)
        row.addWidget(del_btn)
        row.addStretch()
        row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addLayout(row)

        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        del_btn.clicked.connect(self._delete)
        close_btn.clicked.connect(self.accept)
        self.table.doubleClicked.connect(lambda _: self._edit())

        self._reload()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def _reload(self) -> None:
        self.table.setSortingEnabled(False)
        models = self.db.list_models()
        self.table.setRowCount(len(models))
        for i, m in enumerate(models):
            self.table.setItem(i, 0, id_item(int(m["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(m["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(m["api_url"]))
            self.table.setItem(i, 3, QTableWidgetItem(m["api_id"]))
            self.table.setItem(
                i, 4, QTableWidgetItem("да" if m["is_active"] else "нет")
            )
        self.table.setSortingEnabled(True)
        apply_table_filter(self.table, self.search.text())

    def _add(self) -> None:
        dlg = ModelEditDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, url, api_id, active = dlg.values()
        if not name or not url or not api_id:
            QMessageBox.warning(self, "Модели", "Заполните все поля.")
            return
        try:
            self.db.create_model(name, url, api_id, active)
        except Exception as exc:
            QMessageBox.critical(self, "Модели", str(exc))
            return
        self._reload()

    def _edit(self) -> None:
        model_id = self._selected_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите строку.")
            return
        data = self.db.get_model(model_id)
        if not data:
            return
        dlg = ModelEditDialog(self, data)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, url, api_id, active = dlg.values()
        if not name or not url or not api_id:
            QMessageBox.warning(self, "Модели", "Заполните все поля.")
            return
        try:
            self.db.update_model(
                model_id, name=name, api_url=url, api_id=api_id, is_active=active
            )
        except Exception as exc:
            QMessageBox.critical(self, "Модели", str(exc))
            return
        self._reload()

    def _delete(self) -> None:
        model_id = self._selected_id()
        if model_id is None:
            QMessageBox.information(self, "Модели", "Выберите строку.")
            return
        if (
            QMessageBox.question(
                self,
                "Модели",
                "Удалить модель? Если есть сохранённые результаты — удаление может не пройти.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.db.delete_model(model_id)
        except Exception as exc:
            QMessageBox.critical(self, "Модели", str(exc))
            return
        self._reload()


class PromptEditDialog(QDialog):
    def __init__(self, parent=None, data: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Промт" if data else "Новый промт")
        self.resize(640, 360)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Текст промта…")
        if data:
            self.prompt_edit.setPlainText(data.get("prompt") or "")
        self.tags_edit = QLineEdit(data.get("tags") or "" if data else "")

        form = QFormLayout()
        form.addRow("Теги:", self.tags_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Текст:"))
        layout.addWidget(self.prompt_edit)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return (
            self.prompt_edit.toPlainText().strip(),
            self.tags_edit.text().strip(),
        )


class PromptsDialog(QDialog):
    """Просмотр промтов. При «Использовать» возвращает id выбранного промта."""

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_prompt_id: int | None = None
        self.setWindowTitle("Сохранённые промты")
        self.resize(800, 480)

        self.search = make_search_box(
            "Поиск по тексту и тегам…",
            lambda text: apply_table_filter(self.table, text),
        )
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Теги", "Промт"])
        configure_table(self.table)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 420)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(120)

        self.tags_edit = QLineEdit()
        self.tags_edit.setReadOnly(True)

        add_btn = QPushButton("Добавить")
        edit_btn = QPushButton("Изменить")
        del_btn = QPushButton("Удалить")
        use_btn = QPushButton("Использовать")
        close_btn = QPushButton("Закрыть")

        row = QHBoxLayout()
        row.addWidget(add_btn)
        row.addWidget(edit_btn)
        row.addWidget(del_btn)
        row.addWidget(use_btn)
        row.addStretch()
        row.addWidget(close_btn)

        form = QFormLayout()
        form.addRow("Теги:", self.tags_edit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Текст:"))
        layout.addWidget(self.preview)
        layout.addLayout(form)
        layout.addLayout(row)

        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        del_btn.clicked.connect(self._delete)
        use_btn.clicked.connect(self._use)
        close_btn.clicked.connect(self.reject)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.doubleClicked.connect(lambda _: self._edit())

        self._reload()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def _reload(self) -> None:
        self.table.setSortingEnabled(False)
        prompts = self.db.list_prompts()
        self.table.setRowCount(len(prompts))
        for i, p in enumerate(prompts):
            preview = p["prompt"].replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "…"
            self.table.setItem(i, 0, id_item(int(p["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(p["created_at"]))
            self.table.setItem(i, 2, QTableWidgetItem(p["tags"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(preview))
        self.table.setSortingEnabled(True)
        apply_table_filter(self.table, self.search.text())

    def _on_select(self) -> None:
        prompt_id = self._selected_id()
        if prompt_id is None:
            self.preview.clear()
            self.tags_edit.clear()
            return
        row = self.db.get_prompt(prompt_id)
        if not row:
            return
        self.preview.setPlainText(row["prompt"])
        self.tags_edit.setText(row["tags"] or "")

    def _use(self) -> None:
        prompt_id = self._selected_id()
        if prompt_id is None:
            QMessageBox.information(self, "Промты", "Выберите промт.")
            return
        self.selected_prompt_id = prompt_id
        self.accept()

    def _add(self) -> None:
        dlg = PromptEditDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        prompt, tags = dlg.values()
        if not prompt:
            QMessageBox.warning(self, "Промты", "Введите текст промта.")
            return
        try:
            new_id = self.db.create_prompt(prompt, tags)
        except Exception as exc:
            QMessageBox.critical(self, "Промты", str(exc))
            return
        self._reload()
        self._select_id(new_id)

    def _edit(self) -> None:
        prompt_id = self._selected_id()
        if prompt_id is None:
            QMessageBox.information(self, "Промты", "Выберите промт.")
            return
        data = self.db.get_prompt(prompt_id)
        if not data:
            return
        dlg = PromptEditDialog(self, data)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        prompt, tags = dlg.values()
        if not prompt:
            QMessageBox.warning(self, "Промты", "Введите текст промта.")
            return
        try:
            self.db.update_prompt(prompt_id, prompt=prompt, tags=tags)
        except Exception as exc:
            QMessageBox.critical(self, "Промты", str(exc))
            return
        self._reload()
        self._select_id(prompt_id)

    def _select_id(self, prompt_id: int) -> None:
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and int(item.text()) == prompt_id:
                self.table.selectRow(i)
                self._on_select()
                return
        self._on_select()

    def _delete(self) -> None:
        prompt_id = self._selected_id()
        if prompt_id is None:
            QMessageBox.information(self, "Промты", "Выберите промт.")
            return
        if (
            QMessageBox.question(
                self, "Промты", "Удалить промт и связанные результаты?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.db.delete_prompt(prompt_id)
        self.preview.clear()
        self.tags_edit.clear()
        self._reload()


class ResultsDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Сохранённые результаты")
        self.resize(900, 500)
        self._rows: list[dict] = []

        self.search = make_search_box(
            "Поиск по модели, промту, ответу…",
            lambda text: apply_table_filter(self.table, text),
        )
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Модель", "Промт", "Ответ"]
        )
        configure_table(self.table)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 220)
        self.table.setColumnWidth(4, 280)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        export_btn = QPushButton("Экспорт…")
        open_btn = QPushButton("Open")
        del_btn = QPushButton("Удалить")
        close_btn = QPushButton("Закрыть")
        row = QHBoxLayout()
        row.addWidget(export_btn)
        row.addWidget(open_btn)
        row.addWidget(del_btn)
        row.addStretch()
        row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Полный ответ:"))
        layout.addWidget(self.preview)
        layout.addLayout(row)

        export_btn.clicked.connect(self._export)
        open_btn.clicked.connect(self._open_markdown)
        del_btn.clicked.connect(self._delete)
        close_btn.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.doubleClicked.connect(lambda _: self._open_markdown())

        self._reload()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def _visible_rows(self) -> list[dict]:
        by_id = {int(r["id"]): r for r in self._rows}
        visible: list[dict] = []
        for i in range(self.table.rowCount()):
            if self.table.isRowHidden(i):
                continue
            item = self.table.item(i, 0)
            if item is None:
                continue
            data = by_id.get(int(item.text()))
            if data:
                visible.append(data)
        selected_ids = set()
        for idx in self.table.selectionModel().selectedRows():
            item = self.table.item(idx.row(), 0)
            if item:
                selected_ids.add(int(item.text()))
        if selected_ids:
            return [r for r in visible if int(r["id"]) in selected_ids]
        return visible

    def _reload(self) -> None:
        self.table.setSortingEnabled(False)
        results = self.db.list_results()
        self._rows = results
        self.table.setRowCount(len(results))
        for i, r in enumerate(results):
            prompt_preview = (r.get("prompt_text") or "").replace("\n", " ")
            if len(prompt_preview) > 50:
                prompt_preview = prompt_preview[:47] + "…"
            resp_preview = (r.get("response") or "").replace("\n", " ")
            if len(resp_preview) > 60:
                resp_preview = resp_preview[:57] + "…"
            item0 = id_item(int(r["id"]))
            self.table.setItem(i, 0, item0)
            self.table.setItem(i, 1, QTableWidgetItem(r["created_at"]))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("model_name") or ""))
            self.table.setItem(i, 3, QTableWidgetItem(prompt_preview))
            self.table.setItem(i, 4, QTableWidgetItem(resp_preview))
        self.table.setSortingEnabled(True)
        apply_table_filter(self.table, self.search.text())

    def _on_select(self) -> None:
        result_id = self._selected_id()
        if result_id is None:
            self.preview.clear()
            return
        data = next((r for r in self._rows if int(r["id"]) == result_id), None)
        if not data:
            self.preview.clear()
            return
        text = (
            f"Модель: {data.get('model_name')}\n"
            f"Промт:\n{data.get('prompt_text')}\n\n"
            f"Ответ:\n{data.get('response')}"
        )
        self.preview.setPlainText(text)

    def _export(self) -> None:
        rows = self._visible_rows()
        export_rows(self, rows)

    def _open_markdown(self) -> None:
        result_id = self._selected_id()
        if result_id is None:
            QMessageBox.information(self, "Результаты", "Выберите строку.")
            return
        data = next((r for r in self._rows if int(r["id"]) == result_id), None)
        if not data:
            return
        MarkdownViewDialog(
            f"{data.get('model_name') or 'Ответ'}",
            data.get("response") or "",
            self,
        ).exec()

    def _delete(self) -> None:
        result_id = self._selected_id()
        if result_id is None:
            QMessageBox.information(self, "Результаты", "Выберите строку.")
            return
        if (
            QMessageBox.question(self, "Результаты", "Удалить запись?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.db.delete_result(result_id)
        self.preview.clear()
        self._reload()


class LogsDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Логи запросов")
        self.resize(900, 500)
        self._rows: list[dict] = []

        self.search = make_search_box(
            "Поиск по модели, статусу, промту…",
            lambda text: apply_table_filter(self.table, text),
        )
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Модель", "Статус", "HTTP", "мс"]
        )
        configure_table(self.table)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 280)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        clear_btn = QPushButton("Очистить все")
        close_btn = QPushButton("Закрыть")
        row = QHBoxLayout()
        row.addWidget(clear_btn)
        row.addStretch()
        row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Детали:"))
        layout.addWidget(self.preview)
        layout.addLayout(row)

        clear_btn.clicked.connect(self._clear)
        close_btn.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._on_select)
        self._reload()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def _reload(self) -> None:
        self.table.setSortingEnabled(False)
        self._rows = self.db.list_logs()
        self.table.setRowCount(len(self._rows))
        for i, r in enumerate(self._rows):
            http_status = r.get("http_status")
            self.table.setItem(i, 0, id_item(int(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["created_at"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["model_name"]))
            self.table.setItem(i, 3, QTableWidgetItem(r["status"]))
            self.table.setItem(
                i, 4, QTableWidgetItem("" if http_status is None else str(http_status))
            )
            self.table.setItem(i, 5, id_item(int(r.get("duration_ms") or 0)))
        self.table.setSortingEnabled(True)
        apply_table_filter(self.table, self.search.text())

    def _on_select(self) -> None:
        log_id = self._selected_id()
        if log_id is None:
            self.preview.clear()
            return
        data = next((r for r in self._rows if int(r["id"]) == log_id), None)
        if not data:
            self.preview.clear()
            return
        self.preview.setPlainText(
            f"Статус: {data.get('status')}\n"
            f"HTTP: {data.get('http_status')}\n"
            f"Длительность: {data.get('duration_ms')} мс\n\n"
            f"Промт:\n{data.get('prompt')}\n\n"
            f"Ответ / ошибка:\n{data.get('response')}"
        )

    def _clear(self) -> None:
        if (
            QMessageBox.question(self, "Логи", "Удалить все записи логов?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.db.clear_logs()
        self.preview.clear()
        self._reload()


class SettingsDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Настройки")
        self.resize(420, 220)

        timeout = db.get_setting("request_timeout_sec", "60") or "60"
        width = db.get_setting("window_width", "900") or "900"
        height = db.get_setting("window_height", "600") or "600"

        self.db_path_label = QLabel(str(db.db_path))
        self.db_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        try:
            self.timeout_spin.setValue(int(float(timeout)))
        except ValueError:
            self.timeout_spin.setValue(60)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(400, 3000)
        try:
            self.width_spin.setValue(int(width))
        except ValueError:
            self.width_spin.setValue(900)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 2000)
        try:
            self.height_spin.setValue(int(height))
        except ValueError:
            self.height_spin.setValue(600)

        form = QFormLayout()
        form.addRow("Путь к БД:", self.db_path_label)
        form.addRow("Таймаут запроса (сек):", self.timeout_spin)
        form.addRow("Ширина окна:", self.width_spin)
        form.addRow("Высота окна:", self.height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def apply(self) -> None:
        self.db.set_setting("request_timeout_sec", str(self.timeout_spin.value()))
        self.db.set_setting("window_width", str(self.width_spin.value()))
        self.db.set_setting("window_height", str(self.height_spin.value()))
        self.db.set_setting("db_path", str(self.db.db_path))
