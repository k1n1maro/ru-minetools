#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный скрипт для создания EXE файлов разных версий
Без автоматической загрузки на GitHub
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def create_version_config(version):
    """Создает конфигурацию для конкретной версии"""
    config_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация системы обновлений для RU-MINETOOLS
"""

# Основные настройки репозитория
GITHUB_REPO = "k1n1maro/ru-minetools-test"
GITHUB_API_URL = f"https://api.github.com/repos/{{GITHUB_REPO}}/releases/latest"

# Текущая версия приложения
CURRENT_VERSION = "{version}"

# Интервал автоматической проверки обновлений (в миллисекундах)
UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000  # 24 часа

# Настройки обновлений
UPDATE_SETTINGS = {{
    "auto_check": True,
    "check_interval": UPDATE_CHECK_INTERVAL,
    "silent_check": True,
    "backup_enabled": True,
    "restart_after_update": True,
}}

# Файлы, которые нужно исключить из обновления
EXCLUDE_FROM_UPDATE = [
    "config.json",
    "user_data.json", 
    "*.log",
    "cache/",
]

# Обязательные файлы для проверки целостности
REQUIRED_FILES = [
    "modern_gui_interface.py",
    "modern_updater.py",
]

def validate_config():
    """Проверяет корректность конфигурации"""
    errors = []
    
    if not GITHUB_REPO or GITHUB_REPO == "your-username/ru-minetools":
        errors.append("GITHUB_REPO не настроен")
    
    if not CURRENT_VERSION:
        errors.append("CURRENT_VERSION не указана")
    
    if UPDATE_CHECK_INTERVAL < 60000:
        errors.append("UPDATE_CHECK_INTERVAL слишком мал")
    
    return errors

if __name__ == "__main__":
    print("🔧 Проверка конфигурации обновлений...")
    errors = validate_config()
    
    if errors:
        print("❌ Найдены ошибки в конфигурации:")
        for error in errors:
            print(f"  • {{error}}")
        print("\\n📝 Отредактируйте файл config/update_config.py")
    else:
        print("✅ Конфигурация корректна")
        print(f"📦 Репозиторий: {{GITHUB_REPO}}")
        print(f"🏷️ Текущая версия: {{CURRENT_VERSION}}")
        print(f"🔄 Интервал проверки: {{UPDATE_CHECK_INTERVAL // (60 * 60 * 1000)}} часов")
'''
    return config_content

def build_exe_version(version):
    """Собирает EXE файл для конкретной версии"""
    print(f"🔨 Сборка EXE для версии {version}...")
    
    # Сохраняем оригинальный конфиг
    original_config = None
    config_path = Path("update_config.py")
    if config_path.exists():
        original_config = config_path.read_text(encoding='utf-8')
    
    try:
        # Создаем конфигурацию для этой версии
        config_path.write_text(create_version_config(version), encoding='utf-8')
        
        # Команда для PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed", 
            "--name", f"ru-minetools-v{version}",
            "--clean"
        ]
        
        # Добавляем иконку если есть
        if Path("logo.png").exists():
            cmd.extend(["--icon", "logo.png"])
        
        # Добавляем ресурсы из assets
        for file_path in Path("assets").glob("*"):
            if file_path.is_file():
                cmd.extend(["--add-data", f"{file_path};assets"])
        
        # Добавляем конфигурацию
        for file_path in Path("config").glob("*"):
            if file_path.is_file():
                cmd.extend(["--add-data", f"{file_path};config"])
        
        # Добавляем src модули
        cmd.extend(["--add-data", "src;src"])
        
        # Добавляем остальные ресурсы
        resources = ["*.png", "*.jpg", "*.ttf", "*.json"]
        for resource in resources:
            for file_path in Path("assets").glob(resource):
                if file_path.is_file():
                    cmd.extend(["--add-data", f"{file_path};."])
        
        # Добавляем скрытые импорты
        hidden_imports = ["translatepy", "requests", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets"]
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # Основной файл
        cmd.append("src/modern_gui_interface.py")
        
        print(f"📦 Запуск PyInstaller...")
        print(f"🔧 Команда: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ошибка сборки:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return None
        
        # Ищем созданный EXE файл
        exe_path = Path("dist") / f"ru-minetools-v{version}.exe"
        if not exe_path.exists():
            print(f"❌ EXE файл не найден: {exe_path}")
            return None
        
        # Копируем EXE в корневую папку
        final_exe_path = Path(f"ru-minetools-v{version}.exe")
        shutil.copy2(exe_path, final_exe_path)
        
        print(f"✅ EXE создан: {final_exe_path}")
        print(f"📏 Размер: {final_exe_path.stat().st_size / (1024*1024):.1f} МБ")
        
        return final_exe_path
        
    except Exception as e:
        print(f"❌ Ошибка сборки версии {version}: {e}")
        return None
    
    finally:
        # Восстанавливаем оригинальный конфиг
        if original_config:
            config_path.write_text(original_config, encoding='utf-8')
        
        # Очищаем временные файлы PyInstaller
        for cleanup_dir in ["build", "dist", "__pycache__"]:
            if Path(cleanup_dir).exists():
                shutil.rmtree(cleanup_dir, ignore_errors=True)
        
        # Удаляем .spec файл
        spec_file = Path(f"ru-minetools-v{version}.spec")
        if spec_file.exists():
            spec_file.unlink()

def create_release_zip(version, exe_path):
    """Создает ZIP архив для релиза"""
    zip_path = Path(f"ru-minetools-v{version}.zip")
    
    print(f"📦 Создание ZIP архива для версии {version}...")
    
    # Создаем временную папку для архива
    temp_dir = Path(f"temp_release_v{version}")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    try:
        # Копируем EXE в папку релиза
        release_exe_path = temp_dir / f"ru-minetools-v{version}.exe"
        shutil.copy2(exe_path, release_exe_path)
        
        # Создаем README для релиза
        readme_content = f"""# RU-MINETOOLS v{version}

## 🚀 Установка
1. Скачайте файл `ru-minetools-v{version}.exe`
2. Запустите программу
3. Наслаждайтесь переводом модов!

## 🔄 Обновления
Программа автоматически проверяет обновления при запуске.
При наличии новой версии появится уведомление.

## 📝 Изменения в версии {version}
- Система автоматических обновлений
- Улучшенный интерфейс в стиле приложения
- Исправления ошибок

## 💜 Поддержка проекта
Если программа вам нравится, поддержите разработку!

## 🔧 Технические детали
- Версия: {version}
- Репозиторий обновлений: k1n1maro/ru-minetools-test
- Автоматическая проверка обновлений: включена
"""
        
        readme_path = temp_dir / "README.md"
        readme_path.write_text(readme_content, encoding='utf-8')
        
        # Создаем ZIP архив
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', temp_dir)
        
        print(f"✅ ZIP создан: {zip_path}")
        print(f"📏 Размер: {zip_path.stat().st_size / (1024*1024):.1f} МБ")
        
        return zip_path
        
    except Exception as e:
        print(f"❌ Ошибка создания ZIP: {e}")
        return None
    
    finally:
        # Очищаем временную папку
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    """Основная функция"""
    print("Простая сборка EXE релизов для тестирования обновлений")
    print("=" * 65)
    
    # Проверяем наличие PyInstaller
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                              capture_output=True, check=True, text=True)
        print(f"PyInstaller найден: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("PyInstaller не установлен!")
        print("Установите: pip install pyinstaller")
        return
    
    # Проверяем наличие основных файлов
    required_files = ["modern_gui_interface.py", "modern_updater.py", "update_config.py"]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"Не найден файл: {file_path}")
            return
    
    print("Все необходимые файлы найдены")
    
    versions = ["1.0.0", "1.1.0"]
    successful_builds = []
    
    for version in versions:
        print(f"\n🔨 Обработка версии {version}")
        print("-" * 40)
        
        # Собираем EXE
        exe_path = build_exe_version(version)
        if not exe_path:
            print(f"❌ Не удалось собрать EXE для версии {version}")
            continue
        
        # Создаем ZIP
        zip_path = create_release_zip(version, exe_path)
        if not zip_path:
            print(f"❌ Не удалось создать ZIP для версии {version}")
            continue
        
        successful_builds.append((version, exe_path, zip_path))
        print(f"✅ Версия {version} готова!")
    
    print("\n🎉 Сборка завершена!")
    print("=" * 40)
    
    if successful_builds:
        print("📦 Созданные файлы:")
        for version, exe_path, zip_path in successful_builds:
            print(f"  v{version}:")
            print(f"    📄 EXE: {exe_path}")
            print(f"    📦 ZIP: {zip_path}")
        
        print("\n📋 Следующие шаги:")
        print("1. Загрузите ZIP файлы в релизы GitHub вручную:")
        print("   https://github.com/k1n1maro/ru-minetools-test/releases")
        print("2. Скачайте ru-minetools-v1.0.0.exe из релиза")
        print("3. Запустите программу")
        print("4. Проверьте автоматическое обнаружение обновления до v1.1.0")
        print("5. Протестируйте процесс обновления")
        
        print("\n💡 Для автоматической загрузки используйте build_exe_releases.py с GitHub CLI")
    else:
        print("❌ Не удалось создать ни одного релиза")

if __name__ == "__main__":
    main()