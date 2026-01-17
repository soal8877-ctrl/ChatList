"""Скрипт для сборки приложения с использованием версии из version.py"""
import subprocess
import sys
import os
from version import __version__

def build_exe():
    """Сборка исполняемого файла с версией в имени"""
    print(f"Сборка ChatList v{__version__}...")
    
    # Команда PyInstaller с версией в имени
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        f'--name=ChatList-{__version__}',
        '--icon=app.ico',
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"\n[OK] Сборка завершена успешно!")
        print(f"Версия: {__version__}")
        print(f"Исполняемый файл: dist\\ChatList-{__version__}.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Ошибка при сборке:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("\n[ERROR] PyInstaller не найден. Установите его:")
        print("pip install pyinstaller")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
