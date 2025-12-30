import logging
import os
from datetime import datetime
from typing import Dict, Optional


class RequestLogger:
    """Класс для логирования запросов к API"""
    
    def __init__(self, log_file: str = "chatlist.log"):
        """
        Инициализация логгера
        
        Args:
            log_file: имя файла для логов
        """
        self.log_file = log_file
        self.setup_logger()
    
    def setup_logger(self):
        """Настройка логгера"""
        # Создаем директорию для логов, если её нет
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_path = os.path.join(log_dir, self.log_file)
        
        # Настройка форматирования
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Настройка файлового обработчика
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Настройка логгера
        self.logger = logging.getLogger('ChatList')
        self.logger.setLevel(logging.INFO)
        
        # Удаляем существующие обработчики, чтобы избежать дублирования
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self.logger.addHandler(file_handler)
    
    def log_request(self, model_name: str, prompt: str, success: bool, 
                   response_text: Optional[str] = None, error: Optional[str] = None,
                   tokens_used: Optional[int] = None, response_time: Optional[float] = None):
        """
        Логирование запроса к API
        
        Args:
            model_name: название модели
            prompt: текст промта
            success: успешность запроса
            response_text: текст ответа (если успешно)
            error: текст ошибки (если неуспешно)
            tokens_used: количество токенов
            response_time: время ответа в секундах
        """
        log_message = f"Request to {model_name} | Prompt: {prompt[:100]}... | "
        
        if success:
            log_message += f"SUCCESS | Response length: {len(response_text) if response_text else 0} chars"
            if tokens_used:
                log_message += f" | Tokens: {tokens_used}"
            if response_time:
                log_message += f" | Time: {response_time:.2f}s"
        else:
            log_message += f"FAILED | Error: {error}"
        
        self.logger.info(log_message)
    
    def log_result_saved(self, results_count: int):
        """
        Логирование сохранения результатов
        
        Args:
            results_count: количество сохраненных результатов
        """
        self.logger.info(f"Saved {results_count} results to database")
    
    def log_prompt_saved(self, prompt_id: int):
        """
        Логирование сохранения промта
        
        Args:
            prompt_id: ID сохраненного промта
        """
        self.logger.info(f"Saved prompt with ID: {prompt_id}")

