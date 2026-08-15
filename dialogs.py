"""Диалоги управления данными: модели, промты, результаты, настройки."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from db import Database


class ModelEditDialog(QDialog):
    def __init__(self, parent=None, data: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Модель" if data else "Новая модель")
        self.resize(520, 200)

        self.name_edit = QLineEdit(data["name"] if data else "")
        self.url_edit = QLineEdit(
            data["api_url"]
            if data
            else "https://openrouter.ai/api/v1/chat/completions"
        )
        self.api_id_edit = QLineEdit(
            data["api_id"] if data else "OPENROUTER_API_KEY"
        )
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(
            bool(data["is_active"]) if data else True
        )

        form = QFormLayout()
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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Имя", "API URL", "api_id", "Активна"]
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
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
        models = self.db.list_models()
        self.table.setRowCount(len(models))
        for i, m in enumerate(models):
            self.table.setItem(i, 0, QTableWidgetItem(str(m["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(m["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(m["api_url"]))
            self.table.setItem(i, 3, QTableWidgetItem(m["api_id"]))
            self.table.setItem(
                i, 4, QTableWidgetItem("да" if m["is_active"] else "нет")
            )

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


class PromptsDialog(QDialog):
    """Просмотр промтов. При «Использовать» возвращает id выбранного промта."""

    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.selected_prompt_id: int | None = None
        self.setWindowTitle("Сохранённые промты")
        self.resize(800, 480)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Теги", "Промт"])
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 420)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(120)

        self.tags_edit = QLineEdit()

        use_btn = QPushButton("Использовать")
        save_tags_btn = QPushButton("Сохранить теги")
        del_btn = QPushButton("Удалить")
        close_btn = QPushButton("Закрыть")

        row = QHBoxLayout()
        row.addWidget(use_btn)
        row.addWidget(save_tags_btn)
        row.addWidget(del_btn)
        row.addStretch()
        row.addWidget(close_btn)

        form = QFormLayout()
        form.addRow("Теги:", self.tags_edit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Текст:"))
        layout.addWidget(self.preview)
        layout.addLayout(form)
        layout.addLayout(row)

        use_btn.clicked.connect(self._use)
        save_tags_btn.clicked.connect(self._save_tags)
        del_btn.clicked.connect(self._delete)
        close_btn.clicked.connect(self.reject)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.doubleClicked.connect(lambda _: self._use())

        self._reload()

    def _selected_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        return int(item.text()) if item else None

    def _reload(self) -> None:
        prompts = self.db.list_prompts()
        self.table.setRowCount(len(prompts))
        for i, p in enumerate(prompts):
            preview = p["prompt"].replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "…"
            self.table.setItem(i, 0, QTableWidgetItem(str(p["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(p["created_at"]))
            self.table.setItem(i, 2, QTableWidgetItem(p["tags"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(preview))

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

    def _save_tags(self) -> None:
        prompt_id = self._selected_id()
        if prompt_id is None:
            QMessageBox.information(self, "Промты", "Выберите промт.")
            return
        self.db.update_prompt(prompt_id, tags=self.tags_edit.text().strip())
        self._reload()

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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Дата", "Модель", "Промт", "Ответ"]
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 220)
        self.table.setColumnWidth(4, 280)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        del_btn = QPushButton("Удалить")
        close_btn = QPushButton("Закрыть")
        row = QHBoxLayout()
        row.addWidget(del_btn)
        row.addStretch()
        row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Полный ответ:"))
        layout.addWidget(self.preview)
        layout.addLayout(row)

        del_btn.clicked.connect(self._delete)
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
            self.table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["created_at"]))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("model_name") or ""))
            self.table.setItem(i, 3, QTableWidgetItem(prompt_preview))
            self.table.setItem(i, 4, QTableWidgetItem(resp_preview))

    def _on_select(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.preview.clear()
            return
        data = self._rows[rows[0].row()]
        text = (
            f"Модель: {data.get('model_name')}\n"
            f"Промт:\n{data.get('prompt_text')}\n\n"
            f"Ответ:\n{data.get('response')}"
        )
        self.preview.setPlainText(text)

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
