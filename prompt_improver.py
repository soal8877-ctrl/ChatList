import os
from typing import Dict, List, Optional
from network import OpenRouterHandler, get_handler_by_type
from models import ModelFactory, Model


class PromptImprover:
    """Класс для улучшения промтов с помощью AI"""
    
    # Промт-шаблоны для разных задач
    IMPROVE_PROMPT_TEMPLATE = """Ты - эксперт по написанию эффективных промтов для AI-моделей. 

Твоя задача - улучшить следующий промт, сделав его более четким, структурированным и эффективным.

Исходный промт:
{prompt}

Улучшенный промт должен:
1. Быть более конкретным и понятным
2. Содержать четкие инструкции
3. Быть структурированным (если это уместно)
4. Включать контекст, если он необходим
5. Использовать лучшие практики написания промтов

Верни только улучшенную версию промта без дополнительных комментариев."""

    VARIANTS_PROMPT_TEMPLATE = """Ты - эксперт по написанию эффективных промтов для AI-моделей.

Твоя задача - создать 2-3 альтернативные формулировки следующего промта, каждая из которых подходит для разных целей или стилей общения.

Исходный промт:
{prompt}

Создай 2-3 варианта переформулировки. Каждый вариант должен:
- Сохранять основную суть и цель промта
- Иметь свой уникальный стиль или подход
- Быть эффективным для получения нужного результата

Верни варианты в следующем формате:
Вариант 1: [текст варианта]
Вариант 2: [текст варианта]
Вариант 3: [текст варианта]"""

    ADAPT_CODE_TEMPLATE = """Ты - эксперт по написанию промтов для программирования и работы с кодом.

Адаптируй следующий промт для работы с кодом и техническими задачами:

Исходный промт:
{prompt}

Адаптированный промт должен:
1. Использовать техническую терминологию
2. Включать конкретные требования к формату ответа (если применимо)
3. Указывать язык программирования или технологии (если релевантно)
4. Быть структурированным для технических задач

Верни только адаптированную версию промта без дополнительных комментариев."""

    ADAPT_ANALYSIS_TEMPLATE = """Ты - эксперт по написанию промтов для аналитических задач.

Адаптируй следующий промт для аналитических и исследовательских задач:

Исходный промт:
{prompt}

Адаптированный промт должен:
1. Фокусироваться на анализе и исследовании
2. Требовать структурированного ответа
3. Включать критерии оценки или сравнения (если применимо)
4. Поощрять глубокое размышление и детальный анализ

Верни только адаптированную версию промта без дополнительных комментариев."""

    ADAPT_CREATIVE_TEMPLATE = """Ты - эксперт по написанию промтов для креативных задач.

Адаптируй следующий промт для творческих и креативных задач:

Исходный промт:
{prompt}

Адаптированный промт должен:
1. Поощрять творчество и оригинальность
2. Использовать более выразительный язык
3. Давать свободу для интерпретации
4. Включать элементы вдохновения и воображения

Верни только адаптированную версию промта без дополнительных комментариев."""

    def __init__(self, model_factory: ModelFactory, db):
        """
        Инициализация улучшателя промтов
        
        Args:
            model_factory: фабрика моделей для получения моделей
            db: экземпляр базы данных для получения настроек
        """
        self.model_factory = model_factory
        self.db = db
        self.handler = OpenRouterHandler()
    
    def get_improvement_model(self) -> Optional[Model]:
        """
        Получение модели для улучшения промтов
        
        Returns:
            Модель для улучшения или None
        """
        # Сначала пытаемся получить сохраненную модель из настроек
        saved_model_id = self.db.get_setting('improvement_model_id')
        if saved_model_id:
            try:
                model = self.model_factory.get_model_by_id(int(saved_model_id))
                if model and model.is_active == 1 and model.model_type == 'openrouter':
                    return model
            except (ValueError, TypeError):
                pass
        
        # Если сохраненной модели нет, ищем первую активную модель OpenRouter
        all_models = self.model_factory.get_all_models()
        for model in all_models:
            if model.is_active == 1 and model.model_type == 'openrouter':
                return model
        
        return None
    
    def improve_prompt(self, original_prompt: str, timeout: int = 30) -> Dict:
        """
        Улучшение промта
        
        Args:
            original_prompt: исходный промт
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом:
            - success: bool - успешность запроса
            - improved_prompt: str - улучшенный промт (если success=True)
            - error: str - текст ошибки (если success=False)
        """
        model = self.get_improvement_model()
        if not model:
            return {
                'success': False,
                'error': 'Не найдена активная модель OpenRouter для улучшения промтов'
            }
        
        api_key = os.getenv(model.api_id)
        if not api_key:
            return {
                'success': False,
                'error': f'API ключ не найден для {model.api_id}'
            }
        
        model_name = model.api_model_id if model.api_model_id else 'openai/gpt-3.5-turbo'
        prompt = self.IMPROVE_PROMPT_TEMPLATE.format(prompt=original_prompt)
        
        result = self.handler.send_request(prompt, api_key, model_name, timeout)
        
        if result.get('success'):
            return {
                'success': True,
                'improved_prompt': result.get('response_text', '').strip(),
                'model_name': model.name
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Неизвестная ошибка')
            }
    
    def generate_variants(self, original_prompt: str, timeout: int = 30) -> Dict:
        """
        Генерация вариантов переформулировки промта
        
        Args:
            original_prompt: исходный промт
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом:
            - success: bool - успешность запроса
            - variants: List[str] - список вариантов (если success=True)
            - error: str - текст ошибки (если success=False)
        """
        model = self.get_improvement_model()
        if not model:
            return {
                'success': False,
                'error': 'Не найдена активная модель OpenRouter для улучшения промтов'
            }
        
        api_key = os.getenv(model.api_id)
        if not api_key:
            return {
                'success': False,
                'error': f'API ключ не найден для {model.api_id}'
            }
        
        model_name = model.api_model_id if model.api_model_id else 'openai/gpt-3.5-turbo'
        prompt = self.VARIANTS_PROMPT_TEMPLATE.format(prompt=original_prompt)
        
        result = self.handler.send_request(prompt, api_key, model_name, timeout)
        
        if result.get('success'):
            # Парсим варианты из ответа
            response_text = result.get('response_text', '').strip()
            variants = self._parse_variants(response_text)
            
            return {
                'success': True,
                'variants': variants,
                'model_name': model.name
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Неизвестная ошибка')
            }
    
    def adapt_for_model_type(self, prompt: str, model_type: str, timeout: int = 30) -> Dict:
        """
        Адаптация промта под разные типы моделей
        
        Args:
            prompt: исходный промт
            model_type: тип модели ('code', 'analysis', 'creative')
            timeout: таймаут запроса в секундах
            
        Returns:
            Словарь с результатом:
            - success: bool - успешность запроса
            - adapted_prompt: str - адаптированный промт (если success=True)
            - error: str - текст ошибки (если success=False)
        """
        model = self.get_improvement_model()
        if not model:
            return {
                'success': False,
                'error': 'Не найдена активная модель OpenRouter для улучшения промтов'
            }
        
        api_key = os.getenv(model.api_id)
        if not api_key:
            return {
                'success': False,
                'error': f'API ключ не найден для {model.api_id}'
            }
        
        # Выбираем шаблон в зависимости от типа
        templates = {
            'code': self.ADAPT_CODE_TEMPLATE,
            'analysis': self.ADAPT_ANALYSIS_TEMPLATE,
            'creative': self.ADAPT_CREATIVE_TEMPLATE
        }
        
        template = templates.get(model_type.lower(), self.ADAPT_CODE_TEMPLATE)
        adapted_prompt = template.format(prompt=prompt)
        
        model_name = model.api_model_id if model.api_model_id else 'openai/gpt-3.5-turbo'
        
        result = self.handler.send_request(adapted_prompt, api_key, model_name, timeout)
        
        if result.get('success'):
            return {
                'success': True,
                'adapted_prompt': result.get('response_text', '').strip(),
                'model_name': model.name
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Неизвестная ошибка')
            }
    
    def _parse_variants(self, response_text: str) -> List[str]:
        """
        Парсинг вариантов из ответа модели
        
        Args:
            response_text: текст ответа модели
            
        Returns:
            Список вариантов промтов
        """
        variants = []
        lines = response_text.split('\n')
        
        current_variant = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Ищем строки вида "Вариант 1:", "Вариант 2:" и т.д.
            if line.lower().startswith('вариант') and ':' in line:
                # Сохраняем предыдущий вариант, если есть
                if current_variant:
                    variants.append(current_variant.strip())
                
                # Начинаем новый вариант
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_variant = parts[1].strip()
                else:
                    current_variant = ""
            elif current_variant is not None:
                # Продолжаем текущий вариант
                if current_variant:
                    current_variant += " " + line
                else:
                    current_variant = line
        
        # Добавляем последний вариант
        if current_variant:
            variants.append(current_variant.strip())
        
        # Если не удалось распарсить структурированно, пытаемся найти варианты по-другому
        if not variants:
            # Разделяем по номерам или маркерам
            import re
            # Ищем паттерны типа "1.", "2.", "-", и т.д.
            parts = re.split(r'\n\s*(?:\d+\.|[-•]|Вариант\s*\d+:)', response_text, flags=re.IGNORECASE)
            variants = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
        
        # Если все еще нет вариантов, возвращаем весь текст как один вариант
        if not variants:
            variants = [response_text.strip()]
        
        return variants[:3]  # Возвращаем максимум 3 варианта
