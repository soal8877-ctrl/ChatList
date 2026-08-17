# Схема базы данных ChatList

СУБД: **SQLite**.  
Доступ к БД — только через модуль `db.py`.  
API-ключи **не хранятся** в БД: в таблице `models` лежит имя переменной окружения (`api_id`), значение берётся из файла `.env`.

Файл БД по умолчанию: `chatlist.db` (рядом с приложением или путь из `settings`).

---

## Обзор связей

```
prompts ─────┐
             ├──< results >── models
settings     │
request_logs │
             └── (временная таблица результатов — только в памяти, не в SQLite)
```

---

## Таблица `prompts` — запросы

Хранит введённые пользователем промты для повторного использования.

| Поле         | Тип        | Ограничения              | Описание                          |
|--------------|------------|--------------------------|-----------------------------------|
| `id`         | INTEGER    | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор        |
| `created_at` | TEXT       | NOT NULL                 | Дата/время создания (ISO 8601)    |
| `prompt`     | TEXT       | NOT NULL                 | Текст промта                      |
| `tags`       | TEXT       | DEFAULT ''               | Теги через запятую или пробел     |

Индексы (рекомендуемые):
- `idx_prompts_created_at` по `created_at`
- при необходимости — FTS/поиск по `prompt` и `tags` на уровне приложения

---

## Таблица `models` — нейросети

Справочник моделей/провайдеров, в которые отправляется промт.

| Поле       | Тип     | Ограничения              | Описание |
|------------|---------|--------------------------|----------|
| `id`       | INTEGER | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор |
| `name`     | TEXT    | NOT NULL, UNIQUE         | Отображаемое имя (например `DeepSeek`) |
| `api_url`  | TEXT    | NOT NULL                 | Базовый URL API |
| `api_id`   | TEXT    | NOT NULL                 | Имя переменной в `.env` с ключом (например `OPENROUTER_API_KEY`) |
| `is_active`| INTEGER | NOT NULL, DEFAULT 1      | `1` — участвует в рассылке, `0` — нет |

Правила:
- активные модели: `WHERE is_active = 1`
- сам секрет ключа читается как `os.environ[api_id]` / `dotenv`

Индексы:
- `idx_models_is_active` по `is_active`

---

## Таблица `results` — сохранённые результаты

Постоянное хранилище строк, которые пользователь отметил чекбоксом и нажал «Сохранить».

| Поле         | Тип     | Ограничения                         | Описание |
|--------------|---------|-------------------------------------|----------|
| `id`         | INTEGER | PRIMARY KEY, AUTOINCREMENT          | Уникальный идентификатор |
| `prompt_id`  | INTEGER | NOT NULL, FK → `prompts(id)`        | Связанный промт |
| `model_id`   | INTEGER | NOT NULL, FK → `models(id)`         | Модель, давшая ответ |
| `response`   | TEXT    | NOT NULL                            | Текст ответа модели |
| `created_at` | TEXT    | NOT NULL                            | Дата/время сохранения (ISO 8601) |

Внешние ключи:
- `FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE`
- `FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE RESTRICT`

Индексы:
- `idx_results_prompt_id` по `prompt_id`
- `idx_results_model_id` по `model_id`
- `idx_results_created_at` по `created_at`

Примечание: перед сохранением результата промт должен существовать в `prompts` (создать новую запись или взять выбранную).

---

## Таблица `settings` — настройки программы

Пары ключ–значение для конфигурации приложения.

| Поле    | Тип  | Ограничения        | Описание |
|---------|------|--------------------|----------|
| `key`   | TEXT | PRIMARY KEY        | Имя настройки |
| `value` | TEXT | NOT NULL DEFAULT ''| Значение (строка; типы интерпретирует код) |

Примеры ключей:
- `db_path` — путь к файлу SQLite
- `request_timeout_sec` — таймаут HTTP
- `window_width` / `window_height` — размер окна

---

## Таблица `request_logs` — логи запросов

Журнал каждого HTTP-запроса к модели (успех и ошибка). Не содержит API-ключей.

| Поле          | Тип     | Ограничения              | Описание |
|---------------|---------|--------------------------|----------|
| `id`          | INTEGER | PRIMARY KEY, AUTOINCREMENT | Уникальный идентификатор |
| `created_at`  | TEXT    | NOT NULL                 | Дата/время запроса (ISO 8601) |
| `model_name`  | TEXT    | NOT NULL                 | Имя модели |
| `prompt`      | TEXT    | NOT NULL                 | Отправленный текст |
| `status`      | TEXT    | NOT NULL                 | `ok` или `error` |
| `response`    | TEXT    | NOT NULL DEFAULT ''      | Ответ или текст ошибки |
| `duration_ms` | INTEGER | NOT NULL DEFAULT 0       | Длительность запроса |
| `http_status` | INTEGER | NULL                     | HTTP-код, если известен |

Индекс: `idx_request_logs_created_at` по `created_at`.

---

## Временная таблица результатов (не SQLite)

Создаётся **в памяти** после ответов моделей и **не пишется** в файл БД.

Логическая структура строки:

| Поле         | Тип     | Описание |
|--------------|---------|----------|
| `model_id`   | int     | Ссылка на `models.id` |
| `model_name` | str     | Имя для отображения |
| `response`   | str     | Текст ответа |
| `selected`   | bool    | Чекбокс в UI |
| `prompt_id`  | int\|null | id промта, если уже сохранён/выбран |
| `prompt_text`| str     | Текст отправленного промта |

Жизненный цикл (из `PROJECT.md`):
1. После ответов API — создать временную таблицу.
2. «Сохранить» — строки с `selected=True` → `results`, временную очистить.
3. Новый промт — временную удалить полностью и создать заново после новых ответов.

---

## SQL создания таблиц

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    prompt     TEXT    NOT NULL,
    tags       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS models (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    NOT NULL UNIQUE,
    api_url   TEXT    NOT NULL,
    api_id    TEXT    NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL,
    model_id   INTEGER NOT NULL,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS request_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    model_name  TEXT    NOT NULL,
    prompt      TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    response    TEXT    NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    http_status INTEGER
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs(created_at);
```

---

## Пример `.env` (не в БД)

```env
OPENROUTER_API_KEY=sk-or-v1-...
# Optional, if you add models via Data → Models:
# OPENAI_API_KEY=
# DEEPSEEK_API_KEY=
# GROQ_API_KEY=
```

В `models.api_id` хранится имя переменной (`OPENROUTER_API_KEY` и т.д.), а не сам секрет.

По умолчанию запросы идут через [OpenRouter](https://openrouter.ai):  
`api_url` = `https://openrouter.ai/api/v1/chat/completions`, в поле `name` — id модели (например `google/gemma-4-31b-it:free`).

Можно добавить прямые провайдеры OpenAI / DeepSeek / Groq в **Данные → Модели** (пресеты URL и `api_id`).
