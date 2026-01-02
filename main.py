import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QPushButton, QTableWidget, 
                               QTableWidgetItem, QComboBox, QCheckBox, QLabel, 
                               QMessageBox, QMenuBar, QMenu, QDialog, QDialogButtonBox,
                               QLineEdit, QHeaderView, QProgressBar, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from db import Database
from models import ModelFactory
from network import send_requests_async
from export import export_to_markdown, export_to_json
from logger import RequestLogger
from datetime import datetime
from typing import List, Dict, Optional
from PyQt5.QtWidgets import QFileDialog


class RequestThread(QThread):
    """Поток для асинхронной отправки запросов к API"""
    
    finished = pyqtSignal(list)  # Сигнал о завершении запросов
    
    def __init__(self, models, prompt, timeout=30):
        super().__init__()
        self.models = models
        self.prompt = prompt
        self.timeout = timeout
    
    def run(self):
        """Выполнение запросов в отдельном потоке"""
        results = send_requests_async(self.models, self.prompt, self.timeout)
        self.finished.emit(results)


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.model_factory = ModelFactory(self.db)
        self.temp_results = []  # Временная таблица результатов в памяти
        self.current_prompt_id = None
        self.logger = RequestLogger()
        
        self.init_ui()
        self.load_saved_prompts()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("ChatList - Сравнение ответов нейросетей")
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Создаем меню
        self.create_menu()
        
        # Область ввода промта
        prompt_layout = QVBoxLayout()
        prompt_label = QLabel("Введите промт:")
        prompt_label.setFont(QFont("Arial", 10, QFont.Bold))
        prompt_label.setFixedHeight(20)
        prompt_layout.addWidget(prompt_label)
        
        # Выбор сохраненного промта
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Или выберите сохраненный:"))
        self.prompt_combo = QComboBox()
        self.prompt_combo.currentTextChanged.connect(self.on_prompt_selected)
        select_layout.addWidget(self.prompt_combo)
        select_layout.addStretch()
        prompt_layout.addLayout(select_layout)
        
        # Текстовое поле для ввода промта
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("Введите ваш запрос здесь...")
        self.prompt_text.setMaximumHeight(100)
        prompt_layout.addWidget(self.prompt_text)
        
        # Кнопки управления промтом
        prompt_buttons = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_requests)
        self.send_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        
        self.new_request_button = QPushButton("Новый запрос")
        self.new_request_button.clicked.connect(self.new_request)
        self.new_request_button.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        
        self.save_prompt_button = QPushButton("Сохранить промт")
        self.save_prompt_button.clicked.connect(self.save_prompt)
        self.save_prompt_button.setStyleSheet("background-color: #FF9800; color: white; padding: 8px;")
        
        prompt_buttons.addWidget(self.send_button)
        prompt_buttons.addWidget(self.new_request_button)
        prompt_buttons.addWidget(self.save_prompt_button)
        prompt_buttons.addStretch()
        
        prompt_layout.addLayout(prompt_buttons)
        main_layout.addLayout(prompt_layout)
        
        # Индикатор загрузки
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Таблица результатов
        results_label = QLabel("Результаты:")
        results_label.setFont(QFont("Arial", 10, QFont.Bold))
        main_layout.addWidget(results_label)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Выбрать", "Модель", "Ответ"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSortingEnabled(True)
        main_layout.addWidget(self.results_table)
        
        # Кнопка сохранения результатов
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_results_button = QPushButton("Сохранить выбранные")
        self.save_results_button.clicked.connect(self.save_selected_results)
        self.save_results_button.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold; padding: 8px;")
        self.save_results_button.setEnabled(False)
        save_layout.addWidget(self.save_results_button)
        main_layout.addLayout(save_layout)
    
    def create_menu(self):
        """Создание меню приложения"""
        menubar = self.menuBar()
        
        # Меню "Модели"
        models_menu = menubar.addMenu("Модели")
        models_menu.addAction("Управление моделями", self.show_models_dialog)
        
        # Меню "Промты"
        prompts_menu = menubar.addMenu("Промты")
        prompts_menu.addAction("Просмотр промтов", self.show_prompts_dialog)
        
        # Меню "Результаты"
        results_menu = menubar.addMenu("Результаты")
        results_menu.addAction("Просмотр результатов", self.show_results_dialog)
        results_menu.addSeparator()
        results_menu.addAction("Экспорт в Markdown", self.export_to_markdown)
        results_menu.addAction("Экспорт в JSON", self.export_to_json)
        
        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        settings_menu.addAction("Настройки программы", self.show_settings_dialog)
    
    def load_saved_prompts(self):
        """Загрузка сохраненных промтов в выпадающий список"""
        self.prompt_combo.clear()
        self.prompt_combo.addItem("-- Выберите промт --")
        prompts = self.db.get_prompts()
        for prompt in prompts:
            # Показываем первые 50 символов промта
            display_text = prompt['prompt'][:50] + "..." if len(prompt['prompt']) > 50 else prompt['prompt']
            self.prompt_combo.addItem(f"{prompt['id']}: {display_text}", prompt['id'])
    
    def on_prompt_selected(self, text):
        """Обработка выбора промта из списка"""
        if self.prompt_combo.currentData():
            prompt_id = self.prompt_combo.currentData()
            prompt_data = self.db.get_prompt_by_id(prompt_id)
            if prompt_data:
                self.prompt_text.setPlainText(prompt_data['prompt'])
    
    def save_prompt(self):
        """Сохранение текущего промта в базу данных"""
        prompt_text = self.prompt_text.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст промта для сохранения!")
            return
        
        # Простой диалог для ввода тегов
        tags, ok = QInputDialog.getText(self, "Сохранение промта", 
                                       "Введите теги (через запятую, необязательно):")
        tags = tags.strip() if ok and tags else None
        
        self.db.add_prompt(prompt_text, tags)
        self.load_saved_prompts()
        QMessageBox.information(self, "Успех", "Промт сохранен!")
    
    def send_requests(self):
        """Отправка запросов к активным моделям"""
        prompt_text = self.prompt_text.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст промта!")
            return
        
        # Очищаем временную таблицу
        self.temp_results = []
        self.results_table.setRowCount(0)
        
        # Получаем активные модели
        active_models = self.model_factory.get_active_models()
        if not active_models:
            QMessageBox.warning(self, "Предупреждение", 
                              "Нет активных моделей! Добавьте модели через меню 'Модели'.")
            return
        
        # Сохраняем промт в БД, если его еще нет
        if not self.current_prompt_id:
            self.current_prompt_id = self.db.add_prompt(prompt_text)
            self.logger.log_prompt_saved(self.current_prompt_id)
        
        # Блокируем кнопку отправки и показываем прогресс
        self.send_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        
        # Сохраняем промт для логирования
        self.current_prompt_text = prompt_text
        
        # Создаем поток для отправки запросов
        self.request_thread = RequestThread(active_models, prompt_text)
        self.request_thread.finished.connect(self.on_requests_finished)
        self.request_thread.start()
    
    def on_requests_finished(self, results: List[Dict]):
        """Обработка завершения запросов"""
        self.send_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Сохраняем результаты во временную таблицу
        self.temp_results = results
        
        # Отображаем результаты в таблице
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # Логируем запрос с техническими деталями
            self.logger.log_request(
                model_name=result['model_name'],
                prompt=getattr(self, 'current_prompt_text', ''),
                success=result.get('success', False),
                response_text=result.get('response_text'),
                error=result.get('error'),
                tokens_used=result.get('tokens_used'),
                response_time=result.get('response_time'),
                url=result.get('url'),
                api_model_id=result.get('api_model_id'),
                model_type=result.get('model_type'),
                http_status=result.get('http_status'),
                request_model=result.get('request_model'),
                temperature=result.get('temperature'),
                messages_length=result.get('messages_length'),
                prompt_tokens=result.get('prompt_tokens'),
                completion_tokens=result.get('completion_tokens'),
                error_type=result.get('error_type')
            )
            
            # Чекбокс для выбора
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.results_table.setCellWidget(row, 0, checkbox)
            
            # Название модели
            model_item = QTableWidgetItem(result['model_name'])
            model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 1, model_item)
            
            # Текст ответа или ошибка
            if result.get('success'):
                response_text = result.get('response_text', 'Нет ответа')
                # Добавляем информацию о токенах и времени, если доступно
                info = []
                if result.get('tokens_used'):
                    info.append(f"Токены: {result['tokens_used']}")
                if result.get('response_time'):
                    info.append(f"Время: {result['response_time']:.2f}с")
                if info:
                    response_text += f"\n\n({', '.join(info)})"
            else:
                response_text = f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"
            
            response_item = QTableWidgetItem(response_text)
            response_item.setFlags(response_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 2, response_item)
        
        # Включаем кнопку сохранения
        self.save_results_button.setEnabled(True)
        
        # Автоматически подгоняем высоту строк
        self.results_table.resizeRowsToContents()
    
    def save_selected_results(self):
        """Сохранение выбранных результатов в базу данных"""
        if not self.current_prompt_id:
            QMessageBox.warning(self, "Предупреждение", "Нет активного промта!")
            return
        
        selected_results = []
        
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                result = self.temp_results[row]
                if result.get('success'):
                    selected_results.append({
                        'prompt_id': self.current_prompt_id,
                        'model_id': result['model_id'],
                        'model_name': result['model_name'],
                        'response_text': result.get('response_text', ''),
                        'tokens_used': result.get('tokens_used'),
                        'response_time': result.get('response_time')
                    })
        
        if not selected_results:
            QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы один результат для сохранения!")
            return
        
        self.db.save_results(selected_results)
        self.logger.log_result_saved(len(selected_results))
        QMessageBox.information(self, "Успех", f"Сохранено результатов: {len(selected_results)}")
        
        # Очищаем временную таблицу
        self.new_request()
    
    def new_request(self):
        """Очистка временной таблицы для нового запроса"""
        self.temp_results = []
        self.results_table.setRowCount(0)
        self.current_prompt_id = None
        self.save_results_button.setEnabled(False)
    
    def show_models_dialog(self):
        """Показ диалога управления моделями"""
        dialog = ModelsDialog(self.db, self.model_factory, self)
        dialog.exec_()
        # Обновляем список моделей после закрытия диалога
    
    def show_prompts_dialog(self):
        """Показ диалога просмотра промтов"""
        dialog = PromptsDialog(self.db, self)
        dialog.exec_()
        self.load_saved_prompts()
    
    def show_results_dialog(self):
        """Показ диалога просмотра результатов"""
        dialog = ResultsDialog(self.db, self)
        dialog.exec_()
    
    def show_settings_dialog(self):
        """Показ диалога настроек"""
        dialog = SettingsDialog(self.db, self)
        dialog.exec_()
    
    def export_to_markdown(self):
        """Экспорт результатов в Markdown"""
        if not self.temp_results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта!")
            return
        
        # Фильтруем только успешные результаты
        export_results = []
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                result = self.temp_results[row]
                if result.get('success'):
                    export_results.append({
                        'model_name': result['model_name'],
                        'response_text': result.get('response_text', ''),
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'tokens_used': result.get('tokens_used'),
                        'response_time': result.get('response_time')
                    })
        
        if not export_results:
            QMessageBox.warning(self, "Предупреждение", "Выберите результаты для экспорта!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как Markdown", "", "Markdown Files (*.md);;All Files (*)"
        )
        
        if filename:
            try:
                export_to_markdown(export_results, filename)
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {str(e)}")
    
    def export_to_json(self):
        """Экспорт результатов в JSON"""
        if not self.temp_results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта!")
            return
        
        # Фильтруем только успешные результаты
        export_results = []
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                result = self.temp_results[row]
                if result.get('success'):
                    export_results.append({
                        'model_name': result['model_name'],
                        'response_text': result.get('response_text', ''),
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'tokens_used': result.get('tokens_used'),
                        'response_time': result.get('response_time')
                    })
        
        if not export_results:
            QMessageBox.warning(self, "Предупреждение", "Выберите результаты для экспорта!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            try:
                export_to_json(export_results, filename)
                QMessageBox.information(self, "Успех", f"Результаты экспортированы в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {str(e)}")
    
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        self.db.close()
        event.accept()


class ModelsDialog(QDialog):
    """Диалог управления моделями"""
    
    def __init__(self, db: Database, model_factory: ModelFactory, parent=None):
        super().__init__(parent)
        self.db = db
        self.model_factory = model_factory
        self.init_ui()
        self.load_models()
    
    def init_ui(self):
        self.setWindowTitle("Управление моделями")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Кнопки управления моделями
        buttons_top_layout = QHBoxLayout()
        add_button = QPushButton("Добавить модель")
        add_button.clicked.connect(self.add_model)
        buttons_top_layout.addWidget(add_button)
        
        edit_button = QPushButton("Редактировать модель")
        edit_button.clicked.connect(self.edit_model)
        buttons_top_layout.addWidget(edit_button)
        
        delete_button = QPushButton("Удалить модель")
        delete_button.clicked.connect(self.delete_model)
        delete_button.setStyleSheet("background-color: #f44336; color: white; padding: 5px;")
        buttons_top_layout.addWidget(delete_button)
        
        buttons_top_layout.addStretch()
        layout.addLayout(buttons_top_layout)
        
        # Таблица моделей
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "API URL", "API ID", "Активна"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def load_models(self):
        """Загрузка моделей в таблицу"""
        models = self.model_factory.get_all_models()
        self.table.setRowCount(len(models))
        
        for row, model in enumerate(models):
            self.table.setItem(row, 0, QTableWidgetItem(str(model.id)))
            self.table.setItem(row, 1, QTableWidgetItem(model.name))
            self.table.setItem(row, 2, QTableWidgetItem(model.api_url))
            self.table.setItem(row, 3, QTableWidgetItem(model.api_id))
            
            checkbox = QCheckBox()
            checkbox.setChecked(model.is_active == 1)
            checkbox.stateChanged.connect(lambda state, m=model: self.toggle_model(m, state))
            self.table.setCellWidget(row, 4, checkbox)
    
    def toggle_model(self, model, state):
        """Переключение статуса модели"""
        is_active = 1 if state == Qt.Checked else 0
        model.update_status(is_active)
    
    def add_model(self):
        """Добавление новой модели"""
        dialog = AddModelDialog(self.db, self.model_factory, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_models()
    
    def edit_model(self):
        """Редактирование выбранной модели"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для редактирования!")
            return
        
        row = selected_rows[0].row()
        model_id = int(self.table.item(row, 0).text())
        model = self.model_factory.get_model_by_id(model_id)
        
        if not model:
            QMessageBox.warning(self, "Ошибка", "Модель не найдена!")
            return
        
        dialog = EditModelDialog(self.db, self.model_factory, model, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_models()
    
    def delete_model(self):
        """Удаление выбранной модели"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Предупреждение", "Выберите модель для удаления!")
            return
        
        row = selected_rows[0].row()
        model_id = int(self.table.item(row, 0).text())
        model_name = self.table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить модель '{model_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.delete_model(model_id)
            QMessageBox.information(self, "Успех", "Модель удалена!")
            self.load_models()


class AddModelDialog(QDialog):
    """Диалог добавления модели"""
    
    def __init__(self, db: Database, model_factory: ModelFactory, parent=None):
        super().__init__(parent)
        self.db = db
        self.model_factory = model_factory
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Добавить модель")
        self.setGeometry(250, 250, 500, 400)
        
        layout = QVBoxLayout()
        
        # 1. Название модели
        layout.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # 2. API URL
        layout.addWidget(QLabel("API URL:"))
        self.url_edit = QLineEdit()
        layout.addWidget(self.url_edit)
        
        # 3. API ID (model) - идентификатор модели для API
        layout.addWidget(QLabel("API ID (model):"))
        self.api_model_id_edit = QLineEdit()
        self.api_model_id_edit.setPlaceholderText("Например: gpt-4-turbo или openai/gpt-4-turbo")
        layout.addWidget(self.api_model_id_edit)
        
        # 4. Имя переменной окружения с API-ключом
        layout.addWidget(QLabel("Имя переменной окружения с API-ключом:"))
        self.api_id_edit = QLineEdit()
        layout.addWidget(self.api_id_edit)
        
        # Тип API
        layout.addWidget(QLabel("Тип API:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["openai", "deepseek", "groq", "openrouter"])
        layout.addWidget(self.type_combo)
        
        # 5. Чекбокс "Активна"
        self.active_checkbox = QCheckBox("Активна")
        self.active_checkbox.setChecked(True)  # По умолчанию активна
        layout.addWidget(self.active_checkbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def accept(self):
        """Принятие диалога и добавление модели"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        api_model_id = self.api_model_id_edit.text().strip() or None
        api_id = self.api_id_edit.text().strip()
        model_type = self.type_combo.currentText()
        is_active = 1 if self.active_checkbox.isChecked() else 0
        
        if not all([name, url, api_id]):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля: Название, API URL и Имя переменной окружения!")
            return
        
        self.model_factory.add_model(name, url, api_id, model_type, api_model_id, is_active)
        super().accept()


class EditModelDialog(QDialog):
    """Диалог редактирования модели"""
    
    def __init__(self, db: Database, model_factory: ModelFactory, model, parent=None):
        super().__init__(parent)
        self.db = db
        self.model_factory = model_factory
        self.model = model
        self.init_ui()
        self.load_model_data()
    
    def init_ui(self):
        self.setWindowTitle("Редактировать модель")
        self.setGeometry(250, 250, 500, 400)
        
        layout = QVBoxLayout()
        
        # 1. Название модели
        layout.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        # 2. API URL
        layout.addWidget(QLabel("API URL:"))
        self.url_edit = QLineEdit()
        layout.addWidget(self.url_edit)
        
        # 3. API ID (model) - идентификатор модели для API
        layout.addWidget(QLabel("API ID (model):"))
        self.api_model_id_edit = QLineEdit()
        self.api_model_id_edit.setPlaceholderText("Например: gpt-4-turbo или openai/gpt-4-turbo")
        layout.addWidget(self.api_model_id_edit)
        
        # 4. Имя переменной окружения с API-ключом
        layout.addWidget(QLabel("Имя переменной окружения с API-ключом:"))
        self.api_id_edit = QLineEdit()
        layout.addWidget(self.api_id_edit)
        
        # 5. Чекбокс "Активна"
        self.active_checkbox = QCheckBox("Активна")
        layout.addWidget(self.active_checkbox)
        
        # Тип API (только для информации, не редактируется)
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип API (только для просмотра):"))
        self.type_label = QLabel(self.model.model_type)
        self.type_label.setStyleSheet("font-weight: bold;")
        type_layout.addWidget(self.type_label)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_model_data(self):
        """Загрузка данных модели в поля формы"""
        self.name_edit.setText(self.model.name)
        self.url_edit.setText(self.model.api_url)
        self.api_model_id_edit.setText(self.model.api_model_id or "")
        self.api_id_edit.setText(self.model.api_id)
        self.active_checkbox.setChecked(self.model.is_active == 1)
    
    def accept(self):
        """Принятие диалога и обновление модели"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        api_model_id = self.api_model_id_edit.text().strip() or None
        api_id = self.api_id_edit.text().strip()
        is_active = 1 if self.active_checkbox.isChecked() else 0
        
        if not all([name, url, api_id]):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля: Название, API URL и Имя переменной окружения!")
            return
        
        self.db.update_model(
            self.model.id, 
            name, 
            url, 
            api_id, 
            self.model.model_type, 
            api_model_id, 
            is_active
        )
        super().accept()


class PromptsDialog(QDialog):
    """Диалог просмотра промтов"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_prompts()
    
    def init_ui(self):
        self.setWindowTitle("Просмотр промтов")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.search_prompts)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Таблица промтов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_prompts(self):
        """Загрузка промтов"""
        prompts = self.db.get_prompts()
        self.table.setRowCount(len(prompts))
        
        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(str(prompt['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(prompt['date']))
            self.table.setItem(row, 2, QTableWidgetItem(prompt['prompt']))
            self.table.setItem(row, 3, QTableWidgetItem(prompt.get('tags', '')))
        
        self.table.resizeRowsToContents()
    
    def search_prompts(self, query):
        """Поиск промтов"""
        if query.strip():
            prompts = self.db.search_prompts(query)
        else:
            prompts = self.db.get_prompts()
        
        self.table.setRowCount(len(prompts))
        for row, prompt in enumerate(prompts):
            self.table.setItem(row, 0, QTableWidgetItem(str(prompt['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(prompt['date']))
            self.table.setItem(row, 2, QTableWidgetItem(prompt['prompt']))
            self.table.setItem(row, 3, QTableWidgetItem(prompt.get('tags', '')))
        
        self.table.resizeRowsToContents()


class ResultsDialog(QDialog):
    """Диалог просмотра результатов"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_results()
    
    def init_ui(self):
        self.setWindowTitle("Просмотр результатов")
        self.setGeometry(200, 200, 1000, 600)
        
        layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.search_results)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Модель", "Ответ", "Дата", "Токены"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_results(self):
        """Загрузка результатов"""
        results = self.db.get_results(limit=100)
        self.table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(str(result['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(result['model_name']))
            self.table.setItem(row, 2, QTableWidgetItem(result['response_text']))
            self.table.setItem(row, 3, QTableWidgetItem(result['date']))
            self.table.setItem(row, 4, QTableWidgetItem(str(result.get('tokens_used', ''))))
        
        self.table.resizeRowsToContents()
    
    def search_results(self, query):
        """Поиск результатов"""
        if query.strip():
            results = self.db.search_results(query)
        else:
            results = self.db.get_results(limit=100)
        
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            self.table.setItem(row, 0, QTableWidgetItem(str(result['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(result['model_name']))
            self.table.setItem(row, 2, QTableWidgetItem(result['response_text']))
            self.table.setItem(row, 3, QTableWidgetItem(result['date']))
            self.table.setItem(row, 4, QTableWidgetItem(str(result.get('tokens_used', ''))))
        
        self.table.resizeRowsToContents()


class SettingsDialog(QDialog):
    """Диалог настроек"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("Настройки")
        self.setGeometry(250, 250, 400, 300)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Таймаут запросов (секунды):"))
        self.timeout_edit = QLineEdit()
        layout.addWidget(self.timeout_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_settings(self):
        """Загрузка настроек"""
        timeout = self.db.get_setting('default_timeout', '30')
        self.timeout_edit.setText(timeout)
    
    def save_settings(self):
        """Сохранение настроек"""
        timeout = self.timeout_edit.text().strip()
        if timeout:
            self.db.set_setting('default_timeout', timeout)
        self.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
