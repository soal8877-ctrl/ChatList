"""Скрипт для обновления версии во всех файлах проекта"""
import re
import sys
from pathlib import Path


def update_version_in_file(file_path: Path, pattern: str, replacement: str):
    """Обновление версии в файле"""
    try:
        content = file_path.read_text(encoding='utf-8')
        new_content = re.sub(pattern, replacement, content)
        
        if content != new_content:
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✓ Обновлен: {file_path}")
            return True
        else:
            print(f"- Без изменений: {file_path}")
            return False
    except Exception as e:
        print(f"✗ Ошибка в {file_path}: {e}")
        return False


def update_version(new_version: str):
    """Обновление версии во всех файлах"""
    from version import __version__ as current_version
    
    print(f"Текущая версия: {current_version}")
    print(f"Новая версия: {new_version}")
    print()
    
    # Обновляем version.py
    version_file = Path("version.py")
    version_file.write_text(
        f'"""Версия приложения ChatList"""\n\n__version__ = "{new_version}"\n',
        encoding='utf-8'
    )
    print(f"✓ Обновлен: version.py")
    
    # Обновляем docs/index.html
    html_file = Path("docs/index.html")
    if html_file.exists():
        content = html_file.read_text(encoding='utf-8')
        # Заменяем версию в badge
        content = re.sub(
            r'<span class="version-badge">v\d+\.\d+\.\d+</span>',
            f'<span class="version-badge">v{new_version}</span>',
            content
        )
        # Заменяем версию в ссылках на скачивание
        content = re.sub(
            r'ChatList-Setup-\d+\.\d+\.\d+\.exe',
            f'ChatList-Setup-{new_version}.exe',
            content
        )
        content = re.sub(
            r'ChatList-\d+\.\d+\.\d+\.exe',
            f'ChatList-{new_version}.exe',
            content
        )
        # Заменяем версию в тексте
        content = re.sub(
            r'Последняя версия: <strong>\d+\.\d+\.\d+</strong>',
            f'Последняя версия: <strong>{new_version}</strong>',
            content
        )
        html_file.write_text(content, encoding='utf-8')
        print(f"✓ Обновлен: docs/index.html")
    
    # Обновляем CHANGELOG.md (добавляем новую секцию)
    changelog_file = Path("CHANGELOG.md")
    if changelog_file.exists():
        content = changelog_file.read_text(encoding='utf-8')
        # Проверяем, есть ли уже запись для этой версии
        if f"[{new_version}]" not in content:
            # Добавляем новую секцию после заголовка
            header = "# Changelog\n\n"
            if content.startswith(header):
                new_section = f"## [{new_version}] - {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}\n\n### Добавлено\n- \n\n### Изменено\n- \n\n### Исправлено\n- \n\n"
                content = header + new_section + content[len(header):]
                changelog_file.write_text(content, encoding='utf-8')
                print(f"✓ Обновлен: CHANGELOG.md")
    
    print()
    print("✓ Версия обновлена во всех файлах!")
    print()
    print("Следующие шаги:")
    print(f"1. git add .")
    print(f"2. git commit -m 'Bump version to {new_version}'")
    print(f"3. git tag -a v{new_version} -m 'Release version {new_version}'")
    print(f"4. git push origin main")
    print(f"5. git push origin v{new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Использование: python update_version.py <новая_версия>")
        print("Пример: python update_version.py 1.0.1")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    # Проверка формата версии
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("Ошибка: версия должна быть в формате X.Y.Z (например, 1.0.1)")
        sys.exit(1)
    
    update_version(new_version)
