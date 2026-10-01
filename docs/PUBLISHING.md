# Публикация ChatList на GitHub Release и GitHub Pages

Пошаговая инструкция для репозитория: **https://github.com/soal8877-ctrl/ChatList**

---

## Что уже подготовлено в проекте

| Файл / папка | Назначение |
|--------------|------------|
| `version.py` | Единственный источник номера версии (`__version__`) |
| `build.py` | Сборка `ChatList.exe` и установщика Inno Setup |
| `installer.iss` | Скрипт установщика (с секцией удаления) |
| `release.ps1` | Локальная подготовка артефактов и checksums |
| `.github/workflows/release.yml` | CI: сборка и публикация Release по тегу |
| `.github/workflows/pages.yml` | CI: публикация лендинга на GitHub Pages |
| `docs/index.html` | HTML-лендинг |
| `.github/release-notes/TEMPLATE.md` | Шаблон текста Release |
| `.github/release-notes/v1.0.0.md` | Текст для релиза 1.0.0 |

**Сайт после включения Pages:** https://soal8877-ctrl.github.io/ChatList/

---

## Часть 1. Подготовка нового релиза

### Шаг 1. Обновите версию

Откройте `version.py` и измените версию:

```python
__version__ = "1.0.0"
```

> Менять номер версии в других файлах **не нужно** — `build.py`, установщик и workflows читают `version.py`.

### Шаг 2. Обновите лендинг (опционально)

В `docs/index.html` обновите строку с версией:

```html
<span class="version">v1.0.0 · Windows</span>
```

### Шаг 3. Подготовьте текст Release Notes

1. Скопируйте `.github/release-notes/TEMPLATE.md` → `.github/release-notes/vX.Y.Z.md`
2. Замените `{{VERSION}}` на номер версии
3. Заполните раздел «Что нового»

Для релиза **1.0.0** уже есть готовый файл: `.github/release-notes/v1.0.0.md`

### Шаг 4. Прогоните тесты

```powershell
cd C:\Cursor\ChatList
.\.venv\Scripts\Activate.ps1
python -m unittest test_smoke.py test_prompt_assistant.py -v
```

### Шаг 5. Соберите артефакты локально

```powershell
python .\build.py
python .\release.ps1
```

В папке `dist\` появятся:

- `ChatList.exe`
- `ChatList-1.0.0-setup.exe`
- `ChatList-setup.exe` (алиас для ссылки `/releases/latest/download/`)
- `SHA256SUMS.txt`

Проверьте установщик вручную на своём ПК.

### Шаг 6. Закоммитьте изменения

```powershell
git add .
git commit -m "Релиз 1.0.0"
git push origin main
```

---

## Часть 2. GitHub Release

### Способ A — автоматически (рекомендуется)

Workflow `.github/workflows/release.yml` собирает и публикует Release при push тега.

```powershell
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions:

1. Соберёт exe и установщик на Windows
2. Создаст Release с тегом `v1.0.0`
3. Загрузит файлы из `dist\`

> Тег должен совпадать с версией: `v` + `version.__version__` → `v1.0.0`

### Способ B — вручную через GitHub

1. Откройте **Releases → Draft a new release**
2. **Choose a tag:** `v1.0.0` → Create new tag
3. **Release title:** `ChatList 1.0.0`
4. **Description:** вставьте текст из `.github/release-notes/v1.0.0.md`
5. Перетащите файлы из `dist\`:
   - `ChatList-setup.exe`
   - `ChatList-1.0.0-setup.exe`
   - `ChatList.exe`
   - `SHA256SUMS.txt`
6. Нажмите **Publish release**

### Способ C — через GitHub CLI

```powershell
gh release create v1.0.0 `
  --title "ChatList 1.0.0" `
  --notes-file .github\release-notes\v1.0.0.md `
  dist\ChatList-setup.exe `
  dist\ChatList-1.0.0-setup.exe `
  dist\ChatList.exe `
  dist\SHA256SUMS.txt
```

---

## Часть 3. GitHub Pages (лендинг)

### Первоначальная настройка (один раз)

1. Откройте репозиторий на GitHub
2. **Settings → Pages**
3. **Build and deployment → Source:** `GitHub Actions`
4. Сохраните

Workflow `.github/workflows/pages.yml` публикует содержимое папки `docs/` при push в `main`.

### Обновление лендинга

```powershell
# отредактируйте docs/index.html
git add docs\index.html
git commit -m "Обновить лендинг"
git push origin main
```

Через 1–2 минуты сайт обновится: https://soal8877-ctrl.github.io/ChatList/

### Проверка локально

Откройте `docs\index.html` двойным щелчком в браузере или:

```powershell
Start-Process .\docs\index.html
```

---

## Часть 4. Чек-лист перед публикацией

- [ ] Версия в `version.py` обновлена
- [ ] Тесты проходят
- [ ] `python .\build.py` завершился без ошибок
- [ ] Установщик протестирован вручную
- [ ] Release notes подготовлены (`.github/release-notes/vX.Y.Z.md`)
- [ ] Лендинг `docs/index.html` актуален
- [ ] Тег `vX.Y.Z` создан и запушен
- [ ] Release опубликован, файлы загружены
- [ ] GitHub Pages показывает лендинг
- [ ] Ссылка «Скачать установщик» на лендинге работает

---

## Часть 5. Ссылки после публикации

| Ресурс | URL |
|--------|-----|
| Репозиторий | https://github.com/soal8877-ctrl/ChatList |
| Releases | https://github.com/soal8877-ctrl/ChatList/releases |
| Последний установщик | https://github.com/soal8877-ctrl/ChatList/releases/latest/download/ChatList-setup.exe |
| GitHub Pages | https://soal8877-ctrl.github.io/ChatList/ |

---

## Часть 6. Следующие релизы (кратко)

```powershell
# 1. version.py → "1.1.0"
# 2. docs/index.html → v1.1.0
# 3. .github/release-notes/v1.1.0.md
python -m unittest test_smoke.py test_prompt_assistant.py -v
python .\build.py
git add .
git commit -m "Релиз 1.1.0"
git push origin main
git tag v1.1.0
git push origin v1.1.0
```

---

## Устранение проблем

### Release workflow не запускается

- Проверьте формат тега: `v1.0.0`, не `1.0.0`
- Тег должен быть запушен: `git push origin v1.0.0`

### Pages не обновляется

- **Settings → Pages → Source** = GitHub Actions
- Проверьте вкладку **Actions** — workflow `Deploy GitHub Pages`

### Ссылка «Скачать» не работает

- В Release должен быть файл **`ChatList-setup.exe`** (без версии в имени)
- Скрипт `release.ps1` создаёт этот алиас автоматически

### Inno Setup не найден локально

Установите [Inno Setup 6](https://jrsoftware.org/isinfo.php) или используйте только CI (push тега).
