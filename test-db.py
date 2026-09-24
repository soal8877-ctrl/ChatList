"""Простой графический браузер SQLite с пагинацией и CRUD."""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def quote_identifier(value: str) -> str:
    """Безопасно экранирует имя таблицы или столбца SQLite."""
    return '"' + value.replace('"', '""') + '"'


def display_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def convert_value(text: str, declared_type: str) -> Any:
    """Преобразует введённый текст в базовый тип SQLite."""
    type_name = declared_type.upper()
    if "INT" in type_name:
        return int(text)
    if any(token in type_name for token in ("REAL", "FLOA", "DOUB")):
        return float(text)
    if "BLOB" in type_name:
        return bytes.fromhex(text)
    return text


class FieldEditor(QWidget):
    def __init__(
        self,
        value: Any = "",
        *,
        allow_default: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.edit = QLineEdit()
        self.null_check = QCheckBox("NULL")
        self.default_check = QCheckBox("DEFAULT")
        self.default_check.setVisible(allow_default)

        if value is None:
            self.null_check.setChecked(True)
        elif isinstance(value, bytes):
            self.edit.setText(value.hex())
        else:
            self.edit.setText(str(value))

        self.null_check.toggled.connect(self._update_state)
        self.default_check.toggled.connect(self._update_state)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.null_check)
        layout.addWidget(self.default_check)
        self._update_state()

    def _update_state(self) -> None:
        if self.default_check.isChecked():
            self.null_check.setChecked(False)
        if self.null_check.isChecked():
            self.default_check.setChecked(False)
        self.edit.setEnabled(
            not self.null_check.isChecked() and not self.default_check.isChecked()
        )


class RecordDialog(QDialog):
    def __init__(
        self,
        columns: list[sqlite3.Row],
        values: dict[str, Any] | None = None,
        *,
        create_mode: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self.create_mode = create_mode
        self.editors: dict[str, FieldEditor] = {}
        self.setWindowTitle("Добавить запись" if create_mode else "Изменить запись")
        self.setMinimumWidth(560)

        form = QFormLayout()
        for column in columns:
            name = column["name"]
            declared_type = column["type"] or "TEXT"
            current_value = "" if values is None else values.get(name)
            editor = FieldEditor(current_value, allow_default=create_mode)

            # INTEGER PRIMARY KEY обычно заполняется SQLite автоматически.
            if (
                create_mode
                and column["pk"]
                and "INT" in declared_type.upper()
            ):
                editor.default_check.setChecked(True)

            self.editors[name] = editor
            required = " *" if column["notnull"] and column["dflt_value"] is None else ""
            form.addRow(f"{name} ({declared_type}){required}:", editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[dict[str, Any], set[str]]:
        values: dict[str, Any] = {}
        defaults: set[str] = set()

        for column in self.columns:
            name = column["name"]
            editor = self.editors[name]
            if self.create_mode and editor.default_check.isChecked():
                defaults.add(name)
                continue
            if editor.null_check.isChecked():
                values[name] = None
                continue
            try:
                values[name] = convert_value(editor.edit.text(), column["type"] or "")
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Некорректное значение столбца «{name}»: {exc}"
                ) from exc

        return values, defaults

    def accept(self) -> None:
        try:
            self.get_values()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка ввода", str(exc))
            return
        super().accept()


class DatabaseBrowser(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SQLite Test DB")
        self.resize(1100, 700)

        self.connection: sqlite3.Connection | None = None
        self.database_path: Path | None = None
        self.current_table: str | None = None
        self.columns: list[sqlite3.Row] = []
        self.identity_columns: list[str] = []
        self.current_rows: list[dict[str, Any]] = []
        self.total_rows = 0

        self._build_ui()

        default_db = Path(__file__).resolve().parent / "chatlist.db"
        if default_db.exists():
            self.open_database(default_db)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        file_row = QHBoxLayout()
        choose_button = QPushButton("Выбрать SQLite…")
        choose_button.clicked.connect(self.choose_database)
        self.path_label = QLabel("Файл не выбран")
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        file_row.addWidget(choose_button)
        file_row.addWidget(self.path_label, 1)
        root.addLayout(file_row)

        splitter = QSplitter()
        root.addWidget(splitter, 1)

        tables_panel = QWidget()
        tables_layout = QVBoxLayout(tables_panel)
        tables_layout.addWidget(QLabel("Таблицы"))
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self.open_selected_table)
        tables_layout.addWidget(self.tables_list, 1)
        open_button = QPushButton("Открыть")
        open_button.clicked.connect(self.open_selected_table)
        tables_layout.addWidget(open_button)
        splitter.addWidget(tables_panel)

        data_panel = QWidget()
        data_layout = QVBoxLayout(data_panel)

        self.table_title = QLabel("Выберите таблицу")
        data_layout.addWidget(self.table_title)

        self.data_table = QTableWidget()
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        data_layout.addWidget(self.data_table, 1)

        crud_row = QHBoxLayout()
        create_button = QPushButton("Создать")
        read_button = QPushButton("Открыть запись")
        update_button = QPushButton("Изменить")
        delete_button = QPushButton("Удалить")
        refresh_button = QPushButton("Обновить")
        create_button.clicked.connect(self.create_record)
        read_button.clicked.connect(self.read_record)
        update_button.clicked.connect(self.update_record)
        delete_button.clicked.connect(self.delete_record)
        refresh_button.clicked.connect(self.refresh_page)
        crud_row.addWidget(create_button)
        crud_row.addWidget(read_button)
        crud_row.addWidget(update_button)
        crud_row.addWidget(delete_button)
        crud_row.addWidget(refresh_button)
        crud_row.addStretch()
        data_layout.addLayout(crud_row)

        pagination = QHBoxLayout()
        first_button = QPushButton("«")
        previous_button = QPushButton("‹")
        next_button = QPushButton("›")
        last_button = QPushButton("»")
        first_button.clicked.connect(lambda: self.go_to_page(1))
        previous_button.clicked.connect(lambda: self.go_to_page(self.page_spin.value() - 1))
        next_button.clicked.connect(lambda: self.go_to_page(self.page_spin.value() + 1))
        last_button.clicked.connect(self.go_to_last_page)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(self.refresh_page)
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "25", "50", "100"])
        self.page_size_combo.setCurrentText("25")
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        self.page_info = QLabel("Страница 0 из 0 · записей: 0")

        pagination.addWidget(first_button)
        pagination.addWidget(previous_button)
        pagination.addWidget(QLabel("Страница:"))
        pagination.addWidget(self.page_spin)
        pagination.addWidget(next_button)
        pagination.addWidget(last_button)
        pagination.addSpacing(16)
        pagination.addWidget(QLabel("На странице:"))
        pagination.addWidget(self.page_size_combo)
        pagination.addWidget(self.page_info)
        pagination.addStretch()
        data_layout.addLayout(pagination)

        splitter.addWidget(data_panel)
        splitter.setSizes([240, 860])

    def choose_database(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите базу SQLite",
            str(Path.cwd()),
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if filename:
            self.open_database(Path(filename))

    def open_database(self, path: Path) -> None:
        if self.connection is not None:
            self.connection.close()

        try:
            connection = sqlite3.connect(path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка SQLite", str(exc))
            return

        self.connection = connection
        self.database_path = path
        self.current_table = None
        self.path_label.setText(str(path))
        self.setWindowTitle(f"SQLite Test DB — {path.name}")
        self.load_tables()

    def load_tables(self) -> None:
        if self.connection is None:
            return
        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_schema
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        self.tables_list.clear()
        self.tables_list.addItems([row["name"] for row in rows])
        self.table_title.setText(f"Таблиц: {len(rows)}")
        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)

    def open_selected_table(self, _item: Any = None) -> None:
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Таблица", "Выберите таблицу.")
            return

        self.current_table = item.text()
        assert self.connection is not None
        self.columns = list(
            self.connection.execute(
                f"PRAGMA table_info({quote_identifier(self.current_table)})"
            ).fetchall()
        )
        self.identity_columns = [
            column["name"]
            for column in sorted(self.columns, key=lambda col: col["pk"])
            if column["pk"]
        ]
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.refresh_page()

    def page_size(self) -> int:
        return int(self.page_size_combo.currentText())

    def total_pages(self) -> int:
        return max(1, math.ceil(self.total_rows / self.page_size()))

    def refresh_page(self) -> None:
        if self.connection is None or self.current_table is None:
            return

        table = quote_identifier(self.current_table)
        self.total_rows = int(
            self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        )
        pages = self.total_pages()
        page = min(max(1, self.page_spin.value()), pages)
        if page != self.page_spin.value():
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(page)
            self.page_spin.blockSignals(False)
        self.page_spin.setMaximum(pages)

        offset = (page - 1) * self.page_size()
        column_sql = ", ".join(quote_identifier(col["name"]) for col in self.columns)
        if self.identity_columns:
            sql = f"SELECT {column_sql} FROM {table} LIMIT ? OFFSET ?"
        else:
            sql = (
                f"SELECT rowid AS __browser_rowid__, {column_sql} "
                f"FROM {table} LIMIT ? OFFSET ?"
            )

        try:
            rows = self.connection.execute(sql, (self.page_size(), offset)).fetchall()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка чтения", str(exc))
            return

        self.current_rows = [dict(row) for row in rows]
        names = [column["name"] for column in self.columns]
        self.data_table.clear()
        self.data_table.setColumnCount(len(names))
        self.data_table.setHorizontalHeaderLabels(names)
        self.data_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for column_index, name in enumerate(names):
                value = row[name]
                item = QTableWidgetItem(display_value(value))
                item.setData(Qt.ItemDataRole.UserRole, value)
                self.data_table.setItem(row_index, column_index, item)

        self.table_title.setText(f"Таблица: {self.current_table}")
        self.page_info.setText(
            f"Страница {page} из {pages} · записей: {self.total_rows}"
        )
        self.data_table.resizeColumnsToContents()

    def selected_row_data(self) -> dict[str, Any] | None:
        row = self.data_table.currentRow()
        if row < 0 or row >= len(self.current_rows):
            QMessageBox.information(self, "Запись", "Выберите строку.")
            return None
        return self.current_rows[row]

    def identity_where(
        self, row: dict[str, Any]
    ) -> tuple[str, list[Any]]:
        if self.identity_columns:
            clauses = [
                f"{quote_identifier(name)} IS ?" for name in self.identity_columns
            ]
            values = [row[name] for name in self.identity_columns]
        else:
            clauses = ["rowid = ?"]
            values = [row["__browser_rowid__"]]
        return " AND ".join(clauses), values

    def create_record(self) -> None:
        if self.connection is None or self.current_table is None:
            QMessageBox.information(self, "CRUD", "Сначала откройте таблицу.")
            return

        dialog = RecordDialog(self.columns, create_mode=True, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values, defaults = dialog.get_values()
        actual = {
            name: value for name, value in values.items() if name not in defaults
        }

        table = quote_identifier(self.current_table)
        try:
            if actual:
                columns = ", ".join(quote_identifier(name) for name in actual)
                placeholders = ", ".join("?" for _ in actual)
                self.connection.execute(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                    list(actual.values()),
                )
            else:
                self.connection.execute(f"INSERT INTO {table} DEFAULT VALUES")
            self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.rollback()
            QMessageBox.critical(self, "Ошибка создания", str(exc))
            return
        self.go_to_last_page()

    def read_record(self) -> None:
        row = self.selected_row_data()
        if row is None:
            return
        dialog = RecordDialog(
            self.columns,
            {column["name"]: row[column["name"]] for column in self.columns},
            create_mode=False,
            parent=self,
        )
        dialog.setWindowTitle("Просмотр записи")
        for editor in dialog.editors.values():
            editor.edit.setReadOnly(True)
            editor.null_check.setEnabled(False)
        buttons = dialog.findChild(QDialogButtonBox)
        if buttons is not None:
            save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
            if save_button is not None:
                save_button.hide()
        dialog.exec()

    def update_record(self) -> None:
        if self.connection is None or self.current_table is None:
            return
        old_row = self.selected_row_data()
        if old_row is None:
            return

        values = {
            column["name"]: old_row[column["name"]] for column in self.columns
        }
        dialog = RecordDialog(
            self.columns, values, create_mode=False, parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_values, _ = dialog.get_values()
        assignments = ", ".join(
            f"{quote_identifier(name)} = ?" for name in new_values
        )
        where, identity_values = self.identity_where(old_row)
        table = quote_identifier(self.current_table)

        try:
            self.connection.execute(
                f"UPDATE {table} SET {assignments} WHERE {where}",
                [*new_values.values(), *identity_values],
            )
            self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.rollback()
            QMessageBox.critical(self, "Ошибка изменения", str(exc))
            return
        self.refresh_page()

    def delete_record(self) -> None:
        if self.connection is None or self.current_table is None:
            return
        row = self.selected_row_data()
        if row is None:
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            "Удалить выбранную запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        where, values = self.identity_where(row)
        table = quote_identifier(self.current_table)
        try:
            self.connection.execute(f"DELETE FROM {table} WHERE {where}", values)
            self.connection.commit()
        except sqlite3.Error as exc:
            self.connection.rollback()
            QMessageBox.critical(self, "Ошибка удаления", str(exc))
            return
        self.refresh_page()

    def go_to_page(self, page: int) -> None:
        self.page_spin.setValue(min(max(1, page), self.total_pages()))

    def go_to_last_page(self) -> None:
        if self.connection is not None and self.current_table is not None:
            table = quote_identifier(self.current_table)
            self.total_rows = int(
                self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
        self.go_to_page(self.total_pages())
        self.refresh_page()

    def on_page_size_changed(self) -> None:
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.refresh_page()

    def closeEvent(self, event: Any) -> None:
        if self.connection is not None:
            self.connection.close()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = DatabaseBrowser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
