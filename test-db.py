"""SQLite browser: list tables, open with pagination and CRUD."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PAGE_SIZE_DEFAULT = 50


def connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(r["name"]) for r in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [dict(r) for r in rows]


def primary_key_columns(cols: list[dict[str, Any]]) -> list[str]:
    return [c["name"] for c in cols if c.get("pk")]


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class RowEditDialog(QDialog):
    def __init__(
        self,
        columns: list[dict[str, Any]],
        values: dict[str, Any] | None = None,
        *,
        title: str = "Row",
        read_only_pks: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self.setWindowTitle(title)
        self.resize(480, 320)

        self._fields: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for col in columns:
            name = col["name"]
            edit = QLineEdit()
            if values and name in values and values[name] is not None:
                edit.setText(str(values[name]))
            if read_only_pks and col.get("pk"):
                edit.setReadOnly(True)
            self._fields[name] = edit
            form.addRow(name, edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._fields.items()}


class TableViewerDialog(QDialog):
    def __init__(self, conn: sqlite3.Connection, table: str, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.table = table
        self.columns = table_columns(conn, table)
        self.pk_cols = primary_key_columns(self.columns)
        self.col_names = [c["name"] for c in self.columns]
        self.page = 0
        self.page_size = PAGE_SIZE_DEFAULT
        self.total_rows = 0

        self.setWindowTitle(f"Table: {table}")
        self.resize(900, 560)

        self.table_widget = QTableWidget(0, len(self.col_names))
        self.table_widget.setHorizontalHeaderLabels(self.col_names)
        self.table_widget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

        self.page_label = QLabel()
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.valueChanged.connect(self._goto_page)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 500)
        self.size_spin.setValue(PAGE_SIZE_DEFAULT)
        self.size_spin.valueChanged.connect(self._page_size_changed)

        prev_btn = QPushButton("◀ Prev")
        next_btn = QPushButton("Next ▶")
        refresh_btn = QPushButton("Refresh")
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        delete_btn = QPushButton("Delete")
        close_btn = QPushButton("Close")

        nav = QHBoxLayout()
        nav.addWidget(prev_btn)
        nav.addWidget(self.page_label)
        nav.addWidget(next_btn)
        nav.addStretch()
        nav.addWidget(QLabel("Page:"))
        nav.addWidget(self.page_spin)
        nav.addWidget(QLabel("Rows/page:"))
        nav.addWidget(self.size_spin)
        nav.addWidget(refresh_btn)

        crud = QHBoxLayout()
        crud.addWidget(add_btn)
        crud.addWidget(edit_btn)
        crud.addWidget(delete_btn)
        crud.addStretch()
        crud.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table_widget)
        layout.addLayout(nav)
        layout.addLayout(crud)

        prev_btn.clicked.connect(self._prev_page)
        next_btn.clicked.connect(self._next_page)
        refresh_btn.clicked.connect(self.reload)
        add_btn.clicked.connect(self._add_row)
        edit_btn.clicked.connect(self._edit_row)
        delete_btn.clicked.connect(self._delete_row)
        close_btn.clicked.connect(self.accept)
        self.table_widget.doubleClicked.connect(lambda _: self._edit_row())

        self.reload()

    def _quoted_table(self) -> str:
        return quote_ident(self.table)

    def _count_rows(self) -> int:
        row = self.conn.execute(
            f"SELECT COUNT(*) AS c FROM {self._quoted_table()}"
        ).fetchone()
        return int(row["c"]) if row else 0

    def _max_page(self) -> int:
        if self.total_rows == 0:
            return 0
        return (self.total_rows - 1) // self.page_size

    def _update_page_controls(self) -> None:
        max_page = max(self._max_page(), 0)
        if self.page > max_page:
            self.page = max_page
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(max_page + 1)
        self.page_spin.setValue(self.page + 1)
        self.page_spin.blockSignals(False)
        shown_from = self.page * self.page_size + 1 if self.total_rows else 0
        shown_to = min((self.page + 1) * self.page_size, self.total_rows)
        self.page_label.setText(
            f"Rows {shown_from}–{shown_to} of {self.total_rows} "
            f"(page {self.page + 1}/{max_page + 1})"
        )

    def reload(self) -> None:
        self.total_rows = self._count_rows()
        self._update_page_controls()
        offset = self.page * self.page_size
        rows = self.conn.execute(
            f"SELECT rowid, * FROM {self._quoted_table()} LIMIT ? OFFSET ?",
            (self.page_size, offset),
        ).fetchall()

        self.table_widget.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            row_dict = dict(row)
            for c_idx, name in enumerate(self.col_names):
                val = row_dict.get(name)
                item = QTableWidgetItem("" if val is None else str(val))
                item.setData(Qt.ItemDataRole.UserRole, row_dict)
                self.table_widget.setItem(r_idx, c_idx, item)

    def _prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.reload()

    def _next_page(self) -> None:
        if self.page < self._max_page():
            self.page += 1
            self.reload()

    def _goto_page(self, one_based: int) -> None:
        self.page = max(0, one_based - 1)
        self.reload()

    def _page_size_changed(self, size: int) -> None:
        self.page_size = size
        self.page = 0
        self.reload()

    def _selected_row_data(self) -> dict[str, Any] | None:
        indexes = self.table_widget.selectionModel().selectedRows()
        if not indexes:
            return None
        item = self.table_widget.item(indexes[0].row(), 0)
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return dict(data) if data else None

    def _add_row(self) -> None:
        dlg = RowEditDialog(self.columns, title=f"Add — {self.table}", parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        values = dlg.values()
        cols = [quote_ident(n) for n in self.col_names]
        placeholders = ", ".join("?" for _ in cols)
        sql = (
            f"INSERT INTO {self._quoted_table()} "
            f"({', '.join(cols)}) VALUES ({placeholders})"
        )
        try:
            self.conn.execute(sql, [values.get(n, "") for n in self.col_names])
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Add", str(exc))
            return
        self.reload()

    def _edit_row(self) -> None:
        current = self._selected_row_data()
        if current is None:
            QMessageBox.information(self, "Edit", "Select a row.")
            return
        dlg = RowEditDialog(
            self.columns,
            current,
            title=f"Edit — {self.table}",
            read_only_pks=bool(self.pk_cols),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_values = dlg.values()
        try:
            if self.pk_cols:
                set_cols = [c for c in self.col_names if c not in self.pk_cols]
                if not set_cols:
                    QMessageBox.information(self, "Edit", "No editable columns.")
                    return
                set_clause = ", ".join(
                    f"{quote_ident(c)} = ?" for c in set_cols
                )
                where = " AND ".join(
                    f"{quote_ident(c)} = ?" for c in self.pk_cols
                )
                params = [new_values[c] for c in set_cols]
                params.extend(current[c] for c in self.pk_cols)
                sql = (
                    f"UPDATE {self._quoted_table()} SET {set_clause} WHERE {where}"
                )
            else:
                set_clause = ", ".join(
                    f"{quote_ident(c)} = ?" for c in self.col_names
                )
                sql = (
                    f"UPDATE {self._quoted_table()} SET {set_clause} WHERE rowid = ?"
                )
                params = [new_values[c] for c in self.col_names]
                params.append(current["rowid"])
            self.conn.execute(sql, params)
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Edit", str(exc))
            return
        self.reload()

    def _delete_row(self) -> None:
        current = self._selected_row_data()
        if current is None:
            QMessageBox.information(self, "Delete", "Select a row.")
            return
        if (
            QMessageBox.question(self, "Delete", "Delete selected row?")
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            if self.pk_cols:
                where = " AND ".join(
                    f"{quote_ident(c)} = ?" for c in self.pk_cols
                )
                params = [current[c] for c in self.pk_cols]
                sql = f"DELETE FROM {self._quoted_table()} WHERE {where}"
            else:
                sql = f"DELETE FROM {self._quoted_table()} WHERE rowid = ?"
                params = [current["rowid"]]
            self.conn.execute(sql, params)
            self.conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Delete", str(exc))
            return
        self.reload()


class MainWindow(QMainWindow):
    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("SQLite test browser")
        self.resize(480, 400)
        self.conn: sqlite3.Connection | None = None
        self.db_path: Path | None = None

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path to .db file…")
        browse_btn = QPushButton("Browse…")
        open_file_btn = QPushButton("Open file")

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(browse_btn)
        path_row.addWidget(open_file_btn)

        self.table_list = QListWidget()
        open_table_btn = QPushButton("Open")
        open_table_btn.setEnabled(False)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(open_table_btn)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(path_row)
        layout.addWidget(QLabel("Tables:"))
        layout.addWidget(self.table_list)
        layout.addLayout(row)
        self.setCentralWidget(central)

        browse_btn.clicked.connect(self._browse)
        open_file_btn.clicked.connect(self._open_file)
        open_table_btn.clicked.connect(self._open_table)
        self.table_list.itemDoubleClicked.connect(lambda _: self._open_table())
        self.table_list.itemSelectionChanged.connect(
            lambda: open_table_btn.setEnabled(bool(self.table_list.currentItem()))
        )

        if db_path:
            self.path_edit.setText(str(db_path))
            self._open_file()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.conn:
            self.conn.close()
        super().closeEvent(event)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SQLite database",
            str(Path.cwd()),
            "SQLite (*.db *.sqlite *.sqlite3);;All (*.*)",
        )
        if path:
            self.path_edit.setText(path)

    def _open_file(self) -> None:
        path = Path(self.path_edit.text().strip())
        if not path.is_file():
            QMessageBox.warning(self, "Open", "File not found.")
            return
        if self.conn:
            self.conn.close()
        try:
            self.conn = connect_db(path)
            self.db_path = path
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Open", str(exc))
            return
        self.setWindowTitle(f"SQLite test browser — {path.name}")
        self.table_list.clear()
        for name in list_tables(self.conn):
            self.table_list.addItem(name)

    def _open_table(self) -> None:
        item = self.table_list.currentItem()
        if not item or not self.conn:
            return
        TableViewerDialog(self.conn, item.text(), self).exec()


def main() -> None:
    db_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = QApplication(sys.argv)
    window = MainWindow(db_arg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
