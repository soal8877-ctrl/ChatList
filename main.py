"""Главное окно ChatList."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import db
import export
import models
import network
import prompt_assistant
from prompt_assistant import PromptImprovementResult


def save_text_to_file(parent: QWidget, default_name: str, content: str) -> bool:
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Сохранить файл",
        default_name,
        "Markdown (*.md);;JSON (*.json);;Все файлы (*.*)",
    )
    if not path:
        return False
    Path(path).write_text(content, encoding="utf-8")
    return True


class ResponseViewDialog(QDialog):
    def __init__(
        self,
        model_name: str,
        prompt: str,
        response: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ответ — {model_name}")
        self.resize(760, 580)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(self._build_markdown(model_name, prompt, response))

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(browser, 1)
        layout.addLayout(buttons)

    @staticmethod
    def _build_markdown(model_name: str, prompt: str, response: str) -> str:
        lines = [f"# {model_name}", ""]
        if prompt.strip():
            lines.extend(["## Промт", "", prompt.strip(), ""])
        lines.extend(["## Ответ", "", response.strip()])
        return "\n".join(lines)

    @classmethod
    def from_saved_result(
        cls, result: models.Result, parent: QWidget | None = None
    ) -> ResponseViewDialog:
        return cls(result.model_name, result.prompt_text, result.response, parent)

    @classmethod
    def from_prompt(
        cls, prompt: models.Prompt, parent: QWidget | None = None
    ) -> ResponseViewDialog:
        dialog = cls.__new__(cls)
        QDialog.__init__(dialog, parent)
        dialog.setWindowTitle(f"Промт — {prompt.id}")
        dialog.resize(760, 580)

        saved_results = models.load_results_by_prompt(prompt.id)
        markdown = cls._build_prompt_markdown(prompt, saved_results)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setMarkdown(markdown)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(dialog)
        layout.addWidget(browser, 1)
        layout.addLayout(buttons)
        return dialog

    @staticmethod
    def _build_prompt_markdown(
        prompt: models.Prompt, results: list[models.Result]
    ) -> str:
        lines = ["# Промт", ""]
        if prompt.tags:
            lines.extend([f"**Теги:** {prompt.tags}", ""])
        lines.extend([prompt.prompt.strip(), ""])
        if not results:
            lines.append("_Нет сохранённых ответов для этого промта._")
            return "\n".join(lines)
        lines.append("---")
        lines.append("")
        for result in results:
            lines.extend(
                [
                    f"## {result.model_name}",
                    "",
                    f"**Дата:** {result.created_at}",
                    "",
                    result.response.strip(),
                    "",
                    "---",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"


class ImprovePromptWorker(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        prompt_text: str,
        model: models.Model,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.prompt_text = prompt_text
        self.model = model

    def run(self) -> None:
        result = prompt_assistant.improve_prompt(self.prompt_text, self.model)
        if isinstance(result, str):
            self.failed.emit(result)
        else:
            self.finished.emit(result)


class PromptImprovementDialog(QDialog):
    def __init__(
        self,
        result: PromptImprovementResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.selected_text = ""
        self.setWindowTitle("Улучшение промта")
        self.resize(760, 640)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        layout.addWidget(self._make_section("Исходный промт", result.original, readonly=True))
        layout.addWidget(
            self._make_section("Улучшенный промт", result.improved, button_label="Подставить")
        )

        for suggestion in result.alternatives:
            layout.addWidget(
                self._make_section(
                    suggestion.label,
                    suggestion.text,
                    button_label="Подставить",
                )
            )

        for suggestion in result.adaptations:
            layout.addWidget(
                self._make_section(
                    suggestion.label,
                    suggestion.text,
                    button_label="Подставить",
                )
            )

        layout.addStretch()
        scroll.setWidget(content)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(close_btn)

        root = QVBoxLayout(self)
        root.addWidget(scroll, 1)
        root.addLayout(buttons)

    def _make_section(
        self,
        title: str,
        text: str,
        *,
        readonly: bool = False,
        button_label: str | None = None,
    ) -> QWidget:
        box = QGroupBox(title)
        box_layout = QVBoxLayout(box)
        editor = QPlainTextEdit()
        editor.setPlainText(text)
        editor.setReadOnly(readonly)
        editor.setMinimumHeight(90)
        box_layout.addWidget(editor)

        if button_label:
            button = QPushButton(button_label)
            button.clicked.connect(lambda: self._apply_text(editor.toPlainText()))
            box_layout.addWidget(button)
        return box

    def _apply_text(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        self.selected_text = cleaned
        self.accept()


class SendWorker(QThread):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        session: models.ChatSession,
        model_list: list[models.Model],
        prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.model_list = model_list
        self.prompt = prompt

    def run(self) -> None:
        try:
            network.send_prompt_to_all(self.model_list, self.prompt, self.session)
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class ModelEditDialog(QDialog):
    def __init__(self, model: models.Model | None = None, parent=None) -> None:
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Редактирование модели" if model else "Новая модель")
        self.setMinimumWidth(520)

        self.name_edit = QLineEdit(model.name if model else "")
        self.api_url_edit = QLineEdit(
            model.api_url if model else db.OPENROUTER_API_URL
        )
        self.api_url_edit.setReadOnly(True)
        self.api_id_edit = QLineEdit(model.api_id if model else "")
        self.api_id_edit.setPlaceholderText("provider/model:free или openrouter/free")
        self.api_key_env_edit = QLineEdit(
            model.api_key_env if model else db.OPENROUTER_API_KEY_ENV
        )
        self.api_key_env_edit.setReadOnly(True)
        self.is_active_check = QCheckBox("Активна")
        self.is_active_check.setChecked(model.is_active if model else True)

        hint = QLabel(
            "Все модели подключаются через OpenRouter. "
            "Разрешены только бесплатные id (:free или openrouter/free)."
        )
        hint.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Название:", self.name_edit)
        form.addRow("OpenRouter URL:", self.api_url_edit)
        form.addRow("ID модели:", self.api_id_edit)
        form.addRow("Ключ .env:", self.api_key_env_edit)
        form.addRow("", self.is_active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Укажите название модели.")
            return
        api_id = self.api_id_edit.text().strip()
        if not api_id:
            QMessageBox.warning(self, "Ошибка", "Укажите ID модели OpenRouter.")
            return
        if not network.is_free_openrouter_model(api_id):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Разрешены только бесплатные модели: openrouter/free или id с суффиксом :free.",
            )
            return
        super().accept()

    def get_data(self) -> dict:
        api_id = self.api_id_edit.text().strip()
        return {
            "name": self.name_edit.text().strip(),
            "api_url": db.OPENROUTER_API_URL,
            "api_id": api_id,
            "api_key_env": db.OPENROUTER_API_KEY_ENV,
            "model_type": "openrouter",
            "is_active": self.is_active_check.isChecked(),
        }


class ModelsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Модели")
        self.resize(900, 420)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию или API ID...")
        self.search_edit.textChanged.connect(self.refresh_table)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Название", "API URL", "API ID", "Переменная .env", "Активна"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        add_btn = QPushButton("Добавить")
        edit_btn = QPushButton("Изменить")
        delete_btn = QPushButton("Удалить")
        toggle_btn = QPushButton("Вкл/выкл активность")
        close_btn = QPushButton("Закрыть")

        add_btn.clicked.connect(self.add_model)
        edit_btn.clicked.connect(self.edit_model)
        delete_btn.clicked.connect(self.delete_model)
        toggle_btn.clicked.connect(self.toggle_active)
        close_btn.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(toggle_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        self.refresh_table()

    def _selected_model_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def refresh_table(self) -> None:
        search = self.search_edit.text().strip() or None
        all_models = models.get_all_models()
        if search:
            needle = search.lower()
            all_models = [
                m
                for m in all_models
                if needle in m.name.lower()
                or needle in m.api_id.lower()
                or needle in m.api_url.lower()
            ]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for model in all_models:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(model.id)))
            self.table.setItem(row, 1, QTableWidgetItem(model.name))
            self.table.setItem(row, 2, QTableWidgetItem(model.api_url))
            self.table.setItem(row, 3, QTableWidgetItem(model.api_id))
            self.table.setItem(row, 4, QTableWidgetItem(model.api_key_env))
            active_item = QTableWidgetItem("Да" if model.is_active else "Нет")
            active_item.setData(Qt.ItemDataRole.UserRole, model.is_active)
            self.table.setItem(row, 5, active_item)
        self.table.setSortingEnabled(True)

    def add_model(self) -> None:
        dialog = ModelEditDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            data = dialog.get_data()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        if not all([data["name"], data["api_id"]]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля.")
            return
        try:
            models.add_model(**data)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить модель:\n{exc}")
            return
        self.refresh_table()

    def edit_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Выбор", "Выберите модель в таблице.")
            return
        row = db.get_model(model_id)
        if row is None:
            return
        model = models.row_to_model(row)
        dialog = ModelEditDialog(model, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            data = dialog.get_data()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        if not all([data["name"], data["api_id"]]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля.")
            return
        model.name = data["name"]
        model.api_url = data["api_url"]
        model.api_id = data["api_id"]
        model.api_key_env = data["api_key_env"]
        model.model_type = data["model_type"]
        model.is_active = data["is_active"]
        try:
            models.update_model(model)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить модель:\n{exc}")
            return
        self.refresh_table()

    def delete_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Выбор", "Выберите модель в таблице.")
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную модель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            models.delete_model(model_id)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить модель:\n{exc}")
            return
        self.refresh_table()

    def toggle_active(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Выбор", "Выберите модель в таблице.")
            return
        row = db.get_model(model_id)
        if row is None:
            return
        is_active = not bool(row["is_active"])
        models.set_model_active(model_id, is_active)
        self.refresh_table()


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(420)

        settings = models.get_settings()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(int(settings.get("request_timeout", "30") or 30))
        self.env_file_edit = QLineEdit(settings.get("env_file", ".env"))
        self.log_requests_check = QCheckBox("Логировать запросы")
        self.log_requests_check.setChecked(settings.get("log_requests", "0") == "1")
        self.default_tags_edit = QLineEdit(settings.get("default_tags", ""))
        self.assistant_enabled_check = QCheckBox("Включить AI-ассистент промтов")
        self.assistant_enabled_check.setChecked(
            settings.get("assistant_enabled", "1") == "1"
        )
        self.assistant_model_combo = QComboBox()
        self.assistant_model_combo.setMinimumWidth(280)
        self._load_assistant_models(settings.get("assistant_model_id", ""))

        form = QFormLayout()
        form.addRow("Таймаут запросов (с):", self.timeout_spin)
        form.addRow("Файл .env:", self.env_file_edit)
        form.addRow("Теги по умолчанию:", self.default_tags_edit)
        form.addRow("", self.log_requests_check)
        form.addRow("", self.assistant_enabled_check)
        form.addRow("Модель ассистента:", self.assistant_model_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _load_assistant_models(self, selected_id: str) -> None:
        self.assistant_model_combo.clear()
        all_models = models.get_all_models()
        if not all_models:
            self.assistant_model_combo.addItem("— модели не найдены —", "")
            return

        selected_index = 0
        for index, model in enumerate(all_models):
            label = f"{model.name} ({'активна' if model.is_active else 'выкл.'})"
            self.assistant_model_combo.addItem(label, str(model.id))
            if selected_id and str(model.id) == selected_id:
                selected_index = index
        self.assistant_model_combo.setCurrentIndex(selected_index)

    def save(self) -> None:
        assistant_model_id = self.assistant_model_combo.currentData() or ""
        models.save_settings(
            {
                "request_timeout": str(self.timeout_spin.value()),
                "env_file": self.env_file_edit.text().strip() or ".env",
                "log_requests": "1" if self.log_requests_check.isChecked() else "0",
                "default_tags": self.default_tags_edit.text().strip(),
                "assistant_enabled": "1" if self.assistant_enabled_check.isChecked() else "0",
                "assistant_model_id": assistant_model_id,
            }
        )
        network.load_env(models.get_env_file())
        self.accept()


class PromptsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сохранённые промты")
        self.resize(900, 520)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по тексту или тегам...")
        self.search_edit.textChanged.connect(self.refresh_table)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        delete_btn = QPushButton("Удалить")
        open_btn = QPushButton("Открыть")
        close_btn = QPushButton("Закрыть")
        open_btn.clicked.connect(self.open_selected)
        delete_btn.clicked.connect(self.delete_selected)
        close_btn.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(open_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        self.refresh_table()

    def refresh_table(self) -> None:
        search = self.search_edit.text().strip() or None
        rows = models.load_prompts(search)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for prompt in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            id_item = QTableWidgetItem(str(prompt.id))
            id_item.setData(Qt.ItemDataRole.UserRole, prompt)
            self.table.setItem(row_idx, 0, id_item)
            self.table.setItem(row_idx, 1, QTableWidgetItem(prompt.created_at))
            text = prompt.prompt.replace("\n", " ")
            if len(text) > 160:
                text = text[:160] + "..."
            self.table.setItem(row_idx, 2, QTableWidgetItem(text))
            self.table.setItem(row_idx, 3, QTableWidgetItem(prompt.tags or ""))
        self.table.setSortingEnabled(True)

    def _selected_prompt(self) -> models.Prompt | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        prompt = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(prompt, models.Prompt):
            return prompt
        prompt_id = int(item.text())
        row_data = db.get_prompt(prompt_id)
        if row_data is None:
            return None
        return models.row_to_prompt(row_data)

    def open_selected(self) -> None:
        prompt = self._selected_prompt()
        if prompt is None:
            QMessageBox.information(self, "Открыть", "Выберите промт в таблице.")
            return
        ResponseViewDialog.from_prompt(prompt, parent=self).exec()

    def on_row_double_clicked(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        prompt = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(prompt, models.Prompt):
            ResponseViewDialog.from_prompt(prompt, parent=self).exec()

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Выберите промт в таблице.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        prompt_id = int(item.text())
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранный промт и связанные результаты?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        models.delete_prompt(prompt_id)
        self.refresh_table()


class ResultsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сохранённые результаты")
        self.resize(960, 520)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по промту, модели или ответу...")
        self.search_edit.textChanged.connect(self.refresh_table)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Модель", "Промт", "Ответ"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        delete_btn = QPushButton("Удалить")
        open_btn = QPushButton("Открыть")
        export_md_btn = QPushButton("Экспорт MD")
        export_json_btn = QPushButton("Экспорт JSON")
        close_btn = QPushButton("Закрыть")
        open_btn.clicked.connect(self.open_selected)
        delete_btn.clicked.connect(self.delete_selected)
        export_md_btn.clicked.connect(self.export_markdown)
        export_json_btn.clicked.connect(self.export_json)
        close_btn.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(open_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(export_md_btn)
        buttons.addWidget(export_json_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        self.refresh_table()

    def refresh_table(self) -> None:
        search = self.search_edit.text().strip() or None
        rows = models.load_results(search)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for result in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            id_item = QTableWidgetItem(str(result.id))
            id_item.setData(Qt.ItemDataRole.UserRole, result)
            self.table.setItem(row_idx, 0, id_item)
            self.table.setItem(row_idx, 1, QTableWidgetItem(result.created_at))
            self.table.setItem(row_idx, 2, QTableWidgetItem(result.model_name))
            prompt_preview = result.prompt_text
            if len(prompt_preview) > 120:
                prompt_preview = prompt_preview[:120] + "..."
            self.table.setItem(row_idx, 3, QTableWidgetItem(prompt_preview))
            response_preview = result.response
            if len(response_preview) > 200:
                response_preview = response_preview[:200] + "..."
            self.table.setItem(row_idx, 4, QTableWidgetItem(response_preview))
        self.table.setSortingEnabled(True)

    def _selected_result(self) -> models.Result | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        result = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(result, models.Result):
            return result
        return None

    def open_selected(self) -> None:
        result = self._selected_result()
        if result is None:
            QMessageBox.information(self, "Открыть", "Выберите результат в таблице.")
            return
        ResponseViewDialog.from_saved_result(result, parent=self).exec()

    def on_row_double_clicked(self, row: int, column: int) -> None:
        item = self.table.item(row, 0)
        if item is None:
            return
        result = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(result, models.Result):
            ResponseViewDialog.from_saved_result(result, parent=self).exec()

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Выбор", "Выберите результат в таблице.")
            return
        item = self.table.item(row, 0)
        if item is None:
            return
        result_id = int(item.text())
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранный результат?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db.delete_result(result_id)
        self.refresh_table()

    def _visible_results(self) -> list[models.Result]:
        search = self.search_edit.text().strip() or None
        return models.load_results(search)

    def export_markdown(self) -> None:
        rows = self._visible_results()
        if not rows:
            QMessageBox.information(self, "Экспорт", "Нет данных для экспорта.")
            return
        content = export.saved_results_to_markdown(rows)
        if save_text_to_file(self, "chatlist-results.md", content):
            QMessageBox.information(self, "Экспорт", "Файл Markdown сохранён.")

    def export_json(self) -> None:
        rows = self._visible_results()
        if not rows:
            QMessageBox.information(self, "Экспорт", "Нет данных для экспорта.")
            return
        content = export.saved_results_to_json(rows)
        if save_text_to_file(self, "chatlist-results.json", content):
            QMessageBox.information(self, "Экспорт", "Файл JSON сохранён.")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.resize(980, 680)

        db.init_db()
        network.load_env(models.get_env_file())
        self.session = models.ChatSession()
        self.worker: SendWorker | None = None
        self.improve_worker: ImprovePromptWorker | None = None

        self._build_menu()
        self._build_ui()
        self.refresh_prompts_combo()

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        models_action = QAction("Модели", self)
        models_action.triggered.connect(self.open_models_dialog)
        menu_bar.addAction(models_action)

        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        menu_bar.addAction(settings_action)

        results_action = QAction("Сохранённые результаты", self)
        results_action.triggered.connect(self.open_results_dialog)
        menu_bar.addAction(results_action)

        prompts_action = QAction("Промты", self)
        prompts_action.triggered.connect(self.open_prompts_dialog)
        menu_bar.addAction(prompts_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        prompt_group = QGroupBox("Промт")
        prompt_layout = QVBoxLayout(prompt_group)

        saved_row = QHBoxLayout()
        saved_row.addWidget(QLabel("Сохранённые:"))
        self.prompts_combo = QComboBox()
        self.prompts_combo.setMinimumWidth(320)
        self.prompts_combo.currentIndexChanged.connect(self.on_prompt_selected)
        saved_row.addWidget(self.prompts_combo, 1)
        reload_btn = QPushButton("Обновить")
        reload_btn.clicked.connect(self.refresh_prompts_combo)
        saved_row.addWidget(reload_btn)
        prompt_layout.addLayout(saved_row)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса...")
        self.prompt_edit.setMinimumHeight(100)
        prompt_layout.addWidget(self.prompt_edit)

        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Теги:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("python, api")
        options_row.addWidget(self.tags_edit, 1)
        self.save_prompt_check = QCheckBox("Сохранить промт в базу")
        options_row.addWidget(self.save_prompt_check)
        self.improve_btn = QPushButton("Улучшить промт")
        self.improve_btn.clicked.connect(self.improve_prompt)
        options_row.addWidget(self.improve_btn)
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_prompt)
        options_row.addWidget(self.send_btn)
        prompt_layout.addLayout(options_row)

        root.addWidget(prompt_group)

        results_group = QGroupBox("Результаты")
        results_layout = QVBoxLayout(results_group)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Без сортировки", "По модели (А–Я)", "По ответу (А–Я)"])
        self.sort_combo.currentIndexChanged.connect(self.apply_temp_sort)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()
        results_layout.addLayout(sort_row)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setWordWrap(True)
        self.results_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        vheader = self.results_table.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        vheader.setMinimumSectionSize(96)
        self.results_table.cellChanged.connect(self.on_result_cell_changed)
        self.results_table.cellDoubleClicked.connect(self.on_result_double_clicked)
        results_layout.addWidget(self.results_table)
        root.addWidget(results_group, 1)

        bottom_row = QHBoxLayout()
        self.open_btn = QPushButton("Открыть")
        self.open_btn.clicked.connect(self.open_selected_response)
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_selected)
        self.export_md_btn = QPushButton("Экспорт MD")
        self.export_md_btn.clicked.connect(self.export_selected_markdown)
        self.export_json_btn = QPushButton("Экспорт JSON")
        self.export_json_btn.clicked.connect(self.export_selected_json)
        self.new_btn = QPushButton("Новый запрос")
        self.new_btn.clicked.connect(self.new_request)
        bottom_row.addWidget(self.open_btn)
        bottom_row.addWidget(self.save_btn)
        bottom_row.addWidget(self.export_md_btn)
        bottom_row.addWidget(self.export_json_btn)
        bottom_row.addWidget(self.new_btn)
        bottom_row.addStretch()
        root.addLayout(bottom_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        self.status_label = QLabel("Готово")
        root.addWidget(self.status_label)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.send_btn.setEnabled(not busy)
        self.improve_btn.setEnabled(not busy)
        self.open_btn.setEnabled(not busy)
        self.save_btn.setEnabled(not busy)
        self.export_md_btn.setEnabled(not busy)
        self.export_json_btn.setEnabled(not busy)
        self.new_btn.setEnabled(not busy)
        if busy:
            self.progress.show()
            self.status_label.setText(message or "Отправка запросов...")
        else:
            self.progress.hide()
            self.status_label.setText(message or "Готово")

    def refresh_prompts_combo(self) -> None:
        self.prompts_combo.blockSignals(True)
        self.prompts_combo.clear()
        self.prompts_combo.addItem("— новый промт —", None)
        for prompt in models.load_prompts():
            label = prompt.prompt.replace("\n", " ")
            if len(label) > 80:
                label = label[:80] + "..."
            self.prompts_combo.addItem(label, prompt.id)
        self.prompts_combo.blockSignals(False)

    def on_prompt_selected(self, index: int) -> None:
        if index <= 0:
            return
        prompt_id = self.prompts_combo.currentData()
        if prompt_id is None:
            return
        row = db.get_prompt(int(prompt_id))
        if row is None:
            return
        self.prompt_edit.setPlainText(row["prompt"])
        self.tags_edit.setText(row["tags"] or "")
        self.session.set_current_prompt(row["prompt"], row["id"], row["tags"])

    def _current_prompt_text(self) -> str:
        return self.prompt_edit.toPlainText().strip()

    def _sync_session_prompt(self) -> bool:
        text = self._current_prompt_text()
        if not text:
            QMessageBox.warning(self, "Промт", "Введите текст промта.")
            return False

        prompt_id = None
        tags = self.tags_edit.text().strip() or None
        combo_index = self.prompts_combo.currentIndex()
        if combo_index > 0:
            prompt_id = self.prompts_combo.currentData()

        if self.save_prompt_check.isChecked() and prompt_id is None:
            default_tags = models.get_settings().get("default_tags", "")
            if not tags and default_tags:
                tags = default_tags
            saved = models.save_prompt(text, tags)
            prompt_id = saved.id
            self.refresh_prompts_combo()
            idx = self.prompts_combo.findData(saved.id)
            if idx >= 0:
                self.prompts_combo.setCurrentIndex(idx)

        self.session.set_current_prompt(text, prompt_id, tags)
        return True

    def improve_prompt(self) -> None:
        if self.improve_worker and self.improve_worker.isRunning():
            return

        text = self._current_prompt_text()
        if not text:
            QMessageBox.warning(self, "Промт", "Введите текст промта.")
            return

        assistant_model = models.get_assistant_model()
        if assistant_model is None:
            QMessageBox.warning(
                self,
                "AI-ассистент",
                "Ассистент отключён или модель не выбрана. "
                "Откройте «Настройки» и укажите модель для улучшения промтов.",
            )
            return

        self.set_busy(True, f"Улучшение промта ({assistant_model.name})...")
        self.improve_worker = ImprovePromptWorker(
            text,
            assistant_model,
            parent=self,
        )
        self.improve_worker.finished.connect(self.on_improve_finished)
        self.improve_worker.failed.connect(self.on_improve_failed)
        self.improve_worker.start()

    def on_improve_finished(self, result: PromptImprovementResult) -> None:
        self.set_busy(False, "Промт улучшен")
        dialog = PromptImprovementDialog(result, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.selected_text:
            self.prompt_edit.setPlainText(dialog.selected_text)
            self.session.set_current_prompt(
                dialog.selected_text,
                self.session.current_prompt_id,
                self.session.current_tags,
            )

    def on_improve_failed(self, message: str) -> None:
        self.set_busy(False, "Ошибка улучшения")
        QMessageBox.critical(self, "AI-ассистент", message)

    def send_prompt(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if not self._sync_session_prompt():
            return

        active = models.get_active_models()
        if not active:
            QMessageBox.warning(
                self,
                "Модели",
                "Нет активных моделей. Откройте «Модели» и включите хотя бы одну.",
            )
            return

        self.session.clear_temp_results()
        self.populate_results_table()
        self.set_busy(True, f"Отправка в {len(active)} модель(ей)...")

        self.worker = SendWorker(
            self.session,
            active,
            self.session.current_prompt_text,
            parent=self,
        )
        self.worker.finished.connect(self.on_send_finished)
        self.worker.failed.connect(self.on_send_failed)
        self.worker.start()

    def on_send_finished(self) -> None:
        self.populate_results_table()
        count = len(self.session.get_temp_results())
        self.set_busy(False, f"Получено ответов: {count}")

    def on_send_failed(self, message: str) -> None:
        self.set_busy(False, "Ошибка отправки")
        QMessageBox.critical(self, "Ошибка", message)

    def populate_results_table(self) -> None:
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(0)
        for index, item in enumerate(self.session.get_temp_results()):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            model_item = QTableWidgetItem(item.model_name)
            model_item.setTextAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            )
            self.results_table.setItem(row, 0, model_item)

            response_item = QTableWidgetItem(item.response)
            response_item.setTextAlignment(
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            )
            self.results_table.setItem(row, 1, response_item)

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            check_item.setCheckState(
                Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked
            )
            check_item.setData(Qt.ItemDataRole.UserRole, index)
            self.results_table.setItem(row, 2, check_item)

        self.results_table.resizeRowsToContents()
        for row in range(self.results_table.rowCount()):
            if self.results_table.rowHeight(row) < 96:
                self.results_table.setRowHeight(row, 96)
        self.results_table.blockSignals(False)

    def on_result_cell_changed(self, row: int, column: int) -> None:
        if column != 2:
            return
        item = self.results_table.item(row, column)
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None:
            return
        selected = item.checkState() == Qt.CheckState.Checked
        self.session.set_temp_result_selected(int(index), selected)

    def _response_from_row(self, row: int) -> tuple[str, str] | None:
        if row < 0:
            return None
        model_item = self.results_table.item(row, 0)
        response_item = self.results_table.item(row, 1)
        if response_item is None:
            return None
        model_name = model_item.text() if model_item else "Модель"
        return model_name, response_item.text()

    def open_selected_response(self) -> None:
        row = self.results_table.currentRow()
        data = self._response_from_row(row)
        if data is None:
            QMessageBox.information(self, "Открыть", "Выберите строку с ответом в таблице.")
            return
        model_name, response = data
        ResponseViewDialog(
            model_name,
            self.session.current_prompt_text,
            response,
            parent=self,
        ).exec()

    def on_result_double_clicked(self, row: int, column: int) -> None:
        if column == 2:
            return
        data = self._response_from_row(row)
        if data is None:
            return
        model_name, response = data
        ResponseViewDialog(
            model_name,
            self.session.current_prompt_text,
            response,
            parent=self,
        ).exec()

    def apply_temp_sort(self) -> None:
        mode = self.sort_combo.currentIndex()
        if mode == 1:
            self.session.sort_temp_results(by_model=True)
        elif mode == 2:
            self.session.sort_temp_results(by_response=True)
        self.populate_results_table()

    def export_selected_markdown(self) -> None:
        selected = self.session.get_selected_temp_results()
        if not selected:
            QMessageBox.information(self, "Экспорт", "Отметьте хотя бы один результат.")
            return
        content = export.temp_results_to_markdown(self.session.current_prompt_text, selected)
        if save_text_to_file(self, "chatlist-export.md", content):
            QMessageBox.information(self, "Экспорт", "Файл Markdown сохранён.")

    def export_selected_json(self) -> None:
        selected = self.session.get_selected_temp_results()
        if not selected:
            QMessageBox.information(self, "Экспорт", "Отметьте хотя бы один результат.")
            return
        content = export.temp_results_to_json(self.session.current_prompt_text, selected)
        if save_text_to_file(self, "chatlist-export.json", content):
            QMessageBox.information(self, "Экспорт", "Файл JSON сохранён.")

    def save_selected(self) -> None:
        selected = self.session.get_selected_temp_results()
        if not selected:
            QMessageBox.information(self, "Сохранение", "Отметьте хотя бы один результат.")
            return
        if not self.session.current_prompt_text and not self._sync_session_prompt():
            return

        try:
            count = models.save_selected_results(
                self.session,
                save_prompt_if_new=self.save_prompt_check.isChecked()
                or self.session.current_prompt_id is None,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{exc}")
            return

        self.populate_results_table()
        QMessageBox.information(self, "Сохранение", f"Сохранено записей: {count}")

    def new_request(self) -> None:
        self.session.reset_for_new_request()
        self.prompt_edit.clear()
        self.tags_edit.clear()
        self.save_prompt_check.setChecked(False)
        self.prompts_combo.setCurrentIndex(0)
        self.populate_results_table()
        self.status_label.setText("Новый запрос")

    def open_models_dialog(self) -> None:
        ModelsDialog(self).exec()

    def open_settings_dialog(self) -> None:
        SettingsDialog(self).exec()

    def open_results_dialog(self) -> None:
        ResultsDialog(self).exec()

    def open_prompts_dialog(self) -> None:
        dialog = PromptsDialog(self)
        dialog.exec()
        self.refresh_prompts_combo()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
