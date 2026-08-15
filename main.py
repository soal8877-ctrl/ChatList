"""GUI ChatList: ввод промта, рассылка в модели, сохранение выбранных ответов."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import Database
from dialogs import ModelsDialog, PromptsDialog, ResultsDialog, SettingsDialog
from models import MissingApiKeyError, get_active_models, validate_active_models
from network import NetworkError, send_prompt
from temp_results import TempResultsTable


class SendWorker(QThread):
    finished_ok = pyqtSignal(list)
    finished_err = pyqtSignal(str)

    def __init__(self, prompt_text: str, timeout_sec: float) -> None:
        super().__init__()
        self.prompt_text = prompt_text
        self.timeout_sec = timeout_sec

    def run(self) -> None:
        db = Database()
        try:
            try:
                active = get_active_models(db)
            except MissingApiKeyError as exc:
                self.finished_err.emit(str(exc))
                return

            if not active:
                self.finished_err.emit("Нет активных моделей в базе.")
                return

            items: list[tuple[int, str, str]] = []
            for model in active:
                try:
                    answer = send_prompt(
                        model, self.prompt_text, timeout_sec=self.timeout_sec
                    )
                except NetworkError as exc:
                    answer = f"[Ошибка] {exc}"
                items.append((model.id, model.name, answer))
            self.finished_ok.emit(items)
        finally:
            db.close()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")

        self.db = Database()
        self.db.seed_default_models()
        self._ensure_default_settings()
        self._apply_window_size()

        self.temp = TempResultsTable()
        self.worker: SendWorker | None = None
        self.current_prompt_id: int | None = None

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItem("— Новый промт —", None)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите промт…")
        self.prompt_edit.setMinimumHeight(100)

        self.send_btn = QPushButton("Отправить")
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setEnabled(False)
        self.status_label = QLabel("")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 600)
        self.table.setColumnWidth(2, 80)

        top = QHBoxLayout()
        top.addWidget(QLabel("Сохранённый промт:"))
        top.addWidget(self.prompt_combo, stretch=1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.send_btn)
        buttons.addWidget(self.save_btn)
        buttons.addStretch()
        buttons.addWidget(self.status_label)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.prompt_edit)
        layout.addLayout(buttons)
        layout.addWidget(self.table)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._build_menu()

        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_chosen)
        self.send_btn.clicked.connect(self._on_send)
        self.save_btn.clicked.connect(self._on_save)
        self.table.itemChanged.connect(self._on_table_changed)

        self._reload_prompts()
        self._check_keys_hint()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Данные")
        menu.addAction("Модели…", self._open_models)
        menu.addAction("Промты…", self._open_prompts)
        menu.addAction("Результаты…", self._open_results)
        menu.addSeparator()
        menu.addAction("Настройки…", self._open_settings)

    def _ensure_default_settings(self) -> None:
        if self.db.get_setting("request_timeout_sec") is None:
            self.db.set_setting("request_timeout_sec", "60")
        if self.db.get_setting("window_width") is None:
            self.db.set_setting("window_width", "900")
        if self.db.get_setting("window_height") is None:
            self.db.set_setting("window_height", "600")
        self.db.set_setting("db_path", str(self.db.db_path))

    def _apply_window_size(self) -> None:
        try:
            w = int(self.db.get_setting("window_width", "900") or "900")
            h = int(self.db.get_setting("window_height", "600") or "600")
        except ValueError:
            w, h = 900, 600
        self.resize(w, h)

    def _open_models(self) -> None:
        ModelsDialog(self.db, self).exec()
        self._check_keys_hint()

    def _open_prompts(self) -> None:
        dlg = PromptsDialog(self.db, self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.selected_prompt_id:
            self._use_prompt(dlg.selected_prompt_id)
        self._reload_prompts()

    def _use_prompt(self, prompt_id: int) -> None:
        row = self.db.get_prompt(prompt_id)
        if not row:
            return
        self.current_prompt_id = prompt_id
        self.prompt_edit.setPlainText(row["prompt"])
        self._reload_prompts()
        idx = self.prompt_combo.findData(prompt_id)
        if idx >= 0:
            self.prompt_combo.setCurrentIndex(idx)

    def _open_results(self) -> None:
        ResultsDialog(self.db, self).exec()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.db, self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            dlg.apply()
            self._apply_window_size()
            self.status_label.setText("Настройки сохранены")

    def closeEvent(self, event) -> None:  # noqa: N802
        self.db.close()
        super().closeEvent(event)

    def _check_keys_hint(self) -> None:
        errors = validate_active_models(self.db)
        if errors:
            self.status_label.setText(
                "Нет ключей в .env: " + "; ".join(errors)
            )
        else:
            active_n = len(self.db.list_models(active_only=True))
            self.status_label.setText(f"Активных моделей: {active_n}")

    def _reload_prompts(self) -> None:
        current = self.prompt_combo.currentData()
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— Новый промт —", None)
        for row in self.db.list_prompts():
            preview = row["prompt"].replace("\n", " ")
            if len(preview) > 60:
                preview = preview[:57] + "…"
            self.prompt_combo.addItem(f"#{row['id']}: {preview}", row["id"])
        self.prompt_combo.blockSignals(False)
        if current is not None:
            idx = self.prompt_combo.findData(current)
            if idx >= 0:
                self.prompt_combo.setCurrentIndex(idx)

    def _on_prompt_chosen(self, _index: int) -> None:
        prompt_id = self.prompt_combo.currentData()
        self.current_prompt_id = prompt_id
        if prompt_id is None:
            return
        row = self.db.get_prompt(int(prompt_id))
        if row:
            self.prompt_edit.setPlainText(row["prompt"])

    def _timeout_sec(self) -> float:
        raw = self.db.get_setting("request_timeout_sec", "60") or "60"
        try:
            return float(raw)
        except ValueError:
            return 60.0

    def _on_send(self) -> None:
        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return

        self.temp.reset()
        self._fill_table()
        self.save_btn.setEnabled(False)

        if self.current_prompt_id is None:
            self.current_prompt_id = self.db.create_prompt(text)
            self._reload_prompts()
            idx = self.prompt_combo.findData(self.current_prompt_id)
            if idx >= 0:
                self.prompt_combo.setCurrentIndex(idx)
        else:
            stored = self.db.get_prompt(self.current_prompt_id)
            if stored and stored["prompt"] != text:
                self.current_prompt_id = self.db.create_prompt(text)
                self._reload_prompts()
                idx = self.prompt_combo.findData(self.current_prompt_id)
                if idx >= 0:
                    self.prompt_combo.setCurrentIndex(idx)

        self.send_btn.setEnabled(False)
        self.status_label.setText("Отправка…")

        self.worker = SendWorker(text, self._timeout_sec())
        self.worker.finished_ok.connect(self._on_send_ok)
        self.worker.finished_err.connect(self._on_send_err)
        self.worker.finished.connect(lambda: self.send_btn.setEnabled(True))
        self.worker.start()

    def _on_send_ok(self, items: list) -> None:
        text = self.prompt_edit.toPlainText().strip()
        self.temp.create_from_responses(
            prompt_text=text,
            prompt_id=self.current_prompt_id,
            items=items,
        )
        self._fill_table()
        self.save_btn.setEnabled(bool(self.temp.rows))
        self.status_label.setText(f"Получено ответов: {len(items)}")

    def _on_send_err(self, message: str) -> None:
        self.status_label.setText("")
        QMessageBox.critical(self, "ChatList", message)

    def _fill_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.temp.rows))
        for i, row in enumerate(self.temp.rows):
            name_item = QTableWidgetItem(row.model_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            resp_item = QTableWidgetItem(row.response)
            resp_item.setFlags(resp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            check.setCheckState(
                Qt.CheckState.Checked if row.selected else Qt.CheckState.Unchecked
            )
            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, resp_item)
            self.table.setItem(i, 2, check)
        self.table.blockSignals(False)

    def _on_table_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2:
            return
        row = item.row()
        if 0 <= row < len(self.temp.rows):
            self.temp.set_selected(
                row, item.checkState() == Qt.CheckState.Checked
            )

    def _on_save(self) -> None:
        selected = self.temp.selected_rows()
        if not selected:
            QMessageBox.information(
                self, "ChatList", "Отметьте строки чекбоксом «Выбрать»."
            )
            return

        prompt_id = self.current_prompt_id
        if prompt_id is None:
            text = self.prompt_edit.toPlainText().strip()
            prompt_id = self.db.create_prompt(text)
            self.current_prompt_id = prompt_id

        for row in selected:
            self.db.save_result(prompt_id, row.model_id, row.response)

        self.temp.clear()
        self._fill_table()
        self.save_btn.setEnabled(False)
        self.status_label.setText(f"Сохранено результатов: {len(selected)}")
        QMessageBox.information(
            self, "ChatList", f"Сохранено в БД: {len(selected)}"
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
