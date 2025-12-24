#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания двух версий EXE файлов для тестирования системы обновлений
Версия 1.0.0 - базовая
Версия 1.1.0 - с отличительной чертой (NEW в заголовке)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import json

def backup_original_files():
    """Создает резервные копии оригинальных файлов"""
    files_to_backup = [
        "config/update_config.py",
        "src/modern_gui_interface.py"
    ]
    
    for file_path in files_to_backup:
        if Path(file_path).exists():
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            print(f"📋 Создана резервная копия: {backup_path}")

def restore_original_files():
    """Восстанавливает оригинальные файлы из резервных копий"""
    files_to_restore = [
        "config/update_config.py",
        "src/modern_gui_interface.py"
    ]
    
    for file_path in files_to_restore:
        backup_path = f"{file_path}.backup"
        if Path(backup_path).exists():
            shutil.copy2(backup_path, file_path)
            Path(backup_path).unlink()
            print(f"🔄 Восстановлен файл: {file_path}")

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
    "auto_check": True,  # Автоматическая проверка при запуске
    "check_interval": UPDATE_CHECK_INTERVAL,
    "silent_check": False,  # Показываем уведомления для тестирования
    "backup_enabled": True,  # Создавать резервную копию перед обновлением
    "restart_after_update": True,  # Перезапускать приложение после обновления
}}

# Файлы, которые нужно исключить из обновления (сохранить пользовательские данные)
EXCLUDE_FROM_UPDATE = [
    "config.json",  # Конфигурация пользователя
    "user_data.json",  # Пользовательские данные
    "*.log",  # Лог файлы
    "cache/",  # Кэш
]

# Обязательные файлы для проверки целостности
REQUIRED_FILES = [
    "modern_gui_interface.py",  # Основной файл приложения
    "modern_updater.py",  # Система обновлений
]

def validate_config():
    """Проверяет корректность конфигурации"""
    errors = []
    
    if not GITHUB_REPO or GITHUB_REPO == "your-username/ru-minetools":
        errors.append("GITHUB_REPO не настроен")
    
    if not CURRENT_VERSION:
        errors.append("CURRENT_VERSION не указана")
    
    if UPDATE_CHECK_INTERVAL < 60000:  # Минимум 1 минута
        errors.append("UPDATE_CHECK_INTERVAL слишком мал")
    
    return errors

if __name__ == "__main__":
    print("🔧 Проверка конфигурации обновлений...")
    errors = validate_config()
    
    if errors:
        print("❌ Найдены ошибки в конфигурации:")
        for error in errors:
            print(f"  • {{error}}")
        print("\\n📝 Отредактируйте файл update_config.py")
    else:
        print("✅ Конфигурация корректна")
        print(f"📦 Репозиторий: {{GITHUB_REPO}}")
        print(f"🏷️ Текущая версия: {{CURRENT_VERSION}}")
        print(f"🔄 Интервал проверки: {{UPDATE_CHECK_INTERVAL // (60 * 60 * 1000)}} часов")
'''
    return config_content

def modify_interface_for_version(version):
    """Модифицирует интерфейс для конкретной версии"""
    interface_file = Path("src/modern_gui_interface.py")
    
    if not interface_file.exists():
        print(f"❌ Файл {interface_file} не найден")
        return False
    
    # Читаем содержимое файла
    content = interface_file.read_text(encoding='utf-8')
    
    if version == "1.1.0":
        # Для версии 1.1.0 добавляем "NEW" в заголовок
        content = content.replace(
            'self.setWindowTitle("RU-MINETOOLS")',
            'self.setWindowTitle("RU-MINETOOLS NEW")'
        )
        
        # Также изменяем заголовки в диалогах
        content = content.replace(
            'title_label = QLabel("RU-MINETOOLS")',
            'title_label = QLabel("RU-MINETOOLS NEW")'
        )
        
        print(f"✨ Добавлена отличительная черта для версии {version}: NEW в заголовке")
    
    # Записываем изменения
    interface_file.write_text(content, encoding='utf-8')
    return True

def build_exe_version(version):
    """Собирает EXE файл для конкретной версии"""
    print(f"🔨 Сборка EXE для версии {version}...")
    
    try:
        # Обновляем конфигурацию версии
        config_path = Path("config/update_config.py")
        config_path.write_text(create_version_config(version), encoding='utf-8')
        
        # Модифицируем интерфейс для версии
        if not modify_interface_for_version(version):
            return None
        
        # Команда для PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed", 
            "--name", f"ru-minetools-v{version}",
            "--clean",
            "--distpath", "dist",
            "--workpath", "build"
        ]
        
        # Добавляем иконку если есть
        icon_paths = ["assets/icons/app_icon.ico", "assets/logo.png", "logo.png"]
        for icon_path in icon_paths:
            if Path(icon_path).exists():
                cmd.extend(["--icon", icon_path])
                break
        
        # Добавляем все файлы из assets
        assets_path = Path("assets")
        if assets_path.exists():
            for file_path in assets_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(assets_path)
                    cmd.extend(["--add-data", f"{file_path};assets/{relative_path.parent}"])
        
        # Добавляем конфигурацию
        config_path = Path("config")
        if config_path.exists():
            for file_path in config_path.glob("*"):
                if file_path.is_file() and not file_path.name.endswith('.example.json'):
                    cmd.extend(["--add-data", f"{file_path};config"])
        
        # Добавляем src модули
        src_path = Path("src")
        if src_path.exists():
            for file_path in src_path.glob("*.py"):
                if file_path.name != "modern_gui_interface.py":  # Основной файл добавится автоматически
                    cmd.extend(["--add-data", f"{file_path};src"])
        
        # Добавляем скрытые импорты
        hidden_imports = [
            "translatepy", "requests", "PyQt6.QtCore", "PyQt6.QtGui", 
            "PyQt6.QtWidgets", "sqlite3", "json", "pathlib", "threading",
            "concurrent.futures", "datetime", "shutil", "zipfile"
        ]
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # Основной файл
        cmd.append("src/modern_gui_interface.py")
        
        print(f"📦 Запуск PyInstaller для версии {version}...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print(f"❌ Ошибка сборки версии {version}:")
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
        import traceback
        traceback.print_exc()
        return None

def cleanup_build_files():
    """Очищает временные файлы сборки"""
    cleanup_dirs = ["build", "dist", "__pycache__"]
    for cleanup_dir in cleanup_dirs:
        if Path(cleanup_dir).exists():
            shutil.rmtree(cleanup_dir, ignore_errors=True)
    
    # Удаляем .spec файлы
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()

def main():
    """Основная функция"""
    print("🚀 Создание двух версий EXE для тестирования системы обновлений")
    print("=" * 70)
    
    # Проверяем наличие PyInstaller
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                              capture_output=True, check=True, text=True)
        print(f"✅ PyInstaller найден: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("❌ PyInstaller не установлен!")
        print("Установите: pip install pyinstaller")
        return
    
    # Проверяем наличие основных файлов
    required_files = [
        "src/modern_gui_interface.py", 
        "config/update_config.py"
    ]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Не найден файл: {file_path}")
            return
    
    print("✅ Все необходимые файлы найдены")
    
    # Создаем резервные копии
    backup_original_files()
    
    versions = ["1.0.0", "1.1.0"]
    successful_builds = []
    
    try:
        for version in versions:
            print(f"\\n🔨 Обработка версии {version}")
            print("-" * 40)
            
            # Очищаем предыдущие файлы сборки
            cleanup_build_files()
            
            # Собираем EXE
            exe_path = build_exe_version(version)
            if exe_path:
                successful_builds.append((version, exe_path))
                print(f"✅ Версия {version} готова!")
            else:
                print(f"❌ Не удалось собрать EXE для версии {version}")
            
            # Восстанавливаем оригинальные файлы перед следующей сборкой
            restore_original_files()
    
    finally:
        # Финальная очистка
        cleanup_build_files()
        
        # Убеждаемся, что оригинальные файлы восстановлены
        restore_original_files()
    
    print("\\n🎉 Сборка завершена!")
    print("=" * 40)
    
    if successful_builds:
        print("📦 Созданные файлы:")
        for version, exe_path in successful_builds:
            print(f"  ✅ v{version}: {exe_path}")
        
        print("\\n📋 Следующие шаги:")
        print("1. Загрузите EXE файлы на GitHub:")
        print("   - Создайте релиз v1.0.0 и загрузите ru-minetools-v1.0.0.exe")
        print("   - Создайте релиз v1.1.0 и загрузите ru-minetools-v1.1.0.exe")
        print("2. Скачайте ru-minetools-v1.0.0.exe из релиза")
        print("3. Запустите программу")
        print("4. Проверьте автоматическое обнаружение обновления до v1.1.0")
        print("5. Протестируйте процесс обновления")
        print("\\n💡 В версии 1.1.0 в заголовке окна будет 'RU-MINETOOLS NEW'")
    else:
        print("❌ Не удалось создать ни одного релиза")

if __name__ == "__main__":
    main()