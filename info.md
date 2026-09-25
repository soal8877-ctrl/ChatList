# ChatList — выжимка для нового чата

Краткий контекст проекта и история работ из текущего чата.

---

## Что это за проект

**ChatList** — Python-приложение с GUI на **PyQt6**. Пользователь вводит один промт, программа отправляет его в несколько нейросетей через **OpenRouter** (только бесплатные модели `:free` или `openrouter/free`), показывает ответы во временной таблице. Отмеченные строки сохраняются в SQLite.

**Путь проекта:** `C:\Cursor\ChatList`

**Спецификация:** `PROJECT.md`  
**План разработки:** `PLAN.md`  
**Схема БД:** `DATABASE.md`

---

## Стек

- Python 3.11+
- PyQt6
- SQLite (`chatlist.db`)
- httpx + python-dotenv
- OpenRouter API (`https://openrouter.ai/api/v1/chat/completions`)
- PyInstaller (сборка exe)

---

## Запуск

```powershell
cd C:\Cursor\ChatList
python -m pip install -r requirements.txt
python .\main.py
```

**Первый запуск:** скопировать `.env.example` → `.env`, указать ключ:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

**Тесты:**

```powershell
python -m unittest test_smoke.py test_prompt_assistant.py -v
```

**Просмотр БД (отдельная утилита):**

```powershell
python .\test-db.py
```

**Сборка exe:**

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name ChatList .\main.py
```

---

## Архитектура модулей

| Файл | Назначение |
|------|------------|
| `main.py` | GUI, диалоги, workers (отправка, улучшение промта) |
| `db.py` | SQLite: CRUD, seed, миграции |
| `models.py` | Бизнес-логика, `ChatSession`, настройки, ассистент |
| `network.py` | HTTP к OpenRouter: `send_prompt`, `send_chat`, retry при 429 |
| `prompt_assistant.py` | AI-ассистент улучшения промтов (JSON-ответ) |
| `export.py` | Экспорт MD/JSON |
| `logger.py` | Логи в `logs/chatlist.log` |
| `test-db.py` | GUI-браузер SQLite с пагинацией и CRUD |
| `test_smoke.py` | Базовые тесты |
| `test_prompt_assistant.py` | Тесты ассистента |

---

## База данных (SQLite)

Таблицы: `prompts`, `models`, `results`, `settings`.

API-ключи **не** в БД — только имя переменной (`OPENROUTER_API_KEY`), сам ключ в `.env`.

### Модели по умолчанию (OpenRouter, бесплатные)

Активны по умолчанию:
- OpenRouter Free (`openrouter/free`)
- Nemotron 3.5 Lightning (free)
- North Mini Code (free)

Неактивны (часто 429):
- Gemma 4 26B (free)
- Qwen3.8 27B (free)

### Настройки (`settings`)

| Ключ | Описание |
|------|----------|
| `request_timeout` | Таймаут HTTP (с) |
| `env_file` | Путь к `.env` |
| `log_requests` | `1` / `0` |
| `default_tags` | Теги по умолчанию |
| `assistant_enabled` | Включить AI-ассистент |
| `assistant_model_id` | ID модели из таблицы `models` |

---

## Что сделано в этом чате (хронология)

1. **Минимальное PyQt-приложение** → кнопка «Нажми меня».
2. **Этапы 0–6 PLAN.md:** `db.py`, `models.py`, `network.py`, полный GUI, CRUD моделей/промтов/результатов.
3. **OpenRouter:** все модели через один ключ `OPENROUTER_API_KEY`, только `:free`.
4. **Исправление .env:** ключ был в редакторе, но не сохранён на диск; улучшена загрузка `.env` (несколько путей, `override=True`).
5. **429 ошибки:** retry, последовательная отправка, смена активных моделей по умолчанию.
6. **UI:** многострочные ответы в таблице, кнопка «Открыть» (Markdown-просмотр), экспорт MD/JSON, логи.
7. **Этап 8:** тесты, README, сборка exe.
8. **`test-db.py`:** просмотр SQLite с пагинацией и CRUD.
9. **Этап 9 — AI-ассистент промтов:**
   - кнопка «Улучшить промт»;
   - `prompt_assistant.py`, `network.send_chat()`;
   - диалог с улучшенным / альтернативами / адаптациями + «Подставить»;
   - настройки модели ассистента.

---

## Текущий функционал GUI

### Главное окно
- Ввод промта, теги, сохранённые промты
- **Отправить**, **Улучшить промт**
- Таблица результатов (модель | ответ | чекбокс), сортировка
- **Открыть**, **Сохранить**, **Экспорт MD/JSON**, **Новый запрос**

### Меню
- **Модели** — CRUD, поиск, вкл/выкл
- **Настройки** — таймаут, `.env`, логи, модель ассистента
- **Промты** — список, поиск, удаление, «Открыть» (просмотр + сохранённые ответы)
- **Сохранённые результаты** — поиск, экспорт, «Открыть»

---

## Статус по PLAN.md

| Этап | Статус |
|------|--------|
| 0–8 | ✅ Выполнено |
| 9 — AI-ассистент промтов | ✅ Выполнено |

---

## Что ещё НЕ сделано (из PROJECT.md)

### П. 8 — Настройки (расширенные)
- Светлая/тёмная тема
- Размер шрифта панелей
- Сохранение в `settings`

### П. 9 — «О программе»
- Диалог с краткой информацией о приложении

---

## Важные технические детали

1. **`.env`:** после правок сохранять файл (**Ctrl+S**). Программа читает `.env` рядом с кодом, exe или из cwd.
2. **OpenRouter free:** ~20 req/min, ~50 req/day без пополнения баланса.
3. **HTTP 429:** не баг приложения — лимит провайдера; есть retry и понятные сообщения.
4. **Отправка в модели:** последовательная (`parallel=False`), чтобы снизить 429.
5. **Логи ассистента:** статусы `assistant_ok` / `assistant_error` в `logs/chatlist.log`.

---

## Зависимости (`requirements.txt`)

```
PyQt6>=6.6.0
httpx>=0.27.0
python-dotenv>=1.0.0
pyinstaller>=6.6.0
```

---

## Файлы, которых нет в git

- `.env` (секреты)
- `chatlist.db`
- `logs/`
- `build/`, `dist/`

---

## Рекомендации для продолжения

1. Реализовать **п. 8 PROJECT.md** — тема и размер шрифта.
2. Реализовать **«О программе»** (п. 9 PROJECT.md).
3. При необходимости — обновить `DATABASE.md` ключами `assistant_*`.
4. Не коммитить `.env` и `chatlist.db`.

---

## Полезные команды (PowerShell)

```powershell
# Основная программа
python .\main.py

# Тесты
python -m unittest test_smoke.py test_prompt_assistant.py -v

# Браузер БД
python .\test-db.py

# Проверка загрузки ключа (без вывода секрета)
python -c "import network, models; print(bool(network.get_api_key()))"
```
