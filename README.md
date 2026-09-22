# ChatList

Приложение отправляет один промт в несколько бесплатных моделей через **OpenRouter** и позволяет сравнить ответы.

## Требования

- Python 3.11+
- Windows (PowerShell)

## Установка

```powershell
cd c:\Cursor\ChatList
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Укажите ключ OpenRouter в `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

Ключ можно получить на [openrouter.ai/keys](https://openrouter.ai/keys).

## Запуск

```powershell
python .\main.py
```

## Использование

1. В меню **Модели** включите нужные бесплатные модели (`:free` или `openrouter/free`).
2. Введите промт или выберите сохранённый.
3. Нажмите **Отправить** — ответы появятся в таблице.
4. Отметьте нужные строки и нажмите **Сохранить**.
5. Экспортируйте выбранные результаты в **Markdown** или **JSON**.

### Меню

| Пункт | Описание |
|-------|----------|
| Модели | Список моделей OpenRouter, поиск, сортировка |
| Настройки | Таймаут, путь к `.env`, логирование |
| Промты | Сохранённые промты, поиск, удаление |
| Сохранённые результаты | История ответов, экспорт MD/JSON |

### Логи

При включённой опции «Логировать запросы» в настройках записи пишутся в `logs/chatlist.log`.

## Тесты

```powershell
python -m unittest test_smoke.py -v
```

## Сборка exe

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name ChatList .\main.py
```

Исполняемый файл: `dist\ChatList.exe`

> Рядом с exe должны лежать `.env` и файл БД `chatlist.db` (создаётся при первом запуске).

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | GUI |
| `db.py` | SQLite |
| `models.py` | Бизнес-логика |
| `network.py` | Запросы к OpenRouter |
| `export.py` | Экспорт MD/JSON |
| `logger.py` | Логирование запросов |
| `DATABASE.md` | Схема БД |
| `PLAN.md` | План разработки |

## Лимиты бесплатных моделей OpenRouter

- ~20 запросов в минуту
- ~50 запросов в день (без пополнения баланса на $10)

Актуальный список моделей: [openrouter.ai/models](https://openrouter.ai/models).
