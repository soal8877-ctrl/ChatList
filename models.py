from typing import Optional, Dict
from db import Database


class Model:
    """Класс для представления модели нейросети"""
    
    def __init__(self, model_id: int, name: str, api_url: str, api_id: str, 
                 model_type: str, is_active: int, db: Database):
        """
        Инициализация модели
        
        Args:
            model_id: ID модели в БД
            name: название модели
            api_url: URL API
            api_id: имя переменной окружения для API ключа
            model_type: тип API (openai, deepseek, groq)
            is_active: активна ли модель (1 - да, 0 - нет)
            db: экземпляр класса Database
        """
        self.id = model_id
        self.name = name
        self.api_url = api_url
        self.api_id = api_id
        self.model_type = model_type
        self.is_active = is_active
        self.db = db
    
    @classmethod
    def from_dict(cls, data: Dict, db: Database) -> 'Model':
        """
        Создание экземпляра Model из словаря
        
        Args:
            data: словарь с данными модели
            db: экземпляр класса Database
            
        Returns:
            Экземпляр класса Model
        """
        return cls(
            model_id=data['id'],
            name=data['name'],
            api_url=data['api_url'],
            api_id=data['api_id'],
            model_type=data['model_type'],
            is_active=data['is_active'],
            db=db
        )
    
    def to_dict(self) -> Dict:
        """
        Преобразование модели в словарь
        
        Returns:
            Словарь с данными модели
        """
        return {
            'id': self.id,
            'name': self.name,
            'api_url': self.api_url,
            'api_id': self.api_id,
            'model_type': self.model_type,
            'is_active': self.is_active
        }
    
    def update_status(self, is_active: int):
        """
        Обновление статуса модели
        
        Args:
            is_active: новый статус (1 - активна, 0 - неактивна)
        """
        self.db.update_model_status(self.id, is_active)
        self.is_active = is_active


class ModelFactory:
    """Фабрика для создания моделей и получения активных моделей"""
    
    def __init__(self, db: Database):
        """
        Инициализация фабрики
        
        Args:
            db: экземпляр класса Database
        """
        self.db = db
    
    def get_active_models(self) -> list[Model]:
        """
        Получение всех активных моделей
        
        Returns:
            Список активных моделей
        """
        models_data = self.db.get_active_models()
        return [Model.from_dict(model_data, self.db) for model_data in models_data]
    
    def get_all_models(self) -> list[Model]:
        """
        Получение всех моделей
        
        Returns:
            Список всех моделей
        """
        models_data = self.db.get_all_models()
        return [Model.from_dict(model_data, self.db) for model_data in models_data]
    
    def get_model_by_id(self, model_id: int) -> Optional[Model]:
        """
        Получение модели по ID
        
        Args:
            model_id: ID модели
            
        Returns:
            Экземпляр Model или None
        """
        model_data = self.db.get_model_by_id(model_id)
        if model_data:
            return Model.from_dict(model_data, self.db)
        return None
    
    def add_model(self, name: str, api_url: str, api_id: str, 
                  model_type: str, is_active: int = 1) -> Model:
        """
        Добавление новой модели
        
        Args:
            name: название модели
            api_url: URL API
            api_id: имя переменной окружения для API ключа
            model_type: тип API (openai, deepseek, groq)
            is_active: активна ли модель (1 - да, 0 - нет)
            
        Returns:
            Созданная модель
        """
        model_id = self.db.add_model(name, api_url, api_id, model_type, is_active)
        return self.get_model_by_id(model_id)

