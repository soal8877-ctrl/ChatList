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
6. Нажмите **Улучшить промт**, чтобы AI предложил улучшенные и альтернативные формулировки.

### AI-ассистент промтов

1. Введите текст промта.
2. Нажмите **Улучшить промт**.
3. В окне выберите вариант и нажмите **Подставить**.
4. Модель ассистента настраивается в **Настройки → Модель ассистента**.

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
python -m unittest test_smoke.py test_prompt_assistant.py -v
```

## Сборка exe

Версия приложения задаётся в `version.py` (`__version__`).

Сначала создайте иконку (если ещё не создана):

```powershell
python .\create_icon.py
```

Сборка exe и установщика Inno Setup `ChatList-<версия>-setup.exe`:

```powershell
python .\build.py
```

Результат:

- `dist\ChatList.exe` — исполняемый файл с версией в свойствах Windows
- `dist\ChatList-<версия>-setup.exe` — установщик Inno Setup (с удалением через «Программы и компоненты»)

Требуется [Inno Setup 6](https://jrsoftware.org/isinfo.php).

> Рядом с exe должны лежать `.env` и файл БД `chatlist.db` (создаётся при первом запуске).

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | GUI |
| `db.py` | SQLite |
| `models.py` | Бизнес-логика |
| `network.py` | Запросы к OpenRouter |
| `prompt_assistant.py` | AI-ассистент для улучшения промтов |
| `export.py` | Экспорт MD/JSON |
| `logger.py` | Логирование запросов |
| `version.py` | Версия приложения (`__version__`) |
| `build.py` | Сборка exe и установщика |
| `installer.iss` | Скрипт Inno Setup |
| `release.ps1` | Подготовка артефактов Release |
| `docs/PUBLISHING.md` | Инструкция публикации |
| `docs/index.html` | Лендинг GitHub Pages |
| `create_icon.py` | Генерация `app.ico` |
| `app.ico` | Иконка приложения |
| `DATABASE.md` | Схема БД |
| `PLAN.md` | План разработки |

## Лимиты бесплатных моделей OpenRouter

- ~20 запросов в минуту
- ~50 запросов в день (без пополнения баланса на $10)

Актуальный список моделей: [openrouter.ai/models](https://openrouter.ai/models).

## Публикация

- [Инструкция: GitHub Release и GitHub Pages](docs/PUBLISHING.md)
- [Лендинг (GitHub Pages)](https://soal8877-ctrl.github.io/ChatList/)
- [Скачать последнюю версию](https://github.com/soal8877-ctrl/ChatList/releases/latest/download/ChatList-setup.exe)
