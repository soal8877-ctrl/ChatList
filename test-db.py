import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QLabel, QMessageBox, QDialog,
                             QDialogButtonBox, QLineEdit, QFileDialog, QListWidget,
                             QListWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt
from typing import List, Optional, Dict


class DatabaseViewer(QMainWindow):
    """Главное окно для просмотра SQLite базы данных"""
    
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.conn = None
        self.current_table = None
        self.current_page = 1
        self.rows_per_page = 50
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("SQLite Database Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Кнопка выбора файла
        file_layout = QHBoxLayout()
        self.file_label = QLabel("База данных не выбрана")
        file_layout.addWidget(self.file_label)
        
        self.select_file_button = QPushButton("Выбрать файл БД")
        self.select_file_button.clicked.connect(self.select_database_file)
        file_layout.addWidget(self.select_file_button)
        main_layout.addLayout(file_layout)
        
        # Список таблиц
        tables_label = QLabel("Таблицы:")
        main_layout.addWidget(tables_label)
        
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self.open_table)
        main_layout.addWidget(self.tables_list)
        
        # Кнопка "Открыть"
        self.open_button = QPushButton("Открыть")
        self.open_button.clicked.connect(self.open_selected_table)
        self.open_button.setEnabled(False)
        main_layout.addWidget(self.open_button)
        
        # Область для отображения таблицы (будет показана после открытия)
        self.table_widget = None
    
    def select_database_file(self):
        """Выбор файла базы данных"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл базы данных", "", "SQLite Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        
        if filename:
            try:
                # Закрываем предыдущее соединение, если есть
                if self.conn:
                    self.conn.close()
                
                self.db_path = filename
                self.conn = sqlite3.connect(filename)
                self.conn.row_factory = sqlite3.Row
                
                self.file_label.setText(f"База данных: {filename}")
                self.load_tables()
                self.open_button.setEnabled(True)
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу данных:\n{str(e)}")
    
    def load_tables(self):
        """Загрузка списка таблиц"""
        self.tables_list.clear()
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()
            
            for table in tables:
                item = QListWidgetItem(table[0])
                self.tables_list.addItem(item)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список таблиц:\n{str(e)}")
    
    def open_selected_table(self):
        """Открытие выбранной таблицы"""
        selected_items = self.tables_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Выберите таблицу из списка!")
            return
        
        table_name = selected_items[0].text()
        self.open_table_by_name(table_name)
    
    def open_table(self, item: QListWidgetItem):
        """Открытие таблицы по двойному клику"""
        table_name = item.text()
        self.open_table_by_name(table_name)
    
    def open_table_by_name(self, table_name: str):
        """Открытие таблицы по имени"""
        self.current_table = table_name
        self.current_page = 1
        
        # Удаляем предыдущий виджет таблицы, если есть
        if self.table_widget:
            self.table_widget.setParent(None)
        
        # Создаем новый виджет для отображения таблицы
        self.table_widget = TableViewWidget(self.conn, table_name, self.rows_per_page, self)
        self.centralWidget().layout().addWidget(self.table_widget)


class TableViewWidget(QWidget):
    """Виджет для отображения таблицы с пагинацией и CRUD операциями"""
    
    def __init__(self, conn: sqlite3.Connection, table_name: str, rows_per_page: int = 50, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.table_name = table_name
        self.rows_per_page = rows_per_page
        self.current_page = 1
        self.total_rows = 0
        
        self.init_ui()
        self.load_table_data()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок с названием таблицы
        header_label = QLabel(f"Таблица: {self.table_name}")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)
        
        # Кнопки CRUD
        crud_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Создать")
        self.create_button.clicked.connect(self.create_record)
        self.create_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        crud_layout.addWidget(self.create_button)
        
        self.edit_button = QPushButton("Редактировать")
        self.edit_button.clicked.connect(self.edit_record)
        self.edit_button.setStyleSheet("background-color: #2196F3; color: white; padding: 5px;")
        crud_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self.delete_record)
        self.delete_button.setStyleSheet("background-color: #f44336; color: white; padding: 5px;")
        crud_layout.addWidget(self.delete_button)
        
        crud_layout.addStretch()
        layout.addLayout(crud_layout)
        
        # Таблица данных
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Пагинация
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("◀ Назад")
        self.prev_button.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_button)
        
        self.page_label = QLabel()
        pagination_layout.addWidget(self.page_label)
        
        self.next_button = QPushButton("Вперед ▶")
        self.next_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_button)
        
        pagination_layout.addStretch()
        
        # Кнопка обновления
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.load_table_data)
        pagination_layout.addWidget(self.refresh_button)
        
        layout.addLayout(pagination_layout)
    
    def get_table_schema(self) -> List[Dict]:
        """Получение схемы таблицы"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({self.table_name})")
        columns = cursor.fetchall()
        
        schema = []
        for col in columns:
            schema.append({
                'name': col[1],
                'type': col[2],
                'notnull': col[3],
                'default': col[4],
                'pk': col[5]
            })
        
        return schema
    
    def get_total_rows(self) -> int:
        """Получение общего количества строк"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
        return cursor.fetchone()[0]
    
    def load_table_data(self):
        """Загрузка данных таблицы"""
        try:
            # Получаем схему таблицы
            schema = self.get_table_schema()
            column_names = [col['name'] for col in schema]
            
            # Устанавливаем количество столбцов
            self.table.setColumnCount(len(column_names))
            self.table.setHorizontalHeaderLabels(column_names)
            
            # Получаем общее количество строк
            self.total_rows = self.get_total_rows()
            
            # Вычисляем offset для пагинации
            offset = (self.current_page - 1) * self.rows_per_page
            
            # Загружаем данные с пагинацией
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?", 
                          (self.rows_per_page, offset))
            rows = cursor.fetchall()
            
            # Заполняем таблицу
            self.table.setRowCount(len(rows))
            
            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.table.setItem(row_idx, col_idx, item)
            
            # Обновляем информацию о пагинации
            total_pages = (self.total_rows + self.rows_per_page - 1) // self.rows_per_page
            self.page_label.setText(f"Страница {self.current_page} из {total_pages} (Всего записей: {self.total_rows})")
            
            # Обновляем состояние кнопок
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < total_pages)
            
            # Автоматически подгоняем ширину столбцов
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{str(e)}")
    
    def prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_table_data()
    
    def next_page(self):
        """Переход на следующую страницу"""
        total_pages = (self.total_rows + self.rows_per_page - 1) // self.rows_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_table_data()
    
    def create_record(self):
        """Создание новой записи"""
        schema = self.get_table_schema()
        dialog = RecordEditDialog(self.conn, self.table_name, schema, None, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_table_data()
    
    def edit_record(self):
        """Редактирование выбранной записи"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Предупреждение", "Выберите строку для редактирования!")
            return
        
        row_idx = selected_rows[0].row()
        
        # Получаем данные выбранной строки
        schema = self.get_table_schema()
        pk_columns = [col['name'] for col in schema if col['pk']]
        
        if not pk_columns:
            QMessageBox.warning(self, "Предупреждение", 
                              "Таблица не имеет первичного ключа. Редактирование невозможно.")
            return
        
        # Получаем значения первичного ключа
        pk_values = {}
        for pk_col in pk_columns:
            col_idx = next(i for i, col in enumerate(schema) if col['name'] == pk_col)
            pk_values[pk_col] = self.table.item(row_idx, col_idx).text()
        
        dialog = RecordEditDialog(self.conn, self.table_name, schema, pk_values, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_table_data()
    
    def delete_record(self):
        """Удаление выбранной записи"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Предупреждение", "Выберите строку для удаления!")
            return
        
        row_idx = selected_rows[0].row()
        
        # Получаем схему таблицы
        schema = self.get_table_schema()
        pk_columns = [col['name'] for col in schema if col['pk']]
        
        if not pk_columns:
            QMessageBox.warning(self, "Предупреждение", 
                              "Таблица не имеет первичного ключа. Удаление невозможно.")
            return
        
        # Получаем значения первичного ключа
        pk_values = {}
        for pk_col in pk_columns:
            col_idx = next(i for i, col in enumerate(schema) if col['name'] == pk_col)
            pk_values[pk_col] = self.table.item(row_idx, col_idx).text()
        
        # Подтверждение удаления
        reply = QMessageBox.question(
            self, 
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor()
                where_clause = " AND ".join([f"{col} = ?" for col in pk_columns])
                values = [pk_values[col] for col in pk_columns]
                
                cursor.execute(f"DELETE FROM {self.table_name} WHERE {where_clause}", values)
                self.conn.commit()
                
                QMessageBox.information(self, "Успех", "Запись удалена!")
                self.load_table_data()
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{str(e)}")
                self.conn.rollback()


class RecordEditDialog(QDialog):
    """Диалог для создания/редактирования записи"""
    
    def __init__(self, conn: sqlite3.Connection, table_name: str, schema: List[Dict], 
                 pk_values: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.table_name = table_name
        self.schema = schema
        self.pk_values = pk_values
        self.is_edit_mode = pk_values is not None
        
        self.init_ui()
        
        if self.is_edit_mode:
            self.load_existing_data()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        title = f"Редактировать запись - {self.table_name}" if self.is_edit_mode else f"Создать запись - {self.table_name}"
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 500, 400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Поля для редактирования
        self.fields = {}
        
        for col in self.schema:
            col_name = col['name']
            col_type = col['type']
            is_pk = col['pk']
            is_notnull = col['notnull']
            default_value = col['default']
            
            # Пропускаем первичный ключ при создании, если он AUTOINCREMENT
            if not self.is_edit_mode and is_pk:
                continue
            
            # Создаем метку
            label_text = col_name
            if is_pk:
                label_text += " (PK)"
            if is_notnull:
                label_text += " *"
            
            label = QLabel(label_text)
            layout.addWidget(label)
            
            # Создаем поле ввода
            field = QLineEdit()
            if self.is_edit_mode and is_pk:
                field.setReadOnly(True)  # Первичный ключ нельзя редактировать
            
            if default_value and not self.is_edit_mode:
                field.setText(str(default_value))
            
            self.fields[col_name] = field
            layout.addWidget(field)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_record)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_existing_data(self):
        """Загрузка существующих данных для редактирования"""
        try:
            cursor = self.conn.cursor()
            pk_columns = [col['name'] for col in self.schema if col['pk']]
            where_clause = " AND ".join([f"{col} = ?" for col in pk_columns])
            values = [self.pk_values[col] for col in pk_columns]
            
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE {where_clause}", values)
            row = cursor.fetchone()
            
            if row:
                column_names = [col['name'] for col in self.schema]
                for col_name, value in zip(column_names, row):
                    if col_name in self.fields:
                        self.fields[col_name].setText(str(value) if value is not None else "")
                        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{str(e)}")
    
    def save_record(self):
        """Сохранение записи"""
        try:
            cursor = self.conn.cursor()
            
            if self.is_edit_mode:
                # Обновление существующей записи
                pk_columns = [col['name'] for col in self.schema if col['pk']]
                set_clause = ", ".join([f"{col} = ?" for col in self.schema if not col['pk']])
                where_clause = " AND ".join([f"{col} = ?" for col in pk_columns])
                
                values = []
                for col in self.schema:
                    if not col['pk']:
                        value = self.fields[col['name']].text()
                        if value == "":
                            value = None
                        values.append(value)
                
                for pk_col in pk_columns:
                    values.append(self.pk_values[pk_col])
                
                cursor.execute(f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}", values)
                
            else:
                # Создание новой записи
                columns = [col['name'] for col in self.schema if not col['pk']]
                placeholders = ", ".join(["?" for _ in columns])
                columns_str = ", ".join(columns)
                
                values = []
                for col in self.schema:
                    if not col['pk']:
                        value = self.fields[col['name']].text()
                        if value == "":
                            value = None
                        values.append(value)
                
                cursor.execute(f"INSERT INTO {self.table_name} ({columns_str}) VALUES ({placeholders})", values)
            
            self.conn.commit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить запись:\n{str(e)}")
            self.conn.rollback()


def main():
    app = QApplication(sys.argv)
    window = DatabaseViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

