import logging
import os
from datetime import datetime
from typing import Dict, Optional
from version import __version__


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
        
        # Логируем версию при запуске
        self.logger.info(f"ChatList v{__version__} started")
    
    def log_request(self, model_name: str, prompt: str, success: bool, 
                   response_text: Optional[str] = None, error: Optional[str] = None,
                   tokens_used: Optional[int] = None, response_time: Optional[float] = None,
                   url: Optional[str] = None, api_model_id: Optional[str] = None,
                   model_type: Optional[str] = None, http_status: Optional[int] = None,
                   request_model: Optional[str] = None, temperature: Optional[float] = None,
                   messages_length: Optional[int] = None, prompt_tokens: Optional[int] = None,
                   completion_tokens: Optional[int] = None, error_type: Optional[str] = None):
        """
        Логирование запроса к API с техническими деталями
        
        Args:
            model_name: название модели (отображаемое имя)
            prompt: текст промта
            success: успешность запроса
            response_text: текст ответа (если успешно)
            error: текст ошибки (если неуспешно)
            tokens_used: общее количество токенов
            response_time: время ответа в секундах
            url: URL эндпоинта API
            api_model_id: идентификатор модели для API
            model_type: тип API (openai, deepseek, groq, openrouter)
            http_status: HTTP статус код ответа
            request_model: идентификатор модели в запросе
            temperature: значение temperature в запросе
            messages_length: количество сообщений в запросе
            prompt_tokens: количество токенов в промте
            completion_tokens: количество токенов в ответе
            error_type: тип ошибки (timeout, network, api_error)
        """
        # Основная информация
        log_message = f"Request to {model_name} | Prompt: {prompt[:100]}... | "
        
        # Технические детали запроса
        tech_details = []
        if url:
            tech_details.append(f"URL: {url}")
        if api_model_id:
            tech_details.append(f"API Model ID: {api_model_id}")
        if model_type:
            tech_details.append(f"API Type: {model_type}")
        if request_model:
            tech_details.append(f"Request Model: {request_model}")
        if temperature is not None:
            tech_details.append(f"Temperature: {temperature}")
        if messages_length is not None:
            tech_details.append(f"Messages: {messages_length}")
        
        if tech_details:
            log_message += " | " + " | ".join(tech_details)
        
        # Результат запроса
        if success:
            log_message += " | SUCCESS"
            if http_status:
                log_message += f" | HTTP Status: {http_status}"
            if response_text:
                log_message += f" | Response length: {len(response_text)} chars"
            
            # Детализация токенов
            token_details = []
            if prompt_tokens is not None:
                token_details.append(f"Prompt tokens: {prompt_tokens}")
            if completion_tokens is not None:
                token_details.append(f"Completion tokens: {completion_tokens}")
            if tokens_used:
                token_details.append(f"Total tokens: {tokens_used}")
            
            if token_details:
                log_message += " | " + " | ".join(token_details)
            
            if response_time:
                log_message += f" | Time: {response_time:.2f}s"
        else:
            log_message += " | FAILED"
            if error_type:
                log_message += f" | Error Type: {error_type}"
            if http_status:
                log_message += f" | HTTP Status: {http_status}"
            if error:
                log_message += f" | Error: {error}"
            if response_time:
                log_message += f" | Time: {response_time:.2f}s"
        
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

