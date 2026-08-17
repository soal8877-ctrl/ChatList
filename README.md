# ChatList

Python + PyQt app that sends one prompt to several AI models and lets you compare the answers. Checked rows can be saved to SQLite.

## Requirements

- Python 3.11+
- An [OpenRouter](https://openrouter.ai/keys) API key (default setup)

## Install and run (PowerShell)

```powershell
cd C:\Cursor\ChatList
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key
```

Save the file, then:

```powershell
python main.py
```

On first launch the app creates `chatlist.db` and seeds four free OpenRouter models.

## How to use

1. Type a prompt (or pick a saved one).
2. Click **Отправить**. Answers appear in a temporary table (not written to SQLite yet).
3. Check the rows you want and click **Сохранить**.
4. Optional: **Экспорт…** writes selected (or all current) answers to Markdown or JSON.

Menu **Данные**:

- **Модели…** — add/edit models, provider presets (OpenRouter, OpenAI, DeepSeek, Groq), active flag
- **Промты…** — reuse or delete saved prompts
- **Результаты…** — saved history, export
- **Логи запросов…** — HTTP request log
- **Настройки…** — timeout and window size

Every table supports search and column sort.

## Direct providers

Default models use OpenRouter. To call OpenAI / DeepSeek / Groq directly:

1. Put the matching key in `.env` (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`).
2. Open **Данные → Модели → Добавить**, pick a provider preset, set the model id.

## Build a Windows exe

```powershell
cd C:\Cursor\ChatList
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name ChatList main.py
```

The exe is `dist\ChatList.exe`. Put a `.env` file next to the exe (same `OPENROUTER_API_KEY=` line).

```powershell
.\dist\ChatList.exe
```

## Project layout

| File | Role |
|------|------|
| `main.py` | GUI |
| `db.py` | SQLite only |
| `models.py` | Active models and `.env` keys |
| `network.py` | HTTP send |
| `adapters.py` | OpenRouter / OpenAI / DeepSeek / Groq |
| `temp_results.py` | In-memory result table |
| `dialogs.py` | Data dialogs |
| `export.py` | Markdown / JSON export |

Schema: `DATABASE.md`. Spec: `PROJECT.md`.
