# Схема базы данных ChatList

База данных SQLite с именем `chatlist.db` содержит следующие таблицы:

## Таблица: prompts (Промты)

Хранит сохраненные промты пользователя.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY AUTOINCREMENT |
| date | TEXT | Дата создания промта | NOT NULL, формат: YYYY-MM-DD HH:MM:SS |
| prompt | TEXT | Текст промта | NOT NULL |
| tags | TEXT | Теги для категоризации (через запятую) | NULL |

**Индексы:**
- `idx_prompts_date` на поле `date` (для быстрой сортировки)
- `idx_prompts_tags` на поле `tags` (для поиска по тегам)

**Пример записи:**
```sql
INSERT INTO prompts (date, prompt, tags) 
VALUES ('2024-01-15 10:30:00', 'Объясни квантовую физику простыми словами', 'наука, физика');
```

---

## Таблица: models (Модели нейросетей)

Хранит информацию о доступных моделях нейросетей.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | Название модели | NOT NULL, UNIQUE |
| api_url | TEXT | URL API для запросов | NOT NULL |
| api_id | TEXT | Идентификатор API ключа в .env файле | NOT NULL |
| is_active | INTEGER | Активна ли модель (1 - да, 0 - нет) | NOT NULL, DEFAULT 1 |
| model_type | TEXT | Тип API (openai, deepseek, groq и т.д.) | NOT NULL |

**Индексы:**
- `idx_models_active` на поле `is_active` (для быстрого получения активных моделей)

**Пример записи:**
```sql
INSERT INTO models (name, api_url, api_id, is_active, model_type) 
VALUES ('GPT-4', 'https://api.openai.com/v1/chat/completions', 'OPENAI_API_KEY', 1, 'openai');
```

**Примечание:** API ключи хранятся в файле `.env`, а в таблице указывается только имя переменной окружения (api_id).

---

## Таблица: results (Результаты)

Хранит сохраненные результаты ответов моделей.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY AUTOINCREMENT |
| prompt_id | INTEGER | ID промта из таблицы prompts | FOREIGN KEY REFERENCES prompts(id) |
| model_id | INTEGER | ID модели из таблицы models | FOREIGN KEY REFERENCES models(id) |
| model_name | TEXT | Название модели (для быстрого доступа) | NOT NULL |
| response_text | TEXT | Текст ответа модели | NOT NULL |
| date | TEXT | Дата сохранения результата | NOT NULL, формат: YYYY-MM-DD HH:MM:SS |
| tokens_used | INTEGER | Количество использованных токенов (если доступно) | NULL |
| response_time | REAL | Время ответа в секундах | NULL |

**Индексы:**
- `idx_results_prompt_id` на поле `prompt_id` (для поиска по промту)
- `idx_results_model_id` на поле `model_id` (для поиска по модели)
- `idx_results_date` на поле `date` (для сортировки по дате)

**Пример записи:**
```sql
INSERT INTO results (prompt_id, model_id, model_name, response_text, date, tokens_used, response_time) 
VALUES (1, 1, 'GPT-4', 'Квантовая физика изучает...', '2024-01-15 10:31:00', 150, 2.5);
```

---

## Таблица: settings (Настройки)

Хранит настройки программы в формате ключ-значение.

| Поле | Тип | Описание | Ограничения |
|------|-----|----------|-------------|
| id | INTEGER | Первичный ключ | PRIMARY KEY AUTOINCREMENT |
| key | TEXT | Ключ настройки | NOT NULL, UNIQUE |
| value | TEXT | Значение настройки | NOT NULL |

**Пример записи:**
```sql
INSERT INTO settings (key, value) 
VALUES ('default_timeout', '30');
INSERT INTO settings (key, value) 
VALUES ('auto_save', 'false');
INSERT INTO settings (key, value) 
VALUES ('theme', 'light');
```

**Возможные настройки:**
- `default_timeout` - таймаут запросов по умолчанию (секунды)
- `auto_save` - автоматическое сохранение результатов (true/false)
- `theme` - тема интерфейса (light/dark)
- `export_format` - формат экспорта по умолчанию (markdown/json)

---

## Связи между таблицами

```
prompts (1) ──< (many) results
models (1) ──< (many) results
```

- Один промт может иметь множество результатов (от разных моделей)
- Одна модель может иметь множество результатов (для разных промтов)
- Результат всегда связан с одним промтом и одной моделью

---

## SQL скрипт создания базы данных

```sql
-- Таблица промтов
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_prompts_date ON prompts(date);
CREATE INDEX IF NOT EXISTS idx_prompts_tags ON prompts(tags);

-- Таблица моделей
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_url TEXT NOT NULL,
    api_id TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    model_type TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);

-- Таблица результатов
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER,
    model_id INTEGER,
    model_name TEXT NOT NULL,
    response_text TEXT NOT NULL,
    date TEXT NOT NULL,
    tokens_used INTEGER,
    response_time REAL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (model_id) REFERENCES models(id)
);

CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_date ON results(date);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL
);
```

---

## Примеры запросов

### Получить все активные модели:
```sql
SELECT * FROM models WHERE is_active = 1;
```

### Получить все промты с тегом "наука":
```sql
SELECT * FROM prompts WHERE tags LIKE '%наука%';
```

### Получить все результаты для конкретного промта:
```sql
SELECT r.*, m.name as model_name, p.prompt 
FROM results r
JOIN models m ON r.model_id = m.id
JOIN prompts p ON r.prompt_id = p.id
WHERE r.prompt_id = 1;
```

### Получить последние 10 сохраненных результатов:
```sql
SELECT * FROM results 
ORDER BY date DESC 
LIMIT 10;
```

