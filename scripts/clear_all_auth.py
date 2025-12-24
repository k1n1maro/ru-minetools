#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для полной очистки всех файлов авторизации
"""

import os

def clear_all_auth():
    """Удаляет все файлы авторизации"""
    files_to_remove = [
        "telegram_auth.json",
        "guest_access.json"
    ]
    
    removed_count = 0
    
    print("🧹 Очистка всех файлов авторизации...")
    print()
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                print(f"✅ Удален: {file_name}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Ошибка удаления {file_name}: {e}")
        else:
            print(f"⚪ Не найден: {file_name}")
    
    print()
    if removed_count > 0:
        print(f"🎉 Очистка завершена! Удалено файлов: {removed_count}")
        print("💡 Теперь при запуске программы потребуется новая авторизация")
    else:
        print("📝 Файлы авторизации не найдены - очистка не требуется")
    
    print()
    print("=" * 50)

if __name__ == "__main__":
    clear_all_auth()
    input("Нажмите Enter для выхода...")