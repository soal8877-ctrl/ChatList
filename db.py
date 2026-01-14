import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_name: str = "chatlist.db"):
        """
        Инициализация подключения к базе данных
        
        Args:
            db_name: имя файла базы данных
        """
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Создание всех таблиц базы данных при первом запуске"""
        cursor = self.conn.cursor()
        
        # Таблица промтов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags)
        """)
        
        # Таблица моделей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                api_url TEXT NOT NULL,
                api_id TEXT NOT NULL,
                api_model_id TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                model_type TEXT NOT NULL
            )
        """)
        
        # Миграция: добавляем поле api_model_id, если его нет
        try:
            cursor.execute("ALTER TABLE models ADD COLUMN api_model_id TEXT")
        except sqlite3.OperationalError:
            # Поле уже существует, пропускаем
            pass
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active)
        """)
        
        # Таблица результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER,
                model_id INTEGER,
                model_name TEXT NOT NULL,
                response_text TEXT NOT NULL,
                date TEXT NOT NULL,
                tokens_used INTEGER,
                response_time REAL,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id),
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_date ON results(date)
        """)
        
        # Таблица настроек
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    # Методы для работы с промтами
    def add_prompt(self, prompt: str, tags: Optional[str] = None) -> int:
        """
        Добавление промта в базу данных
        
        Args:
            prompt: текст промта
            tags: теги через запятую (опционально)
            
        Returns:
            ID добавленного промта
        """
        cursor = self.conn.cursor()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO prompts (date, prompt, tags)
            VALUES (?, ?, ?)
        """, (date, prompt, tags))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_prompts(self) -> List[Dict]:
        """
        Получение всех промтов
        
        Returns:
            Список словарей с данными промтов
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM prompts ORDER BY date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def search_prompts(self, query: str) -> List[Dict]:
        """
        Поиск промтов по тексту
        
        Args:
            query: поисковый запрос
            
        Returns:
            Список найденных промтов
        """
        cursor = self.conn.cursor()
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT * FROM prompts 
            WHERE prompt LIKE ? OR tags LIKE ?
            ORDER BY date DESC
        """, (search_pattern, search_pattern))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_prompt_by_id(self, prompt_id: int) -> Optional[Dict]:
        """
        Получение промта по ID
        
        Args:
            prompt_id: ID промта
            
        Returns:
            Словарь с данными промта или None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_prompt(self, prompt_id: int, prompt: str, tags: Optional[str] = None):
        """
        Обновление промта
        
        Args:
            prompt_id: ID промта
            prompt: новый текст промта
            tags: новые теги через запятую (опционально)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE prompts 
            SET prompt = ?, tags = ?
            WHERE id = ?
        """, (prompt, tags, prompt_id))
        self.conn.commit()
    
    def delete_prompt(self, prompt_id: int):
        """
        Удаление промта
        
        Args:
            prompt_id: ID промта для удаления
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        self.conn.commit()
    
    # Методы для работы с моделями
    def add_model(self, name: str, api_url: str, api_id: str, 
                  model_type: str, api_model_id: str = None, is_active: int = 1) -> int:
        """
        Добавление модели в базу данных
        
        Args:
            name: название модели
            api_url: URL API
            api_id: имя переменной окружения для API ключа
            model_type: тип API (openai, deepseek, groq)
            api_model_id: идентификатор модели для API (опционально)
            is_active: активна ли модель (1 - да, 0 - нет)
            
        Returns:
            ID добавленной модели
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO models (name, api_url, api_id, api_model_id, is_active, model_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, api_url, api_id, api_model_id, is_active, model_type))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_active_models(self) -> List[Dict]:
        """
        Получение всех активных моделей
        
        Returns:
            Список активных моделей
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models WHERE is_active = 1")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_all_models(self) -> List[Dict]:
        """
        Получение всех моделей
        
        Returns:
            Список всех моделей
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def update_model_status(self, model_id: int, is_active: int):
        """
        Обновление статуса модели
        
        Args:
            model_id: ID модели
            is_active: новый статус (1 - активна, 0 - неактивна)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE models SET is_active = ? WHERE id = ?
        """, (is_active, model_id))
        self.conn.commit()
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        """
        Получение модели по ID
        
        Args:
            model_id: ID модели
            
        Returns:
            Словарь с данными модели или None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM models WHERE id = ?", (model_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_model(self, model_id: int, name: str, api_url: str, api_id: str, 
                     model_type: str, api_model_id: str = None, is_active: int = None):
        """
        Обновление данных модели
        
        Args:
            model_id: ID модели
            name: новое название модели
            api_url: новый URL API
            api_id: новое имя переменной окружения для API ключа
            model_type: новый тип API
            api_model_id: идентификатор модели для API (опционально)
            is_active: активна ли модель (1 - да, 0 - нет) (опционально)
        """
        cursor = self.conn.cursor()
        if is_active is not None:
            cursor.execute("""
                UPDATE models 
                SET name = ?, api_url = ?, api_id = ?, model_type = ?, api_model_id = ?, is_active = ?
                WHERE id = ?
            """, (name, api_url, api_id, model_type, api_model_id, is_active, model_id))
        else:
            cursor.execute("""
                UPDATE models 
                SET name = ?, api_url = ?, api_id = ?, model_type = ?, api_model_id = ?
                WHERE id = ?
            """, (name, api_url, api_id, model_type, api_model_id, model_id))
        self.conn.commit()
    
    def delete_model(self, model_id: int):
        """
        Удаление модели из базы данных
        
        Args:
            model_id: ID модели для удаления
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
        self.conn.commit()
    
    # Методы для работы с результатами
    def save_results(self, results_list: List[Dict]):
        """
        Сохранение результатов в базу данных
        
        Args:
            results_list: список словарей с результатами
                Каждый словарь должен содержать:
                - prompt_id: ID промта
                - model_id: ID модели
                - model_name: название модели
                - response_text: текст ответа
                - tokens_used: количество токенов (опционально)
                - response_time: время ответа в секундах (опционально)
        """
        cursor = self.conn.cursor()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for result in results_list:
            cursor.execute("""
                INSERT INTO results 
                (prompt_id, model_id, model_name, response_text, date, tokens_used, response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('prompt_id'),
                result.get('model_id'),
                result.get('model_name'),
                result.get('response_text'),
                date,
                result.get('tokens_used'),
                result.get('response_time')
            ))
        
        self.conn.commit()
    
    def get_results(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Получение сохраненных результатов
        
        Args:
            limit: максимальное количество результатов (опционально)
            
        Returns:
            Список результатов
        """
        cursor = self.conn.cursor()
        if limit:
            cursor.execute("""
                SELECT * FROM results 
                ORDER BY date DESC 
                LIMIT ?
            """, (limit,))
        else:
            cursor.execute("SELECT * FROM results ORDER BY date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def search_results(self, query: str) -> List[Dict]:
        """
        Поиск результатов по тексту
        
        Args:
            query: поисковый запрос
            
        Returns:
            Список найденных результатов
        """
        cursor = self.conn.cursor()
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT * FROM results 
            WHERE response_text LIKE ? OR model_name LIKE ?
            ORDER BY date DESC
        """, (search_pattern, search_pattern))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_results_by_prompt_id(self, prompt_id: int) -> List[Dict]:
        """
        Получение результатов по ID промта
        
        Args:
            prompt_id: ID промта
            
        Returns:
            Список результатов для данного промта
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM results 
            WHERE prompt_id = ?
            ORDER BY date DESC
        """, (prompt_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Методы для работы с настройками
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Получение настройки по ключу
        
        Args:
            key: ключ настройки
            default: значение по умолчанию, если настройка не найдена
            
        Returns:
            Значение настройки или default
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default
    
    def set_setting(self, key: str, value: str):
        """
        Сохранение настройки
        
        Args:
            key: ключ настройки
            value: значение настройки
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        self.conn.commit()
    
    def close(self):
        """Закрытие подключения к базе данных"""
        self.conn.close()

