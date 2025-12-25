#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ИСПРАВЛЕННЫЙ скрипт для создания EXE файлов с правильными импортами
Включает все необходимые модули для работы программы
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
GITHUB_REPO = "k1n1maro/ru-minetools"
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
        print("\\n📝 Отредактируйте файл update_config.py")
    else:
        print("✅ Конфигурация корректна")
        print(f"📦 Репозиторий: {{GITHUB_REPO}}")
        print(f"🏷️ Текущая версия: {{CURRENT_VERSION}}")
        print(f"🔄 Интервал проверки: {{UPDATE_CHECK_INTERVAL // (60 * 60 * 1000)}} часов")
'''
    return config_content

def build_exe_version(version):
    """Собирает EXE файл для конкретной версии с правильными импортами"""
    print(f"🔨 Сборка EXE для версии {version}...")
    
    # Сохраняем оригинальный конфиг
    original_config = None
    config_path = Path("config/update_config.py")
    if config_path.exists():
        original_config = config_path.read_text(encoding='utf-8')
    
    try:
        # Создаем конфигурацию для этой версии
        config_path.write_text(create_version_config(version), encoding='utf-8')
        
        # Команда для PyInstaller с правильными импортами
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed", 
            "--name", f"ru-minetools-v{version}",
            "--clean",
            "--distpath", "dist",
            "--workpath", "build"
        ]
        
        # Добавляем иконку
        icon_paths = [
            "assets/icons/app_icon.ico",
            "assets/icons/icon.ico", 
            "assets/icons/simple_icon.ico"
        ]
        for icon_path in icon_paths:
            if Path(icon_path).exists():
                cmd.extend(["--icon", icon_path])
                break
        
        # Добавляем все файлы из assets (включая подпапки)
        assets_path = Path("assets")
        if assets_path.exists():
            for file_path in assets_path.rglob("*"):
                if file_path.is_file():
                    # Сохраняем структуру папок
                    relative_path = file_path.relative_to(assets_path)
                    parent_dir = relative_path.parent if relative_path.parent != Path('.') else ''
                    if parent_dir:
                        cmd.extend(["--add-data", f"{file_path};assets/{parent_dir}"])
                    else:
                        cmd.extend(["--add-data", f"{file_path};assets"])
        
        # Добавляем конфигурацию (включая секретные файлы для работы EXE)
        config_files = [
            "config/bot_config.example.json",
            "config/bot_responses.json", 
            "config/guest_access.example.json",
            "config/beta_warning.json",
            "config/update_config.py",
            "config/minecraft_terms.json",
            "config/translation_quality.json"
        ]
        
        # КРИТИЧЕСКИ ВАЖНО: Добавляем секретные файлы если они есть
        secret_files = [
            "config/bot_config.json",
            "config/guest_access.json"
        ]
        
        for config_file in config_files:
            if Path(config_file).exists():
                cmd.extend(["--add-data", f"{config_file};config"])
        
        for secret_file in secret_files:
            if Path(secret_file).exists():
                cmd.extend(["--add-data", f"{secret_file};config"])
                print(f"✅ Добавлен секретный файл: {secret_file}")
            else:
                print(f"⚠️ Секретный файл не найден: {secret_file}")
                # Копируем example файл как основной
                example_file = secret_file.replace('.json', '.example.json')
                if Path(example_file).exists():
                    cmd.extend(["--add-data", f"{example_file};config"])
                    print(f"📄 Использован example файл: {example_file}")
        
        # КРИТИЧЕСКИ ВАЖНО: Добавляем все Python модули из src как данные
        src_files = [
            "src/modern_updater.py",
            "src/modern_update_overlays.py", 
            "src/translate_jar_simple.py",
            "src/enhanced_translator.py",  # Улучшенный переводчик
            "src/update_notifications.py",  # Кастомные диалоги ошибок (восстановлено)
            "src/utils.py"
        ]
        for src_file in src_files:
            if Path(src_file).exists():
                cmd.extend(["--add-data", f"{src_file};."])  # Добавляем в корень
        
        # КРИТИЧЕСКИ ВАЖНО: Добавляем update_config.py в корень для fallback импорта
        if Path("config/update_config.py").exists():
            cmd.extend(["--add-data", "config/update_config.py;."])
            print("✅ Добавлен update_config.py в корень для fallback импорта")
        
        # КРИТИЧЕСКИ ВАЖНО: Скрытые импорты для всех модулей
        hidden_imports = [
            # Основные библиотеки
            "translatepy", "requests", "json", "pathlib", "threading",
            "concurrent.futures", "datetime", "shutil", "zipfile", "logging",
            "pickle", "hashlib", "tempfile", "subprocess", "webbrowser",
            "traceback", "time", "random", "re", "os", "sys", "urllib3",
            "ssl", "certifi", "urllib.request", "urllib.parse", "urllib.error",
            
            # PyQt6 модули
            "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "PyQt6.QtNetwork",
            
            # Наши модули (КРИТИЧЕСКИ ВАЖНО!)
            "modern_updater", "modern_update_overlays", 
            "translate_jar_simple", "enhanced_translator",
            "update_notifications",  # Кастомные диалоги ошибок (восстановлено)
            "utils", "update_config",
            
            # Дополнительные модули для переводчика
            "translatepy.translators", "translatepy.language",
            "translatepy.exceptions", "translatepy.utils",
            
            # Модули для HTTP запросов и SSL
            "requests.adapters", "requests.auth", "requests.cookies",
            "requests.exceptions", "requests.models", "requests.sessions",
            "requests.structures", "requests.utils", "requests.packages",
            "requests.packages.urllib3", "requests.packages.urllib3.util",
            
            # SSL и сертификаты
            "ssl", "certifi", "_ssl"
        ]
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # Добавляем SSL сертификаты для HTTPS запросов
        try:
            import certifi
            cert_path = certifi.where()
            cmd.extend(["--add-data", f"{cert_path};certifi"])
            print(f"✅ Добавлены SSL сертификаты: {cert_path}")
        except ImportError:
            print("⚠️ certifi не найден, SSL может не работать")
        
        # Добавляем пути для поиска модулей
        cmd.extend(["--paths", "src"])
        cmd.extend(["--paths", "config"])
        cmd.extend(["--paths", "."])
        
        # Основной файл (главный модуль)
        cmd.append("src/modern_gui_interface.py")
        
        print(f"📦 Запуск PyInstaller для версии {version}...")
        print(f"🔧 Команда: {' '.join(cmd[:10])}... (сокращено)")
        
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
        
        # Копируем EXE в папку releases
        releases_dir = Path("releases")
        releases_dir.mkdir(exist_ok=True)
        final_exe_path = releases_dir / f"ru-minetools-v{version}.exe"
        shutil.copy2(exe_path, final_exe_path)
        
        print(f"✅ EXE создан: {final_exe_path}")
        print(f"📏 Размер: {final_exe_path.stat().st_size / (1024*1024):.1f} МБ")
        
        return final_exe_path
        
    except Exception as e:
        print(f"❌ Ошибка сборки версии {version}: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Восстанавливаем оригинальный конфиг
        if original_config:
            config_path.write_text(original_config, encoding='utf-8')
        
        # Очищаем временные файлы PyInstaller
        for cleanup_dir in ["build", "dist"]:
            if Path(cleanup_dir).exists():
                shutil.rmtree(cleanup_dir, ignore_errors=True)
        
        # Удаляем .spec файл
        spec_file = Path(f"ru-minetools-v{version}.spec")
        if spec_file.exists():
            spec_file.unlink()

def create_release_zip(version, exe_path):
    """Создает ZIP архив для релиза"""
    releases_dir = Path("releases")
    zip_path = releases_dir / f"ru-minetools-v{version}.zip"
    
    print(f"📦 Создание ZIP архива для версии {version}...")
    
    # Создаем временную папку для архива
    temp_dir = releases_dir / f"temp_release_v{version}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    
    try:
        # Копируем EXE в папку релиза
        release_exe_path = temp_dir / f"ru-minetools-v{version}.exe"
        shutil.copy2(exe_path, release_exe_path)
        
        # Создаем README для релиза
        readme_content = f"""# RU-MINETOOLS v{version}

## 🚀 Новые возможности в этой версии:
- ✅ Улучшенный переводчик с контекстом и терминологией
- ✅ Автоматическое определение типа мода для лучших переводов
- ✅ Встроенный словарь Minecraft терминов
- ✅ Умная фильтрация строк для перевода
- ✅ Система авторизации через Telegram
- ✅ Автоматические обновления
- ✅ Исправлен дергающийся прогресс-бар

## 📦 Установка:
1. Скачайте файл `ru-minetools-v{version}.exe`
2. Запустите программу
3. Наслаждайтесь переводом модов!

## 🔄 Обновления:
Программа автоматически проверяет обновления при запуске.

## 💜 Поддержка проекта:
Если программа вам нравится, поддержите разработку!

## 🔧 Технические детали:
- Версия: {version}
- Включает: улучшенный переводчик, авторизацию, обновления
- Размер: ~46 МБ
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
    print("🚀 ИСПРАВЛЕННАЯ сборка EXE с правильными импортами")
    print("=" * 60)
    
    # Проверяем наличие PyInstaller
    try:
        result = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                              capture_output=True, check=True, text=True)
        print(f"✅ PyInstaller найден: {result.stdout.strip()}")
    except subprocess.CalledProcessError:
        print("❌ PyInstaller не установлен!")
        print("Установите: pip install pyinstaller")
        return
    
    # Проверяем наличие ВСЕХ критически важных файлов
    required_files = [
        "src/modern_gui_interface.py",
        "src/modern_updater.py", 
        "src/modern_update_overlays.py",
        "src/translate_jar_simple.py",
        "src/enhanced_translator.py",  # Улучшенный переводчик
        "src/utils.py",
        "config/update_config.py",
        "config/minecraft_terms.json",  # Словарь терминов
        "assets/logo.png",
        "assets/sans3.ttf"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Отсутствуют критически важные файлы:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\n📖 Проверьте CRITICAL_FILES.md")
        return
    
    print("✅ Все необходимые файлы найдены")
    
    # Создаем папку releases если её нет
    releases_dir = Path("releases")
    releases_dir.mkdir(exist_ok=True)
    
    # Получаем версию из конфигурации
    try:
        sys.path.append('config')
        from update_config import CURRENT_VERSION
        version = CURRENT_VERSION
        print(f"✅ Версия из конфигурации: {version}")
    except ImportError:
        version = "1.0.0"
        print(f"⚠️ Не удалось получить версию из конфигурации, используем: {version}")
    
    print(f"\n🔨 Сборка версии {version}")
    print("-" * 50)
    
    # Собираем EXE
    exe_path = build_exe_version(version)
    if not exe_path:
        print(f"❌ Не удалось собрать EXE для версии {version}")
        return
    
    # Создаем ZIP
    zip_path = create_release_zip(version, exe_path)
    if not zip_path:
        print(f"❌ Не удалось создать ZIP для версии {version}")
        return
    
    print(f"\n🎉 Сборка завершена успешно!")
    print("=" * 40)
    print("📦 Созданные файлы:")
    print(f"  📄 EXE: {exe_path}")
    print(f"  📦 ZIP: {zip_path}")
    print(f"\n📁 Файлы сохранены в: {releases_dir.absolute()}")
    
    print("\n🧪 Тестирование:")
    print("1. Запустите EXE файл")
    print("2. Проверьте работу авторизации")
    print("3. Протестируйте улучшенный переводчик")
    print("4. Проверьте систему обновлений")
    
    print("\n✨ Улучшения в этой версии:")
    print("- ✅ Правильные импорты всех модулей")
    print("- ✅ Включен улучшенный переводчик")
    print("- ✅ Словарь терминов")
    print("- ✅ Система авторизации")
    print("- ✅ Автообновления")

if __name__ == "__main__":
    main()