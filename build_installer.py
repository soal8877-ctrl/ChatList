"""Скрипт для автоматической сборки инсталлятора с помощью Inno Setup"""
import subprocess
import sys
import os
from pathlib import Path

def find_inno_setup():
    """Поиск Inno Setup Compiler"""
    # Стандартные пути установки Inno Setup
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def build_installer():
    """Сборка инсталлятора"""
    print("Поиск Inno Setup Compiler...")
    
    iscc_path = find_inno_setup()
    
    if not iscc_path:
        print("\n[ERROR] Inno Setup Compiler не найден!")
        print("\nПожалуйста, установите Inno Setup:")
        print("1. Скачайте с https://jrsoftware.org/isdl.php")
        print("2. Установите Inno Setup")
        print("3. Запустите этот скрипт снова")
        print("\nИли используйте Inno Setup Compiler вручную:")
        print("  - Откройте installer.iss в Inno Setup Compiler")
        print("  - Нажмите Build -> Compile")
        return False
    
    print(f"Найден: {iscc_path}")
    
    installer_script = Path(__file__).parent / "installer.iss"
    
    if not installer_script.exists():
        print(f"\n[ERROR] Файл {installer_script} не найден!")
        return False
    
    # Проверка наличия исполняемого файла
    exe_file = Path(__file__).parent / "dist" / "ChatList-1.0.0.exe"
    if not exe_file.exists():
        print(f"\n[WARNING] Исполняемый файл {exe_file} не найден!")
        print("Сначала выполните сборку приложения:")
        print("  python build.py")
        response = input("\nПродолжить сборку инсталлятора? (y/n): ")
        if response.lower() != 'y':
            return False
    
    print(f"\nКомпиляция инсталлятора из {installer_script}...")
    
    try:
        cmd = [iscc_path, str(installer_script)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("\n" + result.stdout)
        print(f"\n[OK] Инсталлятор успешно создан!")
        print(f"Файл: dist\\ChatList-Setup-1.0.0.exe")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Ошибка при компиляции инсталлятора:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"\n[ERROR] Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)
