#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для очистки проекта от временных файлов и мусора
"""

import os
import shutil
from pathlib import Path

def clean_project():
    """Очищает проект от временных файлов"""
    print("🧹 Очистка проекта RU-MINETOOLS...")
    
    # Файлы и папки для удаления
    patterns_to_remove = [
        # Python кэш
        "__pycache__",
        "*.pyc",
        "*.pyo", 
        "*.pyd",
        
        # Логи
        "*.log",
        "ru_minetools_errors.log",
        "src/*.log",
        
        # Кэш переводов
        "translation_cache.pkl",
        "translation_cache_optimized.db",
        "src/translation_cache.pkl",
        "src/translation_cache_optimized.db",
        
        # Временные файлы авторизации
        "telegram_auth.json",
        "src/telegram_auth.json",
        
        # Временные файлы обновлений
        "update_ru_minetools.bat",
        "*.backup",
        "test_write_access.tmp",
        
        # Тестовые файлы
        "test_*.py",
        "*_test.py",
        "*_fix.py",
        "temp_*.py",
        "debug_*.py",
        
        # Сборка PyInstaller
        "build",
        "dist", 
        "*.spec",
        
        # Временные папки релизов
        "releases/temp_*",
    ]
    
    removed_count = 0
    
    # Удаляем файлы и папки
    for pattern in patterns_to_remove:
        if "*" in pattern:
            # Glob pattern
            for file_path in Path(".").rglob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"🗑️  Удален файл: {file_path}")
                        removed_count += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        print(f"🗑️  Удалена папка: {file_path}")
                        removed_count += 1
                except Exception as e:
                    print(f"⚠️  Не удалось удалить {file_path}: {e}")
        else:
            # Точное имя
            for file_path in Path(".").rglob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        print(f"🗑️  Удален файл: {file_path}")
                        removed_count += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        print(f"🗑️  Удалена папка: {file_path}")
                        removed_count += 1
                except Exception as e:
                    print(f"⚠️  Не удалось удалить {file_path}: {e}")
    
    print(f"\n✅ Очистка завершена! Удалено элементов: {removed_count}")
    
    # Показываем финальную структуру
    print("\n📁 Структура проекта после очистки:")
    important_dirs = ["src", "assets", "config", "scripts", "docs", "releases"]
    for dir_name in important_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            files = list(dir_path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            print(f"  📁 {dir_name}/ - {file_count} файлов")
    
    print(f"\n📊 Критически важные файлы:")
    critical_files = [
        "src/modern_gui_interface.py",
        "src/utils.py",
        "assets/sans3.ttf", 
        "assets/logo.png",
        "config/update_config.py",
        "run.py"
    ]
    for file_path in critical_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - ОТСУТСТВУЕТ!")
    
    print(f"\n💡 Для проверки целостности запустите: python -c \"exec(open('CRITICAL_FILES.md').read().split('```bash')[1].split('```')[0])\"")
    print(f"📖 Подробнее о важных файлах: CRITICAL_FILES.md")

if __name__ == "__main__":
    clean_project()