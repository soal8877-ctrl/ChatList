import json
from typing import List, Dict
from datetime import datetime
import os


def export_to_markdown(results: List[Dict], filename: str = None) -> str:
    """
    Экспорт результатов в Markdown формат
    
    Args:
        results: список словарей с результатами
        filename: имя файла для сохранения (опционально)
        
    Returns:
        Путь к сохраненному файлу или содержимое в виде строки
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.md"
    
    markdown_content = "# Результаты сравнения моделей\n\n"
    markdown_content += f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown_content += "---\n\n"
    
    for i, result in enumerate(results, 1):
        markdown_content += f"## Результат {i}\n\n"
        markdown_content += f"**Модель:** {result.get('model_name', 'Неизвестно')}\n\n"
        markdown_content += f"**Дата:** {result.get('date', 'Неизвестно')}\n\n"
        
        if result.get('tokens_used'):
            markdown_content += f"**Токены:** {result['tokens_used']}\n\n"
        if result.get('response_time'):
            markdown_content += f"**Время ответа:** {result['response_time']:.2f}с\n\n"
        
        markdown_content += "**Ответ:**\n\n"
        markdown_content += f"{result.get('response_text', 'Нет ответа')}\n\n"
        markdown_content += "---\n\n"
    
    # Сохраняем в файл
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return filename


def export_to_json(results: List[Dict], filename: str = None) -> str:
    """
    Экспорт результатов в JSON формат
    
    Args:
        results: список словарей с результатами
        filename: имя файла для сохранения (опционально)
        
    Returns:
        Путь к сохраненному файлу
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.json"
    
    export_data = {
        'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results_count': len(results),
        'results': results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    return filename

