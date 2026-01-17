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
        
        # Проверяем, что файл действительно создался
        exe_path = os.path.join('dist', f'ChatList-{__version__}.exe')
        if not os.path.exists(exe_path):
            print(f"\n[ERROR] Файл не найден по пути: {exe_path}")
            # Показываем содержимое dist для отладки
            if os.path.exists('dist'):
                print("\nСодержимое директории dist:")
                for item in os.listdir('dist'):
                    item_path = os.path.join('dist', item)
                    if os.path.isfile(item_path):
                        print(f"  Файл: {item}")
                    elif os.path.isdir(item_path):
                        print(f"  Папка: {item}")
            return False
        
        print(f"\n[OK] Сборка завершена успешно!")
        print(f"Версия: {__version__}")
        print(f"Исполняемый файл: {exe_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Ошибка при сборке:")
        print(e.stderr)
        if e.stdout:
            print("Вывод PyInstaller:")
            print(e.stdout)
        return False
    except FileNotFoundError:
        print("\n[ERROR] PyInstaller не найден. Установите его:")
        print("pip install pyinstaller")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
