# Инструкция по публикации ChatList на GitHub Release и GitHub Pages

## Подготовка

### 1. Настройка репозитория GitHub

1. Создайте репозиторий на GitHub (если еще не создан)
2. Убедитесь, что репозиторий публичный (для GitHub Pages)
3. Склонируйте репозиторий локально:
   ```bash
   git clone https://github.com/yourusername/ChatList.git
   cd ChatList
   ```

### 2. Настройка GitHub Actions Secrets

Для автоматической сборки и публикации необходимо настроить секреты:

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте следующие секреты (если нужны):
   - `GH_TOKEN` - Personal Access Token с правами `repo` (для публикации релизов)
   - `INNO_SETUP_PATH` - путь к Inno Setup (опционально, если не используется стандартный путь)

**Создание Personal Access Token:**
- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate new token → Выберите `repo` scope
- Скопируйте токен и добавьте как секрет `GH_TOKEN`

### 3. Настройка веток

Убедитесь, что у вас есть:
- `main` или `master` - основная ветка с кодом
- `gh-pages` - ветка для GitHub Pages (создастся автоматически)

## Публикация релиза (вручную)

### Шаг 1: Обновите версию

1. Откройте `version.py`
2. Измените версию (например, с `1.0.0` на `1.0.1`)
3. Закоммитьте изменения:
   ```bash
   git add version.py
   git commit -m "Bump version to 1.0.1"
   git push
   ```

### Шаг 2: Создайте тег

```bash
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
```

### Шаг 3: Соберите приложение локально

```bash
# Соберите исполняемый файл
python build.py

# Создайте инсталлятор (если установлен Inno Setup)
python build_installer.py
```

### Шаг 4: Создайте Release на GitHub

1. Перейдите на страницу репозитория → Releases → Create a new release
2. Выберите созданный тег (например, `v1.0.1`)
3. Заголовок: `ChatList v1.0.1`
4. Описание (используйте шаблон из `RELEASE_NOTES_TEMPLATE.md`):
   ```markdown
   ## Что нового
   - Исправления и улучшения
   
   ## Скачать
   - Windows Installer: [ChatList-Setup-1.0.1.exe](ссылка)
   - Portable: [ChatList-1.0.1.exe](ссылка)
   ```
5. Загрузите файлы:
   - `dist/ChatList-Setup-1.0.1.exe` (инсталлятор)
   - `dist/ChatList-1.0.1.exe` (portable версия, опционально)
6. Нажмите "Publish release"

## Автоматическая публикация (GitHub Actions)

После настройки GitHub Actions релизы будут создаваться автоматически при создании тега.

### Как использовать:

1. Обновите версию в `version.py`
2. Закоммитьте и запушьте изменения:
   ```bash
   git add version.py
   git commit -m "Bump version to 1.0.1"
   git push
   ```
3. Создайте и запушьте тег:
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```
4. GitHub Actions автоматически:
   - Соберет приложение
   - Создаст инсталлятор
   - Создаст Release с прикрепленными файлами

## Публикация на GitHub Pages

### Вариант 1: Автоматическая публикация (рекомендуется)

GitHub Actions автоматически публикует сайт при пуше в `main` ветку.

### Вариант 2: Ручная публикация

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/ChatList.git
   cd ChatList
   ```

2. Скопируйте файлы сайта в папку `docs`:
   ```bash
   mkdir docs
   cp index.html docs/
   cp assets/ docs/ -r  # если есть дополнительные файлы
   ```

3. Закоммитьте и запушьте:
   ```bash
   git add docs/
   git commit -m "Add GitHub Pages site"
   git push
   ```

4. Включите GitHub Pages:
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / `docs`
   - Save

5. Сайт будет доступен по адресу:
   `https://yourusername.github.io/ChatList/`

## Структура файлов для GitHub Pages

```
ChatList/
├── docs/              # Файлы для GitHub Pages
│   ├── index.html     # Главная страница
│   └── assets/        # CSS, изображения и т.д.
├── .github/
│   └── workflows/
│       ├── release.yml    # Автоматическая сборка релизов
│       └── pages.yml      # Автоматическая публикация Pages
└── ...
```

## Проверка после публикации

1. **GitHub Release:**
   - Проверьте, что файлы загружены
   - Проверьте, что описание корректно
   - Проверьте ссылки на скачивание

2. **GitHub Pages:**
   - Откройте `https://yourusername.github.io/ChatList/`
   - Проверьте, что все ссылки работают
   - Проверьте отображение на мобильных устройствах

## Обновление сайта

После каждого релиза обновите информацию на сайте:
1. Откройте `docs/index.html`
2. Обновите версию в разделе "Download"
3. Обновите список изменений
4. Закоммитьте и запушьте изменения

## Troubleshooting

### GitHub Actions не запускается
- Проверьте, что файл `.github/workflows/release.yml` существует
- Проверьте синтаксис YAML файла
- Проверьте, что секреты настроены правильно

### Инсталлятор не создается
- Убедитесь, что Inno Setup установлен на GitHub Actions runner
- Проверьте путь к ISCC.exe в workflow файле
- Проверьте логи GitHub Actions для деталей ошибки

### GitHub Pages не обновляется
- Проверьте настройки Pages в Settings
- Убедитесь, что файлы в папке `docs/` или корневой ветке
- Подождите несколько минут (обновление может занять время)
