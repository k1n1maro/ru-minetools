#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическое создание релизов v1.0.0 и v1.1.0 для RU-MINETOOLS
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, description=""):
    """Выполняет команду и показывает результат"""
    if description:
        print(f"🔧 {description}")
    
    print(f"💻 Команда: {command}")
    
    try:
        # Используем cp1251 для Windows консоли
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='cp1251')
        
        if result.returncode == 0:
            print(f"✅ Успешно")
            if result.stdout and result.stdout.strip():
                print(f"📄 Вывод: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Ошибка (код {result.returncode})")
            if result.stderr and result.stderr.strip():
                print(f"🚨 Ошибка: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def update_version(version):
    """Обновляет версию в конфигурации"""
    config_path = Path("config/update_config.py")
    
    if not config_path.exists():
        print(f"❌ Файл конфигурации не найден: {config_path}")
        return False
    
    # Читаем файл
    content = config_path.read_text(encoding='utf-8')
    
    # Заменяем версию
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('CURRENT_VERSION = '):
            lines[i] = f'CURRENT_VERSION = "{version}"'
            break
    
    # Записываем обратно
    config_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ Версия обновлена на {version}")
    return True

def build_version(version):
    """Собирает версию"""
    print(f"\n🔨 Сборка версии {version}")
    print("=" * 50)
    
    # Обновляем версию в конфигурации
    if not update_version(version):
        return False
    
    # Собираем EXE
    if not run_command("python scripts/build_simple_exe.py", f"Сборка EXE для версии {version}"):
        return False
    
    # Проверяем что файлы созданы
    exe_path = Path(f"releases/RU-MINETOOLS-v{version}.exe")
    zip_path = Path(f"releases/RU-MINETOOLS-v{version}.zip")
    
    if not exe_path.exists():
        print(f"❌ EXE файл не создан: {exe_path}")
        return False
    
    if not zip_path.exists():
        print(f"❌ ZIP файл не создан: {zip_path}")
        return False
    
    print(f"✅ Версия {version} собрана успешно")
    return True

def delete_existing_releases():
    """Удаляет существующие релизы"""
    print("\n🗑️ Удаление существующих релизов")
    print("=" * 40)
    
    # Проверяем существующие релизы
    result = subprocess.run("gh release list --repo k1n1maro/ru-minetools-test", 
                          shell=True, capture_output=True, text=True, encoding='cp1251')
    
    if result.returncode != 0:
        print("❌ Ошибка получения списка релизов")
        return False
    
    if "no releases found" in result.stdout:
        print("ℹ️ Релизов не найдено")
        return True
    
    # Удаляем v1.0.0
    run_command("gh release delete v1.0.0 --yes --repo k1n1maro/ru-minetools-test", 
                "Удаление релиза v1.0.0")
    
    # Удаляем v1.1.0
    run_command("gh release delete v1.1.0 --yes --repo k1n1maro/ru-minetools-test", 
                "Удаление релиза v1.1.0")
    
    print("✅ Старые релизы удалены")
    return True

def create_github_release(version, title, notes):
    """Создает релиз на GitHub"""
    print(f"\n📤 Загрузка релиза {version}")
    print("=" * 40)
    
    exe_file = f"releases/RU-MINETOOLS-v{version}.exe"
    zip_file = f"releases/RU-MINETOOLS-v{version}.zip"
    
    command = f'gh release create v{version} "{exe_file}" "{zip_file}" --title "{title}" --notes "{notes}" --repo k1n1maro/ru-minetools-test'
    
    if run_command(command, f"Создание релиза v{version}"):
        print(f"✅ Релиз v{version} создан успешно")
        return True
    else:
        print(f"❌ Ошибка создания релиза v{version}")
        return False

def main():
    """Основная функция"""
    print("🚀 АВТОМАТИЧЕСКОЕ СОЗДАНИЕ РЕЛИЗОВ RU-MINETOOLS")
    print("=" * 60)
    print("📦 Создаем версии: 1.0.0 и 1.1.0")
    print("🌐 Репозиторий: k1n1maro/ru-minetools-test")
    print("=" * 60)
    
    # Проверяем что мы в корне проекта
    if not Path("config/update_config.py").exists():
        print("❌ Запустите скрипт из корня проекта!")
        return
    
    # Проверяем наличие gh CLI
    result = subprocess.run("gh --version", shell=True, capture_output=True, encoding='cp1251')
    if result.returncode != 0:
        print("❌ GitHub CLI (gh) не установлен!")
        print("Установите: https://cli.github.com/")
        return
    
    try:
        # 1. Удаляем существующие релизы
        if not delete_existing_releases():
            print("❌ Ошибка удаления старых релизов")
            return
        
        # 2. Создаем иконки
        print("\n🎨 Создание иконок")
        print("=" * 30)
        if not run_command("python scripts/create_icons.py", "Создание высококачественных иконок"):
            print("⚠️ Ошибка создания иконок, продолжаем...")
        
        # 3. Собираем версию 1.0.0
        if not build_version("1.0.0"):
            print("❌ Ошибка сборки версии 1.0.0")
            return
        
        # 4. Собираем версию 1.1.0
        if not build_version("1.1.0"):
            print("❌ Ошибка сборки версии 1.1.0")
            return
        
        # 5. Создаем релиз v1.0.0
        notes_100 = """Базовая версия RU-MINETOOLS

✨ Возможности:
- ✅ Система авторизации
- ✅ Улучшенный переводчик
- ✅ Исключение синих названий модов
- ✅ Автоматические обновления
- ✅ Высококачественные иконки (из logow.PNG)

🔧 Иконки:
- Источник: logow.PNG (1024×1024)
- Размеры: 16×16, 32×32, 48×48, 64×64, 128×128, 256×256
- Четкие во всех размерах Windows

🎯 Для тестирования:
1. Запустите эту версию
2. Проверьте обновление до v1.1.0"""
        
        if not create_github_release("1.0.0", "RU-MINETOOLS v1.0.0", notes_100):
            print("❌ Ошибка создания релиза v1.0.0")
            return
        
        # 6. Создаем релиз v1.1.0
        notes_110 = """🔧 ИСПРАВЛЕНИЯ СИСТЕМЫ ОБНОВЛЕНИЙ:

✅ Принудительное завершение старых процессов
✅ Гарантированное удаление старых версий
✅ Улучшенный batch скрипт с taskkill
✅ Высококачественные иконки (из logow.PNG)

🔄 Как работает обновление:
1. Программа показывает диалог
2. Запускается зеленое консольное окно
3. Программа закрывается через 2 секунды
4. Скрипт принудительно завершает все процессы ru-minetools
5. Удаляет старые версии с помощью del /f /q
6. Запускает новую версию
7. Ждет нажатия клавиши

🎨 Качество иконок:
- Источник: logow.PNG (1024×1024)
- Размер ICO: ~117 KB (высокое качество)
- Все размеры в одном файле

⚠️ ВАЖНО: НЕ ЗАКРЫВАЙТЕ зеленое консольное окно!"""
        
        if not create_github_release("1.1.0", "RU-MINETOOLS v1.1.0 - ИСПРАВЛЕНИЯ", notes_110):
            print("❌ Ошибка создания релиза v1.1.0")
            return
        
        # 7. Показываем результат
        print("\n🎉 ВСЕ РЕЛИЗЫ СОЗДАНЫ УСПЕШНО!")
        print("=" * 50)
        print("📦 Созданные релизы:")
        print("  🔹 v1.0.0 - Базовая версия")
        print("  🔹 v1.1.0 - Исправленная версия")
        print()
        print("🌐 Ссылки:")
        print("  📄 v1.0.0: https://github.com/k1n1maro/ru-minetools-test/releases/tag/v1.0.0")
        print("  📄 v1.1.0: https://github.com/k1n1maro/ru-minetools-test/releases/tag/v1.1.0")
        print()
        print("🧪 Тестирование:")
        print("  1. Скачайте v1.0.0")
        print("  2. Запустите и проверьте обновление до v1.1.0")
        print("  3. Убедитесь что старая версия удаляется")
        print()
        print("✅ Готово к тестированию!")
        
    except KeyboardInterrupt:
        print("\n❌ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()