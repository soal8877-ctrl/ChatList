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
from datetime import datetime
from typing import List, Dict, Optional


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
        
        # Блокируем кнопку отправки и показываем прогресс
        self.send_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        
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
        
        # Кнопка добавления модели
        add_button = QPushButton("Добавить модель")
        add_button.clicked.connect(self.add_model)
        layout.addWidget(add_button)
        
        # Таблица моделей
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "API URL", "API ID", "Активна"])
        self.table.horizontalHeader().setStretchLastSection(True)
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


class AddModelDialog(QDialog):
    """Диалог добавления модели"""
    
    def __init__(self, db: Database, model_factory: ModelFactory, parent=None):
        super().__init__(parent)
        self.db = db
        self.model_factory = model_factory
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Добавить модель")
        self.setGeometry(250, 250, 500, 300)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Название модели:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("API URL:"))
        self.url_edit = QLineEdit()
        layout.addWidget(self.url_edit)
        
        layout.addWidget(QLabel("API ID (имя переменной в .env):"))
        self.api_id_edit = QLineEdit()
        layout.addWidget(self.api_id_edit)
        
        layout.addWidget(QLabel("Тип API:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["openai", "deepseek", "groq"])
        layout.addWidget(self.type_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def accept(self):
        """Принятие диалога и добавление модели"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        api_id = self.api_id_edit.text().strip()
        model_type = self.type_combo.currentText()
        
        if not all([name, url, api_id]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return
        
        self.model_factory.add_model(name, url, api_id, model_type)
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
