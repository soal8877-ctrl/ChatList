import requests
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class APIHandler(ABC):
    """Базовый абстрактный класс для обработчиков API"""
    
    @abstractmethod
    def send_request(self, prompt: str, api_key: str, model_name: str = None, timeout: int = 30) -> Dict:
        """
        Отправка запроса к API
        
        Args:
            prompt: текст промта
            api_key: API ключ
            model_name: название модели (опционально)
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом:
            - success: bool - успешность запроса
            - response_text: str - текст ответа (если success=True)
            - error: str - текст ошибки (если success=False)
            - tokens_used: int - количество токенов (если доступно)
            - response_time: float - время ответа в секундах
        """
        pass


class OpenAIHandler(APIHandler):
    """Обработчик для OpenAI API"""
    
    def send_request(self, prompt: str, api_key: str, model_name: str = "gpt-3.5-turbo", timeout: int = 30) -> Dict:
        """
        Отправка запроса к OpenAI API
        
        Args:
            prompt: текст промта
            api_key: API ключ OpenAI
            model_name: название модели (по умолчанию gpt-3.5-turbo)
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом запроса
        """
        start_time = time.time()
        
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens')
                
                return {
                    'success': True,
                    'response_text': response_text,
                    'tokens_used': tokens_used,
                    'response_time': response_time
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code} - {response.text}",
                    'response_time': response_time
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f"Timeout: запрос превысил {timeout} секунд",
                'response_time': time.time() - start_time
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Network Error: {str(e)}",
                'response_time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected Error: {str(e)}",
                'response_time': time.time() - start_time
            }


class DeepSeekHandler(APIHandler):
    """Обработчик для DeepSeek API"""
    
    def send_request(self, prompt: str, api_key: str, model_name: str = "deepseek-chat", timeout: int = 30) -> Dict:
        """
        Отправка запроса к DeepSeek API
        
        Args:
            prompt: текст промта
            api_key: API ключ DeepSeek
            model_name: название модели (по умолчанию deepseek-chat)
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом запроса
        """
        start_time = time.time()
        
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens')
                
                return {
                    'success': True,
                    'response_text': response_text,
                    'tokens_used': tokens_used,
                    'response_time': response_time
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code} - {response.text}",
                    'response_time': response_time
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f"Timeout: запрос превысил {timeout} секунд",
                'response_time': time.time() - start_time
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Network Error: {str(e)}",
                'response_time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected Error: {str(e)}",
                'response_time': time.time() - start_time
            }


class GroqHandler(APIHandler):
    """Обработчик для Groq API"""
    
    def send_request(self, prompt: str, api_key: str, model_name: str = "llama2-70b-4096", timeout: int = 30) -> Dict:
        """
        Отправка запроса к Groq API
        
        Args:
            prompt: текст промта
            api_key: API ключ Groq
            model_name: название модели (по умолчанию llama2-70b-4096)
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом запроса
        """
        start_time = time.time()
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result['choices'][0]['message']['content']
                tokens_used = result.get('usage', {}).get('total_tokens')
                
                return {
                    'success': True,
                    'response_text': response_text,
                    'tokens_used': tokens_used,
                    'response_time': response_time
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code} - {response.text}",
                    'response_time': response_time
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f"Timeout: запрос превысил {timeout} секунд",
                'response_time': time.time() - start_time
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Network Error: {str(e)}",
                'response_time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected Error: {str(e)}",
                'response_time': time.time() - start_time
            }


def get_handler_by_type(model_type: str) -> Optional[APIHandler]:
    """
    Получение обработчика API по типу модели
    
    Args:
        model_type: тип модели (openai, deepseek, groq)
        
    Returns:
        Экземпляр соответствующего обработчика или None
    """
    handlers = {
        'openai': OpenAIHandler(),
        'deepseek': DeepSeekHandler(),
        'groq': GroqHandler()
    }
    return handlers.get(model_type.lower())


def send_requests_async(models: List, prompt: str, timeout: int = 30) -> List[Dict]:
    """
    Асинхронная отправка запросов к нескольким моделям одновременно
    
    Args:
        models: список экземпляров Model
        prompt: текст промта
        timeout: таймаут для каждого запроса в секундах
        
    Returns:
        Список словарей с результатами:
        - model_id: ID модели
        - model_name: название модели
        - success: успешность запроса
        - response_text: текст ответа (если success=True)
        - error: текст ошибки (если success=False)
        - tokens_used: количество токенов
        - response_time: время ответа в секундах
    """
    results = []
    
    def send_single_request(model):
        """Отправка запроса к одной модели"""
        # Получаем API ключ из переменных окружения
        api_key = os.getenv(model.api_id)
        
        if not api_key:
            return {
                'model_id': model.id,
                'model_name': model.name,
                'success': False,
                'error': f"API ключ не найден для {model.api_id}",
                'response_time': 0
            }
        
        # Получаем обработчик для данного типа API
        handler = get_handler_by_type(model.model_type)
        
        if not handler:
            return {
                'model_id': model.id,
                'model_name': model.name,
                'success': False,
                'error': f"Неподдерживаемый тип API: {model.model_type}",
                'response_time': 0
            }
        
        # Отправляем запрос
        result = handler.send_request(prompt, api_key, timeout=timeout)
        
        # Добавляем информацию о модели к результату
        result['model_id'] = model.id
        result['model_name'] = model.name
        
        return result
    
    # Используем ThreadPoolExecutor для параллельной отправки запросов
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        future_to_model = {executor.submit(send_single_request, model): model for model in models}
        
        for future in as_completed(future_to_model):
            result = future.result()
            results.append(result)
    
    return results

