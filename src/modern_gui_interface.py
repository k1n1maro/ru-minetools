#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RU-MINETOOLS - Утилита для работы с переводами и модами Minecraft
"""

import sys
import os

# Настройка обработки ошибок для PyInstaller
if getattr(sys, 'frozen', False):
    # В режиме EXE логируем ошибки в файл вместо подавления
    import io
    import datetime
    
    class ErrorLogger:
        def __init__(self):
            self.original_stderr = sys.stderr
            self.error_log_path = "ru_minetools_errors.log"
            
        def write(self, text):
            # Записываем в оригинальный stderr (если доступен)
            try:
                self.original_stderr.write(text)
                self.original_stderr.flush()
            except:
                pass
            
            # Также записываем в файл лога
            if text.strip():  # Игнорируем пустые строки
                try:
                    with open(self.error_log_path, 'a', encoding='utf-8') as f:
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {text}")
                        f.flush()
                except:
                    pass  # Если не можем записать в лог, не падаем
        
        def flush(self):
            try:
                self.original_stderr.flush()
            except:
                pass
    
    # Заменяем stderr на наш логгер
    sys.stderr = ErrorLogger()

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar,
    QGridLayout, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QStackedWidget, QSplitter, QHeaderView, QSpacerItem, QSizePolicy, QGraphicsBlurEffect,
    QTextEdit, QFileDialog, QMessageBox, QComboBox, QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QParallelAnimationGroup, QSequentialAnimationGroup, QPoint, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon, QPalette, QFontDatabase, QBrush, QPen, QPainterPath, QRegion, QLinearGradient
import json
import webbrowser
import random
import requests
import threading
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import shutil
import time
import logging
# Добавляем пути для импорта модулей из других папок
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Импортируем утилиты для работы с ресурсами
from utils import get_resource_path, get_asset_path, get_config_path

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ru_minetools.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Логируем настройку для EXE режима если нужно
if getattr(sys, 'frozen', False):
    logger.info("Настроено логирование ошибок для EXE режима")

# ФУНКЦИИ ВАЛИДАЦИИ И БЕЗОПАСНОСТИ

def validate_file_path(path: Path, allowed_extensions: set = None) -> bool:
    """
    Валидирует путь к файлу на безопасность
    
    Args:
        path: Путь к файлу
        allowed_extensions: Разрешенные расширения файлов (например, {'.snbt', '.json'})
    
    Returns:
        bool: True если путь безопасен, False иначе
    """
    try:
        # Проверяем что путь существует и это файл
        if not path.exists() or not path.is_file():
            logger.warning(f"Файл не существует или не является файлом: {path}")
            return False
        
        # Проверяем расширение если указано
        if allowed_extensions and path.suffix.lower() not in allowed_extensions:
            logger.warning(f"Недопустимое расширение файла: {path.suffix}")
            return False
        
        # Проверяем что путь не содержит опасных символов
        path_str = str(path.resolve())
        dangerous_patterns = ['..', '~', '$', '`', ';', '|', '&']
        for pattern in dangerous_patterns:
            if pattern in path_str:
                logger.warning(f"Опасный символ в пути: {pattern}")
                return False
        
        # Проверяем размер файла (не больше 100MB)
        file_size = path.stat().st_size
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            logger.warning(f"Файл слишком большой: {file_size} bytes > {max_size}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка валидации пути {path}: {e}")
        return False

def validate_text_input(text: str, max_length: int = 10000) -> str:
    """
    Валидирует и очищает текстовый ввод
    
    Args:
        text: Входной текст
        max_length: Максимальная длина текста
    
    Returns:
        str: Очищенный текст
    
    Raises:
        ValueError: Если текст невалиден
    """
    if not isinstance(text, str):
        raise ValueError("Текст должен быть строкой")
    
    if len(text) > max_length:
        raise ValueError(f"Текст слишком длинный: {len(text)} > {max_length}")
    
    # Удаляем потенциально опасные символы
    dangerous_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()

def safe_file_operation(operation_func, file_path: Path, *args, **kwargs):
    """
    Безопасное выполнение файловых операций с обработкой ошибок
    
    Args:
        operation_func: Функция для выполнения
        file_path: Путь к файлу
        *args, **kwargs: Аргументы для функции
    
    Returns:
        Результат операции или None при ошибке
    """
    try:
        return operation_func(file_path, *args, **kwargs)
    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
        return None
    except PermissionError:
        logger.error(f"Нет прав доступа к файлу: {file_path}")
        return None
    except OSError as e:
        logger.error(f"Ошибка файловой системы для {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при работе с {file_path}: {e}")
        logger.debug(traceback.format_exc())
        return None


# Импорт переводчика
try:
    from translatepy import Translator
    translator_snbt = Translator()
    TRANSLATOR_AVAILABLE = True
except Exception:
    translator_snbt = None
    TRANSLATOR_AVAILABLE = False

# Импорт системы обновлений
try:
    from modern_updater import StandardUpdateChecker, show_update_available_dialog, start_update_process
    from config.update_config import UPDATE_SETTINGS
    from modern_update_overlays import show_modern_update_dialog, show_modern_progress_dialog
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    UPDATE_SETTINGS = {"auto_check": True}  # Значение по умолчанию
    logger.debug("Система обновлений недоступна")

# ФУНКЦИИ ПЕРЕВОДА FTB КВЕСТОВ

def safe_translate_snbt(text: str, lang_to: str) -> str:
    """Простой перевод текста с базовой защитой от ошибок"""
    if translator_snbt is None:
        return text
    
    # Валидация входных данных
    if text is None:
        logger.warning("Получен None вместо текста для перевода")
        return ""
    
    if not isinstance(text, str):
        logger.warning(f"Получен не-строковый тип для перевода: {type(text)}")
        return str(text) if text else ""
    
    if not text.strip():
        return text
    
    try:
        # Валидация текста
        text = validate_text_input(text, max_length=5000)  # Ограничиваем длину для API
    except ValueError as e:
        logger.warning(f"Невалидный текст для перевода: {e}")
        return text
    
    # Пропускаем уже переведенный текст (кириллица)
    # Улучшенная проверка: считаем долю кириллицы
    cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
    if cyrillic_count > len(text) * 0.3:  # Если больше 30% кириллицы
        return text
    
    # Пропускаем технические ID
    if ':' in text and len(text) < 50 and ' ' not in text:
        return text
    
    # Пропускаем строки с фигурными скобками
    if '{' in text or '}' in text:
        return text
    
    try:
        # Сохраняем форматирующие коды
        placeholders = re.findall(r"&([0-9a-fk-or]|\d{1,3})", text, flags=re.IGNORECASE)
        temp = re.sub(r"&([0-9a-fk-or]|\d{1,3})", "^^*^^", text, flags=re.IGNORECASE)
        
        # Переводим с дополнительными проверками
        try:
            translated = str(translator_snbt.translate(temp, lang_to))
        except Exception as translate_error:
            logger.warning(f"Ошибка API перевода для текста '{text[:30]}...': {translate_error}")
            return text  # Возвращаем оригинальный текст при ошибке API
        
        if translated is None or translated.strip() == "":
            logger.warning(f"Переводчик вернул пустой результат для текста: {text[:50]}")
            return text
        
        # Очищаем кавычки
        translated = translated.replace('"', "''")
        
        # Восстанавливаем форматирующие коды
        for code in placeholders:
            translated = translated.replace('^^*^^', f'&{code}', 1)
        
        return translated
        
    except Exception as e:
        logger.warning(f"Ошибка перевода текста '{text[:50] if len(text) > 50 else text}': {e}")
        logger.debug(f"Полный текст для отладки: {text}")
        logger.debug(f"Трассировка ошибки: {traceback.format_exc()}")
        # Возвращаем оригинальный текст при ошибке
        return text

def translate_description_block(block_text: str, lang_to: str) -> str:
    """Переводит блок описания квеста (массив строк)"""
    lines = block_text.splitlines()
    out_lines = []
    
    for line in lines:
        # Ищем строки в кавычках
        m = re.match(r'^(\s*")(?P<content>.*?)(".*)', line)
        if m:
            content = m.group("content")
            translated = safe_translate_snbt(content, lang_to)
            out_lines.append(f'{m.group(1)}{translated}{m.group(3)}')
        else:
            out_lines.append(line)
    
    return "\n".join(out_lines)

def process_lang_snbt_file(input_path: Path, base_input: Path, base_output: Path, lang_to: str) -> tuple[Path, str]:
    """Обрабатывает файлы из языковых папок (en_us/, de_de/ и т.д.) и сохраняет в ru_ru/"""
    try:
        # Определяем относительный путь
        rel_path = input_path.relative_to(base_input)
        
        # Если файл из языковой папки (например, lang/en_us/file.snbt)
        if len(rel_path.parts) >= 2 and rel_path.parts[-2] == 'en_us':
            # Заменяем en_us на ru_ru: lang/en_us/file.snbt -> lang/ru_ru/file.snbt
            new_parts = list(rel_path.parts[:-2]) + ['ru_ru'] + [rel_path.parts[-1]]
            output_path = base_output / Path(*new_parts)
        elif input_path.name == "en_us.snbt":
            # Старый формат: en_us.snbt -> ru_ru.snbt
            output_path = base_output / rel_path.parent / "ru_ru.snbt"
        else:
            # Для других файлов сохраняем структуру
            output_path = base_output / rel_path
        
        # Читаем файл
        text = input_path.read_text(encoding="utf-8")
        changed = False
        
        # Переводим title
        def repl_title(m):
            nonlocal changed
            before, core, after = m.group(1), m.group(2), m.group(3)
            translated = safe_translate_snbt(core, lang_to)
            if translated != core:
                changed = True
            return f'{before}{translated}{after}'
        
        text = re.sub(r'(\btitle:\s*")([^"]*)(\")', repl_title, text, flags=re.IGNORECASE)
        
        # Переводим description
        def repl_desc(m):
            nonlocal changed
            start, body, end = m.group(1), m.group(2), m.group(3)
            translated_body = translate_description_block(body, lang_to)
            if translated_body != body:
                changed = True
            return f'{start}{translated_body}{end}'
        
        text = re.sub(r'(\bdescription:\s*\[)(.*?)(\])', repl_desc, text,
                     flags=re.DOTALL | re.IGNORECASE)
        
        # Переводим дополнительные поля
        for field_name in ('subtitle', 'quest_subtitle', 'description_short'):
            pattern = rf'(\b{re.escape(field_name)}:\s*")([^"]*)(\")'
            def repl(m):
                nonlocal changed
                translated = safe_translate_snbt(m.group(2), lang_to)
                if translated != m.group(2):
                    changed = True
                return f'{m.group(1)}{translated}{m.group(3)}'
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
        # Создаем папку и сохраняем файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding='utf-8')
        
        status = "TRANSLATED" if changed else "NO_CHANGES"
        return (input_path, f"{status}: {input_path.name} -> {output_path.relative_to(base_output)}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла {input_path}: {e}")
        return (input_path, f"ERROR: {e}")

def process_lang_file(input_path: Path, base_input: Path, base_output: Path, lang_to: str) -> tuple[Path, str]:
    """Обрабатывает файл en_us.snbt и сохраняет как ru_ru.snbt"""
    try:
        # Для файлов lang меняем имя с en_us.snbt на ru_ru.snbt
        rel = input_path.relative_to(base_input)
        if input_path.name == "en_us.snbt":
            # Заменяем имя файла на ru_ru.snbt
            output_path = base_output / rel.parent / "ru_ru.snbt"
        else:
            output_path = base_output / rel
        
        # Читаем файл
        text = input_path.read_text(encoding="utf-8")
        changed = False
        
        # Переводим title
        def repl_title(m):
            nonlocal changed
            before, core, after = m.group(1), m.group(2), m.group(3)
            translated = safe_translate_snbt(core, lang_to)
            if translated != core:
                changed = True
            return f'{before}{translated}{after}'
        
        text = re.sub(r'(\btitle:\s*")([^"]*)(\")', repl_title, text, flags=re.IGNORECASE)
        
        # Переводим description
        def repl_desc(m):
            nonlocal changed
            start, body, end = m.group(1), m.group(2), m.group(3)
            translated_body = translate_description_block(body, lang_to)
            if translated_body != body:
                changed = True
            return f'{start}{translated_body}{end}'
        
        text = re.sub(r'(\bdescription:\s*\[)(.*?)(\])', repl_desc, text,
                     flags=re.DOTALL | re.IGNORECASE)
        
        # Переводим дополнительные поля
        for field_name in ('subtitle', 'quest_subtitle', 'description_short'):
            pattern = rf'(\b{re.escape(field_name)}:\s*")([^"]*)(\")'
            def repl(m):
                nonlocal changed
                translated = safe_translate_snbt(m.group(2), lang_to)
                if translated != m.group(2):
                    changed = True
                return f'{m.group(1)}{translated}{m.group(3)}'
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
        # Создаем папку и сохраняем файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding='utf-8')
        
        status = "TRANSLATED" if changed else "NO_CHANGES"
        return (input_path, f"{status}: {input_path.name} -> {output_path.name}")
        
    except Exception as e:
        return (input_path, f"ERROR: {e}")

def process_snbt_file(input_path: Path, base_input: Path, base_output: Path, lang_to: str) -> tuple[Path, str]:
    """Обрабатывает один SNBT файл. Возвращает (путь, ошибка или None)"""
    try:
        # Валидация входного файла
        if not validate_file_path(input_path, {'.snbt'}):
            return (input_path, "ERROR: Небезопасный или недопустимый путь к файлу")
        
        rel = input_path.relative_to(base_input)
        output_path = base_output / rel
        
        # Создаем выходную директорию безопасно
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Безопасное чтение файла
        def read_file(path):
            return path.read_text(encoding="utf-8")
        
        text = safe_file_operation(read_file, input_path)
        if text is None:
            return (input_path, "ERROR: Не удалось прочитать файл")
        
        # Валидация содержимого
        try:
            text = validate_text_input(text, max_length=10000000)  # 10MB текста
        except ValueError as e:
            return (input_path, f"ERROR: Невалидное содержимое файла: {e}")
        
        changed = False
        
        # Переводим title
        def repl_title(m):
            nonlocal changed
            before, core, after = m.group(1), m.group(2), m.group(3)
            translated = safe_translate_snbt(core, lang_to)
            if translated != core:
                changed = True
            return f'{before}{translated}{after}'
        
        text = re.sub(r'(\btitle:\s*")([^"]*)(\")', repl_title, text, flags=re.IGNORECASE)
        
        # Переводим description
        def repl_desc(m):
            nonlocal changed
            start, body, end = m.group(1), m.group(2), m.group(3)
            translated_body = translate_description_block(body, lang_to)
            if translated_body != body:
                changed = True
            return f'{start}{translated_body}{end}'
        
        text = re.sub(r'(\bdescription:\s*\[)(.*?)(\])', repl_desc, text,
                     flags=re.DOTALL | re.IGNORECASE)
        
        # Переводим дополнительные поля
        for field_name in ('subtitle', 'quest_subtitle', 'description_short'):
            pattern = rf'(\b{re.escape(field_name)}:\s*")([^"]*)(\")'
            def repl(m):
                nonlocal changed
                translated = safe_translate_snbt(m.group(2), lang_to)
                if translated != m.group(2):
                    changed = True
                return f'{m.group(1)}{translated}{m.group(3)}'
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
        # Безопасное сохранение файла
        def write_file(path, content):
            path.write_text(content, encoding='utf-8')
            return True
        
        if not safe_file_operation(write_file, output_path, text):
            return (input_path, "ERROR: Не удалось сохранить файл")
        
        status = "TRANSLATED" if changed else "NO_CHANGES"
        return (input_path, f"{status}: {rel}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла {input_path}: {e}")
        logger.debug(traceback.format_exc())
        return (input_path, f"ERROR: {e}")

class ChaptersLangTranslationWorker(QThread):
    """Воркер для перевода папок chapters и lang в отдельном потоке"""
    
    progress_updated = pyqtSignal(str)  # Сигнал для обновления прогресса
    file_processed = pyqtSignal(str, bool)  # Сигнал обработки файла (имя, успех)
    translation_finished = pyqtSignal(int, int)  # Сигнал завершения (успешно, всего)
    
    def __init__(self, folder_path, lang_to, parent=None):
        super().__init__(parent)
        self.folder_path = Path(folder_path)
        self.lang_to = lang_to
        self.is_cancelled = False
        self.is_paused = False  # Состояние паузы
        self.pause_message_sent = False  # Флаг для отправки сообщения о паузе только один раз
    
    def cancel(self):
        """Отменяет выполнение"""
        self.is_cancelled = True
    
    def pause(self):
        """Пауза перевода"""
        self.is_paused = True
        self.pause_message_sent = False  # Сбрасываем флаг при паузе
    
    def resume(self):
        """Возобновление перевода"""
        self.is_paused = False
        self.pause_message_sent = False  # Сбрасываем флаг при возобновлении
        # Отправляем сигнал о возобновлении для немедленного обновления UI
        self.progress_updated.emit("🔄 Возобновление перевода...")
    
    def run(self):
        """Основная логика перевода папок chapters и lang"""
        try:
            # Проверяем доступность переводчика
            if not TRANSLATOR_AVAILABLE:
                self.progress_updated.emit("❌ Ошибка: Модуль translatepy не установлен!")
                return
            
            # Ищем папки chapters и lang - проверяем несколько вариантов путей
            chapters_folders = []
            lang_folders = []
            
            # Варианты путей для поиска
            possible_paths = [
                # Вариант 1: выбранная папка уже содержит config/ftbquests/quests
                self.folder_path / "config" / "ftbquests" / "quests",
                # Вариант 2: выбранная папка содержит minecraft/config/ftbquests/quests
                self.folder_path / "minecraft" / "config" / "ftbquests" / "quests",
                # Вариант 3: выбранная папка УЖЕ является папкой quests
                self.folder_path,
                # Вариант 4: выбранная папка является ftbquests
                self.folder_path / "quests",
            ]
            
            quests_path_found = None
            for quests_path in possible_paths:
                if quests_path.exists() and quests_path.is_dir():
                    # Ищем папки chapters и lang в quests директории
                    chapters_path = quests_path / "chapters"
                    lang_path = quests_path / "lang"
                    
                    if chapters_path.exists() and chapters_path.is_dir():
                        chapters_folders.append(chapters_path)
                        
                    if lang_path.exists() and lang_path.is_dir():
                        lang_folders.append(lang_path)
                    
                    # Если нашли хотя бы одну папку, запоминаем путь и прекращаем поиск
                    if chapters_folders or lang_folders:
                        quests_path_found = quests_path
                        self.progress_updated.emit(f"✅ Найден путь к квестам: {quests_path}")
                        break
            
            if not quests_path_found:
                self.progress_updated.emit("❌ Не удалось найти путь к папке квестов!")
                self.progress_updated.emit("💡 Убедитесь что выбрана папка содержащая config/ftbquests/quests")
                return
            
            all_folders = chapters_folders + lang_folders
            if not all_folders:
                self.progress_updated.emit("❌ Не найдено папок 'chapters' или 'lang'!")
                return
            
            # Собираем файлы для перевода
            snbt_files = []
            
            # Из папок chapters берем все .snbt файлы
            for folder in chapters_folders:
                if folder.is_dir():
                    folder_snbt_files = list(folder.rglob('*.snbt'))
                    snbt_files.extend(folder_snbt_files)
                    if folder_snbt_files:
                        self.progress_updated.emit(f"📁 {folder.name}: найдено {len(folder_snbt_files)} файлов")
            
            # Из папок lang проверяем языковые папки
            for folder in lang_folders:
                if folder.is_dir():
                    # Проверяем есть ли уже русский перевод
                    ru_folder = folder / "ru_ru"
                    if ru_folder.exists() and ru_folder.is_dir():
                        ru_files = list(ru_folder.glob("*.snbt"))
                        if ru_files:
                            self.progress_updated.emit(f"✅ {folder.name}: уже переведен (найдено {len(ru_files)} файлов в ru_ru/), пропускаем")
                            continue
                    
                    # Ищем английскую папку для перевода
                    en_folder = folder / "en_us"
                    if en_folder.exists() and en_folder.is_dir():
                        en_files = list(en_folder.glob("*.snbt"))
                        if en_files:
                            snbt_files.extend(en_files)
                            self.progress_updated.emit(f"📁 {folder.name}: найдено {len(en_files)} файлов в en_us/ для перевода")
                        else:
                            self.progress_updated.emit(f"⚠️ {folder.name}: папка en_us/ существует, но пуста")
                    else:
                        # Проверяем старый формат (en_us.snbt файл в корне папки lang)
                        en_us_file = folder / "en_us.snbt"
                        if en_us_file.exists():
                            # Проверяем нет ли уже ru_ru.snbt
                            ru_ru_file = folder / "ru_ru.snbt"
                            if ru_ru_file.exists():
                                self.progress_updated.emit(f"✅ {folder.name}: уже переведен (найден ru_ru.snbt), пропускаем")
                                continue
                            
                            snbt_files.append(en_us_file)
                            self.progress_updated.emit(f"📁 {folder.name}: найден en_us.snbt (старый формат) для перевода")
                        else:
                            # Ищем любые языковые папки для информации
                            lang_subfolders = [d.name for d in folder.iterdir() if d.is_dir() and '_' in d.name and len(d.name) == 5]
                            if lang_subfolders:
                                self.progress_updated.emit(f"ℹ️ {folder.name}: найдены языковые папки {lang_subfolders}, но нет en_us для перевода")
                            else:
                                self.progress_updated.emit(f"⚠️ {folder.name}: не найдено файлов для перевода")
            
            if not snbt_files:
                self.progress_updated.emit("❌ Не найдено .snbt файлов в папках chapters/lang!")
                return
            
            self.progress_updated.emit(f"📄 Всего найдено {len(snbt_files)} файлов для перевода")
            
            # Обрабатываем файлы по папкам
            successful = 0
            total = len(snbt_files)
            processed_folders = set()
            output_folders = []  # Список созданных выходных папок
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {}
                
                # Группируем файлы по папкам chapters/lang
                for file_path in snbt_files:
                    # Находим родительскую папку chapters или lang
                    for part in file_path.parts:
                        if part in ['chapters', 'lang']:
                            # Находим полный путь к папке chapters/lang
                            chapters_lang_folder = None
                            for parent in file_path.parents:
                                if parent.name == part:
                                    chapters_lang_folder = parent
                                    break
                            
                            if chapters_lang_folder:
                                # Создаем выходную папку с суффиксом -translate
                                output_folder = chapters_lang_folder.with_name(chapters_lang_folder.name + "-translate")
                                
                                if chapters_lang_folder not in processed_folders:
                                    output_folder.mkdir(parents=True, exist_ok=True)
                                    self.progress_updated.emit(f"📂 Создана папка: {output_folder.name}")
                                    processed_folders.add(chapters_lang_folder)
                                    output_folders.append(output_folder)  # Сохраняем выходную папку
                                
                                # Выбираем функцию обработки в зависимости от типа папки
                                if part == 'lang':
                                    # Для папок lang используем специальную функцию (en_us.snbt -> ru_ru.snbt)
                                    future = executor.submit(process_lang_file, file_path, chapters_lang_folder, output_folder, self.lang_to)
                                else:
                                    # Для папок chapters используем обычную функцию
                                    future = executor.submit(process_snbt_file, file_path, chapters_lang_folder, output_folder, self.lang_to)
                                futures[future] = file_path
                            break
                
                # Обрабатываем результаты
                for i, future in enumerate(as_completed(futures)):
                    if self.is_cancelled:
                        break
                    
                    # Проверяем паузу
                    while self.is_paused and not self.is_cancelled:
                        if not self.pause_message_sent:
                            self.progress_updated.emit("⏸️ На паузе...")
                            self.pause_message_sent = True
                        self.msleep(100)
                    
                    if self.is_cancelled:
                        break
                    
                    file_path = futures[future]
                    try:
                        _, result = future.result()
                        
                        if result.startswith("ERROR"):
                            self.progress_updated.emit(f"❌ {result}")
                            self.file_processed.emit(file_path.name, False)
                            logger.error(f"Ошибка обработки файла {file_path}: {result}")
                        else:
                            if "TRANSLATED" in result:
                                successful += 1
                                # Показываем детальную информацию о переводе
                                if " -> " in result:
                                    self.progress_updated.emit(f"✅ {result.split(': ')[1]}")
                                else:
                                    self.progress_updated.emit(f"✅ {file_path.name}: переведен")
                            else:
                                self.progress_updated.emit(f"⚪ {file_path.name}: без изменений")
                            self.file_processed.emit(file_path.name, True)
                        
                        # Обновляем прогресс
                        progress = int((i + 1) / total * 100)
                        self.progress_updated.emit(f"📊 Прогресс: {progress}% ({i + 1}/{total})")
                        
                    except Exception as e:
                        error_msg = f"❌ {file_path.name}: {e}"
                        self.progress_updated.emit(error_msg)
                        self.file_processed.emit(file_path.name, False)
                        logger.error(f"Исключение при обработке файла {file_path}: {e}")
                        logger.debug(traceback.format_exc())
            
            if not self.is_cancelled:
                self.progress_updated.emit(f"🎉 Перевод завершен! Успешно: {successful}/{total}")
                # Показываем список созданных папок
                if output_folders:
                    folder_names = ", ".join([f.name for f in output_folders])
                    self.progress_updated.emit(f"📂 Результат в папках: {folder_names}")
                self.translation_finished.emit(successful, total)
            
        except Exception as e:
            logger.error(f"Критическая ошибка в процессе перевода: {e}")
            logger.debug(traceback.format_exc())
            self.progress_updated.emit(f"❌ Критическая ошибка: {e}")
            self.progress_updated.emit("🔄 Попробуйте перезапустить перевод или выберите другую папку")
            self.translation_finished.emit(0, 0)  # Сигнализируем о неудаче

class NavButton(QPushButton):
    """Кнопка навигации с hover анимацией"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("navButton")
        
        # Анимация для hover эффекта (сдвиг вправо)
        self.hover_animation = QPropertyAnimation(self, b"pos")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_pos = None
        self.is_hovered = False
    
    def paintEvent(self, event):
        """Переопределяем отрисовку для добавления сглаживания"""
        painter = QPainter(self)
        # Включаем максимальное сглаживание
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        
        # Вызываем стандартную отрисовку
        super().paintEvent(event)
    
    def enterEvent(self, event):
        """Анимация при наведении - сдвиг вправо"""
        self.is_hovered = True
        
        # Останавливаем предыдущую анимацию если она запущена
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos is None:
            self.original_pos = self.pos()
        
        # Сдвигаем вправо на 4 пикселя
        target_pos = QPoint(
            self.original_pos.x() + 4,
            self.original_pos.y()
        )
        
        self.hover_animation.setStartValue(self.pos())
        self.hover_animation.setEndValue(target_pos)
        self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Возврат к исходному состоянию"""
        self.is_hovered = False
        
        # Останавливаем предыдущую анимацию если она запущена
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos:
            self.hover_animation.setStartValue(self.pos())
            self.hover_animation.setEndValue(self.original_pos)
            self.hover_animation.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """При клике плавно возвращаем в исходную позицию"""
        if self.original_pos:
            self.hover_animation.setStartValue(self.pos())
            self.hover_animation.setEndValue(self.original_pos)
            self.hover_animation.start()
        
        super().mousePressEvent(event)


class AnimatedButton(QPushButton):
    """Кнопка с анимацией подпрыгивания как на экране авторизации"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # Анимация подпрыгивания вверх
        self.bounce_up_animation = QPropertyAnimation(self, b"geometry")
        self.bounce_down_animation = QPropertyAnimation(self, b"geometry")
        
        # Анимация hover эффекта
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_geometry = None
        self.is_animating = False
        self.is_hovered = False
    
    def enterEvent(self, event):
        """Анимация при наведении - подъем вверх"""
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        
        if not self.is_animating and not self.is_hovered:
            self.is_hovered = True
            
            # Поднимаем кнопку на 4 пикселя вверх
            current_rect = self.geometry()
            hover_rect = QRect(
                current_rect.x(),
                current_rect.y() - 4,
                current_rect.width(),
                current_rect.height()
            )
            
            self.hover_animation.setStartValue(current_rect)
            self.hover_animation.setEndValue(hover_rect)
            self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Возврат к исходному положению"""
        if not self.is_animating and self.is_hovered:
            self.is_hovered = False
            
            # Возвращаем кнопку в исходное положение
            if self.original_geometry:
                self.hover_animation.setStartValue(self.geometry())
                self.hover_animation.setEndValue(self.original_geometry)
                self.hover_animation.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Анимация подпрыгивания при клике"""
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        
        # Запускаем анимацию подпрыгивания
        self.create_bounce_animation()
        
        super().mousePressEvent(event)
    
    def create_bounce_animation(self):
        """Создает анимацию подпрыгивания вверх"""
        if not self.original_geometry or self.is_animating:
            return
        
        self.is_animating = True
        
        current_rect = self.geometry()
        
        # Позиция подпрыгивания (вверх на 8 пикселей от исходной позиции)
        bounce_rect = QRect(
            self.original_geometry.x(),
            self.original_geometry.y() - 8,
            self.original_geometry.width(),
            self.original_geometry.height()
        )
        
        # Определяем конечную позицию в зависимости от hover состояния
        if self.is_hovered:
            # Если мышь на кнопке, возвращаемся в hover позицию
            final_rect = QRect(
                self.original_geometry.x(),
                self.original_geometry.y() - 4,
                self.original_geometry.width(),
                self.original_geometry.height()
            )
        else:
            # Если мыши нет, возвращаемся в исходную позицию
            final_rect = self.original_geometry
        
        # Фаза 1: Быстрый подъем вверх
        self.bounce_up_animation.setDuration(100)
        self.bounce_up_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.bounce_up_animation.setStartValue(current_rect)
        self.bounce_up_animation.setEndValue(bounce_rect)
        
        # Фаза 2: Плавное возвращение вниз с отскоком
        self.bounce_down_animation.setDuration(200)
        self.bounce_down_animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.bounce_down_animation.setStartValue(bounce_rect)
        self.bounce_down_animation.setEndValue(final_rect)
        
        # Запускаем анимации последовательно
        self.bounce_up_animation.finished.connect(self.bounce_down_animation.start)
        self.bounce_down_animation.finished.connect(self.on_animation_finished)
        self.bounce_up_animation.start()
    
    def on_animation_finished(self):
        """Завершение анимации"""
        self.is_animating = False


class HoverLiftButton(QPushButton):
    """Кнопка с анимацией подъема при наведении мыши"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # Анимация для hover эффекта (подъем вверх) - точно как в NavButton
        self.hover_animation = QPropertyAnimation(self, b"pos")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_pos = None
        self.is_hovered = False
    
    def paintEvent(self, event):
        """Переопределяем отрисовку для добавления сглаживания"""
        painter = QPainter(self)
        # Включаем максимальное сглаживание
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        
        # Вызываем стандартную отрисовку
        super().paintEvent(event)
    
    def enterEvent(self, event):
        """Анимация при наведении - подъем вверх"""
        self.is_hovered = True
        
        # Останавливаем предыдущую анимацию если она запущена
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos is None:
            self.original_pos = self.pos()
        
        # Поднимаем вверх на 4 пикселя (как NavButton сдвигает вправо)
        target_pos = QPoint(
            self.original_pos.x(),
            self.original_pos.y() - 4
        )
        
        self.hover_animation.setStartValue(self.pos())
        self.hover_animation.setEndValue(target_pos)
        self.hover_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Возврат к исходному состоянию"""
        self.is_hovered = False
        
        # Останавливаем предыдущую анимацию если она запущена
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos:
            self.hover_animation.setStartValue(self.pos())
            self.hover_animation.setEndValue(self.original_pos)
            self.hover_animation.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """При клике плавно возвращаем в исходную позицию"""
        if self.original_pos:
            self.hover_animation.setStartValue(self.pos())
            self.hover_animation.setEndValue(self.original_pos)
            self.hover_animation.start()
        
        super().mousePressEvent(event)


class GlassmorphismProgressBar(QWidget):
    """Современный прогресс-бар в стиле glassmorphism с улучшенными эффектами"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setMinimumWidth(300)
        self._value = 0
        self._maximum = 100
        self._minimum = 0
        self._text = ""
        
    def setValue(self, value):
        """Устанавливает текущее значение"""
        self._value = max(self._minimum, min(self._maximum, value))
        self.update()
    
    def setMaximum(self, maximum):
        """Устанавливает максимальное значение"""
        self._maximum = maximum
        self.update()
    
    def setMinimum(self, minimum):
        """Устанавливает минимальное значение"""
        self._minimum = minimum
        self.update()
    
    def value(self):
        return self._value
    
    def maximum(self):
        return self._maximum
    
    def minimum(self):
        return self._minimum
    
    def setText(self, text):
        """Устанавливает текст"""
        self._text = text
        self.update()
    
    def paintEvent(self, event):
        """Отрисовка glassmorphism прогресс-бара"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        rect = self.rect()
        radius = 16
        
        # Фон с glassmorphism эффектом
        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, radius, radius)
        
        # Полупрозрачный фон
        bg_color = QColor(255, 255, 255, 20)
        painter.fillPath(bg_path, QBrush(bg_color))
        
        # Рамка
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.drawPath(bg_path)
        
        # Прогресс
        if self._maximum > self._minimum:
            progress = (self._value - self._minimum) / (self._maximum - self._minimum)
            progress_width = (rect.width() - 4) * progress
            progress_rect = QRect(2, 2, int(progress_width), rect.height() - 4)
            
            if progress_rect.width() > 0:
                # Создаем путь для прогресса
                progress_path = QPainterPath()
                progress_path.addRoundedRect(progress_rect, radius - 2, radius - 2)
                
                # Градиент прогресса
                progress_gradient = QLinearGradient(0, 0, rect.width(), 0)
                progress_gradient.setColorAt(0, QColor(187, 134, 252, 180))
                progress_gradient.setColorAt(0.5, QColor(156, 77, 204, 200))
                progress_gradient.setColorAt(1, QColor(187, 134, 252, 180))
                
                painter.fillPath(progress_path, QBrush(progress_gradient))
        
        # Текст
        if self._text:
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)
    """Современный прогресс-бар в стиле glassmorphism с улучшенными эффектами"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Инициализируем атрибуты ПЕРВЫМИ (до создания анимаций)
        self._animated_value = 0
        self._pulse_value = 1.0
        self._value = 0
        self._maximum = 100
        self._text = ""
        self._is_dark_theme = True  # Поддержка тем
        
        self.setFixedHeight(70)
        
        # Анимация для плавного изменения значения
        self.value_animation = QPropertyAnimation(self, b"animatedValue")
        self.value_animation.setDuration(300)
        self.value_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Создаем плавную двунаправленную анимацию пульсации
        self.pulse_animation_group = QParallelAnimationGroup()
        
        # Анимация загорания (от минимума к максимуму)
        self.pulse_up_animation = QPropertyAnimation(self, b"pulseValue")
        self.pulse_up_animation.setDuration(2000)  # 2 секунды на загорание
        self.pulse_up_animation.setStartValue(0.6)
        self.pulse_up_animation.setEndValue(1.0)
        self.pulse_up_animation.setEasingCurve(QEasingCurve.Type.OutSine)  # Плавное загорание
        
        # Анимация затухания (от максимума к минимуму)
        self.pulse_down_animation = QPropertyAnimation(self, b"pulseValue")
        self.pulse_down_animation.setDuration(2000)  # 2 секунды на затухание
        self.pulse_down_animation.setStartValue(1.0)
        self.pulse_down_animation.setEndValue(0.6)
        self.pulse_down_animation.setEasingCurve(QEasingCurve.Type.InSine)  # Плавное затухание
        
        # Связываем анимации в цикл
        self.pulse_up_animation.finished.connect(self.pulse_down_animation.start)
        self.pulse_down_animation.finished.connect(self.pulse_up_animation.start)
        
        # Основная анимация для совместимости
        self.pulse_animation = self.pulse_up_animation
        
        # Настройка виджета
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
    @pyqtProperty(float)
    def animatedValue(self):
        return self._animated_value
    
    @animatedValue.setter
    def animatedValue(self, value):
        self._animated_value = value
        self.update()
    
    @pyqtProperty(float)
    def pulseValue(self):
        return self._pulse_value
    
    @pulseValue.setter
    def pulseValue(self, value):
        self._pulse_value = value
        self.update()
    
    def setValue(self, value):
        """Устанавливает значение с анимацией"""
        value = max(0, min(self._maximum, value))
        if value != self._value:
            self._value = value
            
            # Запускаем анимацию
            self.value_animation.setStartValue(self._animated_value)
            self.value_animation.setEndValue(value)
            self.value_animation.start()
            
            # ИСПРАВЛЕНИЕ: Немедленно обновляем отображение для быстрых обновлений прогресса
            self.update()
            
            # Запускаем плавную пульсацию если прогресс активен
            if value > 0 and value < self._maximum:
                if (self.pulse_up_animation.state() != QPropertyAnimation.State.Running and 
                    self.pulse_down_animation.state() != QPropertyAnimation.State.Running):
                    self.pulse_up_animation.start()  # Начинаем с загорания
            else:
                # Останавливаем обе анимации
                self.pulse_up_animation.stop()
                self.pulse_down_animation.stop()
                self._pulse_value = 1.0
    
    def setMaximum(self, maximum):
        """Устанавливает максимальное значение"""
        self._maximum = maximum
        
    def setText(self, text):
        """Устанавливает текст для отображения"""
        self._text = text
        self.update()
    
    def setDarkTheme(self, is_dark):
        """Переключает между светлой и темной темой"""
        self._is_dark_theme = is_dark
        self.update()
    
    def value(self):
        """Возвращает текущее значение"""
        return self._value
    
    def paintEvent(self, event):
        """Улучшенная отрисовка glassmorphism прогресс-бара с максимальным сглаживанием"""
        painter = QPainter(self)
        # Включаем максимальное сглаживание
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        
        rect = self.rect().adjusted(4, 4, -4, -4)
        
        # === GLASSMORPHISM КОНТЕЙНЕР ===
        
        # Фон как у лога - простой полупрозрачный без градиента
        if self._is_dark_theme:
            # Фон как у лога: rgba(20, 20, 20, 0.6)
            bg_color = QColor(20, 20, 20, 153)  # 0.6 * 255 ≈ 153
            text_color = QColor(255, 255, 255, 220)
        else:
            bg_color = QColor(240, 240, 250, 153)
            text_color = QColor(50, 50, 70, 220)
        
        # Рисуем контейнер с такими же закругленными углами как у лога (25px)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 8), 1))  # Еле заметная обводка как у лога
        painter.drawRoundedRect(rect, 25, 25)
        
        # === УЛУЧШЕННЫЙ ПРОГРЕСС ИНДИКАТОР С ПЛАВНЫМ СВЕЧЕНИЕМ ===
        
        if self._animated_value > 0:
            progress_width = (rect.width() - 12) * (self._animated_value / self._maximum)  # Увеличили отступ
            progress_rect = QRect(rect.x() + 6, rect.y() + 6, int(progress_width), rect.height() - 12)
            
            # Создаем более плавный градиент прогресса с дополнительными точками
            gradient = QLinearGradient(0, 0, progress_rect.width(), 0)
            
            # Плавная пульсация с более мягкими переходами
            base_alpha = int(180 * self._pulse_value)  # Уменьшили базовую прозрачность
            glow_alpha = int(220 * self._pulse_value)  # Добавили свечение
            
            # Многоступенчатый градиент для более плавного перехода
            gradient.setColorAt(0.0, QColor(164, 70, 255, base_alpha))    # A546FF
            gradient.setColorAt(0.2, QColor(184, 85, 255, glow_alpha))    # B855FF  
            gradient.setColorAt(0.4, QColor(208, 101, 255, glow_alpha))   # D065FF
            gradient.setColorAt(0.6, QColor(224, 107, 255, glow_alpha))   # E06BFF
            gradient.setColorAt(0.8, QColor(240, 128, 255, base_alpha))   # Светлее
            gradient.setColorAt(1.0, QColor(255, 150, 255, base_alpha))   # Еще светлее
            
            # Добавляем внутреннее свечение
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Рисуем прогресс с такими же закругленными углами (21px для внутреннего элемента)
            painter.drawRoundedRect(progress_rect, 21, 21)
            
            # Добавляем дополнительное мягкое свечение по краям
            if self._pulse_value > 0.9:  # Только при активной пульсации
                glow_rect = progress_rect.adjusted(-2, -2, 2, 2)
                glow_gradient = QLinearGradient(0, 0, glow_rect.width(), 0)
                
                soft_alpha = int(60 * (self._pulse_value - 0.9) * 10)  # Очень мягкое свечение
                glow_gradient.setColorAt(0.0, QColor(164, 70, 255, soft_alpha))
                glow_gradient.setColorAt(0.5, QColor(208, 101, 255, soft_alpha))
                glow_gradient.setColorAt(1.0, QColor(224, 107, 255, soft_alpha))
                
                painter.setBrush(QBrush(glow_gradient))
                painter.drawRoundedRect(glow_rect, 23, 23)
        
        # === УЛУЧШЕННЫЙ ТЕКСТ И ПРОЦЕНТ (ЛЕВОЕ ВЫРАВНИВАНИЕ, ВЕРТИКАЛЬНОЕ ЦЕНТРИРОВАНИЕ) ===
        
        painter.setPen(text_color)
        font = painter.font()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)  # Немного жирнее для лучшей читаемости
        painter.setFont(font)
        
        # Основной текст - слева, но вертикально отцентрированный, поднят выше
        if self._text:
            text_rect = QRect(rect.x() + 20, rect.y() + 8, rect.width() - 40, 20)  # Поднял с 12 до 8
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._text)
        
        # Процент - слева, но вертикально отцентрированный, поднят выше
        if self._maximum > 0:
            percent = int((self._animated_value / self._maximum) * 100)
            percent_text = f"{percent}%"
            
            font.setPointSize(13)  # Немного больше
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            
            percent_rect = QRect(rect.x() + 20, rect.y() + 32, rect.width() - 40, 20)  # Поднял с 36 до 32
            painter.drawText(percent_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, percent_text)


class NeonGlowButton(QWidget):
    """Современная неоновая кнопка с мягким свечением и стеклянным эффектом"""
    
    clicked = pyqtSignal()  # Сигнал для клика
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("neonGlowBtn")
        
        # Создаем layout для всех элементов
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)  # Уменьшенные отступы для точной области реакции
        layout.setSpacing(8)
        
        # Создаем кастомную кнопку на основе QLabel (без встроенных эффектов Qt)
        self.button = QLabel(text)
        self.button.setObjectName("neonGlowBtnInner")
        self.button.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Устанавливаем обработчики событий мыши на внутренний QLabel
        self.button.mousePressEvent = self._button_mouse_press
        self.button.mouseReleaseEvent = self._button_mouse_release
        self.button.enterEvent = self._button_enter
        self.button.leaveEvent = self._button_leave
        
        # Переменные для отслеживания состояния
        self.is_hovered = False
        self.is_button_pressed = False
        
        # Создаем элемент тени/отражения
        self.reflection = QLabel()
        self.reflection.setObjectName("neonGlowBtnReflection")
        self.reflection.setFixedHeight(6)
        
        layout.addWidget(self.button)
        layout.addWidget(self.reflection)
        
        # Анимации прозрачности
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Пульсирующая анимация (дыхание)
        self.pulse_animation = QPropertyAnimation(self, b"windowOpacity")
        self.pulse_animation.setDuration(2000)
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setStartValue(0.7)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Анимация появления
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(800)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Анимация движения по вертикали (как в навигационном меню)
        self.hover_animation = QPropertyAnimation(self, b"pos")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_pos = None
        self.is_hovered_for_animation = False
        
        self.original_geometry = None
        self.is_pressed = False
        
        # Включаем отслеживание мыши для точного контроля hover области
        self.setMouseTracking(True)
        
        # Таймеры для защиты от дерганий при быстром движении мыши
        self.enter_timer = QTimer()
        self.enter_timer.setSingleShot(True)
        self.enter_timer.timeout.connect(self._delayed_enter)
        
        self.leave_timer = QTimer()
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self._delayed_leave)
        
        # Флаги для отслеживания состояния
        self.pending_enter = False
        self.pending_leave = False
        
    def setText(self, text):
        """Устанавливает текст кнопки"""
        self.button.setText(text)
        
    def setEnabled(self, enabled):
        """Включает/выключает кнопку"""
        super().setEnabled(enabled)
        self.button.setEnabled(enabled)
        
    def start_pulse(self):
        """Запускает пульсирующую анимацию прозрачности"""
        self.pulse_animation.start()
        
    def stop_pulse(self):
        """Останавливает пульсирующую анимацию"""
        self.pulse_animation.stop()
        self.setWindowOpacity(1.0)
    
    def fade_in(self):
        """Плавное появление кнопки"""
        self.setWindowOpacity(0.0)
        self.fade_in_animation.start()
    
    def fade_to_opacity(self, target_opacity, duration=300):
        """Плавный переход к указанной прозрачности"""
        self.opacity_animation.stop()
        self.opacity_animation.setDuration(duration)
        self.opacity_animation.setStartValue(self.windowOpacity())
        self.opacity_animation.setEndValue(target_opacity)
        self.opacity_animation.start()
    
    def blink_error(self):
        """Мерцание при ошибке - быстрое затемнение и возврат"""
        # Создаем последовательность анимаций мерцания
        blink_animation = QPropertyAnimation(self, b"windowOpacity")
        blink_animation.setDuration(150)
        blink_animation.setStartValue(1.0)
        blink_animation.setEndValue(0.3)
        blink_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Анимация возврата
        return_animation = QPropertyAnimation(self, b"windowOpacity")
        return_animation.setDuration(150)
        return_animation.setStartValue(0.3)
        return_animation.setEndValue(1.0)
        return_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Запускаем последовательно
        blink_animation.finished.connect(return_animation.start)
        blink_animation.start()
        
        # Повторяем мерцание 2 раза
        QTimer.singleShot(300, lambda: blink_animation.start())
        QTimer.singleShot(600, lambda: return_animation.start())
    
    def enterEvent(self, event):
        """Плавная анимация при наведении"""
        # Не добавляем проверку позиции здесь - пусть mouseMoveEvent контролирует точность
        self.is_hovered = True
        self.is_hovered_for_animation = True
        
        # Останавливаем пульсацию и делаем кнопку ярче
        self.pulse_animation.stop()
        self.fade_to_opacity(1.0, 200)
        
        # Плавная анимация движения вверх
        if self.original_pos is None:
            self.original_pos = self.pos()
        
        current_pos = self.pos()
        target_pos = QPoint(
            self.original_pos.x(),
            self.original_pos.y() - 4
        )
        
        # Плавно перенаправляем анимацию (без резкой остановки)
        self.hover_animation.setDuration(300)  # Средняя скорость
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuart)  # Плавная кривая
        self.hover_animation.setStartValue(current_pos)
        self.hover_animation.setEndValue(target_pos)
        self.hover_animation.start()
        
        # Применяем hover стиль
        self.button.setObjectName("neonGlowBtnInnerHover")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Максимально плавный возврат к исходной позиции без дерганий"""
        self.is_hovered = False
        self.is_hovered_for_animation = False
        
        # Супер плавная анимация возврата как перышко
        if self.original_pos:
            current_pos = self.pos()
            
            # НЕ останавливаем анимацию резко, а плавно перенаправляем
            # Это ключ к отсутствию дерганий
            
            # Используем самую мягкую кривую и увеличенное время
            self.hover_animation.setDuration(600)  # Очень медленно
            self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuint)  # Самая мягкая кривая
            
            # Плавно меняем направление анимации
            self.hover_animation.setStartValue(current_pos)
            self.hover_animation.setEndValue(self.original_pos)
            
            # Перезапускаем анимацию (без резкой остановки)
            self.hover_animation.start()
        
        # Возвращаем пульсирующую анимацию с большой задержкой для плавности
        if not self.is_pressed:
            QTimer.singleShot(300, self.start_pulse)
        
        # Возвращаем обычный стиль
        self.button.setObjectName("neonGlowBtnInner")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        
        super().leaveEvent(event)
    
    def mouseMoveEvent(self, event):
        """Простое отслеживание мыши"""
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Быстрое затемнение при нажатии и возврат к исходной позиции"""
        # Проверяем, что клик произошел именно на видимой кнопке
        mouse_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        button_rect = self.button.geometry()
        
        # Обрабатываем клик только если он на видимой части кнопки
        if not button_rect.contains(mouse_pos):
            return  # Игнорируем клики в пустых областях
        
        self.is_pressed = True
        self.is_button_pressed = True
        
        # При клике плавно возвращаем в исходную позицию
        if self.original_pos:
            self.hover_animation.setStartValue(self.pos())
            self.hover_animation.setEndValue(self.original_pos)
            self.hover_animation.start()
        
        # Быстро затемняем кнопку
        self.fade_to_opacity(0.6, 100)
        
        # Применяем pressed стиль
        self.button.setObjectName("neonGlowBtnInnerPressed")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Плавный возврат прозрачности после клика"""
        # Проверяем, что отпускание произошло на видимой кнопке
        mouse_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        button_rect = self.button.geometry()
        
        self.is_pressed = False
        
        # Эмитируем сигнал клика только если мышь была нажата И отпущена на кнопке
        if self.is_button_pressed and button_rect.contains(mouse_pos):
            self.clicked.emit()
        
        # Сбрасываем флаг в любом случае
        self.is_button_pressed = False
        
        # Возвращаем прозрачность в зависимости от состояния
        if self.is_hovered:
            self.fade_to_opacity(1.0, 200)
            self.button.setObjectName("neonGlowBtnInnerHover")
        else:
            self.fade_to_opacity(0.8, 200)
            self.start_pulse()
            self.button.setObjectName("neonGlowBtnInner")
        
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
        
        super().mouseReleaseEvent(event)
    
    # Новые обработчики для внутренней кнопки
    def _button_mouse_press(self, event):
        """Обработка нажатия на внутреннюю кнопку с анимацией подпрыгивания"""
        self.is_pressed = True
        self.is_button_pressed = True
        
        # Анимация подпрыгивания при клике
        if self.original_pos:
            # Создаем анимацию подпрыгивания
            self._create_bounce_animation()
        
        # Быстро затемняем кнопку
        self.fade_to_opacity(0.6, 100)
        
        # Применяем pressed стиль
        self.button.setObjectName("neonGlowBtnInnerPressed")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
    
    def _create_bounce_animation(self):
        """Создает анимацию подпрыгивания"""
        if not self.original_pos:
            return
        
        current_pos = self.pos()
        
        # Позиция подпрыгивания (вверх на 8 пикселей)
        bounce_pos = QPoint(
            self.original_pos.x(),
            self.original_pos.y() - 8
        )
        
        # Фаза 1: Быстрый подъем вверх
        bounce_up = QPropertyAnimation(self, b"pos")
        bounce_up.setDuration(100)
        bounce_up.setEasingCurve(QEasingCurve.Type.OutQuad)
        bounce_up.setStartValue(current_pos)
        bounce_up.setEndValue(bounce_pos)
        
        # Фаза 2: Плавное возвращение вниз
        bounce_down = QPropertyAnimation(self, b"pos")
        bounce_down.setDuration(200)
        bounce_down.setEasingCurve(QEasingCurve.Type.OutBounce)  # Эффект отскока
        bounce_down.setStartValue(bounce_pos)
        
        # Определяем конечную позицию в зависимости от состояния hover
        if self.is_hovered:
            # Если мышь на кнопке, возвращаемся в hover позицию
            final_pos = QPoint(self.original_pos.x(), self.original_pos.y() - 2)
        else:
            # Если мыши нет, возвращаемся в исходную позицию
            final_pos = self.original_pos
        
        bounce_down.setEndValue(final_pos)
        
        # Запускаем анимации последовательно
        bounce_up.finished.connect(bounce_down.start)
        bounce_up.start()
    
    def _button_mouse_release(self, event):
        """Обработка отпускания внутренней кнопки"""
        self.is_pressed = False
        
        # Эмитируем сигнал клика
        if self.is_button_pressed:
            self.clicked.emit()
            self.is_button_pressed = False
        
        # Возвращаем прозрачность в зависимости от состояния
        if self.is_hovered:
            self.fade_to_opacity(1.0, 200)
            self.button.setObjectName("neonGlowBtnInnerHover")
        else:
            self.fade_to_opacity(0.8, 200)
            self.start_pulse()
            self.button.setObjectName("neonGlowBtnInner")
        
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
    
    def _button_enter(self, event):
        """Обработка наведения с задержкой для предотвращения дерганий"""
        # Останавливаем таймер leave если он был запущен
        self.leave_timer.stop()
        self.pending_leave = False
        
        # Если уже в hover состоянии, не делаем ничего
        if self.is_hovered:
            return
        
        # Запускаем задержанный enter только если он еще не запущен
        if not self.pending_enter:
            self.pending_enter = True
            self.enter_timer.start(50)  # Задержка 50ms
    
    def _delayed_enter(self):
        """Задержанное выполнение hover анимации"""
        self.pending_enter = False
        
        # Если уже в hover состоянии, не делаем ничего
        if self.is_hovered:
            return
            
        self.is_hovered = True
        self.is_hovered_for_animation = True
        
        # Останавливаем пульсацию и делаем кнопку ярче
        self.pulse_animation.stop()
        self.fade_to_opacity(1.0, 200)
        
        # Плавная анимация движения вверх
        if self.original_pos is None:
            self.original_pos = self.pos()
        
        current_pos = self.pos()
        target_pos = QPoint(
            self.original_pos.x(),
            self.original_pos.y() - 2  # Минимальный подъем при hover
        )
        
        # Проверяем расстояние - анимируем только если есть смысл
        distance = abs(current_pos.y() - target_pos.y())
        if distance > 1:
            self.hover_animation.setDuration(150)  # Быстрее для минимального движения
            self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.hover_animation.setStartValue(current_pos)
            self.hover_animation.setEndValue(target_pos)
            self.hover_animation.start()
        
        # Применяем hover стиль
        self.button.setObjectName("neonGlowBtnInnerHover")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
    
    def _button_leave(self, event):
        """Обработка ухода мыши с задержкой для предотвращения дерганий"""
        # Останавливаем таймер enter если он был запущен
        self.enter_timer.stop()
        self.pending_enter = False
        
        # Если уже не в hover состоянии, не делаем ничего
        if not self.is_hovered:
            return
        
        # Запускаем задержанный leave только если он еще не запущен
        if not self.pending_leave:
            self.pending_leave = True
            self.leave_timer.start(100)  # Задержка 100ms для leave
    
    def _delayed_leave(self):
        """Задержанное выполнение leave анимации"""
        self.pending_leave = False
        
        # Если уже не в hover состоянии, не делаем ничего
        if not self.is_hovered:
            return
            
        self.is_hovered = False
        self.is_hovered_for_animation = False
        
        # Плавная анимация возврата
        if self.original_pos:
            current_pos = self.pos()
            
            # Проверяем расстояние - анимируем только если есть смысл
            distance = abs(current_pos.y() - self.original_pos.y())
            if distance > 1:
                self.hover_animation.setDuration(350)
                self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.hover_animation.setStartValue(current_pos)
                self.hover_animation.setEndValue(self.original_pos)
                self.hover_animation.start()
        
        # Возвращаем пульсирующую анимацию с большой задержкой для плавности
        if not self.is_pressed:
            QTimer.singleShot(300, self.start_pulse)
        
        # Возвращаем обычный стиль
        self.button.setObjectName("neonGlowBtnInner")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)
    
    # Переопределяем старые методы, чтобы они не срабатывали на основном виджете
    def enterEvent(self, event):
        """Отключаем обработку на основном виджете"""
        pass
    
    def leaveEvent(self, event):
        """Отключаем обработку на основном виджете"""
        pass
    
    def mousePressEvent(self, event):
        """Отключаем обработку на основном виджете"""
        pass
    
    def mouseReleaseEvent(self, event):
        """Отключаем обработку на основном виджете"""
        pass


class Modern3DButton(QWidget):
    """3D кнопка с объемным эффектом и тенью как на изображении"""
    
    clicked = pyqtSignal()  # Сигнал для клика
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("modern3DBtn")
        
        # Простая структура с layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 20)
        layout.setSpacing(5)
        
        # Создаем саму кнопку
        self.button = QPushButton(text)
        self.button.setObjectName("modern3DBtnInner")
        self.button.clicked.connect(self.clicked.emit)
        
        # Создаем элемент тени
        self.shadow = QLabel()
        self.shadow.setObjectName("modern3DBtnShadow")
        self.shadow.setFixedHeight(8)
        
        layout.addWidget(self.button)
        layout.addWidget(self.shadow)
        
        # Создаем свечение через стили кнопки
        self.glow = None  # Убираем отдельный элемент свечения
        
        # Анимации
        self.scale_animation = QPropertyAnimation(self, b"geometry")
        self.scale_animation.setDuration(300)  # Более медленная анимация
        self.scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # Более плавная кривая
        
        # Убираем анимацию свечения, так как glow элемента больше нет
        self.glow_animation = None
        
        # Пульсирующий эффект для всей кнопки
        self.pulse_animation = QPropertyAnimation(self, b"windowOpacity")
        self.pulse_animation.setDuration(2000)
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setStartValue(0.9)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.original_geometry = None
        self.is_pressed = False
        
    def setText(self, text):
        """Устанавливает текст кнопки"""
        self.button.setText(text)
        
    def setEnabled(self, enabled):
        """Включает/выключает кнопку"""
        super().setEnabled(enabled)
        self.button.setEnabled(enabled)
        
    def start_pulse(self):
        """Запускает пульсирующий эффект"""
        self.pulse_animation.start()
        
    def stop_pulse(self):
        """Останавливает пульсирующий эффект"""
        self.pulse_animation.stop()
        self.setWindowOpacity(1.0)
    
    def enterEvent(self, event):
        """Анимация при наведении - легкое увеличение и усиление свечения"""
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        
        # Увеличиваем кнопку на 3%
        current_rect = self.geometry()
        scale_factor = 1.03
        new_width = int(current_rect.width() * scale_factor)
        new_height = int(current_rect.height() * scale_factor)
        
        # Центрируем увеличенную кнопку
        new_x = current_rect.x() - (new_width - current_rect.width()) // 2
        new_y = current_rect.y() - (new_height - current_rect.height()) // 2
        
        target_rect = QRect(new_x, new_y, new_width, new_height)
        
        self.scale_animation.setStartValue(current_rect)
        self.scale_animation.setEndValue(target_rect)
        self.scale_animation.start()
        
        # Свечение теперь управляется через CSS outline в стилях
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Возврат к исходному размеру и обычному свечению"""
        if self.original_geometry and not self.is_pressed:
            self.scale_animation.setStartValue(self.geometry())
            self.scale_animation.setEndValue(self.original_geometry)
            self.scale_animation.start()
        
        # Свечение управляется через CSS
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Эффект нажатия - имитация вдавливания с уменьшением тени"""
        self.is_pressed = True
        
        if self.original_geometry:
            # Уменьшаем кнопку и сдвигаем вниз для реалистичного вдавливания
            current_rect = self.geometry()
            scale_factor = 0.96
            new_width = int(current_rect.width() * scale_factor)
            new_height = int(current_rect.height() * scale_factor)
            
            new_x = current_rect.x() + (current_rect.width() - new_width) // 2
            new_y = current_rect.y() + (current_rect.height() - new_height) // 2 + 3  # Сдвигаем вниз
            
            pressed_rect = QRect(new_x, new_y, new_width, new_height)
            
            # Быстрая анимация нажатия
            press_animation = QPropertyAnimation(self, b"geometry")
            press_animation.setDuration(60)
            press_animation.setStartValue(current_rect)
            press_animation.setEndValue(pressed_rect)
            press_animation.start()
            
            # Уменьшаем тень при нажатии
            self.shadow.setStyleSheet("""
                #modern3DBtnShadow {
                    background: qradial-gradient(ellipse at center,
                        rgba(107, 33, 168, 0.3) 0%,
                        rgba(107, 33, 168, 0.2) 30%,
                        rgba(107, 33, 168, 0.1) 60%,
                        transparent 80%);
                    border: none;
                    border-radius: 25px;
                    margin: 0px 20px;
                }
            """)
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Возврат после отпускания кнопки"""
        self.is_pressed = False
        
        if self.original_geometry:
            # Возвращаемся к hover состоянию
            current_rect = self.original_geometry
            scale_factor = 1.03
            new_width = int(current_rect.width() * scale_factor)
            new_height = int(current_rect.height() * scale_factor)
            
            new_x = current_rect.x() - (new_width - current_rect.width()) // 2
            new_y = current_rect.y() - (new_height - current_rect.height()) // 2
            
            hover_rect = QRect(new_x, new_y, new_width, new_height)
            
            return_animation = QPropertyAnimation(self, b"geometry")
            return_animation.setDuration(150)
            return_animation.setStartValue(self.geometry())
            return_animation.setEndValue(hover_rect)
            return_animation.start()
            
            # Восстанавливаем тень
            self.shadow.setStyleSheet("")  # Возвращаем к стилям по умолчанию
        
        super().mouseReleaseEvent(event)


class AnimatedAuthButton(Modern3DButton):
    """Наследуем от 3D кнопки для совместимости"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("animatedAuthBtn")


class WelcomeBackOverlay(QWidget):
    """Приветственный overlay для уже авторизованных пользователей"""
    
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.keep_blur_on_logout = False  # Флаг для сохранения блюра при выходе
        self.init_ui()
        
        # Убираем автоматическое закрытие - окно закрывается только по кнопке
    
    def init_ui(self):
        """Инициализация приветственного интерфейса в стиле оригинального окна авторизации"""
        # Делаем overlay на весь экран родителя
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Центральная карточка в том же стиле что и авторизация
        self.welcome_card = QFrame()
        self.welcome_card.setObjectName("authCard")  # Используем тот же стиль что и у авторизации
        self.welcome_card.setFixedSize(600, 700)  # Тот же размер что и у авторизации
        
        card_layout = QVBoxLayout(self.welcome_card)
        card_layout.setContentsMargins(50, 30, 50, 30)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок в том же стиле
        self.create_header(card_layout)
        
        # Приветственное описание
        self.create_welcome_description(card_layout)
        
        # Кнопки
        self.create_welcome_buttons(card_layout)
        
        # Статус
        self.create_welcome_status(card_layout)
        
        main_layout.addWidget(self.welcome_card)
        
        # Применяем те же стили что и у авторизации
        self.setStyleSheet(self.get_overlay_styles())
    
    def create_header(self, layout):
        """Создает заголовок точно как в оригинальном окне авторизации"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(2)
        
        # Логотип приложения - точно такой же как в авторизации
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_label = QLabel()
        logo_path = str(get_asset_path("logow.jpg"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("🎮")
            logo_label.setStyleSheet("font-size: 100px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedSize(140, 140)
        
        logo_container.addWidget(logo_label)
        header_layout.addLayout(logo_container)
        
        # Название приложения - точно такое же
        title_label = QLabel("RU-MINETOOLS NEW")
        title_label.setObjectName("overlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок - точно такой же
        subtitle_label = QLabel("by Русский Квестбук")
        subtitle_label.setObjectName("overlaySubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_welcome_description(self, layout):
        """Создает приветственное описание"""
        # Получаем имя пользователя
        if self.user_data:
            first_name = self.user_data.get("first_name", "")
            last_name = self.user_data.get("last_name", "")
            username = self.user_data.get("username", "")
            
            if first_name and last_name:
                display_name = f"{first_name} {last_name}"
            elif first_name:
                display_name = first_name
            elif username:
                display_name = f"@{username}"
            else:
                display_name = "Пользователь"
        else:
            display_name = "Пользователь"
        
        desc_label = QLabel(
            f"С возвращением, {display_name}!\n\n"
            f"Вы уже авторизованы в системе\n"
            f"и можете продолжить работу\n\n"
            f"✦ Все ваши настройки сохранены\n"
            f"✦ Доступ к переводам активен"
        )
        desc_label.setObjectName("overlayDescription")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
    def create_welcome_buttons(self, layout):
        """Создает кнопки в том же стиле что и авторизация"""
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(-20)  # Еще больше отрицательный отступ
        
        # Главная кнопка продолжения - точно такая же как ВОЙТИ (без специального objectName)
        self.continue_btn = NeonGlowButton("ПРОДОЛЖИТЬ")
        self.continue_btn.clicked.connect(self.hide_overlay)
        
        # Запускаем эффект появления кнопки
        QTimer.singleShot(500, self.continue_btn.fade_in)
        
        # Запускаем пульсирующий эффект
        self.continue_btn.start_pulse()
        
        buttons_layout.addWidget(self.continue_btn)
        
        # Добавляем еще больший отрицательный отступ между кнопками
        buttons_layout.addSpacing(-30)
        
        # Кнопка выхода - тоже NeonGlowButton но с серым стилем
        self.logout_btn = NeonGlowButton("Выйти из аккаунта")
        self.logout_btn.setObjectName("neonGlowBtnGray")  # Используем серый стиль
        self.logout_btn.clicked.connect(self.logout_user)
        buttons_layout.addWidget(self.logout_btn)
        
        layout.addLayout(buttons_layout)
        
        # Добавляем отрицательный отступ перед статусом чтобы поднять его ближе к кнопкам
        layout.addSpacing(-25)  # Поднимаем статус ближе к кнопкам
    
    def create_welcome_status(self, layout):
        """Создает статус в том же стиле что и авторизация"""
        self.status_label = QLabel("Нажмите 'ПРОДОЛЖИТЬ' для входа в приложение")
        self.status_label.setObjectName("overlayStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
    
    def hide_overlay(self):
        """Скрывает overlay с анимацией"""
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self._remove_blur_and_delete)
        self.fade_out_animation.start()
    
    def _remove_blur_and_delete(self):
        """Убирает блюр и удаляет overlay"""
        
        # Проверяем, будет ли показано приветственное окно
        will_show_welcome = (not self.keep_blur_on_logout and 
                           self.parent() and 
                           hasattr(self.parent(), 'show_beta_warning_dialog'))
        
        if will_show_welcome:
            # НЕ убираем блюр - пусть приветственное окно само управляет блюром
            logger.debug("🌫️ Блюр НЕ удален - передаем управление приветственному окну (WelcomeBack)")
        elif not self.keep_blur_on_logout and self.parent():
            # Убираем блюр только если не выходим из аккаунта и не будет приветственного окна
            if hasattr(self.parent(), 'remove_blur_effect'):
                self.parent().remove_blur_effect()
            else:
                self.parent().setGraphicsEffect(None)
            logger.debug("🌫️ Блюр удален (WelcomeBack)")
        
        # Обновляем профиль пользователя в sidebar (только если не выходим)
        if not self.keep_blur_on_logout and self.user_data and self.parent() and hasattr(self.parent(), 'sidebar'):
            self.parent().sidebar.update_user_profile(self.user_data)
        
        # Показываем приветственное уведомление (только если не выходим)
        if not self.keep_blur_on_logout and self.parent() and hasattr(self.parent(), 'show_welcome_notification'):
            welcome_msg = f"ДОБРО ПОЖАЛОВАТЬ ОБРАТНО!\nВход выполнен автоматически"
            self.parent().show_welcome_notification(welcome_msg)
        
        # Удаляем overlay
        self.deleteLater()
    
    def logout_user(self):
        """Выход из аккаунта"""
        auth_file = "telegram_auth.json"
        guest_file = "guest_access.json"
        
        # Удаляем файлы авторизации
        if os.path.exists(auth_file):
            os.remove(auth_file)
        if os.path.exists(guest_file):
            os.remove(guest_file)
        
        # Устанавливаем флаг чтобы не удалять блюр при закрытии
        self.keep_blur_on_logout = True
        
        # СНАЧАЛА отключаем ВСЕ сигналы от текущего overlay
        try:
            # Отключаем сигнал destroyed от функции remove_blur_effect
            if self.parent() and hasattr(self.parent(), 'remove_blur_effect'):
                self.destroyed.disconnect(self.parent().remove_blur_effect)
        except:
            pass
        
        # Скрываем и удаляем текущий overlay БЕЗ удаления блюра
        self.hide()
        
        # Создаем новый overlay авторизации с блюром
        if self.parent():
            # Принудительно применяем блюр заново с анимацией
            self.parent().blur_effect = self.parent().animate_blur_in(
                self.parent().centralWidget(), 
                target_radius=15, 
                duration=400
            )
            
            # Создаем новый overlay авторизации
            new_overlay = TelegramAuthOverlay(self.parent())
            self.parent().auth_overlay = new_overlay
            
            # Плавное появление нового overlay
            new_overlay.setWindowOpacity(0.0)
            new_overlay.show()
            new_overlay.raise_()
            
            # Анимация появления
            fade_in = QPropertyAnimation(new_overlay, b"windowOpacity")
            fade_in.setDuration(400)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_in.start()
            
            # Подключаем сигнал для безопасного удаления блюра ТОЛЬКО к новому overlay
            new_overlay.destroyed.connect(self.parent().remove_blur_effect)
        
        # Удаляем текущий overlay ПОСЛЕ создания нового
        self.deleteLater()
    
    def get_overlay_styles(self):
        """Те же стили что и у оригинального окна авторизации"""
        return """
        WelcomeBackOverlay {
            background-color: transparent;
        }
        
        #authCard {
            background-color: transparent;
            border: none;
        }
        
        #overlayTitle {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        }
        
        #overlaySubtitle {
            font-size: 15px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        }
        
        #overlayDescription {
            font-size: 14px;
            color: #e8e8e8;
            background-color: transparent;
        }
        
        #overlayStatus {
            font-size: 13px;
            color: #bb86fc;
            background-color: transparent;
            font-weight: 600;
        }
        
        QPushButton {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            padding: 15px 25px;
            min-height: 25px;
        }
        
        QPushButton:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        QPushButton:pressed {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
        }
        
        #overlaySubscribeBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.5 #d1a7ff, stop:1 #bb86fc);
            border: 2px solid #9966cc;
            color: #ffffff;
            font-weight: 700;
            padding: 18px 25px;
            min-height: 30px;
            border-radius: 15px;
        }
        
        #overlaySubscribeBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #d1a7ff, stop:0.5 #e6ccff, stop:1 #d1a7ff);
            border-color: #aa77dd;
            color: #ffffff;
        }
        
        #overlaySubscribeBtn:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9966cc, stop:0.5 #bb86fc, stop:1 #9966cc);
            border-color: #8855bb;
        }
        
        #overlayLogoutBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6b7280, stop:0.5 #9ca3af, stop:1 #6b7280);
            border: 2px solid #4b5563;
            color: #ffffff;
            font-weight: 700;
            padding: 18px 25px;
            min-height: 30px;
            border-radius: 15px;
        }
        
        #overlayLogoutBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9ca3af, stop:0.5 #d1d5db, stop:1 #9ca3af);
            border-color: #6b7280;
            color: #ffffff;
        }
        
        #overlayLogoutBtn:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4b5563, stop:0.5 #6b7280, stop:1 #4b5563);
            border-color: #374151;
        }
        
        /* Серая версия NeonGlowButton для кнопки выхода */
        #neonGlowBtnGray {
            background: transparent;
            border: none;
        }
        
        #neonGlowBtnGray #neonGlowBtnInner {
            /* Серый градиент */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6b7280,
                stop:0.3 #7c8591,
                stop:0.7 #9ca3af,
                stop:1 #a1a8b6);
            
            /* Те же параметры что и у фиолетовой кнопки */
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            
            /* Серое свечение */
            outline: 8px solid rgba(107, 114, 128, 0.3);
            outline-offset: 4px;
            
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
            selection-background-color: transparent;
            selection-color: #ffffff;
        }
        
        #neonGlowBtnGray #neonGlowBtnInnerHover {
            /* Светло-серый при hover */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7c8591,
                stop:0.3 #8d94a2,
                stop:0.7 #a1a8b6,
                stop:1 #b5bcc7);
            
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 1px solid rgba(255, 255, 255, 0.4);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            
            /* Более яркое серое свечение */
            outline: 12px solid rgba(107, 114, 128, 0.5);
            outline-offset: 6px;
            
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnGray #neonGlowBtnInnerPressed {
            /* Темно-серый при нажатии */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4b5563,
                stop:0.3 #5d6570,
                stop:0.7 #6b7280,
                stop:1 #7c8591);
            
            border-radius: 25px;
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(0, 0, 0, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            
            outline: 6px solid rgba(107, 114, 128, 0.4);
            outline-offset: 2px;
            
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnGray #neonGlowBtnReflection {
            /* Серое отражение/тень */
            background: qradial-gradient(ellipse at center,
                rgba(107, 114, 128, 0.4) 0%,
                rgba(107, 114, 128, 0.2) 40%,
                rgba(107, 114, 128, 0.1) 70%,
                transparent 100%);
            border: none;
            border-radius: 25px;
            margin: 0px 20px;
        }
        
        /* Стили NeonGlowButton для приветственного экрана */
        #neonGlowBtn {
            background: transparent;
            border: none;
        }
        
        #neonGlowBtnInner {
            /* Футуристический градиент от фиолетового к розовому */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #A546FF,
                stop:0.3 #B855FF,
                stop:0.7 #D065FF,
                stop:1 #E06BFF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Стеклянный эффект с внутренним свечением */
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            
            /* Внешнее неоновое свечение */
            outline: 8px solid rgba(165, 70, 255, 0.3);
            outline-offset: 4px;
            
            /* Текст */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
            
            /* Отключаем стандартные эффекты Qt */
            selection-background-color: transparent;
            selection-color: #ffffff;
        }
        
        #neonGlowBtnInnerHover {
            /* Усиленное свечение при наведении */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #B855FF,
                stop:0.3 #C965FF,
                stop:0.7 #E075FF,
                stop:1 #F080FF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Усиленные границы */
            border-top: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 1px solid rgba(255, 255, 255, 0.4);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            
            /* Более яркое внешнее свечение */
            outline: 12px solid rgba(165, 70, 255, 0.5);
            outline-offset: 6px;
            
            /* Текст */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnInnerPressed {
            /* Эффект вдавливания без артефактов */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9540E6,
                stop:0.3 #A650F0,
                stop:0.7 #C060FF,
                stop:1 #D565FF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Инвертированные границы */
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(0, 0, 0, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            
            /* Уменьшенное свечение при нажатии */
            outline: 6px solid rgba(165, 70, 255, 0.4);
            outline-offset: 2px;
            
            /* Чистый белый текст без артефактов */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnReflection {
            /* Отражение/тень под кнопкой */
            background: qradial-gradient(ellipse at center,
                rgba(165, 70, 255, 0.4) 0%,
                rgba(165, 70, 255, 0.2) 40%,
                rgba(165, 70, 255, 0.1) 70%,
                transparent 100%);
            border: none;
            border-radius: 25px;
            margin: 0px 20px;
        }
        """
    
    def resizeEvent(self, event):
        """Обновляет размер overlay при изменении размера родителя"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)


class TelegramAuthOverlay(QWidget):
    """Overlay авторизации поверх главного интерфейса с блюром"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Загружаем настройки Telegram бота из конфигурации
        self.BOT_TOKEN = None
        self.CHANNEL_USERNAME = "@ruquestbook"
        self.CHANNEL_ID = None
        self._load_bot_config()
        
        # Файл для сохранения данных авторизации
        self.auth_file = "telegram_auth.json"
        self.guest_file = "guest_access.json"  # Файл для гостевого доступа
        self.user_data = None
        
        # Флаги состояния бота
        self.bot_available = None  # None - не проверено, True - доступен, False - недоступен
        self.bot_check_timeout = 8  # Таймаут проверки бота в секундах
        
        # Флаг для пропуска создания блюра (используется при переходе от WelcomeBackOverlay)
        self.skip_blur_creation = getattr(self, 'skip_blur_creation', False)
        
        self.init_ui()
        self.check_saved_auth()
    
    def _load_bot_config(self):
        """Загружает конфигурацию Telegram бота из файла"""
        try:
            config_path = get_config_path("bot_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.BOT_TOKEN = config.get("BOT_TOKEN")
                    self.CHANNEL_ID = config.get("CHANNEL_ID")
                    
                    if not self.BOT_TOKEN or not self.CHANNEL_ID:
                        logging.error("Неполная конфигурация бота в bot_config.json")
                        self.BOT_TOKEN = None
                        self.CHANNEL_ID = None
                    else:
                        logging.info("Конфигурация бота успешно загружена")
            else:
                logging.warning(f"Файл конфигурации бота не найден: {config_path}")
                logging.info("Используйте config/bot_config.example.json как шаблон")
        except Exception as e:
            logging.error(f"Ошибка загрузки конфигурации бота: {e}")
            self.BOT_TOKEN = None
            self.CHANNEL_ID = None
    
    def init_ui(self):
        """Инициализация overlay интерфейса"""
        # Делаем overlay на весь экран родителя
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Черный фон без прозрачности
        self.setStyleSheet("""
            TelegramAuthOverlay {
                background-color: #0a0a0a;
            }
        """)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)  # Центр по горизонтали, верх по вертикали
        main_layout.setContentsMargins(50, 10, 50, 50)  # Еще больше уменьшаем верхний отступ
        
        # Центральная карточка авторизации - увеличиваем высоту для кнопок
        self.auth_card = QFrame()
        self.auth_card.setObjectName("authCard")
        self.auth_card.setFixedSize(600, 800)  # Увеличена высота для размещения кнопок
        
        card_layout = QVBoxLayout(self.auth_card)
        card_layout.setContentsMargins(50, 30, 50, 30)  # Равные отступы для центрирования
        card_layout.setSpacing(12)  # Уменьшаем отступы между элементами для компактности
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Центрируем все элементы
        
        # Заголовок
        self.create_header(card_layout)
        
        # Описание
        self.create_description(card_layout)
        
        # Кнопки
        self.create_buttons(card_layout)
        
        # Статус
        self.create_status(card_layout)
        
        main_layout.addWidget(self.auth_card)
        
        # Применяем стили
        self.setStyleSheet(self.get_overlay_styles())
    
    def create_header(self, layout):
        """Создает заголовок в стиле приложения"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(2)  # Уменьшаем отступы в заголовке чтобы поднять "by Русский Квестбук"
        
        # Логотип приложения - оптимальный размер
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_label = QLabel()
        logo_path = str(get_asset_path("logow.jpg"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)  # Оптимальный размер 140
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("🎮")
            logo_label.setStyleSheet("font-size: 100px;")  # Оптимальный размер эмодзи
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedSize(140, 140)  # Оптимальный размер контейнера
        
        logo_container.addWidget(logo_label)
        header_layout.addLayout(logo_container)
        
        # Название приложения
        title_label = QLabel("RU-MINETOOLS NEW")
        title_label.setObjectName("overlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("by Русский Квестбук")
        subtitle_label.setObjectName("overlaySubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        # Сохраняем ссылку на подзаголовок для возможности скрытия
        self.subtitle_label = subtitle_label
        
        layout.addLayout(header_layout)
    
    def create_description(self, layout):
        """Создает описание в стиле приложения"""
        desc_label = QLabel(
            f"Профессиональный инструмент для работы\n"
            f"с квестами и модификациями Minecraft\n\n"
            f"✦ Перевод модов\n"
            f"✦ Перевод квестов FTB"
        )
        desc_label.setObjectName("overlayDescription")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Сохраняем ссылку на описание для возможности скрытия
        self.description_label = desc_label
    
    def _hide_description(self):
        """Скрывает только описание приложения, оставляя подзаголовок видимым"""
        if hasattr(self, 'description_label'):
            # Не просто скрываем, а полностью удаляем из layout чтобы заголовок поднялся
            self.description_label.setParent(None)
            self.description_label.deleteLater()
        # Подзаголовок "by Русский Квестбук" остается видимым
    
    def create_buttons(self, layout):
        """Создает кнопки в стиле приложения"""
        # Добавляем отрицательный отступ чтобы поднять кнопки ближе к описанию (уменьшаем для опускания кнопки)
        layout.addSpacing(-8)  # Было -15, делаем -8 чтобы кнопка была чуть ниже
        
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(25)  # Возвращаем исходные отступы между кнопками
        
        # Неоновая кнопка входа с мягким свечением
        self.main_btn = NeonGlowButton("ВОЙТИ")
        self.main_btn.clicked.connect(self.start_simple_auth)
        
        # Запускаем эффект появления кнопки
        QTimer.singleShot(500, self.main_btn.fade_in)
        
        # Запускаем пульсирующий эффект для привлечения внимания
        self.main_btn.start_pulse()
        
        # Добавляем таймер для изменения текста кнопки
        self.button_text_timer = QTimer()
        self.button_text_timer.timeout.connect(self.animate_button_text)
        self.button_text_timer.start(3000)  # Каждые 3 секунды
        self.button_text_variants = ["ВОЙТИ", "НАЧАТЬ", "ВОЙТИ", "СТАРТ"]
        self.current_text_index = 0
        
        buttons_layout.addWidget(self.main_btn)
        
        layout.addLayout(buttons_layout)
    
    def animate_button_text(self):
        """Анимирует текст кнопки входа с плавным затуханием и появлением"""
        if hasattr(self, 'main_btn') and self.main_btn.isVisible():
            # НЕ МЕНЯЕМ ТЕКСТ если мышь на кнопке (чтобы не конфликтовать с hover анимацией)
            if hasattr(self.main_btn, 'is_hovered') and self.main_btn.is_hovered:
                return
            
            # Получаем новый текст
            self.current_text_index = (self.current_text_index + 1) % len(self.button_text_variants)
            new_text = self.button_text_variants[self.current_text_index]
            
            # Простая смена текста без анимации прозрачности (чтобы не конфликтовать)
            self.main_btn.setText(new_text)
    
    def shake_input_field(self):
        """Эффект дрожания поля ввода при ошибке"""
        if hasattr(self, 'code_input'):
            original_pos = self.code_input.pos()
            
            # Создаем анимацию дрожания
            shake_animation = QPropertyAnimation(self.code_input, b"pos")
            shake_animation.setDuration(500)
            shake_animation.setLoopCount(3)
            
            # Позиции для дрожания (влево-вправо)
            shake_positions = [
                QPoint(original_pos.x() - 5, original_pos.y()),
                QPoint(original_pos.x() + 5, original_pos.y()),
                QPoint(original_pos.x() - 3, original_pos.y()),
                QPoint(original_pos.x() + 3, original_pos.y()),
                original_pos
            ]
            
            # Запускаем анимацию дрожания
            for i, pos in enumerate(shake_positions):
                QTimer.singleShot(i * 100, lambda p=pos: self.code_input.move(p))
            
            # Временно меняем стиль поля на красный
            error_style = """
                QLineEdit {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3a1a1a, stop:0.5 #4a2a2a, stop:1 #3a1a1a);
                    border: 3px solid #ff6b6b;
                    border-radius: 15px;
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 700;
                    padding: 15px 20px;
                    min-height: 20px;
                    letter-spacing: 3px;
                    text-align: center;
                }
            """
            self.code_input.setStyleSheet(error_style)
            
            # Возвращаем обычный стиль через 2 секунды
            QTimer.singleShot(2000, self.restore_input_style)
    
    def restore_input_style(self):
        """Восстанавливает обычный стиль поля ввода"""
        if hasattr(self, 'code_input'):
            normal_style = """
                QLineEdit {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a);
                    border: 3px solid #bb86fc;
                    border-radius: 15px;
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: 700;
                    padding: 15px 20px;
                    min-height: 20px;
                    letter-spacing: 3px;
                    text-align: center;
                }
                QLineEdit:focus {
                    border: 3px solid #d1a7ff;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2a2a2a, stop:0.5 #3a3a3a, stop:1 #2a2a2a);
                }
                QLineEdit::placeholder {
                    color: rgba(187, 134, 252, 0.7);
                    font-weight: 500;
                }
            """
            self.code_input.setStyleSheet(normal_style)
    
    def create_status(self, layout):
        """Создает статус"""
        # Добавляем минимальный отрицательный отступ для максимальной компактности
        layout.addSpacing(-30)  # Поднимаем подсказку еще ближе к кнопке
        
        self.status_label = QLabel("Нажмите 'ВОЙТИ' для получения доступа")
        self.status_label.setObjectName("overlayStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        # Ограничиваем максимальную ширину чтобы не ломать интерфейс
        self.status_label.setMaximumWidth(520)
        self.status_label.setMaximumHeight(220)  # Увеличиваем высоту для окна ошибки
        layout.addWidget(self.status_label)
        
        # Прогресс бар (стилизованный QProgressBar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("overlayProgress")
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
    
    def start_simple_auth(self):
        """Финальный упрощенный процесс авторизации с проверкой доступности бота"""
        # Удаляем предыдущие кнопки выбора если они есть
        if hasattr(self, 'fallback_buttons_widget'):
            card_layout = self.auth_card.layout()
            card_layout.removeWidget(self.fallback_buttons_widget)
            self.fallback_buttons_widget.deleteLater()
            delattr(self, 'fallback_buttons_widget')
        
        # Показываем основную кнопку обратно
        self.main_btn.setVisible(True)
        
        # Сначала проверяем доступность бота
        self.status_label.setText("Проверяем доступность бота...")
        self.main_btn.setEnabled(False)
        
        # Запускаем проверку бота в отдельном потоке
        threading.Thread(target=self._check_bot_availability, daemon=True).start()
    
    def _check_bot_availability(self):
        """Проверяет доступность бота и функции авторизации в Yandex Cloud"""
        try:
            # Проверяем наличие токена бота
            if not self.BOT_TOKEN:
                logger.error("BOT_TOKEN не настроен - авторизация через бота недоступна")
                self.bot_available = False
                QTimer.singleShot(0, self._handle_bot_unavailable)
                return
            
            # Проверяем доступность Telegram API бота
            test_url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/getMe"
            response = requests.get(test_url, timeout=self.bot_check_timeout)
            
            if response.status_code != 200 or not response.json().get("ok"):
                self.bot_available = False
                QTimer.singleShot(0, self._handle_bot_unavailable)
                return
            
            # Теперь проверяем функцию авторизации в Yandex Cloud
            
            yandex_url = f"https://d5dq2g7pcv53nkqcsp1p.svoluuab.apigw.yandexcloud.net/check/test123"
            yandex_response = requests.get(yandex_url, timeout=self.bot_check_timeout)
            
            # Проверяем что функция отвечает (даже если код не найден - это нормально)
            if yandex_response.status_code == 200:
                try:
                    yandex_data = yandex_response.json()
                    # Если получили JSON ответ - функция работает
                    self.bot_available = True
                    QTimer.singleShot(0, self._proceed_with_bot_auth)
                    return
                except:
                    # Если не JSON - функция не работает правильно
                    pass
            
            # Если дошли сюда - функция Yandex Cloud недоступна
            self.bot_available = False
            QTimer.singleShot(0, self._handle_bot_unavailable)
                
        except requests.exceptions.Timeout:
            self.bot_available = False
            QTimer.singleShot(0, self._handle_bot_unavailable)
        except Exception as e:
            self.bot_available = False
            QTimer.singleShot(0, self._handle_bot_unavailable)
    
    def _proceed_with_bot_auth(self):
        """Продолжает обычную авторизацию через бота"""
        # Обновляем статус
        self.status_label.setText("Открываем бота для авторизации...")
        self.main_btn.setEnabled(False)
        
        # Открываем бота (размещенного на Yandex Cloud для 24/7 работы)
        bot_url = "https://t.me/ru_minetools_auth_bot"
        webbrowser.open(bot_url)
        
        # Показываем финальную инструкцию
        QTimer.singleShot(1000, self.show_final_instruction)
    
    def _handle_bot_unavailable(self):
        """Обрабатывает ситуацию когда система авторизации недоступна"""
        # Скрываем заголовок и описание для более компактного вида
        self._hide_header_and_description()
        
        # Оптимизируем отступы карточки для компактного окна ошибки
        card_layout = self.auth_card.layout()
        card_layout.setContentsMargins(30, 20, 30, 20)  # Уменьшаем отступы
        card_layout.setSpacing(8)  # Минимальные отступы между элементами
        
        # Устанавливаем более компактный и читаемый текст
        self.status_label.setText(
            "⚠️ СИСТЕМА АВТОРИЗАЦИИ НЕДОСТУПНА\n\n"
            "Возможные причины:\n"
            "• Проблемы с интернетом\n"
            "• Технические работы\n"
            "• Блокировка Telegram\n"
            "• Недоступность сервиса\n\n"
            "Войдите в гостевом режиме\n"
            "с базовым функционалом"
        )
        
        # Применяем специальные стили для окна ошибки
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #ffffff;
                background-color: transparent;
                line-height: 1.4;
                padding: 5px;
                margin: 0px;
            }
        """)
        
        # Создаем кнопки выбора
        self._create_fallback_buttons()
    
    def _hide_header_and_description(self):
        """Скрывает заголовок и описание для компактного вида окна ошибки"""
        card_layout = self.auth_card.layout()
        
        # Проходим по всем элементам layout и скрываем ненужные
        for i in range(card_layout.count()):
            item = card_layout.itemAt(i)
            if item:
                widget = item.widget()
                layout_item = item.layout()
                
                # Скрываем виджеты с описанием
                if widget and hasattr(widget, 'objectName'):
                    obj_name = widget.objectName()
                    if obj_name in ['overlayTitle', 'overlaySubtitle', 'overlayDescription']:
                        widget.setVisible(False)
                
                # Скрываем layout с заголовком (содержит логотип)
                if layout_item:
                    for j in range(layout_item.count()):
                        sub_item = layout_item.itemAt(j)
                        if sub_item and sub_item.widget():
                            sub_widget = sub_item.widget()
                            # Скрываем логотип и заголовки
                            if hasattr(sub_widget, 'objectName'):
                                obj_name = sub_widget.objectName()
                                if obj_name in ['overlayTitle', 'overlaySubtitle']:
                                    sub_widget.setVisible(False)
                            # Скрываем QLabel без objectName (логотип)
                            elif isinstance(sub_widget, QLabel) and not hasattr(sub_widget, 'objectName'):
                                sub_widget.setVisible(False)
                        # Скрываем layout с логотипом
                        elif sub_item and sub_item.layout():
                            for k in range(sub_item.layout().count()):
                                logo_item = sub_item.layout().itemAt(k)
                                if logo_item and logo_item.widget():
                                    logo_item.widget().setVisible(False)
    
    def _create_fallback_buttons(self):
        """Создает кнопки для выбора при недоступности бота"""
        # Находим layout кнопок
        card_layout = self.auth_card.layout()
        
        # Удаляем предыдущие кнопки если они есть
        if hasattr(self, 'fallback_buttons_widget'):
            card_layout.removeWidget(self.fallback_buttons_widget)
            self.fallback_buttons_widget.deleteLater()
        
        # Создаем контейнер для кнопок с минимальными отступами
        buttons_container = QVBoxLayout()
        buttons_container.setSpacing(0)  # Убираем spacing полностью
        buttons_container.setContentsMargins(0, 0, 0, 0)  # Убираем все отступы
        buttons_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Кнопка повторной попытки
        retry_btn = NeonGlowButton("ПОВТОРИТЬ ПРОВЕРКУ")
        retry_btn.clicked.connect(self._retry_authorization)  # Подключаем к новому методу
        retry_btn.setObjectName("retryBtn")
        
        # Кнопка гостевого входа
        guest_btn = NeonGlowButton("ВОЙТИ КАК ГОСТЬ")
        guest_btn.clicked.connect(self._enter_as_guest)
        guest_btn.setObjectName("guestBtn")
        
        # Запускаем эффекты появления кнопок
        QTimer.singleShot(200, retry_btn.fade_in)
        QTimer.singleShot(400, guest_btn.fade_in)
        
        buttons_container.addWidget(retry_btn)
        buttons_container.addSpacing(-15)  # Отрицательный отступ между кнопками
        buttons_container.addWidget(guest_btn)
        
        # Создаем виджет-контейнер
        self.fallback_buttons_widget = QWidget()
        self.fallback_buttons_widget.setLayout(buttons_container)
        
        # Добавляем отрицательный отступ перед кнопками чтобы убрать большой промежуток
        card_layout.addSpacing(-5)  # Уменьшаем отрицательный отступ чтобы опустить кнопки
        
        # Вставляем кнопки ПОСЛЕ статуса (текста), а не перед ним
        card_layout.addWidget(self.fallback_buttons_widget)
        
        # Скрываем старую кнопку
        self.main_btn.setVisible(False)
    
    def _retry_authorization(self):
        """Повторная попытка авторизации - сброс к исходному состоянию"""
        # Удаляем кнопки ошибки
        if hasattr(self, 'fallback_buttons_widget'):
            card_layout = self.auth_card.layout()
            card_layout.removeWidget(self.fallback_buttons_widget)
            self.fallback_buttons_widget.deleteLater()
            delattr(self, 'fallback_buttons_widget')
        
        # Восстанавливаем исходные отступы карточки
        card_layout = self.auth_card.layout()
        card_layout.setContentsMargins(50, 30, 50, 30)  # Исходные отступы
        card_layout.setSpacing(12)  # Исходное расстояние между элементами
        
        # Показываем скрытые элементы обратно
        self._show_header_and_description()
        
        # Восстанавливаем исходный текст и стили статуса
        self.status_label.setText("Нажмите 'ВОЙТИ' для получения доступа")
        self.status_label.setStyleSheet("")  # Убираем специальные стили
        
        # Показываем основную кнопку
        self.main_btn.setVisible(True)
        self.main_btn.setEnabled(True)
    
    def _show_header_and_description(self):
        """Показывает обратно заголовок и описание"""
        card_layout = self.auth_card.layout()
        
        # Проходим по всем элементам layout и показываем скрытые
        for i in range(card_layout.count()):
            item = card_layout.itemAt(i)
            if item:
                widget = item.widget()
                layout_item = item.layout()
                
                # Показываем виджеты с описанием
                if widget and hasattr(widget, 'objectName'):
                    obj_name = widget.objectName()
                    if obj_name in ['overlayTitle', 'overlaySubtitle', 'overlayDescription']:
                        widget.setVisible(True)
                
                # Показываем layout с заголовком (содержит логотип)
                if layout_item:
                    for j in range(layout_item.count()):
                        sub_item = layout_item.itemAt(j)
                        if sub_item and sub_item.widget():
                            sub_widget = sub_item.widget()
                            # Показываем логотип и заголовки
                            if hasattr(sub_widget, 'objectName'):
                                obj_name = sub_widget.objectName()
                                if obj_name in ['overlayTitle', 'overlaySubtitle']:
                                    sub_widget.setVisible(True)
                            # Показываем QLabel без objectName (логотип)
                            elif isinstance(sub_widget, QLabel):
                                sub_widget.setVisible(True)
                        # Показываем layout с логотипом
                        elif sub_item and sub_item.layout():
                            for k in range(sub_item.layout().count()):
                                logo_item = sub_item.layout().itemAt(k)
                                if logo_item and logo_item.widget():
                                    logo_item.widget().setVisible(True)
    
    def _enter_as_guest(self):
        """Вход в гостевом режиме"""
        # Удаляем кнопки ошибки
        if hasattr(self, 'fallback_buttons_widget'):
            card_layout = self.auth_card.layout()
            card_layout.removeWidget(self.fallback_buttons_widget)
            self.fallback_buttons_widget.deleteLater()
            delattr(self, 'fallback_buttons_widget')
        
        # Создаем данные гостевого пользователя
        self.user_data = {
            "id": "guest",
            "first_name": "Гость",
            "last_name": "",
            "username": "guest_user",
            "auth_date": int(datetime.now().timestamp()),
            "is_guest": True
        }
        
        # Сохраняем данные гостевого доступа
        self._save_guest_access()
        
        # Показываем простое уведомление без кнопок
        self.status_label.setText("✅ ВХОД В ГОСТЕВОМ РЕЖИМЕ\n\nЗагрузка приложения...")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #4CAF50;
                background-color: transparent;
                line-height: 1.5;
                padding: 20px;
                margin: 0px;
            }
        """)
        
        # Сохраняем сообщение для показа после отключения блюра
        self.welcome_message = "ГОСТЕВОЙ РЕЖИМ АКТИВИРОВАН!\nНекоторые функции могут быть ограничены"
        
        # Скрываем overlay с анимацией через 2 секунды
        QTimer.singleShot(2000, self.hide_overlay)
    
    def _save_guest_access(self):
        """Сохраняет данные гостевого доступа"""
        guest_data = {
            "user_data": self.user_data,
            "access_time": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(days=1)).isoformat(),  # Гостевой доступ на 1 день
            "is_guest": True
        }
        
        try:
            with open(self.guest_file, 'w', encoding='utf-8') as f:
                json.dump(guest_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения гостевого доступа: {e}")
    
    def show_final_instruction(self):
        """Показывает финальную упрощенную инструкцию"""
        # Скрываем описание приложения на этапе ввода кода
        self._hide_description()
        
        self.status_label.setText(
            f"В открывшемся боте:\n\n"
            f"▸ Нажмите кнопку 'Подписаться'\n"
            f"▸ Подпишитесь на канал {self.CHANNEL_USERNAME}\n"
            f"▸ Нажмите кнопку 'Получить код'\n"
            f"▸ Введите полученный код ниже"
        )
        
        # Создаем поле для ввода кода
        self._create_code_input_field()
        
        # Применяем новые стили
        self.main_btn.style().unpolish(self.main_btn)
        self.main_btn.style().polish(self.main_btn)
    
    def _check_auth_code(self):
        """Проверяет код авторизации через API бота"""
        auth_code = self.code_input.text().strip()
        
        if not auth_code.isdigit() or len(auth_code) != 6:
            self.status_label.setText("❌ Введите корректный 6-значный код")
            return
        
        self.status_label.setText(
            "ПРОВЕРЯЕМ КОД И ПОДПИСКУ...\n\n"
            "Связываемся с сервером авторизации.\n"
            "Для свежих кодов может потребоваться повторная попытка."
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.main_btn.setEnabled(False)
        
        # Проверяем код через API бота
        threading.Thread(target=self._verify_auth_code, args=(auth_code,), daemon=True).start()
    
    def _verify_auth_code(self, auth_code):
        """Проверяет код авторизации через API бота на Yandex Cloud"""
        try:
            # API endpoint бота на Yandex Cloud
            api_url = f"https://d5dq2g7pcv53nkqcsp1p.svoluuab.apigw.yandexcloud.net/check/{auth_code}"
            
            response = requests.get(api_url, timeout=15)
            data = response.json()
            
            if data.get("success"):
                # Код найден и пользователь подписан
                user_data = data.get("user_data", {})
                user_id = data.get("user_id")
                
                # Сохраняем данные пользователя
                self.user_data = {
                    "id": user_id,
                    "first_name": user_data.get("first_name", "Пользователь"),
                    "last_name": user_data.get("last_name", ""),
                    "username": user_data.get("username", ""),
                    "auth_date": int(datetime.now().timestamp())
                }
                
                QTimer.singleShot(0, self.handle_successful_subscription)
            else:
                # Код не найден или пользователь не подписан
                error = data.get("error", "Неизвестная ошибка")
                if error == "Code not found":
                    self.error_message = f"Код {auth_code} не найден.\n\nПроверьте:\n• Подписка на канал\n• Код получен в боте\n• Код введен правильно"
                else:
                    self.error_message = f"Ошибка проверки: {error}\n\nПопробуйте еще раз или обратитесь в поддержку."
                
                QTimer.singleShot(0, self.handle_subscription_error)
                
        except Exception as e:
            self.error_message = f"Ошибка проверки кода:\n{str(e)}\n\nПроверьте интернет соединение и попробуйте еще раз."
            # Тихая обработка ошибки без системных уведомлений
            QTimer.singleShot(0, self.handle_subscription_error)
    
    def _create_code_input_field(self):
        """Создает поле для ввода кода авторизации с предупреждением"""
        # Находим layout кнопок
        card_layout = self.auth_card.layout()
        
        # Создаем контейнер для поля ввода, предупреждения и кнопки
        input_container = QVBoxLayout()
        input_container.setSpacing(15)  # Уменьшаем отступы для компактности
        
        # Добавляем отступ сверху чтобы поле ввода не перекрывало подзаголовок
        input_container.addSpacing(25)  # Отодвигаем поле ввода от заголовка
        
        # Создаем кастомное поле ввода без системных уведомлений
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Введите 6-значный код")
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Вместо setMaxLength используем кастомную обработку
        self.code_input.textChanged.connect(self.validate_code_input)
        self.code_input.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a);
                border: 3px solid #bb86fc;
                border-radius: 15px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
                padding: 15px 20px;
                min-height: 20px;
                letter-spacing: 3px;
                text-align: center;
            }
            QLineEdit:focus {
                border: 3px solid #d1a7ff;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2a2a2a, stop:0.5 #3a3a3a, stop:1 #2a2a2a);
            }
            QLineEdit::placeholder {
                color: rgba(187, 134, 252, 0.7);
                font-weight: 500;
            }
        """)
        
        input_container.addWidget(self.code_input)
        
        # Добавляем стильное предупреждение о коде МЕЖДУ полем ввода и кнопкой
        code_warning = QLabel(
            "◉ Свежий код активируется через 10-15 секунд\n"
            "◉ При ошибке просто повторите попытку"
        )
        code_warning.setObjectName("codeWarning")
        code_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_warning.setWordWrap(True)
        code_warning.setFixedHeight(50)  # Возвращаем исходную высоту
        code_warning.setStyleSheet("""
            #codeWarning {
                color: #bb86fc;
                font-size: 12px;
                font-weight: 600;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(187, 134, 252, 0.15), 
                    stop:0.5 rgba(209, 167, 255, 0.2), 
                    stop:1 rgba(187, 134, 252, 0.15));
                border: 2px solid rgba(187, 134, 252, 0.4);
                border-radius: 12px;
                padding: 8px 15px;
            }
        """)
        
        input_container.addWidget(code_warning)
        
        # Добавляем отрицательный отступ перед кнопкой чтобы поднять её
        input_container.addSpacing(-5)  # Поднимаем кнопку на 5 пикселей
        
        # Создаем новую неоновую кнопку "ПРОВЕРИТЬ КОД"
        check_code_btn = NeonGlowButton("ПРОВЕРИТЬ КОД")
        check_code_btn.clicked.connect(self._check_auth_code)
        
        # Запускаем эффект появления кнопки с задержкой
        QTimer.singleShot(200, check_code_btn.fade_in)
        
        # Запускаем пульсирующий эффект
        check_code_btn.start_pulse()
        
        input_container.addWidget(check_code_btn)
        
        # Добавляем отрицательный отступ после кнопки чтобы поднять статус ближе
        input_container.addSpacing(-20)  # Поднимаем следующий элемент (статус) ближе к кнопке
        
        # Создаем виджет-контейнер
        input_widget = QWidget()
        input_widget.setLayout(input_container)
        
        # Вставляем контейнер перед статусом (перед последними двумя элементами)
        card_layout.insertWidget(card_layout.count() - 2, input_widget)
        
        # Скрываем старую кнопку
        self.main_btn.setVisible(False)
    
    def validate_code_input(self, text):
        """Валидация ввода кода без системных уведомлений"""
        # Оставляем только цифры и ограничиваем до 6 символов
        filtered_text = ''.join(filter(str.isdigit, text))[:6]
        
        # Если текст изменился, обновляем поле без вызова сигнала
        if filtered_text != text:
            self.code_input.blockSignals(True)
            self.code_input.setText(filtered_text)
            self.code_input.blockSignals(False)
    
    def _check_auth_code(self):
        """Проверяет код авторизации"""
        auth_code = self.code_input.text().strip()
        
        if not auth_code.isdigit() or len(auth_code) != 6:
            self.status_label.setText("❌ Введите корректный 6-значный код")
            self.shake_input_field()  # Добавляем эффект дрожания при ошибке
            return
        
        self.status_label.setText("ПРОВЕРЯЕМ КОД АВТОРИЗАЦИИ...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.main_btn.setEnabled(False)
        
        # Проверяем код через API бота
        threading.Thread(target=self._verify_auth_code, args=(auth_code,), daemon=True).start()
    

    

    

    
    def handle_successful_subscription(self):
        """Обрабатывает успешную подписку"""
        self.progress_bar.setVisible(False)
        
        # Показываем сообщение об успешной проверке
        self.status_label.setText("✅ ПРОВЕРКА УСПЕШНО ПРОЙДЕНА!")
        
        # Сохраняем сообщение для показа после отключения блюра
        self.welcome_message = "ПОДПИСКА ПОДТВЕРЖДЕНА!\nДОБРО ПОЖАЛОВАТЬ В RU-MINETOOLS!"
        
        # Сохраняем данные авторизации
        self.save_auth_data()
        
        # НЕ обновляем UI здесь - все обновления будут после отключения blur
        # Обновление UI перенесено в _remove_blur_and_delete()
        
        # Скрываем overlay с анимацией через 2 секунды (даем время прочитать сообщение)
        QTimer.singleShot(2000, self.hide_overlay)
    
    def handle_subscription_error(self):
        """Обрабатывает ошибку подписки с улучшенным интерфейсом"""
        self.progress_bar.setVisible(False)
        
        # Добавляем компактную подсказку
        enhanced_message = f"{self.error_message}\n\nПодождите 10 сек и повторите"
        
        self.status_label.setText(enhanced_message)
        
        # Меняем кнопку на "Попробовать еще раз"
        self.main_btn.setText("ПОПРОБОВАТЬ ЕЩЕ РАЗ")
        self.main_btn.setObjectName("overlaySubscribeBtn")
        self.main_btn.clicked.disconnect()
        self.main_btn.clicked.connect(self._check_auth_code)
        self.main_btn.setEnabled(True)
        
        # Применяем стили
        self.main_btn.style().unpolish(self.main_btn)
        self.main_btn.style().polish(self.main_btn)
    
    def check_subscription(self):
        """Проверяет подписку (старый метод для совместимости)"""
        self.check_subscription_simple()
    
    def _check_subscription_api(self):
        """Реальная проверка подписки через Telegram Bot API"""
        try:
            # Проверяем наличие токена и ID канала
            if not self.BOT_TOKEN:
                logger.error("BOT_TOKEN не настроен для проверки подписки")
                QTimer.singleShot(0, lambda: self._on_subscription_error("Токен бота не настроен"))
                return
            
            if not self.CHANNEL_ID:
                logger.error("CHANNEL_ID не настроен для проверки подписки")
                QTimer.singleShot(0, lambda: self._on_subscription_error("ID канала не настроен"))
                return
            
            url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/getChatMember"
            params = {
                "chat_id": self.CHANNEL_ID,
                "user_id": self.user_data["id"]
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data["ok"]:
                status = data["result"]["status"]
                is_subscribed = status in ["member", "administrator", "creator"]
                
                # Обновляем UI в главном потоке
                QTimer.singleShot(0, lambda: self._on_subscription_result(is_subscribed, status))
            else:
                error_msg = data.get("description", "Неизвестная ошибка")
                QTimer.singleShot(0, lambda: self._on_subscription_error(error_msg))
                
        except Exception as e:
            logger.error(f"Ошибка проверки подписки: {e}")
            QTimer.singleShot(0, lambda: self._on_subscription_error(str(e)))
    
    def _on_subscription_result(self, is_subscribed, status):
        """Обработка результата проверки подписки"""
        self.progress_bar.setVisible(False)
        
        if is_subscribed:
            # Сохраняем сообщение для показа после отключения блюра
            self.welcome_message = "ПОДПИСКА ПОДТВЕРЖДЕНА!\nДОБРО ПОЖАЛОВАТЬ В RU-MINETOOLS!"
            
            # Сохраняем данные авторизации
            self.save_auth_data()
            
            # Скрываем overlay с анимацией
            QTimer.singleShot(2000, self.hide_overlay)
        else:
            # Для ошибок показываем сразу, так как пользователь должен видеть что делать
            self.status_label.setText(f"❌ ПОДПИСКА НЕ НАЙДЕНА (статус: {status}). Подпишитесь на канал и попробуйте снова.")
    
    def _on_subscription_error(self, error_msg):
        """Обработка ошибки проверки подписки"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ ОШИБКА ПРОВЕРКИ: {error_msg}")
        
        # Показываем подсказки для частых ошибок
        if "user not found" in error_msg.lower():
            self.status_label.setText("❌ ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН. Сначала напишите боту в личные сообщения.")
        elif "chat not found" in error_msg.lower():
            self.status_label.setText("❌ КАНАЛ НЕ НАЙДЕН. Проверьте настройки бота.")
        elif "forbidden" in error_msg.lower():
            self.status_label.setText("❌ БОТ НЕ ИМЕЕТ ДОСТУПА К КАНАЛУ. Добавьте бота как администратора.")
    
    def save_auth_data(self):
        """Сохраняет данные авторизации"""
        auth_data = {
            "user_data": self.user_data,
            "auth_time": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        try:
            with open(self.auth_file, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения авторизации: {e}")
    
    def check_saved_auth(self):
        """Проверяет сохраненную авторизацию (обычную и гостевую)"""
        # Сначала проверяем обычную авторизацию
        if os.path.exists(self.auth_file):
            try:
                with open(self.auth_file, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                
                # Проверяем срок действия
                expires = datetime.fromisoformat(auth_data["expires"])
                if datetime.now() < expires:
                    self.user_data = auth_data["user_data"]
                    
                    # Сохраняем сообщение для показа после отключения блюра
                    self.welcome_message = f"ДОБРО ПОЖАЛОВАТЬ, {self.user_data['first_name'].upper()}!\nВход выполнен автоматически"
                    
                    # Автоматически скрываем overlay
                    QTimer.singleShot(1500, self.hide_overlay)
                    return
                else:
                    # Авторизация истекла
                    os.remove(self.auth_file)
                    
            except Exception as e:
                logger.error(f"Ошибка загрузки авторизации: {e}")
                if os.path.exists(self.auth_file):
                    os.remove(self.auth_file)
        
        # Если обычной авторизации нет, проверяем гостевой доступ
        if os.path.exists(self.guest_file):
            try:
                with open(self.guest_file, 'r', encoding='utf-8') as f:
                    guest_data = json.load(f)
                
                # Проверяем срок действия гостевого доступа
                expires = datetime.fromisoformat(guest_data["expires"])
                if datetime.now() < expires:
                    self.user_data = guest_data["user_data"]
                    
                    # Сохраняем сообщение для показа после отключения блюра
                    self.welcome_message = f"ГОСТЕВОЙ РЕЖИМ\nДобро пожаловать, {self.user_data['first_name']}!"
                    
                    # Автоматически скрываем overlay
                    QTimer.singleShot(1500, self.hide_overlay)
                    return
                else:
                    # Гостевой доступ истек
                    os.remove(self.guest_file)
                    
            except Exception as e:
                logger.error(f"Ошибка загрузки гостевого доступа: {e}")
                if os.path.exists(self.guest_file):
                    os.remove(self.guest_file)
    
    def hide_overlay(self):
        """Скрывает overlay с анимацией"""
        # Создаем анимацию исчезновения overlay
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        
        # Подключаем функции к завершению анимации
        self.fade_animation.finished.connect(self._remove_blur_and_delete)
        
        # Запускаем анимацию исчезновения overlay
        self.fade_animation.start()
    
    def _remove_blur_and_delete(self):
        """Убирает блюр и удаляет overlay одновременно в конце анимации"""
        
        # Убираем блюр с анимацией
        if self.parent():
            if hasattr(self.parent(), 'remove_blur_effect'):
                self.parent().remove_blur_effect()
            else:
                self.parent().setGraphicsEffect(None)
        
        # ТЕПЕРЬ обновляем профиль пользователя в sidebar - после отключения blur
        if hasattr(self, 'user_data') and self.user_data:
            if self.parent() and hasattr(self.parent(), 'sidebar'):
                self.parent().sidebar.update_user_profile(self.user_data)
        
        # Показываем приветственное сообщение если оно есть (для автоматической авторизации)
        if hasattr(self, 'welcome_message') and self.welcome_message:
            if self.parent() and hasattr(self.parent(), 'show_welcome_notification'):
                self.parent().show_welcome_notification(self.welcome_message)
        
        # Удаляем overlay
        self.safe_delete()
    

    
    def safe_delete(self):
        """Безопасно удаляет overlay"""
        try:
            # Убеждаемся что блюр удален
            if self.parent():
                self.parent().setGraphicsEffect(None)
            self.deleteLater()
        except Exception as e:
            logger.error(f"Ошибка удаления overlay: {e}")
            self.deleteLater()
    
    def resizeEvent(self, event):
        """Обновляет размер overlay при изменении размера родителя"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        """Обработка закрытия overlay"""
        # Убираем блюр при закрытии
        if self.parent():
            self.parent().setGraphicsEffect(None)
            if hasattr(self.parent(), 'remove_blur_effect'):
                self.parent().remove_blur_effect()
        super().closeEvent(event)
    
    def get_overlay_styles(self):
        """Стили для overlay на черном фоне"""
        return """
        TelegramAuthOverlay {
            background-color: rgba(0, 0, 0, 0.7);
        }
        
        #authCard {
            background-color: transparent;
            border: none;
        }
        
        #overlayTitle {
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        }
        
        #overlaySubtitle {
            font-size: 15px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        }
        
        #overlayDescription {
            font-size: 14px;
            color: #e8e8e8;
            background-color: transparent;
        }
        
        QPushButton {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            padding: 15px 25px;
            min-height: 25px;
        }
        
        QPushButton:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        QPushButton:pressed {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
        }
        
        QPushButton:disabled {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
            color: #666666;
        }
        
        #overlaySubscribeBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.5 #d1a7ff, stop:1 #bb86fc);
            border: 2px solid #9966cc;
            color: #ffffff;
            font-weight: 700;
            padding: 18px 25px;
            min-height: 30px;
            border-radius: 15px;
        }
        
        #overlaySubscribeBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #d1a7ff, stop:0.5 #e6ccff, stop:1 #d1a7ff);
            border-color: #aa77dd;
            color: #ffffff;
        }
        
        #modern3DBtn {
            background: transparent;
            border: none;
        }
        
        #modern3DBtnInner {
            /* Многослойный 3D эффект с четкими гранями и свечением */
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f5f0ff,
                stop:0.05 #e6ccff,
                stop:0.15 #d1a7ff,
                stop:0.45 #bb86fc,
                stop:0.55 #a855f7,
                stop:0.85 #9333ea,
                stop:0.95 #7c3aed,
                stop:1 #6b21a8);
            
            /* Четкая верхняя граница для 3D эффекта */
            border-top: 2px solid rgba(255, 255, 255, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(0, 0, 0, 0.2);
            border-bottom: 2px solid rgba(0, 0, 0, 0.3);
            
            /* Увеличиваем border-radius и добавляем внешнюю обводку для эффекта свечения */
            border-radius: 25px;
            outline: 3px solid rgba(187, 134, 252, 0.4);
            outline-offset: 2px;
            
            /* Текст */
            color: #ffffff;
            font-weight: 800;
            font-size: 16px;
            padding: 22px 40px;
            min-height: 35px;
        }
        
        #modern3DBtnInner:hover {
            /* Более яркий 3D эффект при наведении */
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #faf8ff,
                stop:0.05 #f0e6ff,
                stop:0.15 #e6ccff,
                stop:0.45 #d1a7ff,
                stop:0.55 #bb86fc,
                stop:0.85 #a855f7,
                stop:0.95 #9333ea,
                stop:1 #7c3aed);
            
            /* Усиливаем границы при наведении */
            border-top: 2px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.3);
            border-right: 1px solid rgba(0, 0, 0, 0.3);
            border-bottom: 2px solid rgba(0, 0, 0, 0.4);
            
            /* Усиливаем свечение при наведении */
            outline: 4px solid rgba(187, 134, 252, 0.7);
            outline-offset: 3px;
        }
        
        #modern3DBtnInner:pressed {
            /* Вдавленный эффект с инвертированными границами */
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6b21a8,
                stop:0.05 #7c3aed,
                stop:0.15 #9333ea,
                stop:0.45 #a855f7,
                stop:0.55 #bb86fc,
                stop:0.85 #d1a7ff,
                stop:0.95 #e6ccff,
                stop:1 #f5f0ff);
            
            /* Инвертированные границы для эффекта вдавливания */
            border-top: 2px solid rgba(0, 0, 0, 0.4);
            border-left: 1px solid rgba(0, 0, 0, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 2px solid rgba(255, 255, 255, 0.4);
        }
        
        /* Неоновая кнопка с мягким свечением */
        #neonGlowBtn {
            background: transparent;
            border: none;
        }
        
        #neonGlowBtnInner {
            /* Футуристический градиент от фиолетового к розовому */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #A546FF,
                stop:0.3 #B855FF,
                stop:0.7 #D065FF,
                stop:1 #E06BFF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Стеклянный эффект с внутренним свечением */
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            
            /* Внешнее неоновое свечение */
            outline: 8px solid rgba(165, 70, 255, 0.3);
            outline-offset: 4px;
            
            /* Текст */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
            
            /* Отключаем стандартные эффекты Qt */
            selection-background-color: transparent;
            selection-color: #ffffff;
        }
        
        #neonGlowBtnInnerHover {
            /* Усиленное свечение при наведении */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #B855FF,
                stop:0.3 #C965FF,
                stop:0.7 #E075FF,
                stop:1 #F080FF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Усиленные границы */
            border-top: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 1px solid rgba(255, 255, 255, 0.4);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            
            /* Более яркое внешнее свечение */
            outline: 12px solid rgba(165, 70, 255, 0.5);
            outline-offset: 6px;
            
            /* Текст */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnInnerPressed {
            /* Эффект вдавливания без артефактов */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9540E6,
                stop:0.3 #A650F0,
                stop:0.7 #C060FF,
                stop:1 #D565FF);
            
            /* Мягкие закругленные углы */
            border-radius: 25px;
            
            /* Инвертированные границы */
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(0, 0, 0, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            
            /* Уменьшенное свечение при нажатии */
            outline: 6px solid rgba(165, 70, 255, 0.4);
            outline-offset: 2px;
            
            /* Чистый белый текст без артефактов */
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnReflection {
            /* Отражение/тень под кнопкой */
            background: qradial-gradient(ellipse at center,
                rgba(165, 70, 255, 0.4) 0%,
                rgba(165, 70, 255, 0.2) 40%,
                rgba(165, 70, 255, 0.1) 70%,
                transparent 100%);
            border: none;
            border-radius: 25px;
            margin: 0px 20px;
        }
        
        #modern3DBtnShadow {
            /* Реалистичная тень */
            background: qradial-gradient(ellipse at center,
                rgba(107, 33, 168, 0.6) 0%,
                rgba(107, 33, 168, 0.4) 30%,
                rgba(107, 33, 168, 0.2) 60%,
                rgba(107, 33, 168, 0.1) 80%,
                transparent 100%);
            border: none;
            border-radius: 25px;
            margin: 0px 15px;
        }
        
        #animatedAuthBtn {
            /* Для совместимости со старыми кнопками */
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e6ccff,
                stop:0.1 #d1a7ff,
                stop:0.5 #bb86fc,
                stop:0.9 #9966cc,
                stop:1 #7d4cdb);
            border: none;
            border-radius: 25px;
            color: #ffffff;
            font-weight: 800;
            font-size: 16px;
            padding: 20px 35px;
            min-height: 35px;
        }
        
        #overlayAuthBtn {
            background-color: #3a3a3a;
            border: 3px solid #bb86fc;
            color: #bb86fc;
            font-weight: 700;
        }
        
        #overlayAuthBtn:hover {
            background-color: rgba(187, 134, 252, 0.2);
            border-color: #d1a7ff;
            color: #d1a7ff;
        }
        
        #overlayCheckBtn {
            background-color: #bb86fc;
            border: 3px solid #e6ccff;
            color: #000000;
            font-weight: 800;
        }
        
        #overlayCheckBtn:hover {
            background-color: #d1a7ff;
            border-color: #f0e6ff;
            color: #000000;
        }
        
        #overlayStatus {
            font-size: 12px;
            color: #c0c0c0;
            background-color: transparent;
            max-width: 520px;
            max-height: 180px;
            line-height: 1.3;
            padding: 10px;
        }
        
        #overlayProgress {
            border: 2px solid #4a4a4a;
            border-radius: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a);
            height: 24px;
            text-align: center;
            font-weight: bold;
            color: #ffffff;
            padding: 2px;
        }
        
        #overlayProgress::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.3 #9c4dcc, stop:0.7 #bb86fc, stop:1 #d1c4e9);
            border-radius: 12px;
            margin: 2px;
        }
        
        #overlayProgress QProgressBar {
            border: 2px solid #4a4a4a;
            border-radius: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a);
            height: 24px;
            text-align: center;
            font-weight: bold;
            color: #ffffff;
        }
        
        /* Стили для кнопок защиты от недоступности бота */
        #retryBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4CAF50, stop:0.5 #66BB6A, stop:1 #4CAF50);
            border: 2px solid #388E3C;
            color: #ffffff;
            font-weight: 700;
            padding: 18px 25px;
            min-height: 30px;
            border-radius: 15px;
        }
        
        #retryBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #66BB6A, stop:0.5 #81C784, stop:1 #66BB6A);
            border-color: #4CAF50;
        }
        
        #guestBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #FF9800, stop:0.5 #FFB74D, stop:1 #FF9800);
            border: 2px solid #F57C00;
            color: #ffffff;
            font-weight: 700;
            padding: 18px 25px;
            min-height: 30px;
            border-radius: 15px;
        }
        
        #guestBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #FFB74D, stop:0.5 #FFCC80, stop:1 #FFB74D);
            border-color: #FF9800;
        }
        """



class FadeInWidget(QWidget):
    """Виджет с анимацией появления"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def fade_in(self):
        """Анимация появления"""
        self.setWindowOpacity(0.0)
        self.show()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

class ModernStyles:
    """Современные стили для интерфейса"""
    
    @staticmethod
    def get_main_styles(font_name="Segoe UI"):
        styles = """
        /* Глобальное сглаживание для всех элементов */
        * {
            /* Web CSS properties removed - not supported by Qt */
        }
        
        QMainWindow {
            background-color: #0a0a0a;
            color: #ffffff;
        }
        
        QWidget {
            background-color: transparent;
            color: #ffffff;
            font-family: "FONT_NAME_PLACEHOLDER", "Segoe UI", "Arial", sans-serif;
            font-size: 11px;
            font-weight: 400;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        /* Сглаживание для кнопок */
        QPushButton {
            /* Web CSS properties removed - not supported by Qt */
        }
        
        /* Сглаживание для текстовых полей */
        QLineEdit, QTextEdit, QPlainTextEdit {
            /* Web CSS properties removed - not supported by Qt */
        }
        
        /* Общие стили для прогресс-баров */
        QProgressBar {
            border: 2px solid #3a3a3a;
            border-radius: 12px;
            background-color: #1a1a1a;
            height: 20px;
            text-align: center;
            font-weight: bold;
            color: #ffffff;
            padding: 1px;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.5 #9c4dcc, stop:1 #bb86fc);
            border-radius: 10px;
            margin: 2px;
        }
        
        QProgressBar[value="0"] {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a1a1a, stop:0.5 #2a2a2a, stop:1 #1a1a1a);
        }
        
        /* Боковая панель */
        #sidebar {
            background-color: #0f0f0f;
            border: none;
            border-right: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 0px;
        }
        

        
        /* Навигационные кнопки */
        #navButton {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 25px;
            padding: 16px 20px;
            margin: 4px 20px 4px 8px;
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
            font-weight: 500;
            text-align: left;
            min-height: 28px;
        }
        
        #navButton:hover {
            background-color: rgba(255, 255, 255, 0.08);
            color: rgba(255, 255, 255, 0.95);
        }
        
        #navButton[active="true"] {
            /* Более насыщенный градиент с большим количеством фиолетового */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(60, 50, 70, 0.95),
                stop:0.2 rgba(80, 60, 100, 0.9),
                stop:0.5 rgba(120, 70, 150, 0.85),
                stop:0.8 rgba(140, 80, 180, 0.8),
                stop:1 rgba(164, 70, 255, 0.7));
            
            /* Более яркая фиолетовая граница */
            border: 1px solid rgba(164, 70, 255, 0.7);
            
            color: #ffffff;
            font-weight: 600;
            border-radius: 25px;
        }
        
        #navButton[active="true"]:hover {
            /* Еще более насыщенный при наведении */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(70, 60, 80, 1.0),
                stop:0.2 rgba(90, 70, 110, 0.95),
                stop:0.5 rgba(130, 80, 160, 0.9),
                stop:0.8 rgba(150, 90, 190, 0.85),
                stop:1 rgba(184, 85, 255, 0.8));
            
            /* Яркая граница при наведении */
            border: 1px solid rgba(184, 85, 255, 0.9);
        }
        

        
        /* Верхняя панель */
        #topBar {
            background-color: #0f0f0f;
            border: none;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            padding: 0px 24px;
            position: relative;
        }
        
        /* Современное поле поиска */
        #modernSearchField {
            background-color: transparent;
            border: none;
            color: #ffffff;
            font-size: 13px;
            font-weight: 400;
            padding: 8px 12px;
        }
        
        #modernSearchField:focus {
            outline: none;
        }
        
        #modernSearchField::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }
        
        /* Кнопки действий */
        .actionButton {
            background-color: #00ff88;
            border: none;
            border-radius: 6px;
            color: #000000;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 16px;
            min-width: 80px;
        }
        
        .actionButton:hover {
            background-color: #00cc6a;
        }
        
        .actionButton:pressed {
            background-color: #009955;
        }
        
        .secondaryButton {
            background-color: transparent;
            border: 1px solid #1a1a1a;
            border-radius: 6px;
            color: #b3b3b3;
            font-size: 12px;
            font-weight: 500;
            padding: 8px 16px;
            min-width: 80px;
        }
        
        .secondaryButton:hover {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
            color: #ffffff;
        }
        
        /* Карточки */
        .card {
            background-color: #0f0f0f;
            border: 1px solid #1a1a1a;
            border-radius: 12px;
            padding: 24px;
            margin: 8px;
        }
        
        .card:hover {
            border-color: #2a2a2a;
            background-color: #1a1a1a;
        }
        
        /* Таблица */
        QTableWidget {
            background-color: #0f0f0f;
            border: 1px solid #1a1a1a;
            border-radius: 8px;
            gridline-color: #1a1a1a;
            selection-background-color: #00ff88;
            color: #ffffff;
        }
        
        QTableWidget::item {
            padding: 12px;
            border-bottom: 1px solid #1a1a1a;
            color: #ffffff;
        }
        
        QTableWidget::item:selected {
            background-color: #00ff88;
            color: #000000;
        }
        
        QHeaderView::section {
            background-color: #0a0a0a;
            border: none;
            border-bottom: 1px solid #1a1a1a;
            padding: 12px;
            font-weight: 600;
            color: #ffffff;
        }
        
        /* Скроллбар */
        QScrollBar:vertical {
            background-color: #0a0a0a;
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #2a2a2a;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #3a3a3a;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        /* Кнопка поддержки проекта (адаптированная под фиолетовую тему) */
        #donateButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(164, 70, 255, 0.8), stop:0.5 rgba(184, 85, 255, 0.9), stop:1 rgba(208, 101, 255, 0.8));
            border: 1px solid rgba(164, 70, 255, 0.6);
            border-radius: 20px;
            color: #ffffff;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 12px;
            text-align: center;
        }
        
        #donateButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(184, 85, 255, 0.9), stop:0.5 rgba(208, 101, 255, 1.0), stop:1 rgba(224, 107, 255, 0.9));
            border: 1px solid rgba(184, 85, 255, 0.8);
        }
        
        #donateButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(144, 50, 215, 0.9), stop:0.5 rgba(164, 70, 255, 1.0), stop:1 rgba(184, 85, 255, 0.9));
            border: 1px solid rgba(144, 50, 215, 0.8);
        }
        
        /* Кнопка GitHub */
        #githubButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4a5568, stop:0.5 #2d3748, stop:1 #1a202c);
            border: 1px solid #4a5568;
            border-radius: 20px;
            color: #ffffff;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 12px;
            text-align: center;
        }
        
        #githubButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #718096, stop:0.5 #4a5568, stop:1 #2d3748);
            border: 1px solid #718096;
        }
        
        #githubButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2d3748, stop:0.5 #1a202c, stop:1 #171923);
            border: 1px solid #2d3748;
        }
        
        /* Кнопка обновления */
        #updateButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(164, 70, 255, 0.8), stop:0.5 rgba(184, 85, 255, 0.9), stop:1 rgba(208, 101, 255, 0.8));
            border: 1px solid rgba(184, 85, 255, 0.6);
            border-radius: 20px;
            color: #ffffff;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 12px;
            text-align: center;
        }
        
        #updateButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(184, 85, 255, 0.9), stop:0.5 rgba(208, 101, 255, 1.0), stop:1 rgba(224, 107, 255, 0.9));
            border: 1px solid rgba(208, 101, 255, 0.8);
        }
        
        #updateButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(144, 50, 215, 0.9), stop:0.5 rgba(164, 70, 255, 1.0), stop:1 rgba(184, 85, 255, 0.9));
            border: 1px solid rgba(164, 70, 255, 0.8);
        }
        """
        return styles.replace("FONT_NAME_PLACEHOLDER", font_name)



class Sidebar(QFrame):
    """Боковая панель навигации"""
    
    # Сигнал для установки аватара из другого потока
    avatar_loaded = pyqtSignal(bytes)
    
    def __init__(self, content_area=None, top_bar=None):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(300)
        
        # Ссылка на область контента для переключения страниц
        self.content_area = content_area
        
        # Ссылка на верхнюю панель для обновления заголовков
        self.top_bar = top_bar
        
        # Текущая активная страница
        self.current_page = "translations"
        
        # Словарь для хранения кнопок навигации
        self.nav_buttons = {}
        
        # Настройки Telegram бота для загрузки аватаров
        self.BOT_TOKEN = None
        self._load_bot_config()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 16, 12, 16)
        self.layout.setSpacing(4)
        
        self.create_header()
        self.create_navigation()
        self.create_footer()
        
        # Подключаем сигнал для установки аватара
        self.avatar_loaded.connect(self._set_avatar_image)
    
    def _load_bot_config(self):
        """Загружает конфигурацию Telegram бота из файла"""
        try:
            config_path = get_config_path("bot_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.BOT_TOKEN = config.get("BOT_TOKEN")
                    
                    if not self.BOT_TOKEN:
                        logger.warning("BOT_TOKEN не найден в конфигурации для Sidebar")
                        self.BOT_TOKEN = None
                    else:
                        logger.info("Конфигурация бота для Sidebar успешно загружена")
            else:
                logger.warning("Файл конфигурации бота не найден для Sidebar")
                self.BOT_TOKEN = None
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации бота для Sidebar: {e}")
            self.BOT_TOKEN = None
    
    def create_header(self):
        """Создает заголовок с логотипом"""
        header_layout = QHBoxLayout()
        
        # Логотип
        self.logo_label = QLabel()
        logo_path = str(get_asset_path("logo.png"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("⬛")
            self.logo_label.setStyleSheet("font-size: 48px; padding: 4px;")
        
        self.logo_label.setFixedSize(56, 56)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.logo_label)
        
        # Уменьшаем отступ между логотипом и названием
        header_layout.setSpacing(8)
        
        # Название программы рядом с логотипом (уменьшенный размер шрифта)
        self.title_label = QLabel("RU-MINETOOLS NEW")
        self.title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            font-weight: 700;
            margin: 0px;
        """)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        self.layout.addSpacing(16)
    
    def create_navigation(self):
        """Создает навигационное меню"""
        nav_items = [
            (str(get_asset_path("3.png")), "◆", "Квесты", "translations"),
            (str(get_asset_path("5.png")), "⬢", "JAR Моды", "jar_mods"),
            (str(get_asset_path("4.png")), "▼", "Настройки", "settings"),
            (str(get_asset_path("2.png")), "◐", "О программе", "about")
        ]
        
        self.nav_buttons = {}
        self.current_page = "translations"
        
        for icon_file, icon_fallback, text, page_id in nav_items:
            btn = self.create_nav_button_with_icon(icon_file, icon_fallback, text, page_id)
            
            btn.clicked.connect(lambda checked, p=page_id: self.switch_page(p))
            
            if page_id == self.current_page:
                btn.setProperty("active", "true")
                # Применяем стили сразу после установки свойства
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            
            self.layout.addWidget(btn)
            self.nav_buttons[page_id] = btn
        
        # Устанавливаем начальное активное состояние после создания всех кнопок
        self.switch_page(self.current_page)
        
        # Добавляем приглашение в сообщество
        self.create_community_invitation()
        
        self.layout.addStretch()
    

    
    def create_nav_button_with_icon(self, icon_file, icon_fallback, text, page_id):
        """Создает кнопку навигации с иконкой или fallback символом"""
        btn = NavButton()
        btn.setObjectName("navButton")
        btn.setFixedHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Сохраняем данные кнопки
        btn.page_id = page_id
        
        # Создаем layout для кнопки
        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(20, 16, 20, 16)
        btn_layout.setSpacing(20)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Загружаем готовые цветные PNG иконки
        btn.icon_widget = QLabel()
        btn.white_pixmap = None
        btn.purple_pixmap = None
        btn.has_png_icon = False
        
        if icon_file:
            # Пути к готовым цветным версиям
            base_name = icon_file[:-4]
            white_path = str(get_asset_path(f"{base_name}_white_32.png"))
            purple_path = str(get_asset_path(f"{base_name}_purple_32.png"))
            
            # Загружаем версии
            if os.path.exists(white_path):
                btn.white_pixmap = QPixmap(white_path)
            
            if os.path.exists(purple_path):
                btn.purple_pixmap = QPixmap(purple_path)
            
            # Если обе версии загружены успешно
            if btn.white_pixmap and not btn.white_pixmap.isNull() and btn.purple_pixmap and not btn.purple_pixmap.isNull():
                btn.has_png_icon = True
                btn.icon_widget.setPixmap(btn.white_pixmap)
                btn.icon_widget.setStyleSheet("""
                    QLabel {
                        background: transparent;
                        border: none;
                    }
                """)
                btn.icon_widget.setScaledContents(False)
            else:
                # Fallback на текстовый символ
                btn.icon_widget.setText(icon_fallback)
                btn.icon_widget.setStyleSheet("font-size: 28px; color: #ffffff;")
        else:
            # Используем текстовый символ
            btn.icon_widget.setText(icon_fallback)
            btn.icon_widget.setStyleSheet("font-size: 28px; color: #ffffff;")
        
        btn.icon_widget.setFixedSize(32, 32)
        btn.icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn.icon_widget.setScaledContents(False)
        btn_layout.addWidget(btn.icon_widget)
        btn_layout.setAlignment(btn.icon_widget, Qt.AlignmentFlag.AlignVCenter)
        
        # Текст
        btn.text_label = QLabel(text)
        btn.text_label.setStyleSheet("font-size: 16px; font-weight: 500; color: #ffffff;")
        btn.text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        btn_layout.addWidget(btn.text_label)
        btn_layout.setAlignment(btn.text_label, Qt.AlignmentFlag.AlignVCenter)
        
        btn_layout.addStretch()
        
        return btn
    
    def create_community_invitation(self):
        """Создает приглашение в сообщество Telegram в стиле основных кнопок программы"""
        # Контейнер для приглашения - увеличиваем для размещения кнопки
        community_container = QWidget()
        community_container.setFixedHeight(140)  # Уменьшили обратно
        community_container.setStyleSheet("""
            QWidget {
                background: rgba(165, 70, 255, 0.1);
                border: 1px solid rgba(165, 70, 255, 0.3);
                border-radius: 20px;
                margin: 12px 16px;
            }
        """)
        
        layout = QVBoxLayout(community_container)
        layout.setContentsMargins(20, 20, 20, 20)  # Равные отступы от краев
        layout.setSpacing(0)  # Убираем автоматические отступы
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Минимальный отступ сверху
        layout.addSpacing(0)
        
        # Заголовок с иконкой
        title = QLabel("💜 Присоединяйтесь!")
        title.setStyleSheet("""
            QLabel {
                color: #E06BFF;
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
                min-height: 20px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Маленький отступ между заголовком и описанием
        layout.addSpacing(5)
        
        # Описание
        description = QLabel("У нас много всего")
        description.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
                min-height: 16px;
            }
        """)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        
        # Отступ между описанием и кнопкой
        layout.addSpacing(15)
        
        # Кнопка - используем обычную QPushButton с принудительной округлостью
        community_btn = QPushButton("Telegram канал")
        community_btn.setFixedSize(180, 36)  # Фиксированный размер
        community_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Применяем стили с принудительной округлостью
        community_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                
                border-radius: 18px;  /* Половина от высоты 36px */
                
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9540E6,
                    stop:0.3 #A650F0,
                    stop:0.7 #C060FF,
                    stop:1 #D565FF);
                
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        
        # Подключаем клик к открытию Telegram канала
        community_btn.clicked.connect(self.open_telegram_community)
        
        layout.addWidget(community_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Максимальный отступ снизу для баланса
        layout.addSpacing(40)
        
        # Добавляем в основной layout
        self.layout.addWidget(community_container)
    
    def open_telegram_community(self):
        """Открывает Telegram канал в браузере"""
        try:
            webbrowser.open("https://t.me/ruquestbook")
        except Exception as e:
            logger.error(f"Ошибка при открытии Telegram канала: {e}")
    
    def create_footer(self):
        """Создает нижнюю часть с профилем пользователя"""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 0, 16, 8)  # Немного правее и выше
        
        # Аватар
        self.avatar = QLabel()
        self.avatar.setFixedSize(40, 40)
        self.avatar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #3b82f6, stop:1 #8b5cf6);
            border-radius: 20px;
            border: 2px solid #e2e8f0;
        """)
        footer_layout.addWidget(self.avatar)
        
        # Информация о пользователе
        user_info = QVBoxLayout()
        user_info.setSpacing(2)
        
        self.user_name = QLabel("Пользователь")
        self.user_name.setStyleSheet("""
            color: #ffffff;
            font-weight: 600;
            font-size: 14px;
        """)
        user_info.addWidget(self.user_name)
        
        # Создаем роль пользователя (пустую по умолчанию, заполняется при входе)
        self.user_role = QLabel("")
        self.user_role.setStyleSheet("""
            color: #94a3b8;
            font-size: 12px;
        """)
        user_info.addWidget(self.user_role)
        
        footer_layout.addLayout(user_info)
        footer_layout.addStretch()
        
        self.layout.addLayout(footer_layout)
    
    def update_user_profile(self, user_data):
        """Обновляет профиль пользователя данными из Telegram"""
        if not user_data:
            return
            
        # Обновляем имя пользователя
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        username = user_data.get("username", "")
        
        # Формируем отображаемое имя
        if first_name and last_name:
            display_name = f"{first_name} {last_name}"
        elif first_name:
            display_name = first_name
        elif username:
            display_name = f"@{username}"
        else:
            display_name = "Пользователь Telegram"
            
        self.user_name.setText(display_name)
        
        # Обновляем роль (показываем username если есть, иначе ID пользователя)
        if username and f"@{username}" != display_name:
            self.user_role.setText(f"@{username}")
            self.user_role.show()  # Показываем строку с ролью
        elif user_data.get("id"):
            self.user_role.setText(f"ID: {user_data.get('id')}")
            self.user_role.show()  # Показываем ID пользователя
        else:
            self.user_role.setText("")
            self.user_role.hide()  # Скрываем пустую строку
        
        # Загружаем аватар из Telegram (если есть)
        self.load_telegram_avatar(user_data.get("id"))
    
    def load_telegram_avatar(self, user_id):
        """Загружает аватар пользователя из Telegram"""
        if not user_id:
            return
        
        # Для гостевого пользователя используем специальный аватар
        if user_id == "guest":
            self.avatar.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6c757d, stop:1 #495057);
                border-radius: 20px;
                border: 2px solid #e2e8f0;
            """)
            return
        
        # Запускаем загрузку аватара в отдельном потоке
        threading.Thread(target=self._download_telegram_avatar, args=(user_id,), daemon=True).start()
        
        # Пока загружается, показываем цветной градиент на основе ID
        colors = [
            ("#ff6b6b", "#ee5a52"),  # Красный
            ("#4ecdc4", "#44a08d"),  # Бирюзовый  
            ("#45b7d1", "#96c93d"),  # Синий-зеленый
            ("#f9ca24", "#f0932b"),  # Желто-оранжевый
            ("#eb4d4b", "#6c5ce7"),  # Красно-фиолетовый
            ("#a55eea", "#26de81"),  # Фиолетово-зеленый
        ]
        
        # Выбираем цвет на основе ID пользователя
        try:
            color_index = int(user_id) % len(colors)
        except ValueError:
            # Если ID не число, используем первый цвет
            color_index = 0
            
        color1, color2 = colors[color_index]
        
        self.avatar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {color1}, stop:1 {color2});
            border-radius: 20px;
            border: 2px solid #e2e8f0;
        """)
    
    def _download_telegram_avatar(self, user_id):
        """Загружает реальный аватар пользователя из Telegram Bot API"""
        try:
            # Проверяем наличие токена бота
            if not self.BOT_TOKEN:
                logger.warning("BOT_TOKEN не настроен - загрузка аватара недоступна")
                return
            
            # Получаем фото профиля через Bot API
            url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/getUserProfilePhotos"
            params = {"user_id": user_id, "limit": 1}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("ok") and data.get("result", {}).get("photos"):
                # Берем первое (самое большое) фото
                photo = data["result"]["photos"][0][-1]  # Последний элемент = самое большое разрешение
                file_id = photo["file_id"]
                
                # Получаем путь к файлу
                file_url = f"https://api.telegram.org/bot{self.BOT_TOKEN}/getFile"
                file_params = {"file_id": file_id}
                
                file_response = requests.get(file_url, params=file_params, timeout=10)
                file_data = file_response.json()
                
                if file_data.get("ok"):
                    file_path = file_data["result"]["file_path"]
                    photo_url = f"https://api.telegram.org/file/bot{self.BOT_TOKEN}/{file_path}"
                    
                    # Загружаем изображение
                    img_response = requests.get(photo_url, timeout=15)
                    
                    if img_response.status_code == 200:
                        # Сохраняем данные изображения в переменную
                        image_data = img_response.content
                        # Отправляем сигнал в главный поток
                        self.avatar_loaded.emit(image_data)
            else:
                pass  # Фото профиля не найдено
                        
        except Exception as e:
            logger.error(f"Ошибка загрузки аватара: {e}")
            logger.debug(traceback.format_exc())
            # Оставляем градиент если загрузка не удалась
    
    def _set_avatar_image(self, image_data):
        """Устанавливает загруженное изображение как аватар"""
        try:
            # Создаем QPixmap из данных изображения
            pixmap = QPixmap()
            success = pixmap.loadFromData(image_data)
            
            if not pixmap.isNull():
                # Масштабируем и обрезаем до круга
                scaled_pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                
                # Создаем круглую маску
                rounded_pixmap = QPixmap(40, 40)
                rounded_pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QBrush(scaled_pixmap))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(0, 0, 40, 40)
                painter.end()
                
                # Устанавливаем изображение
                self.avatar.setPixmap(rounded_pixmap)
                self.avatar.setStyleSheet("""
                    border-radius: 20px;
                    border: 2px solid #e2e8f0;
                """)
                
        except Exception as e:
            logger.error(f"Ошибка установки аватара: {e}")
            logger.debug(traceback.format_exc())

    def switch_page(self, page_id):
        """Переключает активную страницу"""        
        for btn_id, btn in self.nav_buttons.items():
            is_active = btn_id == page_id
            
            # Устанавливаем активное состояние
            btn.setProperty("active", "true" if is_active else "false")
            
            # Переключаем готовые цветные PNG
            if hasattr(btn, 'icon_widget') and hasattr(btn, 'has_png_icon') and btn.has_png_icon:
                # Всегда используем белую иконку, независимо от активного состояния
                if hasattr(btn, 'white_pixmap') and btn.white_pixmap:
                    btn.icon_widget.setPixmap(btn.white_pixmap)
            
            # Переключаем стили текста
            if hasattr(btn, 'text_label'):
                if is_active:
                    btn.text_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")
                else:
                    btn.text_label.setStyleSheet("font-size: 16px; font-weight: 500; color: rgba(255, 255, 255, 0.7);")
            
            # Переключаем цвет fallback символов
            if hasattr(btn, 'icon_widget') and not (hasattr(btn, 'has_png_icon') and btn.has_png_icon):
                if is_active:
                    btn.icon_widget.setStyleSheet("font-size: 28px; color: #ffffff; font-weight: bold;")  # Оставляем белый цвет
                else:
                    btn.icon_widget.setStyleSheet("font-size: 28px; color: rgba(255, 255, 255, 0.7);")
            
            # Применяем стили
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # ГЛАВНОЕ: Переключаем сам stacked_widget на нужную страницу с анимацией!
        if self.content_area and hasattr(self.content_area, 'stacked_widget'):
            page_index = self.get_page_index(page_id)
            if page_index is not None:
                # Используем анимированное переключение
                if hasattr(self.content_area, 'switch_page_animated'):
                    self.content_area.switch_page_animated(page_index)
                else:
                    # Fallback на обычное переключение
                    self.content_area.stacked_widget.setCurrentIndex(page_index)
                
                # Автообновление кэша при переходе в настройки
                if page_id == "settings":
                    try:
                        self.content_area.refresh_cache_info()
                    except Exception as e:
                        logger.error(f"Ошибка автообновления кэша: {e}")
        
        # Обновляем заголовок и подзаголовок страницы
        page_info = {
            "dashboard": {
                "title": "Главная",
                "subtitle": "Управление и информация"
            },
            "translations": {
                "title": "Квесты", 
                "subtitle": "Перевод FTB Quests"
            },
            "jar_mods": {
                "title": "JAR Моды",
                "subtitle": "Перевод Minecraft модов"
            },
            "settings": {
                "title": "Настройки",
                "subtitle": "Конфигурация приложения"
            },
            "about": {
                "title": "О программе",
                "subtitle": "Информация и поддержка"
            }
        }
        
        if hasattr(self, 'top_bar') and page_id in page_info:
            if hasattr(self.top_bar, 'page_title'):
                self.top_bar.page_title.setText(page_info[page_id]["title"])
            if hasattr(self.top_bar, 'page_subtitle'):
                self.top_bar.page_subtitle.setText(page_info[page_id]["subtitle"])
        
        self.current_page = page_id
        
        # Обновляем информацию о кэше при переходе на страницу настроек
        if page_id == "settings" and hasattr(self, 'refresh_cache_info'):
            self.refresh_cache_info()
    
    def get_page_index(self, page_id):
        """Возвращает индекс страницы в stacked_widget"""
        page_mapping = {
            "translations": 0,   # Страница перевода квестов
            "jar_mods": 1,       # Страница перевода JAR модов
            "settings": 2,       # Настройки
            "about": 3,          # О программе (заглушка)
            "files": 4,          # Файлы (заглушка)
            "analytics": 5,      # Аналитика (заглушка)
            "users": 6,          # Пользователи (заглушка)
            "reports": 7,        # Отчеты (заглушка)
            "messages": 8,       # Сообщения (заглушка)
            "notifications": 10  # Уведомления (заглушка)
        }
        return page_mapping.get(page_id)
    
    def get_icon_for_page(self, page_id):
        """Возвращает иконку для страницы"""
        icons = {
            "dashboard": "■",
            "translations": "◆", 
            "settings": "▼",
            "about": "◐"
        }
        return icons.get(page_id, "●")

class TopBar(QFrame):
    """Современная верхняя панель в темном стиле"""
    
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("topBar")
        self.setFixedHeight(80)
        
        # Основной layout для всей панели
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(32, 16, 32, 16)
        main_layout.setSpacing(0)
        
        # Левая часть - заголовки страниц
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        self.page_title = QLabel("Главная")
        self.page_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: 600;
        """)
        left_layout.addWidget(self.page_title)
        
        self.page_subtitle = QLabel("Управление и информация")
        self.page_subtitle.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 11px;
            font-weight: 400;
        """)
        left_layout.addWidget(self.page_subtitle)
        
        # Правая часть - кнопки действий
        right_container = QWidget()
        right_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 5, 100, 5)  # Правый отступ для кнопок управления окном
        right_layout.setSpacing(8)  # Уменьшили отступы: 12 → 8
        right_layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)
        
        # === КНОПКА 1: ПОДДЕРЖАТЬ ПРОЕКТ ===
        self.donate_btn = AnimatedDonateButton("Поддержать проект")
        self.donate_btn.setObjectName("donateButton")
        self.donate_btn.setFixedSize(210, 40)  # Увеличили: 200 → 210
        self.donate_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.donate_btn.clicked.connect(self.open_donate_link)
        right_layout.addWidget(self.donate_btn)
        
        # === КНОПКА 2: ОБНОВИТЬ ===
        self.update_btn = UpdateButton("Обновить")
        self.update_btn.setObjectName("updateButton")
        self.update_btn.setFixedSize(120, 40)  # Увеличили: 110 → 120
        self.update_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.update_btn.setToolTip("Проверить обновления")
        
        # Загружаем иконку обновления
        upd_icon_path = None
        asset_path = get_asset_path("upd.png")
        if asset_path.exists():
            upd_icon_path = str(asset_path)
        
        if upd_icon_path:
            pixmap = QPixmap(upd_icon_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                white_pixmap = QPixmap(scaled.size())
                white_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(white_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(white_pixmap.rect(), QColor(255, 255, 255))
                painter.end()
                self.update_btn.setIcon(QIcon(white_pixmap))
                self.update_btn.setIconSize(QSize(16, 16))
        
        self.update_btn.clicked.connect(self.check_for_updates)
        right_layout.addWidget(self.update_btn)
        
        # === КНОПКА 3: GITHUB ===
        self.github_btn = QPushButton("GitHub")
        self.github_btn.setObjectName("githubButton")
        self.github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.github_btn.setFixedSize(105, 40)  # Увеличили: 95 → 105
        self.github_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.github_btn.setToolTip("GitHub Repository")
        
        # Загружаем иконку GitHub
        git_icon_path = None
        asset_path = get_asset_path("git.png")
        if asset_path.exists():
            git_icon_path = str(asset_path)
        
        if git_icon_path:
            pixmap = QPixmap(git_icon_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                white_pixmap = QPixmap(scaled.size())
                white_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(white_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(white_pixmap.rect(), QColor(255, 255, 255))
                painter.end()
                self.github_btn.setIcon(QIcon(white_pixmap))
                self.github_btn.setIconSize(QSize(16, 16))
        
        self.github_btn.clicked.connect(self.open_github_repo)
        right_layout.addWidget(self.github_btn)
        
        # Добавляем только левый контейнер в layout
        main_layout.addWidget(left_container)
        main_layout.addStretch()
        
        # Правый контейнер позиционируем абсолютно
        right_container.setParent(self)
        
        # Сохраняем ссылку на правый контейнер для позиционирования
        self.right_container = right_container
        
        # Делаем панель перетаскиваемой
        self.mousePressEvent = self.title_bar_mouse_press
        self.mouseMoveEvent = self.title_bar_mouse_move
        self.mouseReleaseEvent = self.title_bar_mouse_release
        
        self.dragging = False
        self.drag_position = QPoint()
    
    def resizeEvent(self, event):
        """Позиционируем кнопки при изменении размера"""
        super().resizeEvent(event)
        if hasattr(self, 'right_container'):
            # Позиционируем правый контейнер в правом верхнем углу
            x = self.width() - self.right_container.width() + 95  # Отрицательный отступ - кнопки правее
            y = 16  # Отступ сверху
            self.right_container.move(x, y)
    
    def open_donate_link(self):
        """Показывает окно поддержки проекта"""
        if self.main_window:
            self.main_window.show_support_dialog()
    
    def check_for_updates(self):
        """Проверяет наличие обновлений"""
        if not UPDATER_AVAILABLE:
            QMessageBox.warning(
                self.main_window,
                "Система обновлений недоступна",
                "Модуль обновлений не найден или не настроен."
            )
            return
        
        # Проверяем, не запущена ли уже проверка
        if hasattr(self, 'update_checker') and self.update_checker:
            return
        
        # Создаем чекер обновлений
        self.update_checker = StandardUpdateChecker(self.main_window)
        
        # Подключаем сигналы
        self.update_checker.update_available.connect(self.on_update_available)
        self.update_checker.no_updates.connect(self.on_no_updates)
        self.update_checker.check_error.connect(self.on_update_error)
        
        # Запускаем проверку
        self.update_checker.check_for_updates(silent=False)
    
    def on_update_available(self, version_info):
        """Обработка доступного обновления"""
        # Показываем индикатор на кнопке
        self.update_btn.set_update_available(True)
        
        # Очищаем чекер
        self.update_checker = None
        
        if show_modern_update_dialog(self.main_window, version_info):
            start_update_process(self.main_window, version_info)
            # Убираем индикатор после начала обновления
            self.update_btn.set_update_available(False)
    
    def on_no_updates(self):
        """Обработка отсутствия обновлений"""
        # Очищаем чекер
        self.update_checker = None
        # Сообщение уже показано в StandardUpdateChecker
    
    def on_update_error(self, error_message):
        """Обработка ошибки проверки обновлений"""
        # Очищаем чекер
        self.update_checker = None
        # Сообщение уже показано в StandardUpdateChecker
    
    def open_github_repo(self):
        """Открывает GitHub репозиторий"""
        webbrowser.open("https://github.com/k1n1maro/ru-minetools")
    
    def title_bar_mouse_press(self, event):
        """Начало перетаскивания окна"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
    
    def title_bar_mouse_move(self, event):
        """Перетаскивание окна"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self.drag_position)
    
    def title_bar_mouse_release(self, event):
        """Окончание перетаскивания окна"""
        self.dragging = False
        


class ContentArea(QWidget):
    """Основная область контента"""
    
    def __init__(self, main_window=None):
        super().__init__()
        
        # Сохраняем ссылку на главное окно для доступа к методам поддержки
        self.main_window = main_window
        
        # Инициализируем статистику перевода
        self.translation_stats = {
            'processed': 0,
            'translated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Инициализируем кастомную подсказку
        self.custom_tooltip = None
        
        # Флаг для предотвращения множественных анимаций переключения
        self.page_animation_running = False
        self.target_page_index = None
        
        # Инициализируем переменные для анимаций
        self.blur_animation = None
        self.fade_out_animation = None
        self.blur_in_animation = None
        self.fade_in_animation = None
        
        # Устанавливаем фон #0A0A0A для основной рабочей области
        self.setStyleSheet("""
            ContentArea {
                background-color: #0a0a0a;
                border-top: 2px solid #4a4a4a;
                border-left: 2px solid #4a4a4a;
            }
        """)
        
        # Создаем стек виджетов для разных страниц
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                background-color: #0a0a0a;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
        
        # Создаем страницы
        self.create_quest_translation_page()
        self.create_jar_mods_translation_page()
        self.create_settings_page()
        self.create_about_page()
        self.create_placeholder_pages()
    
    
    
    def switch_page_animated(self, page_index):
        """Переключает страницу с плавной анимацией fade-out/fade-in и блюром"""
        if not hasattr(self, 'stacked_widget') or page_index is None:
            return
        
        # Сохраняем целевую страницу
        self.target_page_index = page_index
        
        # Если уже на этой странице и нет активной анимации, ничего не делаем
        if self.stacked_widget.currentIndex() == page_index and not (hasattr(self, 'page_animation_running') and self.page_animation_running):
            return
        
        # Если анимация уже запущена, останавливаем все анимации и сбрасываем состояние
        if hasattr(self, 'page_animation_running') and self.page_animation_running:
            # Останавливаем все активные анимации
            if hasattr(self, 'blur_animation') and self.blur_animation:
                self.blur_animation.stop()
            if hasattr(self, 'fade_out_animation') and self.fade_out_animation:
                self.fade_out_animation.stop()
            if hasattr(self, 'blur_in_animation') and self.blur_in_animation:
                self.blur_in_animation.stop()
            if hasattr(self, 'fade_in_animation') and self.fade_in_animation:
                self.fade_in_animation.stop()
            
            # Сбрасываем эффекты со всех виджетов
            for i in range(self.stacked_widget.count()):
                widget = self.stacked_widget.widget(i)
                if widget:
                    widget.setGraphicsEffect(None)
                    widget.setWindowOpacity(1.0)
        
        # Получаем текущий и новый виджеты
        current_widget = self.stacked_widget.currentWidget()
        new_widget = self.stacked_widget.widget(page_index)
        
        if not current_widget or not new_widget:
            self.stacked_widget.setCurrentIndex(page_index)
            return
        
        self.page_animation_running = True
        
        # Применяем блюр к текущему виджету с анимацией
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(0)
        current_widget.setGraphicsEffect(blur_effect)
        
        # Анимация блюра (0 -> 15) - увеличили радиус для более заметного эффекта
        self.blur_animation = QPropertyAnimation(blur_effect, b"blurRadius")
        self.blur_animation.setDuration(350)  # Увеличили с 200 до 350мс
        self.blur_animation.setStartValue(0)
        self.blur_animation.setEndValue(15)  # Увеличили с 10 до 15
        self.blur_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)  # Более плавная кривая
        
        # Анимация затухания текущей страницы
        self.fade_out_animation = QPropertyAnimation(current_widget, b"windowOpacity")
        self.fade_out_animation.setDuration(350)  # Увеличили с 200 до 350мс
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)  # Более плавная кривая
        
        # Когда затухание завершено, переключаем страницу
        def on_fade_out_finished():
            # Убираем блюр с текущей страницы
            current_widget.setGraphicsEffect(None)
            
            # Переключаем страницу
            self.stacked_widget.setCurrentIndex(page_index)
            
            # Устанавливаем начальную прозрачность для новой страницы
            new_widget.setWindowOpacity(0.0)
            
            # Применяем блюр к новой странице
            new_blur_effect = QGraphicsBlurEffect()
            new_blur_effect.setBlurRadius(15)  # Увеличили с 10 до 15
            new_widget.setGraphicsEffect(new_blur_effect)
            
            # Анимация убирания блюра (15 -> 0)
            self.blur_in_animation = QPropertyAnimation(new_blur_effect, b"blurRadius")
            self.blur_in_animation.setDuration(400)  # Увеличили с 200 до 400мс
            self.blur_in_animation.setStartValue(15)  # Увеличили с 10 до 15
            self.blur_in_animation.setEndValue(0)
            self.blur_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)  # Более плавная кривая
            
            # Анимация появления новой страницы
            self.fade_in_animation = QPropertyAnimation(new_widget, b"windowOpacity")
            self.fade_in_animation.setDuration(400)  # Увеличили с 200 до 400мс
            self.fade_in_animation.setStartValue(0.0)
            self.fade_in_animation.setEndValue(1.0)
            self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)  # Более плавная кривая
            
            # Когда появление завершено, убираем блюр
            def on_fade_in_finished():
                new_widget.setGraphicsEffect(None)
                self.page_animation_running = False
                
                # Проверяем, не была ли запрошена другая страница во время анимации
                if hasattr(self, 'target_page_index') and self.target_page_index != page_index:
                    # Запускаем переключение на новую целевую страницу
                    QTimer.singleShot(0, lambda: self.switch_page_animated(self.target_page_index))
            
            self.fade_in_animation.finished.connect(on_fade_in_finished)
            
            # Запускаем анимации появления
            self.blur_in_animation.start()
            self.fade_in_animation.start()
        
        self.fade_out_animation.finished.connect(on_fade_out_finished)
        
        # Запускаем анимации затухания
        self.blur_animation.start()
        self.fade_out_animation.start()
    
    def show_smooth_tooltip(self, widget, tooltip_text):
        """Показывает кастомную подсказку с плавной анимацией и закругленными углами"""
        # Останавливаем все активные анимации и таймеры
        if hasattr(self, 'tooltip_animation_group') and self.tooltip_animation_group:
            self.tooltip_animation_group.stop()
        if hasattr(self, 'tooltip_hide_animation_group') and self.tooltip_hide_animation_group:
            self.tooltip_hide_animation_group.stop()
            
        # Принудительно скрываем существующий tooltip
        if hasattr(self, 'custom_tooltip') and self.custom_tooltip:
            self.custom_tooltip.hide()
            self.custom_tooltip.deleteLater()
            self.custom_tooltip = None
        
        # Создаем подсказку с ГАРАНТИРОВАННО закругленными углами
        class RoundedTooltipWidget(QWidget):
            def __init__(self, text, parent=None):
                super().__init__(parent)
                self.text = text
                self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
                self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                
                # Создаем layout
                layout = QVBoxLayout(self)
                layout.setContentsMargins(18, 16, 18, 16)
                
                # Добавляем текст
                self.label = QLabel(text)
                self.label.setWordWrap(True)
                self.label.setStyleSheet("""
                    QLabel {
                        background: transparent;
                        border: none;
                        color: #e0e0e0;
                        font-size: 12px;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        line-height: 1.4;
                    }
                """)
                layout.addWidget(self.label)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Рисуем закругленный фон
                rect = self.rect()
                painter.setBrush(QBrush(QColor(20, 20, 20, 255)))  # Полностью непрозрачная (100%)
                painter.setPen(QPen(QColor(255, 255, 255, 8), 1))  # Еле заметная обводка как у лога (0.03 * 255 ≈ 8)
                painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 35, 35)
        
        self.custom_tooltip = RoundedTooltipWidget(tooltip_text, self)
        
        # Устанавливаем размер
        self.custom_tooltip.setMaximumWidth(320)
        self.custom_tooltip.adjustSize()
        
        # Улучшенное позиционирование - справа от иконки
        widget_global_pos = widget.mapToGlobal(QPoint(0, 0))
        tooltip_x = widget_global_pos.x() + widget.width() + 8  # Справа от иконки
        tooltip_y = widget_global_pos.y() - 10  # Немного выше
        
        # Проверяем, не выходит ли подсказка за границы экрана
        screen_geometry = QApplication.primaryScreen().geometry()
        if tooltip_x + self.custom_tooltip.width() > screen_geometry.width():
            # Показываем слева от иконки
            tooltip_x = widget_global_pos.x() - self.custom_tooltip.width() - 8
        
        self.custom_tooltip.move(tooltip_x, tooltip_y)
        
        # Начальное состояние для анимации - невидимый и сдвинутый вверх
        self.custom_tooltip.setWindowOpacity(0.0)
        original_geometry = self.custom_tooltip.geometry()
        
        # Начальная позиция - выше на 20 пикселей для эффекта "скольжения сверху"
        start_geometry = QRect(
            original_geometry.x(),
            original_geometry.y() - 20,  # Сдвигаем вверх
            original_geometry.width(),
            original_geometry.height()
        )
        
        self.custom_tooltip.setGeometry(start_geometry)
        self.custom_tooltip.show()
        
        # Создаем группу анимаций для одновременного fade-in и slide-down
        self.tooltip_animation_group = QParallelAnimationGroup()
        
        # Анимация прозрачности - плавное появление
        self.tooltip_fade_animation = QPropertyAnimation(self.custom_tooltip, b"windowOpacity")
        self.tooltip_fade_animation.setDuration(300)
        self.tooltip_fade_animation.setStartValue(0.0)
        self.tooltip_fade_animation.setEndValue(1.0)
        self.tooltip_fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # Плавная кривая
        
        # Анимация позиции - скольжение сверху вниз
        self.tooltip_geometry_animation = QPropertyAnimation(self.custom_tooltip, b"geometry")
        self.tooltip_geometry_animation.setDuration(300)
        self.tooltip_geometry_animation.setStartValue(start_geometry)
        self.tooltip_geometry_animation.setEndValue(original_geometry)
        self.tooltip_geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # Плавное скольжение
        
        self.tooltip_animation_group.addAnimation(self.tooltip_fade_animation)
        self.tooltip_animation_group.addAnimation(self.tooltip_geometry_animation)
        self.tooltip_animation_group.start()
        
        # Добавляем таймер для автоматического скрытия через 5 секунд
        if hasattr(self, 'tooltip_auto_hide_timer'):
            self.tooltip_auto_hide_timer.stop()
        
        self.tooltip_auto_hide_timer = QTimer()
        self.tooltip_auto_hide_timer.setSingleShot(True)
        self.tooltip_auto_hide_timer.timeout.connect(self.hide_smooth_tooltip)
        self.tooltip_auto_hide_timer.start(5000)  # 5 секунд
    
    def hide_smooth_tooltip(self):
        """Скрывает кастомную подсказку с плавной анимацией"""
        try:
            if not (hasattr(self, 'custom_tooltip') and self.custom_tooltip):
                return
                
            # Останавливаем все активные анимации
            if hasattr(self, 'tooltip_animation_group') and self.tooltip_animation_group:
                try:
                    self.tooltip_animation_group.stop()
                except:
                    pass
                self.tooltip_animation_group = None
                
            if hasattr(self, 'tooltip_hide_animation_group') and self.tooltip_hide_animation_group:
                try:
                    self.tooltip_hide_animation_group.stop()
                except:
                    pass
                self.tooltip_hide_animation_group = None
            
            # Если tooltip не видим, просто удаляем его
            if not self.custom_tooltip.isVisible():
                self._destroy_smooth_tooltip()
                return
                
            # Создаем группу анимаций для одновременного fade-out и slide-up
            self.tooltip_hide_animation_group = QParallelAnimationGroup()
            
            # Анимация прозрачности - плавное исчезновение
            self.tooltip_hide_fade_animation = QPropertyAnimation(self.custom_tooltip, b"windowOpacity")
            self.tooltip_hide_fade_animation.setDuration(150)  # Быстрее исчезновение
            self.tooltip_hide_fade_animation.setStartValue(self.custom_tooltip.windowOpacity())
            self.tooltip_hide_fade_animation.setEndValue(0.0)
            self.tooltip_hide_fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            
            # Анимация позиции - скольжение вверх
            current_geometry = self.custom_tooltip.geometry()
            hide_geometry = QRect(
                current_geometry.x(),
                current_geometry.y() - 10,  # Сдвигаем вверх при скрытии
                current_geometry.width(),
                current_geometry.height()
            )
            
            self.tooltip_hide_geometry_animation = QPropertyAnimation(self.custom_tooltip, b"geometry")
            self.tooltip_hide_geometry_animation.setDuration(150)
            self.tooltip_hide_geometry_animation.setStartValue(current_geometry)
            self.tooltip_hide_geometry_animation.setEndValue(hide_geometry)
            self.tooltip_hide_geometry_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            
            self.tooltip_hide_animation_group.addAnimation(self.tooltip_hide_fade_animation)
            self.tooltip_hide_animation_group.addAnimation(self.tooltip_hide_geometry_animation)
            self.tooltip_hide_animation_group.finished.connect(self._destroy_smooth_tooltip)
            self.tooltip_hide_animation_group.start()
            
        except Exception as e:
            logger.error(f"Ошибка в hide_smooth_tooltip: {e}")
            # В случае ошибки просто удаляем tooltip
            try:
                self._destroy_smooth_tooltip()
            except:
                pass
    
    def handle_tooltip_leave(self):
        """Обрабатывает уход мыши с иконки помощи"""
        try:
            # Останавливаем ВСЕ таймеры tooltip'ов
            if hasattr(self, 'tooltip_timer'):
                try:
                    self.tooltip_timer.stop()
                except:
                    pass
            if hasattr(self, 'jar_tooltip_timer'):
                try:
                    self.jar_tooltip_timer.stop()
                except:
                    pass
            if hasattr(self, 'threads_tooltip_timer'):
                try:
                    self.threads_tooltip_timer.stop()
                except:
                    pass
            if hasattr(self, 'cache_tooltip_timer'):
                try:
                    self.cache_tooltip_timer.stop()
                except:
                    pass
            if hasattr(self, 'tooltip_auto_hide_timer'):
                try:
                    self.tooltip_auto_hide_timer.stop()
                except:
                    pass
            
            # Скрываем подсказку если она показана
            self.hide_smooth_tooltip()
            
        except Exception as e:
            logger.error(f"Ошибка в handle_tooltip_leave: {e}")
            # В случае ошибки принудительно очищаем tooltip
            try:
                self._destroy_smooth_tooltip()
            except:
                pass
    
    def _destroy_smooth_tooltip(self):
        """Удаляет подсказку после анимации"""
        try:
            if hasattr(self, 'custom_tooltip') and self.custom_tooltip:
                self.custom_tooltip.hide()
                self.custom_tooltip.deleteLater()
                self.custom_tooltip = None
                
            # Очищаем все анимации
            if hasattr(self, 'tooltip_animation_group'):
                try:
                    if self.tooltip_animation_group:
                        self.tooltip_animation_group.stop()
                except:
                    pass
                self.tooltip_animation_group = None
                
            if hasattr(self, 'tooltip_hide_animation_group'):
                try:
                    if self.tooltip_hide_animation_group:
                        self.tooltip_hide_animation_group.stop()
                except:
                    pass
                self.tooltip_hide_animation_group = None
                
        except Exception as e:
            logger.error(f"Ошибка в _destroy_smooth_tooltip: {e}")
            # Принудительно очищаем все
            try:
                self.custom_tooltip = None
                self.tooltip_animation_group = None
                self.tooltip_hide_animation_group = None
            except:
                pass
    
    # Оставляем старые методы для совместимости
    def show_custom_tooltip(self, widget, tooltip_text):
        """Показывает кастомную анимированную подсказку (старый метод)"""
        self.show_smooth_tooltip(widget, tooltip_text)
    
    def hide_custom_tooltip(self):
        """Скрывает кастомную подсказку с анимацией (старый метод)"""
        self.hide_smooth_tooltip()
    
    def _destroy_tooltip(self):
        """Удаляет подсказку после анимации (старый метод)"""
        self._destroy_smooth_tooltip()

    def create_quest_translation_page(self):
        """
        Создает современную страницу перевода квестов
        
        Дизайн:
        - Glassmorphism эффекты
        - Градиенты и тени
        - Плавные анимации
        - Современный минимализм
        """
        quest_page = QWidget()
        quest_page.setStyleSheet("""
            QWidget {
                background-color: #0f0f0f;
            }
        """)
        main_layout = QVBoxLayout(quest_page)
        main_layout.setContentsMargins(60, 32, 60, 32)  # Одинаковые отступы сверху и снизу
        main_layout.setSpacing(14)  # Увеличили расстояние между элементами с 10 до 14
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Центрируем содержимое
        
        # 1. ЗАГОЛОВОК БЛОКА ВЫБОРА ПАПКИ С ПОДСКАЗКОЙ
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)  # Убираем нижний отступ полностью
        header_layout.setSpacing(6)  # Уменьшаем расстояние между элементами
        
        folder_label = QLabel("Выберите папку с игрой")
        folder_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(folder_label)
        
        # Создаем идеально круглую иконку помощи
        help_icon = QPushButton("?")
        help_icon.setFixedSize(24, 24)  # Увеличиваем для лучшей видимости
        help_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        help_icon.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 12px;
                color: #d0d0d0;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial;
                margin-left: 8px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #6a6a6a;
                color: #ffffff;
                font-weight: 800;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
            }
        """)
        
        # Информативная подсказка с подробным описанием
        help_tooltip = """
        <div style="font-weight: 600; color: #ffffff; margin-bottom: 14px; font-size: 13px;">Как это работает?</div>
        
        <div style="margin-bottom: 12px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Поиск файлов:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • Находит папки <strong>chapters</strong> и <strong>lang</strong><br>
        </div>
        </div>
        
        <div style="margin-bottom: 12px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Процесс перевода:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • <strong>chapters/</strong> — все .snbt файлы квестов<br>
        • <strong>lang/</strong> — файлы из папки en_us/ → ru_ru/ (если ru_ru/ уже есть - пропускаем)<br>
        </div>
        </div>
        
        <div style="margin-bottom: 10px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Результат:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • Создает папки <strong>chapters-translate/</strong> и <strong>lang-translate/</strong><br>
        </div>
        </div>
        
        <div style="text-align: center; margin-top: 14px; padding-top: 10px; border-top: 1px solid #444; color: #888; font-size: 11px;">
        Выберите корневую папку вашей игры
        </div>
        """
        
        # Добавляем иконку помощи сразу после надписи
        header_layout.addWidget(help_icon)
        
        # Создаем кастомную анимированную подсказку с улучшенной анимацией
        self.custom_tooltip = None
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(lambda: self.show_smooth_tooltip(help_icon, help_tooltip))
        
        # Безопасное подключение событий
        def safe_enter_event(event):
            try:
                if hasattr(self, 'tooltip_timer') and self.tooltip_timer:
                    self.tooltip_timer.start(150)
            except Exception as e:
                logger.error(f"Ошибка в tooltip enterEvent: {e}")
        
        def safe_leave_event(event):
            try:
                self.handle_tooltip_leave()
            except Exception as e:
                logger.error(f"Ошибка в tooltip leaveEvent: {e}")
        
        help_icon.enterEvent = safe_enter_event
        help_icon.leaveEvent = safe_leave_event
        header_layout.addStretch()
        
        main_layout.addWidget(header_container)
        
        # 2. БЛОК ВЫБОРА ПАПКИ (главный элемент)
        folder_container = QWidget()
        folder_layout = QHBoxLayout(folder_container)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(12)
        
        # Поле ввода - спокойное, с коротким placeholder
        self.quest_folder_input = QLineEdit()
        self.quest_folder_input.setPlaceholderText("Путь к папке игры...")
        self.quest_folder_input.setFixedHeight(48)
        self.quest_folder_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 24px;
                padding: 0 20px;
                font-size: 14px;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border: 1px solid #8b5cf6;
                background-color: #1f1f1f;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        folder_layout.addWidget(self.quest_folder_input, 1)
        
        # Кнопка "Выбрать" - круглая, secondary style
        browse_btn = QPushButton("Выбрать...")
        browse_btn.setFixedHeight(48)
        browse_btn.setFixedWidth(120)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_quest_folder)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 24px;
                color: #b0b0b0;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        folder_layout.addWidget(browse_btn)
        
        main_layout.addWidget(folder_container)
        
        # 3. КНОПКА "НАЧАТЬ ПЕРЕВОД" (PRIMARY CTA - точно такая же как кнопка авторизации)
        self.start_translation_btn = HoverLiftButton("НАЧАТЬ ПЕРЕВОД")
        self.start_translation_btn.setFixedHeight(60)  # Уменьшили высоту с 80 до 60
        self.start_translation_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_translation_btn.clicked.connect(self.start_quest_translation)
        self.quest_folder_selected = False
        
        # Применяем точно такие же стили как у кнопки авторизации
        self.start_translation_btn.setStyleSheet("""
            QPushButton {
                /* Футуристический градиент от фиолетового к розовому */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                
                /* Мягкие закругленные углы */
                border-radius: 25px;
                
                /* Стеклянный эффект с внутренним свечением */
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                
                /* Текст */
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                /* Усиленное свечение при наведении */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                
                /* Усиленные границы */
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                /* Эффект вдавливания */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9540E6,
                    stop:0.3 #A650F0,
                    stop:0.7 #C060FF,
                    stop:1 #D565FF);
                
                /* Инвертированные границы */
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        
        # Добавляем анимации как у кнопки авторизации
        self.setup_translation_button_animations()
        
        main_layout.addWidget(self.start_translation_btn)
        
        # Glassmorphism Progress Bar - всегда видимый
        self.quest_progress = GlassmorphismProgressBar()
        self.quest_progress.setText("Готов к работе")
        self.quest_progress.setValue(0)
        
        main_layout.addWidget(self.quest_progress)
        
        # 3. КОМПАКТНЫЙ ЛОГ ПЕРЕВОДА
        # UX: Уменьшенная высота, современный дизайн
        self.quest_log = QTextEdit()
        self.quest_log.setReadOnly(True)
        self.quest_log.setMaximumHeight(330)  # Уменьшили с 350 до 330 для баланса
        self.quest_log.setStyleSheet("""
            QTextEdit {
                /* Возвращаем прежний фон */
                background: rgba(20, 20, 20, 0.6);
                
                /* Еле заметная обводка */
                border: 1px solid rgba(255, 255, 255, 0.03);
                
                /* Закругленные углы как у кнопки "Начать перевод" */
                border-radius: 25px;
                
                padding: 20px;
                color: #cbd5e1;
                font-size: 11px;
                font-family: 'FindSans Pro', 'Segoe UI', Arial, sans-serif;
                line-height: 1.4;
                selection-background-color: rgba(20, 20, 20, 0.8);
            }
            QScrollBar:vertical {
                background: rgba(30, 30, 30, 0.5);
                width: 8px;
                border: none;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(164, 70, 255, 0.6);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(164, 70, 255, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Компактное приветственное сообщение (без декора)
        # UX: Краткая и информативная инструкция
        welcome_msg = """🎯 Переводчик квестов FTB

📁 Выберите папку игры → 🚀 Нажмите "Начать перевод"
        """
        self.quest_log.setPlainText(welcome_msg.strip())
        
        main_layout.addWidget(self.quest_log, 1)
        
        # 4. ВТОРИЧНЫЕ КНОПКИ (secondary style - серые, спокойные)
        # UX: Одинаковая высота, минимум контраста
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 4, 0, 0)  # Еще больше уменьшили верхний отступ с 8 до 4
        bottom_layout.setSpacing(12)
        
        # Кнопка паузы - анимированная
        self.stop_translation_btn = HoverLiftButton("Пауза")
        self.stop_translation_btn.setFixedHeight(56)  # Увеличили с 48 до 56
        self.stop_translation_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_translation_btn.clicked.connect(self.toggle_quest_translation_pause)
        self.stop_translation_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(self.stop_translation_btn)
        
        # Кнопка открытия результата - анимированная
        self.open_result_btn = HoverLiftButton("Открыть результат")
        self.open_result_btn.setFixedHeight(56)  # Увеличили с 48 до 56
        self.open_result_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_result_btn.clicked.connect(self.open_quest_result)
        self.open_result_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(self.open_result_btn)
        
        # Кнопка очистки лога - анимированная
        clear_log_btn = HoverLiftButton("Очистить лог")
        clear_log_btn.setFixedHeight(56)  # Увеличили с 48 до 56
        clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_log_btn.clicked.connect(self.clear_quest_log)
        clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(clear_log_btn)
        
        bottom_layout.addStretch()
        
        main_layout.addWidget(bottom_panel)
        
        self.stacked_widget.addWidget(quest_page)

    def create_jar_mods_translation_page(self):
        """
        Создает современную страницу перевода JAR модов
        Новая реализация на основе translate_jar_simple.py
        """
        jar_page = QWidget()
        jar_page.setStyleSheet("""
            QWidget {
                background-color: #0f0f0f;
            }
        """)
        main_layout = QVBoxLayout(jar_page)
        main_layout.setContentsMargins(60, 32, 60, 32)
        main_layout.setSpacing(14)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 1. ЗАГОЛОВОК С ПОДСКАЗКОЙ
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        folder_label = QLabel("Выберите JAR файлы модов")
        folder_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(folder_label)
        
        # Иконка помощи
        help_icon = QPushButton("?")
        help_icon.setFixedSize(24, 24)
        help_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        help_icon.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 12px;
                color: #d0d0d0;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Segoe UI', Arial;
                margin-left: 8px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #6a6a6a;
                color: #ffffff;
                font-weight: 800;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
            }
        """)
        
        help_tooltip = """
        <div style="font-weight: 600; color: #ffffff; margin-bottom: 14px; font-size: 13px;">Простой переводчик JAR модов</div>
        
        <div style="margin-bottom: 12px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Что переводится:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • <strong>assets/*/lang/en_us.json</strong> → ru_ru.json<br>
        • <strong>assets/*/patchouli_books/**/en_us/**/*.json</strong> → ru_ru<br>
        </div>
        </div>
        
        <div style="margin-bottom: 10px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Безопасность:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • Пропускает уже переведенные моды<br>
        • Не трогает код и данные<br>
        • Простая и надежная логика<br>
        </div>
        </div>
        
        <div style="text-align: center; margin-top: 14px; padding-top: 10px; border-top: 1px solid #444; color: #888; font-size: 11px;">
        Аналогично переводу квестов
        </div>
        """
        
        header_layout.addWidget(help_icon)
        
        # Подсказка
        self.jar_custom_tooltip = None
        self.jar_tooltip_timer = QTimer()
        self.jar_tooltip_timer.setSingleShot(True)
        self.jar_tooltip_timer.timeout.connect(lambda: self.show_smooth_tooltip(help_icon, help_tooltip))
        
        # Безопасное подключение событий для JAR tooltip
        def safe_jar_enter_event(event):
            try:
                if hasattr(self, 'jar_tooltip_timer') and self.jar_tooltip_timer:
                    self.jar_tooltip_timer.start(150)
            except Exception as e:
                logger.error(f"Ошибка в JAR tooltip enterEvent: {e}")
        
        def safe_jar_leave_event(event):
            try:
                self.handle_tooltip_leave()
            except Exception as e:
                logger.error(f"Ошибка в JAR tooltip leaveEvent: {e}")
        
        help_icon.enterEvent = safe_jar_enter_event
        help_icon.leaveEvent = safe_jar_leave_event
        header_layout.addStretch()
        
        main_layout.addWidget(header_container)
        
        # 2. БЛОК ВЫБОРА JAR ФАЙЛОВ
        jar_container = QWidget()
        jar_layout = QHBoxLayout(jar_container)
        jar_layout.setContentsMargins(0, 0, 0, 0)
        jar_layout.setSpacing(12)
        
        # Поле ввода
        self.jar_path_input = QLineEdit()
        self.jar_path_input.setPlaceholderText("Путь к JAR файлу или папке...")
        self.jar_path_input.setFixedHeight(48)
        self.jar_path_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 24px;
                padding: 0 20px;
                font-size: 14px;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border: 1px solid #8b5cf6;
                background-color: #1f1f1f;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        jar_layout.addWidget(self.jar_path_input, 1)
        
        # Кнопка "Файл"
        browse_file_btn = QPushButton("Файл")
        browse_file_btn.setFixedHeight(48)
        browse_file_btn.setFixedWidth(80)
        browse_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_file_btn.clicked.connect(self.browse_jar_file)
        browse_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 24px;
                color: #b0b0b0;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        jar_layout.addWidget(browse_file_btn)
        
        # Кнопка "Папка"
        browse_folder_btn = QPushButton("Папка")
        browse_folder_btn.setFixedHeight(48)
        browse_folder_btn.setFixedWidth(80)
        browse_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_btn.clicked.connect(self.browse_jar_folder)
        browse_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 24px;
                color: #b0b0b0;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        jar_layout.addWidget(browse_folder_btn)
        
        main_layout.addWidget(jar_container)
        

        
        # 3. КНОПКА "НАЧАТЬ ПЕРЕВОД"
        self.jar_translate_btn = HoverLiftButton("НАЧАТЬ ПЕРЕВОД JAR МОДОВ")
        self.jar_translate_btn.setFixedHeight(60)
        self.jar_translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.jar_translate_btn.clicked.connect(self.start_jar_translation)
        
        self.jar_translate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9540E6,
                    stop:0.3 #A650F0,
                    stop:0.7 #C060FF,
                    stop:1 #D565FF);
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        
        main_layout.addWidget(self.jar_translate_btn)
        
        # 4. ПРОГРЕСС БАР
        self.jar_progress = GlassmorphismProgressBar()
        self.jar_progress.setText("Готов к работе")
        self.jar_progress.setValue(0)
        
        main_layout.addWidget(self.jar_progress)
        
        # 5. ЛОГ ПЕРЕВОДА
        self.jar_log = QTextEdit()
        self.jar_log.setReadOnly(True)
        self.jar_log.setMaximumHeight(330)
        self.jar_log.setStyleSheet("""
            QTextEdit {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
                padding: 20px;
                color: #cbd5e1;
                font-size: 11px;
                font-family: 'FindSans Pro', 'Segoe UI', Arial, sans-serif;
                line-height: 1.4;
                selection-background-color: rgba(20, 20, 20, 0.8);
            }
            QScrollBar:vertical {
                background: rgba(30, 30, 30, 0.5);
                width: 8px;
                border: none;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(164, 70, 255, 0.6);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(164, 70, 255, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        welcome_msg = """🎯 Переводчик JAR модов Minecraft

📁 Выберите JAR файл(ы) → 🚀 Нажмите "Начать перевод"
        """
        self.jar_log.setPlainText(welcome_msg.strip())
        
        main_layout.addWidget(self.jar_log, 1)
        
        # 6. ВТОРИЧНЫЕ КНОПКИ
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(12)
        
        # Кнопка паузы/возобновления
        self.jar_pause_btn = HoverLiftButton("Пауза")
        self.jar_pause_btn.setFixedHeight(56)
        self.jar_pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.jar_pause_btn.clicked.connect(self.toggle_jar_translation_pause)
        self.jar_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(self.jar_pause_btn)
        
        # Кнопка открытия результата
        self.jar_open_result_btn = HoverLiftButton("Открыть результат")
        self.jar_open_result_btn.setFixedHeight(56)
        self.jar_open_result_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.jar_open_result_btn.clicked.connect(self.open_jar_result)
        self.jar_open_result_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(self.jar_open_result_btn)
        
        # Кнопка очистки лога
        clear_jar_log_btn = HoverLiftButton("Очистить лог")
        clear_jar_log_btn.setFixedHeight(56)
        clear_jar_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_jar_log_btn.clicked.connect(self.clear_jar_log)
        clear_jar_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 28px;
                color: #b0b0b0;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        bottom_layout.addWidget(clear_jar_log_btn)
        
        # Выбор количества потоков - новый однородный дизайн
        threads_label = QLabel("Потоков:")
        threads_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 12px;
                background: transparent;
                border: none;
                margin-right: -6px;
            }
        """)
        bottom_layout.addWidget(threads_label)
        
        # Создаем контейнер для переключателя потоков
        self.threads_value = "6"  # Оптимальное значение по умолчанию для 5-строчных батчей
        threads_container = QWidget()
        threads_container.setFixedSize(80, 32)  # Возвращаем размер для двух кнопок
        threads_layout = QHBoxLayout(threads_container)
        threads_layout.setContentsMargins(2, 2, 2, 2)
        threads_layout.setSpacing(2)
        
        # Кнопки переключения потоков
        self.threads_btn_4 = QPushButton("4")
        self.threads_btn_6 = QPushButton("6")
        
        for btn in [self.threads_btn_4, self.threads_btn_6]:
            btn.setFixedSize(36, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, value=btn.text(): self.set_threads_value(value))
        
        # Устанавливаем стили для активной/неактивной кнопки
        self.update_threads_buttons()
        
        threads_layout.addWidget(self.threads_btn_4)
        threads_layout.addWidget(self.threads_btn_6)
        
        # Стиль контейнера
        threads_container.setStyleSheet("""
            QWidget {
                background: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 16px;
            }
            QWidget:hover {
                border-color: #8b5cf6;
            }
        """)
        
        bottom_layout.addWidget(threads_container)
        
        bottom_layout.addStretch()
        
        main_layout.addWidget(bottom_panel)
        
        self.stacked_widget.addWidget(jar_page)

    def set_threads_value(self, value):
        """Устанавливает значение потоков"""
        self.threads_value = value
        self.update_threads_buttons()
    
    def update_threads_buttons(self):
        """Обновляет стили кнопок потоков"""
        active_style = """
            QPushButton {
                background: #8b5cf6;
                border: none;
                border-radius: 14px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
        """
        
        inactive_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton:hover {
                background: rgba(139, 92, 246, 0.2);
                color: #ffffff;
            }
        """
        
        # Применяем стили
        if self.threads_value == "4":
            self.threads_btn_4.setStyleSheet(active_style)
            self.threads_btn_6.setStyleSheet(inactive_style)
        else:  # threads_value == "6"
            self.threads_btn_4.setStyleSheet(inactive_style)
            self.threads_btn_6.setStyleSheet(active_style)
    
    def get_threads_count(self):
        """Возвращает текущее количество потоков"""
        return int(self.threads_value)

    def browse_minecraft_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите корневую папку Minecraft сборки",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.minecraft_folder_input.setText(folder)
            self.scan_btn.setEnabled(True)
            self.scan_btn.start_pulse()
            
            # Обновляем статус
            self.status_label.setText("✅ Папка выбрана! Нажмите 'Найти файлы' для поиска")
            self.status_label.setStyleSheet("""
                color: #10b981;
                font-size: 14px;
                font-weight: 600;
                padding: 12px;
                background-color: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                margin-top: 8px;
            """)
    
    def scan_translation_files(self):
        """Сканирует папку Minecraft на наличие файлов для перевода"""
        minecraft_path = Path(self.minecraft_folder_input.text().strip())
        
        if not minecraft_path.exists():
            self.status_label.setText("❌ Выбранная папка не существует!")
            self.status_label.setStyleSheet("""
                color: #ef4444;
                font-size: 14px;
                font-weight: 600;
                padding: 12px;
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                margin-top: 8px;
            """)
            return
        
        # Обновляем статус - начинаем поиск
        self.status_label.setText("🔍 Поиск файлов для перевода...")
        self.status_label.setStyleSheet("""
            color: #3b82f6;
            font-size: 14px;
            font-weight: 600;
            padding: 12px;
            background-color: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 8px;
            margin-top: 8px;
        """)
        
        # Ищем файлы для перевода
        found_files = self.find_translation_files(minecraft_path)
        
        if found_files:
            total_files = sum(len(files) for files in found_files.values())
            
            # Формируем отчет
            report_lines = [f"🎉 Найдено {total_files} файлов для перевода:"]
            
            for file_type, files in found_files.items():
                if files:
                    report_lines.append(f"  • {file_type}: {len(files)} файлов")
            
            report_text = "\n".join(report_lines)
            
            self.status_label.setText(report_text)
            self.status_label.setStyleSheet("""
                color: #10b981;
                font-size: 13px;
                font-weight: 600;
                padding: 16px;
                background-color: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                margin-top: 8px;
                line-height: 1.4;
            """)
            
            # Показываем диалог с подробностями
            self.show_translation_files_dialog(found_files)
        else:
            self.status_label.setText("❌ Файлы для перевода не найдены\n\nПроверьте, что выбрана корневая папка Minecraft сборки")
            self.status_label.setStyleSheet("""
                color: #ef4444;
                font-size: 14px;
                font-weight: 600;
                padding: 12px;
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                margin-top: 8px;
            """)
    
    def find_translation_files(self, minecraft_path):
        """Ищет все файлы для перевода в папке Minecraft"""
        found_files = {
            "FTB Квесты (.snbt)": [],
            "Локализация модов (.json)": [],
            "Patchouli книги (.json)": [],
            "Достижения (.json)": []
        }
        
        try:
            # Ищем FTB квесты
            ftb_quests_path = minecraft_path / "config" / "ftbquests" / "quests"
            if ftb_quests_path.exists():
                snbt_files = list(ftb_quests_path.rglob("*.snbt"))
                found_files["FTB Квесты (.snbt)"] = snbt_files
            
            # Ищем файлы локализации модов
            mods_path = minecraft_path / "mods"
            if mods_path.exists():
                for mod_file in mods_path.glob("*.jar"):
                    # Здесь можно добавить проверку содержимого jar файлов
                    pass
            
            # Ищем lang файлы в ресурспаках
            resourcepacks_path = minecraft_path / "resourcepacks"
            if resourcepacks_path.exists():
                lang_files = list(resourcepacks_path.rglob("**/lang/*.json"))
                found_files["Локализация модов (.json)"].extend(lang_files)
            
            # Ищем Patchouli книги
            patchouli_path = minecraft_path / "config" / "patchouli"
            if patchouli_path.exists():
                patchouli_files = list(patchouli_path.rglob("**/*.json"))
                found_files["Patchouli книги (.json)"] = patchouli_files
            
            # Ищем достижения
            advancements_path = minecraft_path / "config" / "advancements"
            if advancements_path.exists():
                advancement_files = list(advancements_path.rglob("*.json"))
                found_files["Достижения (.json)"] = advancement_files
            
        except Exception as e:
            logger.error(f"Ошибка при поиске файлов: {e}")
        
        return found_files
    
    def show_translation_files_dialog(self, found_files):
        """Показывает диалог с найденными файлами"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Найденные файлы для перевода")
        dialog.setFixedSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        
        # Заголовок
        title = QLabel("📋 Найденные файлы для перевода")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #bb86fc;
            margin-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Текстовое поле с результатами
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #2d3748;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                color: #e2e8f0;
            }
        """)
        
        # Формируем текст с результатами
        result_text = ""
        total_files = 0
        
        for file_type, files in found_files.items():
            if files:
                result_text += f"\n🔹 {file_type} ({len(files)} файлов):\n"
                for file_path in files[:10]:  # Показываем первые 10 файлов
                    result_text += f"   • {file_path.name}\n"
                if len(files) > 10:
                    result_text += f"   ... и еще {len(files) - 10} файлов\n"
                result_text += "\n"
                total_files += len(files)
        
        result_text = f"Всего найдено: {total_files} файлов\n" + result_text
        text_area.setPlainText(result_text)
        layout.addWidget(text_area)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def create_settings_page(self):
        """Создает страницу настроек - только информация о системе"""
        settings_page = QWidget()
        settings_page.setStyleSheet("QWidget { background-color: #0f0f0f; }")
        
        main_layout = QVBoxLayout(settings_page)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)
        
        # === ИНФОРМАЦИЯ О СИСТЕМЕ ===
        info_container = QWidget()
        info_container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(30, 25, 30, 25)
        info_layout.setSpacing(15)
        
        # Заголовок секции
        info_title = QLabel("Информация о системе")
        info_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        info_layout.addWidget(info_title)
        
        # Версия программы - берем из конфигурации
        try:
            from config.update_config import CURRENT_VERSION
            version_text = f"Версия программы: {CURRENT_VERSION}"
        except ImportError:
            version_text = "Версия программы: 1.0.0"
        
        version_label = QLabel(version_text)
        version_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 5px 0px;
            }
        """)
        info_layout.addWidget(version_label)
        
        # Статистика использования
        stats_file = "translation_stats.json"
        total_files = 0
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    total_files = stats.get('total_translated', 0)
            except:
                pass
        
        stats_label = QLabel(f"Всего переведено файлов: {total_files}")
        stats_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 5px 0px;
            }
        """)
        info_layout.addWidget(stats_label)
        self.stats_label = stats_label  # Сохраняем для обновления
        
        main_layout.addWidget(info_container)
        
        # === УПРАВЛЕНИЕ КЭШЕМ ПЕРЕВОДОВ ===
        cache_container = QWidget()
        cache_container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
            }
        """)
        cache_layout = QVBoxLayout(cache_container)
        cache_layout.setContentsMargins(30, 25, 30, 25)
        cache_layout.setSpacing(15)
        
        # Заголовок секции с иконкой помощи
        cache_header = QHBoxLayout()
        cache_title = QLabel("Кэш переводов")
        cache_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        cache_header.addWidget(cache_title)
        
        # Иконка помощи для кэша
        cache_help_icon = QPushButton("?")
        cache_help_icon.setFixedSize(24, 24)
        cache_help_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        cache_help_icon.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 12px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #6a6a6a;
                color: #ffffff;
                font-weight: 800;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
                border-color: #4a4a4a;
            }
        """)
        
        cache_help_tooltip = """
        <div style="font-weight: 600; color: #ffffff; margin-bottom: 14px; font-size: 13px;">Кэш переводов - что это?</div>
        
        <div style="margin-bottom: 12px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Что такое кэш:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • <strong>Память программы</strong> - сохраняет уже переведенные строки<br>
        • <strong>Ускорение работы</strong> - повторные переводы в 10-50 раз быстрее<br>
        • <strong>Экономия API</strong> - меньше запросов к серверу переводов<br>
        </div>
        </div>
        
        <div style="margin-bottom: 12px;">
        <div style="color: #bb86fc; font-weight: 600; margin-bottom: 6px;">Когда очищать кэш:</div>
        <div style="margin-left: 14px; color: #e0e0e0;">
        • <strong>Плохое качество</strong> - если переводы стали хуже<br>
        • <strong>Смена языка</strong> - при переходе на другой язык<br>
        • <strong>Освобождение места</strong> - кэш занимает ~50-200 МБ<br>
        • <strong>Проблемы с переводом</strong> - если что-то работает неправильно<br>
        </div>
        </div>
        
        <div style="text-align: center; margin-top: 14px; padding-top: 10px; border-top: 1px solid #444; color: #888; font-size: 11px;">
        После очистки первые переводы будут медленнее
        </div>
        """
        
        # Создаем таймер для подсказки кеша
        self.cache_tooltip_timer = QTimer()
        self.cache_tooltip_timer.setSingleShot(True)
        self.cache_tooltip_timer.timeout.connect(lambda: self.show_smooth_tooltip(cache_help_icon, cache_help_tooltip))
        
        # Безопасное подключение событий для cache tooltip
        def safe_cache_enter_event(event):
            try:
                if hasattr(self, 'cache_tooltip_timer') and self.cache_tooltip_timer:
                    self.cache_tooltip_timer.start(150)
            except Exception as e:
                logger.error(f"Ошибка в cache tooltip enterEvent: {e}")
        
        def safe_cache_leave_event(event):
            try:
                self.handle_tooltip_leave()
            except Exception as e:
                logger.error(f"Ошибка в cache tooltip leaveEvent: {e}")
        
        cache_help_icon.enterEvent = safe_cache_enter_event
        cache_help_icon.leaveEvent = safe_cache_leave_event
        
        cache_header.addWidget(cache_help_icon)
        cache_header.addStretch()
        
        cache_layout.addLayout(cache_header)
        
        # Информация о кэше
        self.cache_info_label = QLabel("Загрузка информации о кэше...")
        self.cache_info_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                background: transparent;
                border: none;
                padding: 5px 0px;
            }
        """)
        cache_layout.addWidget(self.cache_info_label)
        
        # Путь к файлу кэша
        cache_path_layout = QHBoxLayout()
        cache_path_label = QLabel("Файл кэша:")
        cache_path_label.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                background: transparent;
                border: none;
                min-width: 100px;
            }
        """)
        cache_path_layout.addWidget(cache_path_label)
        
        cache_path = os.path.abspath("translation_cache.pkl")
        self.cache_path_display = QLabel(cache_path)
        
        # Устанавливаем шрифт программно
        font = QFont("Segoe UI", 12)
        font.setFamily("Segoe UI")
        self.cache_path_display.setFont(font)
        
        self.cache_path_display.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 12px;
                background: rgba(30, 30, 30, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 24px;
                padding: 14px 18px;
            }
        """)
        self.cache_path_display.setWordWrap(True)
        cache_path_layout.addWidget(self.cache_path_display, 1)
        
        # Кнопка открытия папки с кэшем
        open_cache_folder_btn = HoverLiftButton("Открыть")
        open_cache_folder_btn.setFixedHeight(48)
        open_cache_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_cache_folder_btn.setToolTip("Открыть папку с файлом кэша")
        open_cache_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 24px;
                color: #b0b0b0;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
        """)
        open_cache_folder_btn.clicked.connect(self.open_cache_folder)
        cache_path_layout.addWidget(open_cache_folder_btn)
        
        cache_layout.addLayout(cache_path_layout)
        
        # Кнопки управления кэшем
        cache_buttons_layout = QHBoxLayout()
        cache_buttons_layout.setSpacing(12)
        
        # Кнопка очистки кэша
        clear_cache_btn = HoverLiftButton("Очистить кэш")
        clear_cache_btn.setFixedHeight(48)
        clear_cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_cache_btn.clicked.connect(self.clear_translation_cache)
        clear_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                border: none;
                border-radius: 24px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ef4444;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        cache_buttons_layout.addWidget(clear_cache_btn)
        
        cache_buttons_layout.addStretch()
        cache_layout.addLayout(cache_buttons_layout)
        
        main_layout.addWidget(cache_container)
        
        # Обновляем информацию о кэше при создании страницы
        self.refresh_cache_info()
        
        main_layout.addStretch()  # Добавляем растяжку чтобы контейнер был сверху
        
        self.stacked_widget.addWidget(settings_page)

    def create_about_page(self):
        """Создает страницу О программе с понятной информацией для пользователей"""
        about_page = QWidget()
        about_page.setStyleSheet("QWidget { background-color: #0f0f0f; }")
        
        # Создаем область прокрутки
        scroll_area = QScrollArea(about_page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
        
        # Контент для прокрутки
        scroll_content = QWidget()
        scroll_content.setStyleSheet("QWidget { background: transparent; }")
        
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(20)
        
        # Устанавливаем контент в область прокрутки
        scroll_area.setWidget(scroll_content)
        
        # Основной layout для страницы
        page_layout = QVBoxLayout(about_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll_area)
        
        # === ЗАГОЛОВОК ===
        title_label = QLabel("О программе RU-MINETOOLS")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: 700;
                background: transparent;
                border: none;
                margin-bottom: 8px;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Переводчик модов и квестов Minecraft на русский язык")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 16px;
                font-weight: 400;
                background: transparent;
                border: none;
                margin-bottom: 20px;
            }
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        # === ОПИСАНИЕ ВОЗМОЖНОСТЕЙ ===
        features_container = QWidget()
        features_container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
            }
        """)
        features_layout = QVBoxLayout(features_container)
        features_layout.setContentsMargins(30, 30, 30, 30)
        features_layout.setSpacing(12)
        
        # Заголовок секции
        features_title = QLabel("Что умеет программа")
        features_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 600;
                background: transparent;
                border: none;
                margin-bottom: 15px;
            }
        """)
        features_layout.addWidget(features_title)
        
        # Описание вкладки Квесты (без отдельного контейнера)
        quest_title = QLabel("Вкладка «Квесты»")
        quest_title.setStyleSheet("""
            QLabel {
                color: #bb86fc;
                font-size: 16px;
                font-weight: 600;
                background: transparent;
                border: none;
                margin-top: 5px;
                margin-bottom: 8px;
            }
        """)
        features_layout.addWidget(quest_title)
        
        quest_description = QLabel("Переводит квесты из модпаков FTB с английского на русский язык. Выберите папку с игрой, программа найдет файлы квестов и переведет их автоматически.")
        quest_description.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                line-height: 1.5;
                background: transparent;
                border: none;
                margin-bottom: 20px;
            }
        """)
        quest_description.setWordWrap(True)
        features_layout.addWidget(quest_description)
        
        # Описание вкладки JAR Моды (без отдельного контейнера)
        jar_title = QLabel("Вкладка «JAR Моды»")
        jar_title.setStyleSheet("""
            QLabel {
                color: #bb86fc;
                font-size: 16px;
                font-weight: 600;
                background: transparent;
                border: none;
                margin-top: 5px;
                margin-bottom: 8px;
            }
        """)
        features_layout.addWidget(jar_title)
        
        jar_description = QLabel("Переводит содержимое JAR файлов модов с английского на русский язык. Выберите JAR файлы модов, настройте количество потоков и запустите перевод.")
        jar_description.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                line-height: 1.5;
                background: transparent;
                border: none;
                margin-bottom: 10px;
            }
        """)
        jar_description.setWordWrap(True)
        features_layout.addWidget(jar_description)
        
        main_layout.addWidget(features_container)
        
        # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
        info_container = QWidget()
        info_container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(30, 25, 30, 25)
        info_layout.setSpacing(15)
        
        # Заголовок секции
        info_title = QLabel("Полезная информация")
        info_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 600;
                background: transparent;
                border: none;
                margin-bottom: 10px;
            }
        """)
        info_layout.addWidget(info_title)
        
        # Информационный текст
        info_text = QLabel("""• Программа работает через интернет - переводы выполняются онлайн-сервисами
• Первый перевод может занять время, но повторные переводы будут быстрее благодаря кэшу
• Рекомендуется делать резервные копии модов перед переводом
• В настройках можно управлять кэшем переводов для экономии места
• Программа поддерживает многопоточность для ускорения работы""")
        info_text.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                line-height: 1.6;
                background: transparent;
                border: none;
                padding: 15px;
                background: rgba(30, 30, 30, 0.3);
                border-radius: 12px;
            }
        """)
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        main_layout.addWidget(info_container)
        
        main_layout.addStretch()
        
        self.stacked_widget.addWidget(about_page)

    def refresh_cache_info(self):
        """Обновляет информацию о кэше переводов"""
        try:
            cache_file = "translation_cache.pkl"
            
            if os.path.exists(cache_file):
                # Получаем размер файла
                file_size = os.path.getsize(cache_file)
                size_mb = file_size / (1024 * 1024)
                
                # Загружаем кэш для подсчета записей
                try:
                    import pickle
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                    cache_count = len(cache_data)
                    
                    # Получаем дату последнего изменения
                    import datetime
                    mod_time = os.path.getmtime(cache_file)
                    mod_date = datetime.datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
                    
                    info_text = f"Записей в кэше: {cache_count:,}\nРазмер файла: {size_mb:.1f} МБ\nПоследнее обновление: {mod_date}"
                    
                except Exception as e:
                    info_text = f"Размер файла: {size_mb:.1f} МБ\nОшибка чтения: {str(e)}"
            else:
                info_text = "Кэш пуст (файл не найден)\nКэш создастся после первого перевода"
            
            self.cache_info_label.setText(info_text)
            
        except Exception as e:
            self.cache_info_label.setText(f"Ошибка получения информации: {str(e)}")
    
    def open_cache_folder(self):
        """Открывает папку с файлом кэша"""
        try:
            cache_file = "translation_cache.pkl"
            cache_dir = os.path.dirname(os.path.abspath(cache_file))
            
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.run(["explorer", cache_dir])
            elif sys.platform == "darwin":
                subprocess.run(["open", cache_dir])
            else:
                subprocess.run(["xdg-open", cache_dir])
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{str(e)}")
    
    def clear_translation_cache(self):
        """Очищает кэш переводов с подтверждением"""
        # Получаем информацию о кэше для диалога
        cache_file = "translation_cache.pkl"
        cache_info = "Кэш не найден"
        
        if os.path.exists(cache_file):
            try:
                file_size = os.path.getsize(cache_file)
                size_mb = file_size / (1024 * 1024)
                
                import pickle
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                cache_count = len(cache_data)
                
                cache_info = f"{cache_count:,} переводов ({size_mb:.1f} МБ)"
            except:
                cache_info = f"Файл существует ({file_size} байт)"
        
        # Диалог подтверждения
        reply = QMessageBox.question(
            self,
            "🗑️ Очистка кэша переводов",
            f"Вы уверены что хотите очистить кэш переводов?\n\n"
            f"📊 Текущий кэш: {cache_info}\n\n"
            f"⚠️ ВНИМАНИЕ:\n"
            f"• Все сохраненные переводы будут удалены\n"
            f"• Первые переводы после очистки будут медленнее\n"
            f"• Это действие нельзя отменить\n\n"
            f"💡 Кэш ускоряет повторные переводы в 10-50 раз!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем файл кэша
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                # Очищаем кэш в памяти если модуль загружен
                try:
                    import sys
                    if 'translate_jar_simple' in sys.modules:
                        from translate_jar_simple import TRANSLATION_CACHE
                        TRANSLATION_CACHE.clear()
                except:
                    pass
                
                # Обновляем информацию
                self.refresh_cache_info()
                
                QMessageBox.information(
                    self, 
                    "✅ Готово", 
                    "Кэш переводов успешно очищен!\n\n"
                    "🔄 Новый кэш начнет создаваться при следующем переводе."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "❌ Ошибка",
                    f"Не удалось очистить кэш:\n{str(e)}"
                )
    
    def create_placeholder_pages(self):
        translation_container = QWidget()
        translation_container.setStyleSheet("""
            QWidget {
                background: rgba(20, 20, 20, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.03);
                border-radius: 25px;
            }
        """)
        translation_layout = QVBoxLayout(translation_container)
        translation_layout.setContentsMargins(30, 25, 30, 25)
        translation_layout.setSpacing(15)
        
        # Заголовок секции
        translation_title = QLabel("Настройки перевода")
        translation_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        translation_layout.addWidget(translation_title)
        
        main_layout.addWidget(translation_container)
        
        # === КНОПКИ ДЕЙСТВИЙ ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Кнопка "Сбросить настройки" - в стиле вторичных кнопок со страницы квестов
        reset_btn = HoverLiftButton("Сбросить настройки")
        reset_btn.setFixedHeight(56)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(60, 60, 70, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 25px;
                color: rgba(255, 255, 255, 0.85);
                font-size: 14px;
                font-weight: 500;
                padding: 0px 24px;
            }
            QPushButton:hover {
                background: rgba(70, 70, 80, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(50, 50, 60, 0.6);
            }
        """)
        reset_btn.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(reset_btn)
        
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()
        
        self.stacked_widget.addWidget(settings_page)
    
    def reset_settings(self):
        """Сбрасывает настройки к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены что хотите сбросить все настройки?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Сбрасываем количество потоков
            if hasattr(self, 'set_threads_value'):
                self.set_threads_value("4")  # Сбрасываем на 4 потока
            
            # Удаляем файл статистики
            stats_file = "translation_stats.json"
            if os.path.exists(stats_file):
                try:
                    os.remove(stats_file)
                    if hasattr(self, 'stats_label'):
                        self.stats_label.setText("Всего переведено файлов: 0")
                except:
                    pass
            
            QMessageBox.information(self, "Готово", "Настройки успешно сброшены!")
    
    def create_placeholder_pages(self):
        """Создает заглушки для других страниц"""
        pages = ["files", "analytics", "users", "reports", "messages", "notifications"]  # Убрали settings
        
        for page_name in pages:
            page = QWidget()
            page.setStyleSheet("QWidget { background-color: #0a0a0a; }")
            layout = QVBoxLayout(page)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            placeholder = QLabel(f"Страница '{page_name}' в разработке")
            placeholder.setStyleSheet("""
                color: #94a3b8;
                font-size: 24px;
                font-weight: 600;
            """)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            layout.addWidget(placeholder)
            self.stacked_widget.addWidget(page)
    
    def find_translation_folders(self, root_folder):
        card_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
        """)
        layout.addWidget(card_title)
        
        # Сетка настроек
        settings_grid = QGridLayout()
        settings_grid.setSpacing(16)
        
        # Корневая папка Minecraft
        root_label = QLabel("🏠 Корневая папка Minecraft:")
        root_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 14px;
            font-weight: 500;
        """)
        settings_grid.addWidget(root_label, 0, 0)
        
        root_container = QHBoxLayout()
        root_container.setSpacing(12)
        
        self.minecraft_root_input = QLineEdit()
        self.minecraft_root_input.setPlaceholderText("Выберите корневую папку Minecraft сборки...")
        self.minecraft_root_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d3748;
                border: 2px solid #4a5568;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #bb86fc;
                background-color: #374151;
            }
            QLineEdit::placeholder {
                color: #9ca3af;
            }
        """)
        root_container.addWidget(self.minecraft_root_input)
        
        browse_root_btn = NeonGlowButton("Обзор...")
        browse_root_btn.setFixedSize(100, 48)
        browse_root_btn.clicked.connect(self.browse_quest_folder)
        root_container.addWidget(browse_root_btn)
        
        settings_grid.addLayout(root_container, 0, 1)
        
        # Кнопка автопоиска
        auto_search_btn = Modern3DButton("🔍 Найти квесты автоматически")
        auto_search_btn.setFixedSize(280, 50)
        auto_search_btn.clicked.connect(self.auto_search_quests)
        settings_grid.addWidget(auto_search_btn, 1, 0, 1, 2)
        
        # Результаты поиска
        self.search_results_label = QLabel("📋 Результаты поиска появятся здесь...")
        self.search_results_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 13px;
            padding: 12px;
            background-color: rgba(55, 65, 81, 0.5);
            border-radius: 8px;
            border: 1px solid #374151;
        """)
        self.search_results_label.setWordWrap(True)
        self.search_results_label.setMinimumHeight(80)
        settings_grid.addWidget(self.search_results_label, 2, 0, 1, 2)
        
        # Найденные папки квестов (выпадающий список)
        quest_folders_label = QLabel("📁 Найденные папки квестов:")
        quest_folders_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 14px;
            font-weight: 500;
        """)
        settings_grid.addWidget(quest_folders_label, 3, 0)
        
        self.quest_folders_combo = QComboBox()
        self.quest_folders_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d3748;
                border: 2px solid #4a5568;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: #ffffff;
                min-width: 300px;
            }
            QComboBox:focus {
                border-color: #bb86fc;
                background-color: #374151;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #9ca3af;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 8px;
                selection-background-color: #bb86fc;
                color: #ffffff;
            }
        """)
        self.quest_folders_combo.addItem("Сначала выполните поиск...")
        self.quest_folders_combo.setEnabled(False)
        settings_grid.addWidget(self.quest_folders_combo, 3, 1)
        
        # Язык перевода
        lang_label = QLabel("🌐 Язык перевода:")
        lang_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 14px;
            font-weight: 500;
        """)
        settings_grid.addWidget(lang_label, 1, 0)
        
        self.quest_lang_combo = QComboBox()
        self.quest_lang_combo.addItems([
            "ru - Русский",
            "en - English", 
            "de - Deutsch",
            "fr - Français",
            "es - Español",
            "it - Italiano",
            "pt - Português",
            "zh - 中文",
            "ja - 日本語",
            "ko - 한국어"
        ])
        self.quest_lang_combo.setCurrentIndex(0)  # Русский по умолчанию
        self.quest_lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d3748;
                border: 2px solid #4a5568;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: #ffffff;
                min-width: 200px;
            }
            QComboBox:focus {
                border-color: #bb86fc;
                background-color: #374151;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #9ca3af;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 8px;
                selection-background-color: #bb86fc;
                color: #ffffff;
            }
        """)
        settings_grid.addWidget(self.quest_lang_combo, 1, 1)
        
        layout.addLayout(settings_grid)
        
        # Улучшенная информационная панель с иконками
        info_panel = QFrame()
        info_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(135deg, 
                    rgba(59, 130, 246, 0.15) 0%, 
                    rgba(139, 92, 246, 0.15) 100%);
                border: 2px solid rgba(59, 130, 246, 0.4);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        info_layout = QVBoxLayout(info_panel)
        info_layout.setSpacing(12)
        
        info_title = QLabel("💡 Что делает переводчик")
        info_title.setStyleSheet("""
            color: #60a5fa;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 4px;
        """)
        info_layout.addWidget(info_title)
        
        # Создаем сетку для информации
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        
        info_items = [
            ("✅", "Переводит", "названия квестов, описания, задания"),
            ("🎨", "Сохраняет", "форматирующие коды (&a, &c и т.д.)"),
            ("🚫", "Пропускает", "технические ID, уже переведенный текст"),
            ("📂", "Создает", "папку имя_папки-translate с результатом")
        ]
        
        for i, (icon, action, description) in enumerate(info_items):
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("""
                font-size: 16px;
                padding: 4px;
            """)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            action_label = QLabel(action)
            action_label.setStyleSheet("""
                color: #e2e8f0;
                font-size: 14px;
                font-weight: 600;
            """)
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("""
                color: #94a3b8;
                font-size: 13px;
                line-height: 1.3;
            """)
            desc_label.setWordWrap(True)
            
            info_grid.addWidget(icon_label, i, 0)
            info_grid.addWidget(action_label, i, 1)
            info_grid.addWidget(desc_label, i, 2)
        
        info_grid.setColumnStretch(2, 1)  # Растягиваем колонку с описанием
        info_layout.addLayout(info_grid)
        
        layout.addWidget(info_panel)
        
        return card
    
    def create_quest_control_card(self):
        """Создает карточку управления переводом"""
        card = QFrame()
        card.setObjectName("questControlCard")
        card.setStyleSheet("""
            #questControlCard {
                background: qlinear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(20)
        
        # Заголовок
        card_title = QLabel("🚀 Управление переводом")
        card_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
        """)
        layout.addWidget(card_title)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)  # Увеличиваем отступ с 16 до 20
        
        # Кнопка старта с улучшенным дизайном - точно такая же как кнопка авторизации
        self.start_translation_btn2 = HoverLiftButton("🎯 НАЧАТЬ ПЕРЕВОД")
        self.start_translation_btn2.setFixedSize(200, 80)
        self.start_translation_btn2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_translation_btn2.clicked.connect(self.start_quest_translation)
        
        # Применяем точно такие же стили как у кнопки авторизации
        self.start_translation_btn2.setStyleSheet("""
            QPushButton {
                /* Футуристический градиент от фиолетового к розовому */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                
                /* Мягкие закругленные углы */
                border-radius: 25px;
                
                /* Стеклянный эффект с внутренним свечением */
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                
                /* Текст */
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                /* Усиленное свечение при наведении */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                
                /* Усиленные границы */
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                /* Эффект вдавливания */
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9540E6,
                    stop:0.3 #A650F0,
                    stop:0.7 #C060FF,
                    stop:1 #D565FF);
                
                /* Инвертированные границы */
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        
        # Добавляем анимации как у кнопки авторизации
        self.setup_translation_button2_animations()
        
        buttons_layout.addWidget(self.start_translation_btn2)
        
        # Кнопка паузы
        self.stop_translation_btn = Modern3DButton("Пауза")
        self.stop_translation_btn.setFixedSize(200, 65)  # Увеличиваем ширину до 200px чтобы поместился текст "Продолжить"
        self.stop_translation_btn.clicked.connect(self.toggle_quest_translation_pause)
        self.stop_translation_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_translation_btn)
        
        # Добавляем фиксированный отступ между кнопками
        spacer = QWidget()
        spacer.setFixedWidth(30)  # Фиксированный отступ 30px
        buttons_layout.addWidget(spacer)
        
        # Кнопка открытия результата (без анимации чтобы не конфликтовать с соседними кнопками)
        self.open_result_btn = QPushButton("📂 Открыть результат")
        self.open_result_btn.setFixedSize(200, 65)
        self.open_result_btn.clicked.connect(self.open_quest_result)
        self.open_result_btn.setEnabled(False)
        self.open_result_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a5568, stop:0.5 #2d3748, stop:1 #1a202c);
                border: 1px solid #4a5568;
                border-radius: 20px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #718096, stop:0.5 #4a5568, stop:1 #2d3748);
                border: 1px solid #718096;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d3748, stop:0.5 #1a202c, stop:1 #171923);
                border: 1px solid #2d3748;
            }
            QPushButton:disabled {
                background: #2a2a2a;
                border: 1px solid #3a3a3a;
                color: #666666;
            }
        """)
        buttons_layout.addWidget(self.open_result_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Статистика в реальном времени
        self.stats_container = QFrame()
        self.stats_container.setVisible(False)
        self.stats_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(135deg, 
                    rgba(16, 185, 129, 0.1) 0%, 
                    rgba(34, 197, 94, 0.1) 100%);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 12px;
                padding: 16px;
                margin-top: 8px;
            }
        """)
        
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setSpacing(24)
        
        # Счетчики
        self.files_processed_label = QLabel("📄 Обработано: 0")
        self.files_processed_label.setStyleSheet("""
            color: #10b981;
            font-size: 14px;
            font-weight: 600;
        """)
        
        self.files_translated_label = QLabel("✅ Переведено: 0")
        self.files_translated_label.setStyleSheet("""
            color: #10b981;
            font-size: 14px;
            font-weight: 600;
        """)
        
        self.files_skipped_label = QLabel("⚪ Пропущено: 0")
        self.files_skipped_label.setStyleSheet("""
            color: #6b7280;
            font-size: 14px;
            font-weight: 600;
        """)
        
        self.files_errors_label = QLabel("❌ Ошибок: 0")
        self.files_errors_label.setStyleSheet("""
            color: #ef4444;
            font-size: 14px;
            font-weight: 600;
        """)
        
        stats_layout.addWidget(self.files_processed_label)
        stats_layout.addWidget(self.files_translated_label)
        stats_layout.addWidget(self.files_skipped_label)
        stats_layout.addWidget(self.files_errors_label)
        stats_layout.addStretch()
        
        layout.addWidget(self.stats_container)
        
        # Инициализируем счетчики
        self.translation_stats = {
            'processed': 0,
            'translated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Прогресс бар уже создан выше в основном layout
        
        return card
    
    def create_quest_log_card(self):
        """Создает карточку лога перевода"""
        card = QFrame()
        card.setObjectName("questLogCard")
        card.setStyleSheet("""
            #questLogCard {
                background: qlinear-gradient(135deg, #111827 0%, #1f2937 100%);
                border: 1px solid #374151;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(16)
        
        # Заголовок с кнопкой очистки
        header_layout = QHBoxLayout()
        
        card_title = QLabel("📋 Лог перевода")
        card_title.setStyleSheet("""
            color: #ffffff;
            font-size: 20px;
            font-weight: 600;
        """)
        header_layout.addWidget(card_title)
        
        header_layout.addStretch()
        
        clear_log_btn = NeonGlowButton("🗑️ Очистить")
        clear_log_btn.setFixedSize(120, 36)
        clear_log_btn.clicked.connect(self.clear_quest_log)
        header_layout.addWidget(clear_log_btn)
        
        layout.addLayout(header_layout)
        
        # Лог
        self.quest_log = QTextEdit()
        self.quest_log.setReadOnly(True)
        self.quest_log.setMinimumHeight(300)
        self.quest_log.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                border: 2px solid #1e293b;
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                color: #e2e8f0;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background-color: #1e293b;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #64748b;
            }
        """)
        
        # Добавляем приветственное сообщение
        welcome_msg = f"""🎮 Переводчик FTB Квестов

📁 Выберите папку с квестами → 🌐 Выберите язык → 🚀 Переводите

� Путь: minпecraft/config/ftbquests/quests/
🔧 Статус: {'✅ Готов' if TRANSLATOR_AVAILABLE else '❌ Установите translatepy'}
"""
        self.quest_log.setPlainText(welcome_msg)
        
        layout.addWidget(self.quest_log)
        
        return card
    
    def find_translation_folders(self, root_folder):
        r"""
        Ищет папки chapters и lang ТОЛЬКО в minecraft\config\ftbquests\quests
        
        Возвращает словарь с найденными папками:
        {
            'chapters': [список_путей_к_папкам_chapters],
            'lang': [список_путей_к_папкам_lang]
        }
        """
        root_path = Path(root_folder)
        found_folders = {
            'chapters': [],
            'lang': []
        }
        
        # Ищем папки chapters и lang - проверяем несколько вариантов путей
        try:
            # Варианты путей для поиска
            possible_paths = [
                # Вариант 1: выбранная папка уже содержит config/ftbquests/quests
                root_path / "config" / "ftbquests" / "quests",
                # Вариант 2: выбранная папка содержит minecraft/config/ftbquests/quests
                root_path / "minecraft" / "config" / "ftbquests" / "quests",
                # Вариант 3: выбранная папка УЖЕ является папкой quests
                root_path,
                # Вариант 4: выбранная папка является ftbquests
                root_path / "quests",
            ]
            
            for quests_path in possible_paths:
                if quests_path.exists() and quests_path.is_dir():
                    # Ищем папку chapters
                    chapters_path = quests_path / "chapters"
                    if chapters_path.exists() and chapters_path.is_dir():
                        # Проверяем, что в папке есть .snbt файлы
                        snbt_files = list(chapters_path.rglob("*.snbt"))
                        if snbt_files and str(chapters_path) not in found_folders['chapters']:
                            found_folders['chapters'].append(str(chapters_path))
                    
                    # Ищем папку lang
                    lang_path = quests_path / "lang"
                    if lang_path.exists() and lang_path.is_dir():
                        # Проверяем, что в папке есть en_us.snbt файл
                        en_us_file = lang_path / "en_us.snbt"
                        if en_us_file.exists() and str(lang_path) not in found_folders['lang']:
                            found_folders['lang'].append(str(lang_path))
                    
                    # Если нашли хотя бы одну папку, прекращаем поиск
                    if found_folders['chapters'] or found_folders['lang']:
                        break
                        
        except (PermissionError, OSError):
            pass
        
        return found_folders
    
    def browse_quest_folder(self):
        """
        Открывает диалог выбора корневой папки игры
        Автоматически ищет папки chapters и lang внутри
        """
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите корневую папку игры Minecraft",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.log_quest_message(f"Поиск папок для перевода в: {folder}")
            
            # Ищем папки chapters и lang
            found_folders = self.find_translation_folders(folder)
            
            total_folders = len(found_folders['chapters']) + len(found_folders['lang'])
            
            if total_folders > 0:
                self.quest_folder_input.setText(folder)
                self.log_quest_message(f"Найдено папок для перевода: {total_folders}")
                
                # Показываем что именно найдено
                if found_folders['chapters']:
                    self.log_quest_message(f"📁 Папки chapters: {len(found_folders['chapters'])}")
                if found_folders['lang']:
                    self.log_quest_message(f"📁 Папки lang: {len(found_folders['lang'])}")
                
                self.quest_folder_selected = True
                # Обновляем прогресс-бар
                self.quest_progress.setText("Папка выбрана - готов к переводу")
                self.quest_progress.setValue(0)
            else:
                self.quest_folder_input.setText(folder)
                self.log_quest_message("Папки chapters или lang не найдены.")
                self.quest_folder_selected = False
                # Обновляем прогресс-бар
                self.quest_progress.setText("Папки для перевода не найдены")
                self.quest_progress.setValue(0)
                QMessageBox.warning(
                    self, 
                    "Папки не найдены", 
                    "Не удалось найти папки 'chapters' или 'lang' для перевода.\n\n"
                    "Убедитесь, что выбрана правильная папка игры."
                )
    
    def setup_translation_button_animations(self):
        """Настраивает анимации для кнопки 'начать перевод' как у кнопки авторизации"""
        # Анимация прозрачности для эффекта появления
        self.translation_fade_animation = QPropertyAnimation(self.start_translation_btn, b"windowOpacity")
        self.translation_fade_animation.setDuration(800)
        self.translation_fade_animation.setStartValue(0.0)
        self.translation_fade_animation.setEndValue(1.0)
        self.translation_fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Пульсирующая анимация (дыхание)
        self.translation_pulse_animation = QPropertyAnimation(self.start_translation_btn, b"windowOpacity")
        self.translation_pulse_animation.setDuration(2000)
        self.translation_pulse_animation.setLoopCount(-1)
        self.translation_pulse_animation.setStartValue(0.7)
        self.translation_pulse_animation.setEndValue(1.0)
        self.translation_pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Запускаем эффект появления кнопки
        QTimer.singleShot(500, self.start_translation_fade_in)
        
        # Запускаем пульсирующий эффект для привлечения внимания
        QTimer.singleShot(1300, self.start_translation_pulse)
        
        # Hover анимация - подъем/опускание кнопки (небольшой подъем)
        self.translation_hover_animation = QPropertyAnimation(self.start_translation_btn, b"geometry")
        self.translation_hover_animation.setDuration(200)
        self.translation_hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Сохраняем исходную геометрию кнопки
        self.translation_original_geometry = None
        self.translation_is_hovered = False
        
        # События мыши обрабатываются самим классом HoverLiftButton
        
        # Оставляем статичный текст без анимации смены
    
    def start_translation_fade_in(self):
        """Запускает эффект появления кнопки перевода"""
        self.start_translation_btn.setWindowOpacity(0.0)
        self.translation_fade_animation.start()
    
    def start_translation_pulse(self):
        """Запускает пульсирующий эффект кнопки перевода"""
        self.translation_pulse_animation.start()
    
    def translation_button_enter_event(self, event):
        """Обработка наведения мыши на первую кнопку перевода"""
        if self.translation_original_geometry is None:
            self.translation_original_geometry = self.start_translation_btn.geometry()
        
        if not self.translation_is_hovered:
            self.translation_is_hovered = True
            
            # Поднимаем кнопку на 3 пикселя вверх (небольшой подъем)
            current_rect = self.start_translation_btn.geometry()
            hover_rect = QRect(
                current_rect.x(),
                current_rect.y() - 3,  # Небольшой подъем на 3 пикселя
                current_rect.width(),
                current_rect.height()
            )
            
            self.translation_hover_animation.setStartValue(current_rect)
            self.translation_hover_animation.setEndValue(hover_rect)
            self.translation_hover_animation.start()
    
    def translation_button_leave_event(self, event):
        """Обработка ухода мыши с первой кнопки перевода"""
        if self.translation_is_hovered and self.translation_original_geometry:
            self.translation_is_hovered = False
            
            # Плавно возвращаем кнопку в исходное положение
            self.translation_hover_animation.setStartValue(self.start_translation_btn.geometry())
            self.translation_hover_animation.setEndValue(self.translation_original_geometry)
            self.translation_hover_animation.start()
    
    def translation_button_enter(self, event):
        """Обработка наведения мыши на кнопку перевода - подъем вверх"""
        if self.translation_original_geometry is None:
            self.translation_original_geometry = self.start_translation_btn.geometry()
        
        if not self.translation_is_hovered:
            self.translation_is_hovered = True
            
            # Поднимаем кнопку на 6 пикселей вверх
            current_rect = self.start_translation_btn.geometry()
            hover_rect = QRect(
                current_rect.x(),
                current_rect.y() - 6,
                current_rect.width(),
                current_rect.height()
            )
            
            self.translation_hover_animation.setStartValue(current_rect)
            self.translation_hover_animation.setEndValue(hover_rect)
            self.translation_hover_animation.start()
    
    def translation_button_leave(self, event):
        """Обработка ухода мыши с кнопки перевода - опускание вниз"""
        if self.translation_is_hovered and self.translation_original_geometry:
            self.translation_is_hovered = False
            
            # Возвращаем кнопку в исходное положение
            self.translation_hover_animation.setStartValue(self.start_translation_btn.geometry())
            self.translation_hover_animation.setEndValue(self.translation_original_geometry)
            self.translation_hover_animation.start()
    

    
    def setup_translation_button2_animations(self):
        """Настраивает анимации для второй кнопки 'начать перевод' как у кнопки авторизации"""
        # Анимация прозрачности для эффекта появления
        self.translation2_fade_animation = QPropertyAnimation(self.start_translation_btn2, b"windowOpacity")
        self.translation2_fade_animation.setDuration(800)
        self.translation2_fade_animation.setStartValue(0.0)
        self.translation2_fade_animation.setEndValue(1.0)
        self.translation2_fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Пульсирующая анимация (дыхание)
        self.translation2_pulse_animation = QPropertyAnimation(self.start_translation_btn2, b"windowOpacity")
        self.translation2_pulse_animation.setDuration(2000)
        self.translation2_pulse_animation.setLoopCount(-1)
        self.translation2_pulse_animation.setStartValue(0.7)
        self.translation2_pulse_animation.setEndValue(1.0)
        self.translation2_pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Запускаем эффект появления кнопки
        QTimer.singleShot(500, self.start_translation2_fade_in)
        
        # Запускаем пульсирующий эффект для привлечения внимания
        QTimer.singleShot(1300, self.start_translation2_pulse)
        
        # Hover анимация - подъем/опускание кнопки (небольшой подъем)
        self.translation2_hover_animation = QPropertyAnimation(self.start_translation_btn2, b"geometry")
        self.translation2_hover_animation.setDuration(200)
        self.translation2_hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Сохраняем исходную геометрию кнопки
        self.translation2_original_geometry = None
        self.translation2_is_hovered = False
        
        # События мыши обрабатываются самим классом HoverLiftButton
        
        # Оставляем статичный текст без анимации смены
    
    def start_translation2_fade_in(self):
        """Запускает эффект появления второй кнопки перевода"""
        self.start_translation_btn2.setWindowOpacity(0.0)
        self.translation2_fade_animation.start()
    
    def start_translation2_pulse(self):
        """Запускает пульсирующий эффект второй кнопки перевода"""
        self.translation2_pulse_animation.start()
    
    def translation2_button_enter_event(self, event):
        """Обработка наведения мыши на вторую кнопку перевода"""
        if self.translation2_original_geometry is None:
            self.translation2_original_geometry = self.start_translation_btn2.geometry()
        
        if not self.translation2_is_hovered:
            self.translation2_is_hovered = True
            
            # Поднимаем кнопку на 3 пикселя вверх (небольшой подъем)
            current_rect = self.start_translation_btn2.geometry()
            hover_rect = QRect(
                current_rect.x(),
                current_rect.y() - 3,  # Небольшой подъем на 3 пикселя
                current_rect.width(),
                current_rect.height()
            )
            
            self.translation2_hover_animation.setStartValue(current_rect)
            self.translation2_hover_animation.setEndValue(hover_rect)
            self.translation2_hover_animation.start()
    
    def translation2_button_leave_event(self, event):
        """Обработка ухода мыши со второй кнопки перевода"""
        if self.translation2_is_hovered and self.translation2_original_geometry:
            self.translation2_is_hovered = False
            
            # Плавно возвращаем кнопку в исходное положение
            self.translation2_hover_animation.setStartValue(self.start_translation_btn2.geometry())
            self.translation2_hover_animation.setEndValue(self.translation2_original_geometry)
            self.translation2_hover_animation.start()
    
    def start_quest_translation(self):
        """Запускает перевод квестов"""
        # Проверяем, запущен ли уже перевод
        if hasattr(self, 'translation_worker') and self.translation_worker.isRunning():
            # Если перевод запущен, останавливаем его полностью
            self.cancel_quest_translation()
            return
        
        # Проверяем флаг выбора папки
        if not hasattr(self, 'quest_folder_selected') or not self.quest_folder_selected:
            self.log_quest_message("⚠️ Сначала выберите папку с квестами!")
            return
        
        folder_path = self.quest_folder_input.text().strip()
        
        if not folder_path:
            self.log_quest_message("⚠️ Выберите папку с квестами!")
            return
        
        if not Path(folder_path).exists():
            QMessageBox.warning(self, "Ошибка", "Выбранная папка не существует!")
            return
        
        if not TRANSLATOR_AVAILABLE:
            QMessageBox.critical(self, "Ошибка", 
                               "Модуль translatepy не установлен!\n\n"
                               "Установите его командой:\n"
                               "pip install translatepy")
            return
        
        # Используем русский язык по умолчанию
        lang_code = "ru"
        
        self.log_quest_message(f"🚀 Запуск перевода на русский язык")
        self.log_quest_message(f"📁 Папка: {folder_path}")
        
        # Сбрасываем статистику
        self.translation_stats = {
            'processed': 0,
            'translated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Настраиваем UI (кнопки остаются активными)
        self.quest_progress.setText("Начинаем перевод...")
        self.quest_progress.setValue(0)
        
        # Изменяем кнопку на красную "Остановить"
        self.start_translation_btn.setText("ОСТАНОВИТЬ")
        self.start_translation_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC2626,
                    stop:0.3 #E53E3E,
                    stop:0.7 #EF4444,
                    stop:1 #F56565);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B91C1C,
                    stop:0.3 #DC2626,
                    stop:0.7 #E53E3E,
                    stop:1 #EF4444);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
        """)
        
        # Запускаем воркер
        self.translation_worker = ChaptersLangTranslationWorker(folder_path, lang_code)
        self.translation_worker.progress_updated.connect(self.log_quest_message)
        self.translation_worker.file_processed.connect(self.update_quest_progress)
        self.translation_worker.translation_finished.connect(self.on_quest_translation_finished)
        self.translation_worker.start()
    
    def on_quest_translation_finished(self, successful, total):
        """Завершение перевода квестов в ContentArea"""
        try:
            logger.info(f"on_quest_translation_finished (ContentArea) вызван: successful={successful}, total={total}")
            
            # Показываем окно поддержки после успешного перевода с задержкой
            if successful > 0:
                logger.info("Условие successful > 0 выполнено для квестов, показываем окно поддержки")
                if self.main_window and hasattr(self.main_window, 'safe_show_support_dialog'):
                    logger.info("Планируем показ окна поддержки для квестов через 500мс")
                    QTimer.singleShot(500, self.main_window.safe_show_support_dialog)
                else:
                    logger.error("Главное окно недоступно для показа диалога поддержки")
            else:
                logger.info("Условие successful > 0 НЕ выполнено для квестов, окно поддержки не показываем")
                
        except Exception as e:
            logger.error(f"Ошибка в on_quest_translation_finished (ContentArea): {e}")
            logger.debug(traceback.format_exc())
    
    def reset_quest_translate_button(self):
        """Возвращает кнопку перевода квестов в исходное состояние"""
        self.start_translation_btn.setText("НАЧАТЬ ПЕРЕВОД")
        self.start_translation_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
        """)
    
    def toggle_quest_translation_pause(self):
        """Переключение паузы/возобновления перевода квестов"""
        if hasattr(self, 'translation_worker') and self.translation_worker.isRunning():
            if self.translation_worker.is_paused:
                # Возобновляем
                self.translation_worker.resume()
                self.stop_translation_btn.setText("Пауза")
                self.log_quest_message("▶️ Перевод возобновлен")
                # Сразу обновляем прогресс-бар
                self.quest_progress.setText("Возобновление...")
                
                # Принудительно обновляем layout чтобы кнопки вернулись в исходное положение
                self.stop_translation_btn.updateGeometry()
                self.open_result_btn.updateGeometry()
                QApplication.processEvents()
            else:
                # Ставим на паузу
                self.translation_worker.pause()
                self.stop_translation_btn.setText("Старт")  # Короткое слово вместо "Продолжить"
                self.log_quest_message("⏸️ Перевод приостановлен")
                self.quest_progress.setText("На паузе...")
                
                # Принудительно обновляем layout чтобы кнопки вернулись в исходное положение
                self.stop_translation_btn.updateGeometry()
                self.open_result_btn.updateGeometry()
                QApplication.processEvents()
        else:
            # Если перевод не запущен
            self.log_quest_message("⚠️ Перевод не запущен")
    
    def cancel_quest_translation(self):
        """Полностью останавливает перевод квестов"""
        if hasattr(self, 'translation_worker') and self.translation_worker.isRunning():
            self.log_quest_message("⏹️ Остановка перевода...")
            
            # Сначала снимаем с паузы если нужно
            if self.translation_worker.is_paused:
                self.translation_worker.resume()
            
            self.translation_worker.cancel()
            self.translation_worker.wait(3000)  # Ждем 3 секунды
            
            # Показываем частичную статистику
            stats = self.translation_stats
            self.log_quest_message("⏹️ Перевод остановлен пользователем")
            self.log_quest_message(f"📊 Частичная статистика:")
            self.log_quest_message(f"   • Обработано: {stats['processed']}")
            self.log_quest_message(f"   • Переведено: {stats['translated']}")
            self.log_quest_message(f"   • Пропущено: {stats['skipped']}")
            self.log_quest_message(f"   • Ошибок: {stats['errors']}")
            
            # Восстанавливаем UI (кнопки остаются активными)
            self.quest_progress.setText("Перевод остановлен")
            self.quest_progress.setValue(0)
            
            # Сбрасываем кнопку в исходное состояние
            self.reset_quest_translate_button()
            
            # Восстанавливаем текст кнопки паузы
            self.stop_translation_btn.setText("Пауза")
    
    def open_quest_result(self):
        """Открывает папки с результатами перевода"""
        try:
            # Проверяем, не запущен ли процесс перевода
            if hasattr(self, 'quest_worker') and self.quest_worker and self.quest_worker.isRunning():
                QMessageBox.warning(self, "Предупреждение", 
                                  "Дождитесь завершения перевода перед открытием папки")
                return
            
            folder_path = self.quest_folder_input.text().strip()
            if not folder_path:
                self.log_quest_message("⚠️ Путь к папке не указан")
                return
            
            root_path = Path(folder_path)
            if not root_path.exists():
                self.log_quest_message("⚠️ Указанная папка не найдена")
                return
            
            # Ищем папки с результатами
            result_folders = []
            for chapters_translate in root_path.rglob("chapters-translate"):
                if chapters_translate.is_dir():
                    result_folders.append(chapters_translate)
            
            for lang_translate in root_path.rglob("lang-translate"):
                if lang_translate.is_dir():
                    result_folders.append(lang_translate)
            
            if result_folders:
                # Открываем первую найденную папку (или можно открыть все)
                result_folder = result_folders[0]
                
                # Открываем папку в проводнике
                import subprocess
                if sys.platform.startswith('win'):
                    subprocess.run(["explorer", str(result_folder)], check=False)
                elif sys.platform.startswith('darwin'):
                    subprocess.run(["open", str(result_folder)], check=False)
                else:
                    subprocess.run(["xdg-open", str(result_folder)], check=False)
                
                self.log_quest_message(f"📂 Открыта папка: {result_folder.name}")
                
                # Показываем информацию о всех найденных папках
                if len(result_folders) > 1:
                    self.log_quest_message(f"ℹ️ Найдено папок с результатами: {len(result_folders)}")
            else:
                QMessageBox.information(self, "Информация", "Папки с результатами еще не созданы")
                
        except Exception as e:
            self.log_quest_message(f"❌ Ошибка при открытии папки: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть папку: {e}")
    
    def clear_quest_log(self):
        """
        Очищает лог перевода
        
        UX: Компактное сообщение без декоративных элементов
        """
        self.quest_log.clear()
        
        # Компактное приветственное сообщение (без декора)
        welcome_msg = """🎯 Переводчик квестов FTB

📁 Выберите папку игры → 🚀 Нажмите "Начать перевод"
        """
        self.quest_log.setPlainText(welcome_msg.strip())
        
        # Сбрасываем прогресс-бар в исходное состояние
        self.quest_progress.setText("Готов к работе")
        self.quest_progress.setValue(0)
    
    def log_quest_message(self, message):
        """
        Добавляет сообщение в лог и обновляет прогресс-бар
        
        UX: Спокойные цвета, минимум визуального шума
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Обрабатываем сообщения прогресса для прогресс-бара
        if "📊 Прогресс:" in message:
            # Извлекаем процент из сообщения "📊 Прогресс: 45% (12/27)"
            import re
            match = re.search(r'(\d+)%\s*\((\d+)/(\d+)\)', message)
            if match:
                percent = int(match.group(1))
                current = int(match.group(2))
                total = int(match.group(3))
                
                # Обновляем прогресс-бар
                self.quest_progress.setValue(percent)
                self.quest_progress.setText(f"Обработано файлов: {current} из {total}")
                
                # Не добавляем это сообщение в лог (слишком шумно)
                return
        
        # Обновляем прогресс-бар при начале работы
        if "найдено" in message.lower() and "файлов" in message.lower():
            self.quest_progress.setText("Начинаем перевод...")
            self.quest_progress.setValue(0)
        
        # Определяем цвет в зависимости от типа сообщения
        if "успешно" in message.lower() or "завершен" in message.lower() or "✅" in message:
            color = "#10b981"  # Зеленый для успеха
        elif "ошибка" in message.lower() or "failed" in message.lower() or "❌" in message:
            color = "#ef4444"  # Красный для ошибок
        elif "создана папка" in message.lower() or "📂" in message:
            color = "#8b5cf6"  # Фиолетовый для действий
        else:
            color = "#94a3b8"  # Серый по умолчанию
        
        # Простое форматирование
        formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
        
        self.quest_log.append(formatted_message)
        
        # Прокручиваем к концу
        cursor = self.quest_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.quest_log.setTextCursor(cursor)
    
    def update_quest_progress(self, filename, success):
        """Обновляет прогресс перевода"""
        # Обновляем статистику
        self.translation_stats['processed'] += 1
        
        if success:
            # Определяем тип результата по сообщению в логе
            if "переведен" in self.quest_log.toPlainText().split('\n')[-1]:
                self.translation_stats['translated'] += 1
            else:
                self.translation_stats['skipped'] += 1
        else:
            self.translation_stats['errors'] += 1
        
        self.update_stats_display()
    
    def update_stats_display(self):
        """
        Обновляет отображение статистики
        
        Теперь статистика отображается только в логе
        """
        # Статистика теперь отображается только в логе, никаких UI элементов не обновляем
        pass
    
    def on_quest_translation_finished(self, successful, total):
        """
        Обработка завершения перевода
        
        UX: Компактное сообщение без декоративных элементов
        """
        try:
            logger.info(f"on_quest_translation_finished вызван: successful={successful}, total={total}")
            
            # Восстанавливаем UI (кнопки остаются активными)
            self.quest_progress.setText("Перевод завершен")
            self.quest_progress.setValue(100)
            
            # Финальная статистика
            stats = self.translation_stats
            
            # Простой разделитель
            self.quest_log.append("")
            self.quest_log.append("---")
            
            # Показываем результат
            if successful > 0:
                logger.info("Условие successful > 0 выполнено, показываем результаты")
                self.log_quest_message("Перевод завершен")
                self.quest_log.append("")
                self.log_quest_message("Статистика:")
                self.log_quest_message(f"  Всего файлов: {total}")
                self.log_quest_message(f"  Переведено: {stats['translated']}")
                self.log_quest_message(f"  Пропущено: {stats['skipped']}")
                self.log_quest_message(f"  Ошибок: {stats['errors']}")
                
                # Показываем процент успеха
                success_rate = (stats['translated'] / total) * 100 if total > 0 else 0
                self.quest_log.append("")
                self.log_quest_message(f"Успешно переведено: {success_rate:.1f}%")
                
                # Добавляем инструкции по установке перевода
                self.quest_log.append("")
                self.quest_log.append("📋 ИНСТРУКЦИИ ПО УСТАНОВКЕ ПЕРЕВОДА:")
                self.quest_log.append("=" * 50)
                
                folder_path = self.quest_folder_input.text().strip()
                if folder_path:
                    self.quest_log.append(f"📁 Оригинальная папка с квестами:")
                    self.quest_log.append(f"   {folder_path}")
                    self.quest_log.append("")
                    self.quest_log.append("📦 Переведенные файлы находятся в папках с суффиксом '-translate'")
                    self.quest_log.append("")
                    self.quest_log.append("🔄 Как установить перевод:")
                    self.quest_log.append("   1. Сделайте резервную копию оригинальных папок chapters/ и lang/")
                    self.quest_log.append("   2. Скопируйте содержимое из chapters-translate/ в chapters/")
                    self.quest_log.append("   3. Скопируйте содержимое из lang-translate/ в lang/")
                    self.quest_log.append("   4. Запустите игру и проверьте перевод квестов")
                    self.quest_log.append("")
                    self.quest_log.append("⚠️ ВАЖНО:")
                    self.quest_log.append("   • Всегда делайте резервные копии перед заменой!")
                    self.quest_log.append("   • Если что-то пошло не так, восстановите из копии")
                    self.quest_log.append("   • Перевод применится после перезапуска мира")
                
                self.quest_log.append("=" * 50)
                
                # Показываем окно поддержки после успешного перевода с задержкой
                # Используем QTimer для безопасного показа диалога
                logger.info("Планируем показ окна поддержки для квестов через 500мс")
                if hasattr(self, 'safe_show_support_dialog'):
                    QTimer.singleShot(500, self.safe_show_support_dialog)
                elif hasattr(self, 'main_window') and hasattr(self.main_window, 'safe_show_support_dialog'):
                    QTimer.singleShot(500, self.main_window.safe_show_support_dialog)
                else:
                    logger.error("Метод safe_show_support_dialog недоступен")
                
                self.quest_log.append("")
                self.log_quest_message("Результаты сохранены в папке с суффиксом '-translate'")
            else:
                self.log_quest_message("Не удалось перевести ни одного файла")
                self.quest_log.append("")
                self.log_quest_message("Проверьте:")
                self.log_quest_message("  - Правильность пути к папке")
                self.log_quest_message("  - Наличие .snbt файлов")
                self.log_quest_message("  - Подключение к интернету")
            
            self.quest_log.append("---")
            self.quest_log.append("")
            
            # Сбрасываем кнопку в исходное состояние
            self.reset_quest_translate_button()
            
            # Восстанавливаем текст кнопки паузы
            self.stop_translation_btn.setText("Пауза")
            
            # Сохраняем проект в историю если перевод успешен
            if successful > 0:
                folder_path = self.quest_folder_input.text().strip()
                if folder_path:
                    folder_name = os.path.basename(folder_path)
                    self.save_project_to_history(
                        f"Квесты: {folder_name}",
                        folder_path,
                        "quests"
                    )
        except Exception as e:
            logger.error(f"Ошибка в on_quest_translation_finished: {e}")
            logger.debug(traceback.format_exc())
            # Все равно сбрасываем кнопку в исходное состояние
            try:
                self.reset_quest_translate_button()
                self.stop_translation_btn.setText("Пауза")
            except:
                pass
    
    # МЕТОДЫ ДЛЯ РАБОТЫ С JAR ПЕРЕВОДАМИ
    
    def browse_jar_file(self):
        """Выбор JAR файлов для перевода (множественный выбор)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите JAR файлы модов (можно несколько)",
            "",
            "JAR файлы (*.jar);;Все файлы (*)"
        )
        
        if file_paths:
            # Если выбрано несколько файлов, создаем временную папку со ссылками
            if len(file_paths) == 1:
                # Один файл - просто указываем путь к нему
                self.jar_path_input.setText(file_paths[0])
                file_info = f"📁 Выбран файл: {Path(file_paths[0]).name}"
            else:
                # Несколько файлов - указываем путь к папке первого файла
                # Воркер будет обрабатывать только выбранные файлы
                first_file_dir = str(Path(file_paths[0]).parent)
                self.jar_path_input.setText(first_file_dir)
                
                # Сохраняем список выбранных файлов для воркера
                self.selected_jar_files = file_paths
                
                file_names = [Path(f).name for f in file_paths]
                file_info = f"📁 Выбрано файлов: {len(file_paths)}\n" + "\n".join([f"   • {name}" for name in file_names])
            
            # Запускаем анализ файлов
            self.analyze_selected_jars([Path(p) for p in file_paths])
    
    def browse_jar_folder(self):
        """Выбор папки с JAR файлами для перевода"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с JAR модами",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.jar_path_input.setText(folder_path)
            
            # Очищаем список выбранных файлов при выборе папки
            self.selected_jar_files = None
            
            jar_files = list(Path(folder_path).glob("*.jar"))
            
            if jar_files:
                # Запускаем анализ файлов
                self.analyze_selected_jars(jar_files)
            else:
                welcome_msg = """🎯 Переводчик JAR модов Minecraft

❌ В выбранной папке не найдено JAR файлов
                """
                self.jar_log.setPlainText(welcome_msg.strip())
    
    def analyze_selected_jars(self, jar_files):
        """Анализирует выбранные JAR файлы и показывает статистику"""
        self.jar_log.clear()
        self.jar_log.append("🔍 Анализ JAR файлов...")
        self.jar_log.append("")
        
        # Импортируем функцию анализа
        from translate_jar_simple import analyze_jar_files
        
        def progress_callback(progress, message):
            # Обновляем последнюю строку лога
            cursor = self.jar_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            self.jar_log.append(f"🔍 {message} ({progress:.0f}%)")
        
        try:
            # Анализируем файлы
            analysis = analyze_jar_files(jar_files, progress_callback)
            
            # Очищаем лог и показываем результаты
            self.jar_log.clear()
            self.jar_log.append("📊 АНАЛИЗ JAR ФАЙЛОВ")
            self.jar_log.append("=" * 50)
            self.jar_log.append(f"📁 Всего файлов: {analysis['total_files']}")
            self.jar_log.append("")
            
            # Файлы, которые нуждаются в переводе
            if analysis['need_translation']:
                self.jar_log.append(f"✅ Нуждаются в переводе: {len(analysis['need_translation'])}")
                for jar_info in analysis['need_translation'][:5]:  # Показываем первые 5
                    name = jar_info['file'].name
                    strings_need = jar_info['strings_to_translate'] - jar_info['already_translated_strings']
                    self.jar_log.append(f"   • {name} ({strings_need} строк)")
                if len(analysis['need_translation']) > 5:
                    self.jar_log.append(f"   ... и еще {len(analysis['need_translation']) - 5} файлов")
                self.jar_log.append("")
            
            # Уже переведенные файлы
            if analysis['already_translated']:
                self.jar_log.append(f"⏭️ Уже переведены: {len(analysis['already_translated'])}")
                for jar_info in analysis['already_translated'][:3]:  # Показываем первые 3
                    self.jar_log.append(f"   • {jar_info['file'].name}")
                if len(analysis['already_translated']) > 3:
                    self.jar_log.append(f"   ... и еще {len(analysis['already_translated']) - 3} файлов")
                self.jar_log.append("")
            
            # Файлы без контента для перевода
            if analysis['no_files']:
                self.jar_log.append(f"❌ Нет файлов для перевода: {len(analysis['no_files'])}")
                for jar_info in analysis['no_files'][:3]:  # Показываем первые 3
                    self.jar_log.append(f"   • {jar_info['file'].name}")
                if len(analysis['no_files']) > 3:
                    self.jar_log.append(f"   ... и еще {len(analysis['no_files']) - 3} файлов")
                self.jar_log.append("")
            
            # Файлы без строк для перевода
            if analysis['no_strings']:
                self.jar_log.append(f"⚠️ Нет строк для перевода: {len(analysis['no_strings'])}")
                for jar_info in analysis['no_strings'][:3]:  # Показываем первые 3
                    self.jar_log.append(f"   • {jar_info['file'].name}")
                if len(analysis['no_strings']) > 3:
                    self.jar_log.append(f"   ... и еще {len(analysis['no_strings']) - 3} файлов")
                self.jar_log.append("")
            
            # Общая статистика
            if analysis['need_translation']:
                stats = analysis['stats']
                self.jar_log.append("📈 СТАТИСТИКА ПЕРЕВОДА:")
                self.jar_log.append(f"   • Lang файлов: {stats['total_lang_files']}")
                self.jar_log.append(f"   • Patchouli файлов: {stats['total_patchouli_files']}")
                self.jar_log.append(f"   • Строк для перевода: {stats['total_strings']}")
                self.jar_log.append("")
                self.jar_log.append("🚀 Нажмите 'НАЧАТЬ ПЕРЕВОД' для обработки файлов")
            else:
                self.jar_log.append("ℹ️ Нет файлов, нуждающихся в переводе")
            
            # Сохраняем результаты анализа для использования при переводе
            self.jar_analysis = analysis
            
        except Exception as e:
            self.jar_log.append(f"❌ Ошибка анализа: {e}")
            self.jar_analysis = None
    
    def start_jar_translation(self):
        """Запуск перевода JAR модов - новая реализация"""
        # Проверяем, запущен ли уже перевод
        if hasattr(self, 'jar_translation_worker') and self.jar_translation_worker.isRunning():
            # Если перевод запущен, останавливаем его
            self.stop_jar_translation()
            return
        
        input_path = self.jar_path_input.text().strip()
        
        if not input_path:
            QMessageBox.warning(self, "Ошибка", "Выберите JAR файл или папку с модами!")
            return
        
        if not Path(input_path).exists():
            QMessageBox.warning(self, "Ошибка", "Указанный путь не существует!")
            return
        
        # Проверяем результаты анализа
        if not hasattr(self, 'jar_analysis') or not self.jar_analysis:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите файлы для анализа!")
            return
        
        # Проверяем, есть ли файлы для перевода
        if not self.jar_analysis['need_translation']:
            QMessageBox.information(
                self, 
                "Информация", 
                "Нет файлов, нуждающихся в переводе.\n\n"
                f"• Уже переведены: {len(self.jar_analysis['already_translated'])}\n"
                f"• Нет файлов для перевода: {len(self.jar_analysis['no_files'])}\n"
                f"• Нет строк для перевода: {len(self.jar_analysis['no_strings'])}"
            )
            return
        
        # Показываем диалог с подтверждением
        stats = self.jar_analysis['stats']
        files_count = len(self.jar_analysis['need_translation'])
        
        reply = QMessageBox.question(
            self,
            "Подтверждение перевода",
            f"Готов к переводу:\n\n"
            f"📁 Файлов: {files_count}\n"
            f"📄 Lang файлов: {stats['total_lang_files']}\n"
            f"📚 Patchouli файлов: {stats['total_patchouli_files']}\n"
            f"📝 Строк для перевода: {stats['total_strings']}\n\n"
            f"Как обработать переведенные файлы?\n\n"
            f"🔄 ДА - Заменить оригинальные файлы\n"
            f"📁 НЕТ - Создать новые файлы с суффиксом '_ru'\n\n"
            f"Рекомендуется создать новые файлы для безопасности.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        replace_original = reply == QMessageBox.StandardButton.Yes
        
        # Определяем выходную папку
        input_path_obj = Path(input_path)
        if input_path_obj.is_file():
            output_path = str(input_path_obj.parent)
        else:
            output_path = input_path
        
        # Получаем список файлов для обработки
        selected_files = getattr(self, 'selected_jar_files', None)
        
        # Получаем количество потоков из настроек
        threads_count = self.get_threads_count() if hasattr(self, 'get_threads_count') else 8
        
        # Инициализируем систему упорядоченного отображения модов
        self.mod_lines = {}  # Очищаем предыдущие строки
        self.total_mods = len(self.jar_analysis['need_translation'])  # Устанавливаем общее количество модов
        
        # Запускаем воркер с результатами анализа
        self.jar_translation_worker = SimpleJarTranslationWorker(
            input_path, 
            output_path, 
            replace_original, 
            selected_files, 
            self.jar_analysis,  # Передаем результаты анализа
            threads_count  # Передаем количество потоков
        )
        self.jar_translation_worker.progress_updated.connect(self.on_jar_progress_update)
        self.jar_translation_worker.log_message.connect(self.on_jar_log_message)
        self.jar_translation_worker.log_colored_message.connect(self.log_jar_message)  # Подключаем цветные сообщения
        self.jar_translation_worker.update_mod_line.connect(self.update_ordered_mod_line)  # Подключаем упорядоченное обновление
        self.jar_translation_worker.api_warning.connect(self.on_jar_api_warning)  # Подключаем API предупреждения
        self.jar_translation_worker.finished.connect(self.on_jar_translation_finished)
        
        # Изменяем кнопку на красную "Остановить"
        self.jar_translate_btn.setText("ОСТАНОВИТЬ")
        self.jar_translate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC2626,
                    stop:0.3 #E53E3E,
                    stop:0.7 #EF4444,
                    stop:1 #F56565);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E53E3E,
                    stop:0.3 #EF4444,
                    stop:0.7 #F56565,
                    stop:1 #FC8181);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B91C1C,
                    stop:0.3 #DC2626,
                    stop:0.7 #E53E3E,
                    stop:1 #EF4444);
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        
        self.jar_progress.setText("Инициализация перевода...")
        self.jar_progress.setValue(0)
        
        self.jar_log.clear()
        self.jar_log.append("🚀 Запуск перевода JAR модов...")
        self.jar_log.append(f"📥 Источник: {input_path}")
        self.jar_log.append(f"📤 Вывод: {output_path}")
        self.jar_log.append(f"🌐 Языки: en_us → ru_ru")
        self.jar_log.append(f"⚙️ Режим: {'Замена оригиналов' if replace_original else 'Создание _ru.jar'}")
        self.jar_log.append("")
        
        self.jar_translation_worker.start()
    
    def toggle_jar_translation_pause(self):
        """Переключение паузы/возобновления перевода JAR модов"""
        if hasattr(self, 'jar_translation_worker') and self.jar_translation_worker.isRunning():
            if self.jar_translation_worker.is_paused:
                # Возобновляем
                self.jar_translation_worker.resume()
                self.jar_pause_btn.setText("Пауза")
                self.jar_log.append("▶️ Перевод возобновлен")
                # НЕ меняем текст прогресса - он обновится автоматически при продолжении
            else:
                # Ставим на паузу
                self.jar_translation_worker.pause()
                self.jar_pause_btn.setText("Старт")  # Короткое слово вместо "Продолжить"
                self.jar_log.append("⏸️ Перевод приостановлен")
                self.jar_progress.setText("На паузе...")
        else:
            # Если перевод не запущен
            self.jar_log.append("⚠️ Перевод не запущен")
    
    def stop_jar_translation(self):
        """Остановка перевода JAR модов"""
        if hasattr(self, 'jar_translation_worker') and self.jar_translation_worker.isRunning():
            # Сначала снимаем с паузы если нужно
            if self.jar_translation_worker.is_paused:
                self.jar_translation_worker.resume()
            
            # Затем останавливаем
            self.jar_translation_worker.stop()
            self.jar_log.append("⏹️ Остановка перевода...")
            
            # Возвращаем кнопку в исходное состояние
            self.reset_jar_translate_button()
            
            # Возвращаем кнопку паузы в состояние паузы
            self.jar_pause_btn.setText("Пауза")
        else:
            # Если перевод не запущен
            self.jar_log.append("⚠️ Перевод не запущен")
    
    def open_jar_result(self):
        """Открытие папки с результатами перевода"""
        try:
            input_path = self.jar_path_input.text().strip()
            if not input_path:
                self.jar_log.append("⚠️ Путь к файлам не указан")
                return
            
            input_path_obj = Path(input_path)
            if input_path_obj.is_file():
                result_path = input_path_obj.parent
            else:
                result_path = input_path_obj
            
            if not result_path.exists():
                self.jar_log.append("⚠️ Папка не найдена")
                return
            
            import subprocess
            import sys
            
            # Проверяем, не заблокирована ли папка процессом перевода
            if hasattr(self, 'jar_worker') and self.jar_worker and self.jar_worker.isRunning():
                self.jar_log.append("⚠️ Дождитесь завершения перевода перед открытием папки")
                return
            
            if sys.platform == "win32":
                subprocess.run(["explorer", str(result_path)], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(result_path)], check=False)
            else:
                subprocess.run(["xdg-open", str(result_path)], check=False)
                
            self.jar_log.append(f"📂 Открыта папка: {result_path.name}")
            
        except Exception as e:
            self.jar_log.append(f"❌ Ошибка при открытии папки: {str(e)}")
    
    def log_jar_message(self, message):
        """
        Добавляет цветное сообщение в JAR лог с динамическим обновлением строк
        Светло-фиолетовый для процесса (0-99%), зеленый только для 100%
        """
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Определяем цвет в зависимости от содержимого сообщения
        if "переведен" in message and "[" in message and "]" in message:
            # Для строк вида "[X/Y] ModName - переведен"
            color = "#10b981"  # Зеленый для полностью завершенных модов
        elif "100%" in message and "[" in message and "]" in message:
            # Только для строк вида "[X/Y] ModName - 100%"
            color = "#10b981"  # Зеленый для полностью завершенных модов
        elif "%" in message and "[" in message and "]" in message:
            # Для всех остальных процентов (0%-99%) в строках модов
            color = "#c4b5fd"  # Светло-фиолетовый с белым оттенком для процесса
        elif "завершен" in message.lower() or "✅" in message:
            color = "#10b981"  # Зеленый для общих сообщений о завершении
        elif "ошибка" in message.lower() or "❌" in message:
            color = "#ef4444"  # Красный для ошибок
        elif "нет файлов" in message.lower() or "⚪" in message:
            color = "#6b7280"  # Серый для пропущенных
        else:
            color = "#94a3b8"  # Серый по умолчанию
        
        # Проверяем, является ли это сообщением с прогрессом мода
        is_mod_progress = "[" in message and "]" in message and ("%" in message or "переведен" in message)
        
        if is_mod_progress:
            # Это сообщение с прогрессом мода
            # Сохраняем текущую позицию скролла
            scrollbar = self.jar_log.verticalScrollBar()
            current_scroll_position = scrollbar.value()
            
            cursor = self.jar_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            
            # Получаем весь HTML текст лога
            full_html = self.jar_log.toHtml()
            lines = full_html.split('<br>')
            
            if lines:
                # Ищем последнюю строку с тем же номером мода
                import re
                new_match = re.search(r'\[(\d+)/\d+\]', message)
                
                if new_match:
                    mod_number = new_match.group(1)
                    
                    # Проверяем, является ли это обновлением процента или новым модом
                    # Если сообщение содержит " - 0%", это новый мод - создаем новую строку
                    if " - 0%" in message:
                        # Новый мод - всегда создаем новую строку
                        formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
                        self.jar_log.append(formatted_message)
                    else:
                        # Это обновление процента - ищем строку для замены
                        found_line_to_update = False
                        for i in range(len(lines) - 1, -1, -1):
                            line = lines[i]
                            if f'[{mod_number}/' in line and ('% ' in line or 'переведен' in line or 'нет файлов' in line):
                                # Нашли строку для обновления
                                formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
                                lines[i] = formatted_message
                                
                                # Обновляем весь лог
                                updated_html = '<br>'.join(lines)
                                self.jar_log.setHtml(updated_html)
                                
                                # Восстанавливаем позицию скролла
                                scrollbar.setValue(current_scroll_position)
                                found_line_to_update = True
                                return
                        
                        # Если не нашли строку для обновления, добавляем новую
                        if not found_line_to_update:
                            formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
                            self.jar_log.append(formatted_message)
                else:
                    # Если не смогли извлечь номер мода, добавляем новую строку
                    formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
                    self.jar_log.append(formatted_message)
            else:
                # Если нет строк, добавляем новую
                formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
                self.jar_log.append(formatted_message)
        else:
            # Обычное сообщение - добавляем как есть
            formatted_message = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
            self.jar_log.append(formatted_message)
        
        # НЕ принудительно прокручиваем - позволяем пользователю управлять скроллом
    
    def update_ordered_mod_line(self, jar_index, mod_name, status):
        """
        Обновляет строку мода в упорядоченном виде (1, 2, 3, 4 сверху вниз)
        jar_index: индекс мода (0, 1, 2, 3...)
        mod_name: название мода
        status: статус ("0%", "20%", "40%", "60%", "80%", "100%", "переведен", "нет файлов")
        """
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Определяем цвет в зависимости от статуса
        if status == "переведен" or status == "100%":
            color = "#10b981"  # Зеленый для завершенных
        elif "%" in status:
            color = "#c4b5fd"  # Фиолетовый для в процессе
        elif status == "нет файлов":
            color = "#6b7280"  # Серый для пропущенных
        else:
            color = "#94a3b8"  # Серый по умолчанию
        
        # Формируем строку
        message = f"[{jar_index+1}/{self.total_mods}] {mod_name} - {status}"
        formatted_line = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
        
        # Сохраняем строку
        self.mod_lines[jar_index] = formatted_line
        
        # Перерисовываем весь лог в правильном порядке
        self._redraw_ordered_mod_log()
    
    def _redraw_ordered_mod_log(self):
        """Перерисовывает лог модов в правильном порядке (1, 2, 3, 4 сверху вниз)"""
        # Сохраняем текущую позицию скролла
        scrollbar = self.jar_log.verticalScrollBar()
        current_scroll_position = scrollbar.value()
        
        # Получаем существующий контент лога (все что не относится к модам)
        full_html = self.jar_log.toHtml()
        
        # Удаляем все строки с модами (содержат [X/Y])
        import re
        lines = full_html.split('<br>')
        non_mod_lines = []
        
        for line in lines:
            # Если строка не содержит паттерн [X/Y], это не строка мода
            if not re.search(r'\[\d+/\d+\]', line):
                non_mod_lines.append(line)
        
        # Собираем строки модов в правильном порядке
        ordered_mod_lines = []
        for jar_index in sorted(self.mod_lines.keys()):
            ordered_mod_lines.append(self.mod_lines[jar_index])
        
        # Объединяем: сначала заголовки, потом моды в порядке 1,2,3,4, потом остальное
        if ordered_mod_lines:
            # Находим где заканчиваются заголовки (ищем строку с "🧵 Потоков для перевода")
            header_end_index = 0
            for i, line in enumerate(non_mod_lines):
                if "🧵 Потоков для перевода" in line or "🚀 Запуск" in line:
                    header_end_index = i + 1
                    break
            
            # Разделяем на заголовки и остальное
            header_lines = non_mod_lines[:header_end_index]
            footer_lines = non_mod_lines[header_end_index:]
            
            # Собираем финальный HTML
            all_lines = header_lines + ordered_mod_lines + footer_lines
        else:
            all_lines = non_mod_lines
        
        # Обновляем лог
        new_html = '<br>'.join(all_lines)
        self.jar_log.setHtml(new_html)
        
        # Восстанавливаем позицию скролла
        scrollbar.setValue(current_scroll_position)
    
    def clear_jar_log(self):
        """Очистка лога JAR перевода"""
        welcome_msg = """🎯 Переводчик JAR модов Minecraft

📁 Выберите JAR файл(ы) → 🚀 Нажмите "Начать перевод"
        """
        self.jar_log.setPlainText(welcome_msg.strip())
        # Очищаем также систему упорядоченного отображения
        self.mod_lines = {}
        self.total_mods = 0
    
    def on_jar_progress_update(self, progress, message):
        """Обновление прогресса перевода JAR модов с throttling"""
        # Добавляем throttling для предотвращения "прыжков" прогресс-бара
        current_time = time.time()
        
        # Инициализируем атрибуты throttling если их нет
        if not hasattr(self, '_last_progress_update_time'):
            self._last_progress_update_time = 0
            self._last_progress_value = -1
        
        # Минимальный интервал между обновлениями GUI (50ms)
        min_gui_update_interval = 0.05
        time_since_last_update = current_time - self._last_progress_update_time
        
        # Обновляем только если прошло достаточно времени ИЛИ прогресс значительно изменился
        should_update_gui = (
            time_since_last_update >= min_gui_update_interval or
            abs(progress - self._last_progress_value) >= 5 or  # Изменение на 5% или больше
            progress == 100 or  # Всегда обновляем при 100%
            progress == 0       # Всегда обновляем при 0% (начало нового мода)
        )
        
        if should_update_gui and progress >= 0:
            self.jar_progress.setValue(progress)
            self._last_progress_update_time = current_time
            self._last_progress_value = progress
            
        # Сообщение обновляем всегда (оно не вызывает визуальных "прыжков")
        self.jar_progress.setText(message)
    
    def on_jar_log_message(self, message):
        """Добавление сообщения в лог JAR перевода"""
        # Проверяем, нужно ли обновить существующую строку прогресса
        should_update_line = (
            (("%" in message or "/" in message) and 
             any(x in message for x in ["Lang (", "Patchouli (", "строк"]))
        )
        
        if should_update_line:
            # Это сообщение с прогрессом - обновляем последнюю строку
            cursor = self.jar_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            
            # Если последняя строка содержит прогресс, заменяем её
            current_line = cursor.selectedText()
            if (("%" in current_line or "/" in current_line) and 
                any(x in current_line for x in ["Lang (", "Patchouli (", "строк"])):
                cursor.removeSelectedText()
                cursor.insertText(message)
            else:
                # Иначе добавляем новую строку
                self.jar_log.append(message)
        else:
            # Обычное сообщение - добавляем как есть
            self.jar_log.append(message)
    
    def on_jar_api_warning(self, warning_message):
        """Обработка API предупреждений с особым форматированием"""
        # Добавляем предупреждение с красным цветом и рамкой
        formatted_warning = f"""
<div style="
    background-color: rgba(239, 68, 68, 0.15);
    border: 2px solid #ef4444;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    color: #ffffff;
    font-weight: 600;
">
{warning_message}
</div>
"""
        
        # Добавляем в лог с HTML форматированием
        cursor = self.jar_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(formatted_warning)
        
        # Прокручиваем к концу чтобы предупреждение было видно
        self.jar_log.ensureCursorVisible()
        
        # НЕ принудительно прокручиваем - позволяем пользователю управлять скроллом
    
    def reset_jar_translate_button(self):
        """Возвращает кнопку перевода в исходное состояние"""
        self.jar_translate_btn.setText("НАЧАТЬ ПЕРЕВОД JAR МОДОВ")
        self.jar_translate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                border-left: 1px solid rgba(255, 255, 255, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                color: #ffffff;
                font-weight: 700;
                font-size: 18px;
                padding: 18px 35px;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF,
                    stop:0.3 #C965FF,
                    stop:0.7 #E075FF,
                    stop:1 #F080FF);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9540E6,
                    stop:0.3 #A650F0,
                    stop:0.7 #C060FF,
                    stop:1 #D565FF);
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
    
    def show_translation_summary(self, stats, success):
        """Показывает детальное окно итогов перевода"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Итоги перевода JAR модов")
        dialog.setFixedSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                color: #ffffff;
                border-radius: 15px;
            }
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                margin: 10px 0;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 10px;
                color: #e0e0e0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #8b5cf6;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 20px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок с результатом
        if success:
            if stats.get('jars_failed', 0) == 0:
                title = QLabel("🎉 Перевод завершен успешно!")
                title.setStyleSheet("color: #10b981; font-size: 18px; font-weight: 700;")
            else:
                title = QLabel("⚠️ Перевод завершен с предупреждениями")
                title.setStyleSheet("color: #f59e0b; font-size: 18px; font-weight: 700;")
        else:
            title = QLabel("❌ Перевод завершен с ошибками")
            title.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: 700;")
        
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Детальная статистика
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        
        # Формируем детальный отчет
        total_jars = stats.get('jars_processed', 0) + stats.get('jars_failed', 0)
        
        report = f"""📦 JAR ФАЙЛЫ:
✅ Успешно обработано: {stats.get('jars_processed', 0)} из {total_jars}
❌ С ошибками: {stats.get('jars_failed', 0)}
⏭️ Пропущено (уже переведены): {stats.get('jars_skipped', 0)}

📄 ФАЙЛЫ И СОДЕРЖИМОЕ:
📝 Найдено файлов для перевода: {stats.get('files_found', 0)}
✅ Успешно переведено файлов: {stats.get('files_translated', 0)}
📜 Переведено строк: {stats.get('strings_translated', 0):,}
⏭️ Пропущено строк: {stats.get('strings_skipped', 0):,}

💾 ПРОИЗВОДИТЕЛЬНОСТЬ:
🚀 Попаданий в кэш: {stats.get('cache_hits', 0):,}
⚡ Скорость: ~{stats.get('strings_translated', 0) / max(1, total_jars):.1f} строк/JAR

🎯 ЧТО ПЕРЕВОДИЛОСЬ:
📚 Языковые файлы (*.json, *.lang)
📖 Patchouli книги (name, text, description)  
🏆 Достижения (title, description)

🔧 НАСТРОЙКИ:
🌐 Языки: en_us → ru_ru
⚙️ Режим: {'Замена оригиналов' if stats.get('replace_original', False) else 'Создание новых файлов'}
"""
        
        # Добавляем ошибки если есть
        if 'errors' in stats and stats['errors']:
            report += f"\n❌ ОШИБКИ ({len(stats['errors'])}):\n"
            for i, error in enumerate(stats['errors'][:5], 1):  # Показываем только первые 5
                report += f"{i}. {error}\n"
            if len(stats['errors']) > 5:
                report += f"... и еще {len(stats['errors']) - 5} ошибок\n"
        
        summary_text.setPlainText(report)
        layout.addWidget(summary_text)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        # Кнопка "Открыть папку"
        open_folder_btn = QPushButton("📁 Открыть папку")
        open_folder_btn.clicked.connect(lambda: self.open_jar_result_folder())
        button_layout.addWidget(open_folder_btn)
        
        button_layout.addStretch()
        
        # Кнопка "Закрыть"
        close_btn = QPushButton("✅ Закрыть")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Показываем диалог
        dialog.exec()
    
    def open_jar_result_folder(self):
        """Открывает папку с результатами перевода"""
        try:
            # Проверяем, не запущен ли процесс перевода
            if hasattr(self, 'jar_worker') and self.jar_worker and self.jar_worker.isRunning():
                QMessageBox.warning(self, "Предупреждение", 
                                  "Дождитесь завершения перевода перед открытием папки")
                return
            
            # Определяем папку результатов из последнего перевода
            input_path = self.jar_path_input.text().strip()
            if not input_path:
                QMessageBox.warning(self, "Ошибка", "Путь к файлам не указан")
                return
                
            input_path_obj = Path(input_path)
            if input_path_obj.is_file():
                result_folder = input_path_obj.parent / "translated"
            else:
                result_folder = input_path_obj / "translated"
            
            if not result_folder.exists():
                QMessageBox.warning(self, "Ошибка", 
                                  f"Папка с результатами не найдена:\n{result_folder}")
                return
            
            import subprocess
            import sys
            
            if sys.platform == "win32":
                subprocess.run(["explorer", str(result_folder)], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(result_folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(result_folder)], check=False)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть папку: {e}")
        else:
            QMessageBox.information(self, "Информация", "Папка с результатами не найдена")
    
    def setup_jar_translation_button_animations(self):
        """Настройка анимаций для кнопки перевода JAR (как у кнопки квестов)"""
        # Анимация fade-in при наведении
        self.jar_fade_in_animation = QPropertyAnimation(self.jar_translate_btn, b"windowOpacity")
        self.jar_fade_in_animation.setDuration(200)
        self.jar_fade_in_animation.setStartValue(0.8)
        self.jar_fade_in_animation.setEndValue(1.0)
        self.jar_fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Анимация пульсации
        self.jar_pulse_animation = QPropertyAnimation(self.jar_translate_btn, b"geometry")
        self.jar_pulse_animation.setDuration(1000)
        self.jar_pulse_animation.setLoopCount(-1)  # Бесконечный цикл
        self.jar_pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Подключаем события
        self.jar_translate_btn.enterEvent = lambda event: self.start_jar_translation_fade_in()
        self.jar_translate_btn.leaveEvent = lambda event: None  # Оставляем как есть при уходе
    
    def start_jar_translation_fade_in(self):
        """Запуск анимации fade-in для кнопки JAR перевода"""
        if hasattr(self, 'jar_fade_in_animation'):
            self.jar_fade_in_animation.start()
    
    def start_jar_translation_pulse(self):
        """Запуск анимации пульсации для кнопки JAR перевода"""
        if hasattr(self, 'jar_pulse_animation'):
            original_geometry = self.jar_translate_btn.geometry()
            expanded_geometry = QRect(
                original_geometry.x() - 2,
                original_geometry.y() - 1,
                original_geometry.width() + 4,
                original_geometry.height() + 2
            )
            
            self.jar_pulse_animation.setStartValue(original_geometry)
            self.jar_pulse_animation.setEndValue(expanded_geometry)
            self.jar_pulse_animation.start()
    
    def stop_jar_translation(self):
        """Остановка перевода JAR модов"""
        if hasattr(self, 'jar_translation_worker') and self.jar_translation_worker:
            self.jar_translation_worker.stop()
            self.jar_log.append("⏹️ Остановка перевода...")
            
            # Сброс UI
            self.jar_translate_btn.setEnabled(True)
            self.reset_jar_translate_button()  # Используем функцию сброса
            self.jar_progress.setText("Остановлено пользователем")
    
    def clear_jar_log(self):
        """Очистка лога JAR перевода"""
        self.jar_log.clear()
        
        # Добавляем приветственное сообщение
        welcome_msg = """🎯 Переводчик JAR модов Minecraft

📁 Выберите JAR файл(ы) → 🚀 Нажмите "Начать перевод"
        """
        self.jar_log.setPlainText(welcome_msg.strip())

    def on_jar_translation_finished(self, success, stats):
        """Завершение перевода JAR модов в ContentArea"""
        try:
            logger.info(f"on_jar_translation_finished (ContentArea) вызван: success={success}, stats={stats}")
            
            # Возвращаем кнопку в исходное состояние
            self.jar_translate_btn.setEnabled(True)
            self.jar_translate_btn.setText("НАЧАТЬ ПЕРЕВОД")
            self.jar_translate_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #A546FF,
                        stop:0.3 #B855FF,
                        stop:0.7 #D065FF,
                        stop:1 #E06BFF);
                    border-radius: 25px;
                    border-top: 1px solid rgba(255, 255, 255, 0.4);
                    border-left: 1px solid rgba(255, 255, 255, 0.2);
                    border-right: 1px solid rgba(255, 255, 255, 0.1);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                    color: #ffffff;
                    font-weight: 700;
                    font-size: 18px;
                    padding: 18px 35px;
                    min-height: 25px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #B855FF,
                        stop:0.3 #C965FF,
                        stop:0.7 #E075FF,
                        stop:1 #F080FF);
                    border-top: 1px solid rgba(255, 255, 255, 0.6);
                    border-left: 1px solid rgba(255, 255, 255, 0.4);
                    border-right: 1px solid rgba(255, 255, 255, 0.2);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #9540E6,
                        stop:0.3 #A650F0,
                        stop:0.7 #C060FF,
                        stop:1 #D565FF);
                    border-top: 1px solid rgba(0, 0, 0, 0.3);
                    border-left: 1px solid rgba(0, 0, 0, 0.2);
                    border-right: 1px solid rgba(255, 255, 255, 0.3);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.4);
                }
            """)
            
            if success:
                logger.info("Условие success=True выполнено для JAR (ContentArea), показываем результаты")
                self.jar_progress.setValue(100)
                self.jar_progress.setText("✅ Перевод завершен успешно!")
                
                self.jar_log.append("")
                self.jar_log.append("🎉 ПЕРЕВОД ЗАВЕРШЕН!")
                self.jar_log.append("=" * 50)
                self.jar_log.append(f"📊 Статистика:")
                self.jar_log.append(f"   • JAR обработано: {stats.get('successful', 0)}")
                self.jar_log.append(f"   • JAR с ошибками: {stats.get('failed', 0)}")
                self.jar_log.append(f"   • Lang файлов: {stats.get('lang_files', 0)}")
                self.jar_log.append(f"   • Patchouli файлов: {stats.get('patchouli_files', 0)}")
                self.jar_log.append(f"   • Строк переведено: {stats.get('strings_translated', 0)}")
                self.jar_log.append("=" * 50)
                
                # Показываем окно поддержки после успешного перевода с задержкой
                if self.main_window and hasattr(self.main_window, 'safe_show_support_dialog'):
                    logger.info("Планируем показ окна поддержки для JAR через 1000мс")
                    QTimer.singleShot(1000, self.main_window.safe_show_support_dialog)
                
            else:
                self.jar_progress.setValue(0)
                self.jar_progress.setText("❌ Ошибка при переводе")
                
                self.jar_log.append("")
                self.jar_log.append("❌ ПЕРЕВОД ЗАВЕРШЕН С ОШИБКАМИ")
                
        except Exception as e:
            logger.error(f"Ошибка в on_jar_translation_finished (ContentArea): {e}")
            logger.debug(traceback.format_exc())


class AnimatedWindowButton(QPushButton):
    """Анимированная кнопка управления окном с hover и click эффектами"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # Анимации для различных эффектов
        self.hover_animation = QPropertyAnimation(self, b"geometry")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.click_animation = QPropertyAnimation(self, b"geometry")
        self.click_animation.setDuration(100)
        self.click_animation.setEasingCurve(QEasingCurve.Type.OutQuart)
        
        self.return_animation = QPropertyAnimation(self, b"geometry")
        self.return_animation.setDuration(150)
        self.return_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Анимация прозрачности для плавного появления
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_geometry = None
        self.is_hovered = False
        self.is_pressed = False
        
        # Устанавливаем начальную прозрачность
        self.setWindowOpacity(0.8)
    
    def enterEvent(self, event):
        """Анимация при наведении - подъем вверх и повышение прозрачности"""
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        
        if not self.is_pressed:
            self.is_hovered = True
            
            # Поднимаем кнопку на 4 пикселя вверх
            current_rect = self.geometry()
            hover_rect = QRect(
                current_rect.x(),
                current_rect.y() - 4,  # Поднимаем на 4px вверх
                current_rect.width(),
                current_rect.height()
            )
            
            # Анимация подъема
            self.hover_animation.setStartValue(current_rect)
            self.hover_animation.setEndValue(hover_rect)
            self.hover_animation.start()
            
            # Анимация прозрачности
            self.opacity_animation.setStartValue(self.windowOpacity())
            self.opacity_animation.setEndValue(1.0)
            self.opacity_animation.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Возврат к исходному размеру при уходе мыши"""
        if not self.is_pressed and self.is_hovered:
            self.is_hovered = False
            
            if self.original_geometry:
                # Плавный возврат к исходному размеру
                self.return_animation.setStartValue(self.geometry())
                self.return_animation.setEndValue(self.original_geometry)
                self.return_animation.start()
                
                # Возврат прозрачности
                self.opacity_animation.setStartValue(self.windowOpacity())
                self.opacity_animation.setEndValue(0.8)
                self.opacity_animation.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Анимация нажатия - опускание вниз"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressed = True
            
            # Опускаем кнопку на 2 пикселя вниз от текущей позиции
            current_rect = self.geometry()
            press_rect = QRect(
                current_rect.x(),
                current_rect.y() + 2,  # Опускаем на 2px вниз
                current_rect.width(),
                current_rect.height()
            )
            
            # Быстрая анимация нажатия
            self.click_animation.setStartValue(current_rect)
            self.click_animation.setEndValue(press_rect)
            self.click_animation.start()
        
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Возврат после отпускания кнопки"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressed = False
            
            # Определяем целевую позицию в зависимости от hover состояния
            if self.is_hovered and self.original_geometry:
                # Возвращаемся к hover позиции (поднятой на 4px)
                target_rect = QRect(
                    self.original_geometry.x(),
                    self.original_geometry.y() - 4,
                    self.original_geometry.width(),
                    self.original_geometry.height()
                )
            else:
                # Возвращаемся к исходной позиции
                target_rect = self.original_geometry if self.original_geometry else self.geometry()
            
            # Анимация возврата с отскоком
            self.return_animation.setStartValue(self.geometry())
            self.return_animation.setEndValue(target_rect)
            self.return_animation.start()
        
        super().mouseReleaseEvent(event)
    
    def showEvent(self, event):
        """Плавное появление кнопки при показе"""
        super().showEvent(event)
        
        # Анимация появления
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(0.8)
        self.opacity_animation.start()


# КНОПКИ ИЗ L4D2 ПРОЕКТА (АДАПТИРОВАННЫЕ)


class UpdateButton(QPushButton):
    """Кнопка обновления с индикатором доступных обновлений"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("updateButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.has_update = False
        self._pulse_opacity = 1.0
        
        # Анимация пульсации индикатора
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_direction = -1  # -1 для затухания, 1 для усиления
        
    def set_update_available(self, available=True):
        """Устанавливает индикатор доступного обновления"""
        self.has_update = available
        if available:
            self.pulse_timer.start(50)  # Обновляем каждые 50мс
        else:
            self.pulse_timer.stop()
            self._pulse_opacity = 1.0
        self.update()  # Перерисовываем кнопку
    
    def _update_pulse(self):
        """Обновляет пульсацию индикатора"""
        self._pulse_opacity += self.pulse_direction * 0.05
        
        if self._pulse_opacity <= 0.3:
            self._pulse_opacity = 0.3
            self.pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_opacity = 1.0
            self.pulse_direction = -1
        
        self.update()
        
    def paintEvent(self, event):
        """Переопределяем отрисовку для добавления индикатора"""
        super().paintEvent(event)
        
        if self.has_update:
            # Рисуем пульсирующую красную точку в правом верхнем углу
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Красная точка с пульсацией
            color = QColor(231, 76, 60)
            color.setAlphaF(self._pulse_opacity)
            painter.setBrush(QBrush(color))
            
            # Белая обводка
            pen_color = QColor(255, 255, 255)
            pen_color.setAlphaF(self._pulse_opacity)
            painter.setPen(QPen(pen_color, 2))
            
            # Позиция точки (правый верхний угол)
            dot_size = 8
            x = self.width() - dot_size - 4
            y = 4
            
            painter.drawEllipse(x, y, dot_size, dot_size)


class AnimatedDonateButton(QPushButton):
    """Простая кнопка доната без эффектов сердечек"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("donateButton")
        # Размер будет установлен при создании кнопки
        
        # Загружаем и устанавливаем иконку поддержки
        sup_icon_path = None
        asset_path = get_asset_path("sup.png")
        if asset_path.exists():
            sup_icon_path = str(asset_path)
        
        if sup_icon_path:
            pixmap = QPixmap(sup_icon_path)
            if not pixmap.isNull():
                # Масштабируем до 20x20 для кнопки
                scaled_pixmap = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в белый цвет
                white_pixmap = QPixmap(scaled_pixmap.size())
                white_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(white_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(white_pixmap.rect(), QColor(255, 255, 255))
                painter.end()
                
                icon = QIcon(white_pixmap)
                self.setIcon(icon)
                self.setIconSize(QSize(20, 20))
    



class AnimatedRefreshButton(QPushButton):
    """Кнопка обновления с анимацией вращения на 360 градусов (адаптированная под текущий проект)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("refreshBtn")
        self.setFixedSize(45, 45)
        self.setToolTip("Обновить")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Инициализируем rotation ДО создания анимации
        self._rotation = 0
        
        # Анимация вращения на 360 градусов при клике
        self.rotation_anim = QPropertyAnimation(self, b"rotation")
        self.rotation_anim.setDuration(800)
        self.rotation_anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        # Анимация вращения при hover
        self.hover_anim = QPropertyAnimation(self, b"rotation")
        self.hover_anim.setDuration(800)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        # Загружаем и перекрашиваем иконку обновления
        self.ref_pixmap = None
        ref_path = get_asset_path("ref.png")
        
        if ref_path.exists():
            pixmap = QPixmap(str(ref_path))
            # Перекрашиваем в белый цвет
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor(255, 255, 255, 160))
            painter.end()
            
            # Масштабируем до 16x16
            self.ref_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    @pyqtProperty(int)
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, angle):
        self._rotation = angle
        self.update()
    
    def enterEvent(self, event):
        """При наведении - проигрываем анимацию"""
        super().enterEvent(event)
        # Проигрываем анимацию только если быстрое вращение не запущено
        if self.rotation_anim.state() != QPropertyAnimation.State.Running:
            self.hover_anim.stop()
            self.hover_anim.setStartValue(self._rotation % 360)
            self.hover_anim.setEndValue(self._rotation + 360)
            self.hover_anim.start()
        self.update()
    
    def leaveEvent(self, event):
        """При уходе мыши - ничего не делаем"""
        super().leaveEvent(event)
        self.update()
    
    def mousePressEvent(self, event):
        """При клике запускаем быструю анимацию вращения"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Останавливаем hover анимацию
            self.hover_anim.stop()
            # Запускаем быстрое вращение на 360 градусов
            self.rotation_anim.stop()
            self.rotation_anim.setStartValue(self._rotation % 360)
            self.rotation_anim.setEndValue(self._rotation + 360)
            self.rotation_anim.start()
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Рисуем кнопку с вращающейся иконкой"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Рисуем фон кнопки (адаптируем под текущий проект)
        if self.underMouse():
            if self.isDown():
                painter.setBrush(QBrush(QColor(26, 26, 26)))
            else:
                painter.setBrush(QBrush(QColor(26, 26, 26)))
        else:
            painter.setBrush(QBrush(QColor(26, 26, 26)))
        
        # Обводка (адаптируем цвета под текущий проект)
        painter.setPen(QPen(QColor(42, 42, 42), 2))
        if self.underMouse():
            painter.setPen(QPen(QColor(164, 70, 255), 2))  # Фиолетовый цвет #A546FF
        
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 22, 22)
        
        # Рисуем иконку с вращением
        if self.ref_pixmap:
            painter.save()
            painter.translate(22.5, 22.5)  # Центр кнопки
            painter.rotate(self._rotation)
            painter.translate(-8, -8)  # Половина размера иконки (16/2)
            
            painter.drawPixmap(0, 0, self.ref_pixmap)
            painter.restore()


class ModernGUIInterface(QMainWindow):
    """Главное окно современного интерфейса"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализируем атрибуты уведомлений
        self.current_notification = None
        self.notification_fade_in = None
        self.notification_fade_out = None
        self.notification_timer = None
        
        # Инициализируем атрибуты кнопок управления окном
        self.minimize_btn = None
        self.close_btn = None
        
        # Инициализируем систему tooltip'ов
        self.custom_tooltip = None
        self.tooltip_animation_group = None
        self.tooltip_hide_animation_group = None
        
        # Инициализируем систему упорядоченного отображения модов
        self.mod_lines = {}  # {jar_index: formatted_html_line} - для упорядоченного отображения модов
        self.total_mods = 0  # Общее количество модов для правильной нумерации
        
        # Устанавливаем отслеживание мыши для автоматического скрытия tooltip'ов
        self.setMouseTracking(True)
        
        self.init_ui()
        self.setup_animations()
        
        # Создаем кнопки управления окном после инициализации UI
        self.create_window_control_buttons()
        
        # Автоматическая проверка обновлений при запуске (через 3 секунды)
        if UPDATER_AVAILABLE:
            QTimer.singleShot(3000, self.auto_check_updates)
    
    def apply_rounded_corners(self):
        """Применяет аккуратные закругленные углы к главному окну с максимальным сглаживанием"""
        # Создаем маску с закругленными углами и максимальным антиалиасингом
        radius = 12  # Более аккуратный радиус
        rect = self.rect()
        
        # Создаем pixmap с увеличенным разрешением для лучшего сглаживания
        scale_factor = 2  # Увеличиваем в 2 раза для лучшего качества
        scaled_size = rect.size() * scale_factor
        pixmap = QPixmap(scaled_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Рисуем с максимальным антиалиасингом для идеально гладких углов
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        
        # Рисуем закругленный прямоугольник с отступом для обводки
        scaled_rect = QRect(0, 0, scaled_size.width(), scaled_size.height())
        content_rect = scaled_rect.adjusted(scale_factor, scale_factor, -scale_factor, -scale_factor)
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(content_rect, (radius-1) * scale_factor, (radius-1) * scale_factor)
        painter.end()
        
        # Масштабируем обратно с сглаживанием
        final_pixmap = pixmap.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Создаем маску из pixmap
        mask = final_pixmap.createMaskFromColor(Qt.GlobalColor.transparent)
        self.setMask(QRegion(mask))
        
        # Убираем стили с центрального виджета
        self.centralWidget().setStyleSheet("")
        
        # Создаем обводку через отдельный виджет
        self.create_border_widget()
    
    def create_border_widget(self):
        """Создает отдельный виджет для обводки окна"""
        # Удаляем предыдущий виджет обводки если есть
        if hasattr(self, 'border_widget'):
            self.border_widget.deleteLater()
        
        # Создаем прозрачный виджет для обводки
        self.border_widget = QWidget(self)
        self.border_widget.setGeometry(0, 0, self.width(), self.height())
        self.border_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.border_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: 1px solid #4a4a4a;
                border-radius: 12px;
            }
        """)
        self.border_widget.show()
        self.border_widget.raise_()  # Поднимаем наверх
    
    def resizeEvent(self, event):
        """Обновляем маску при изменении размера окна"""
        super().resizeEvent(event)
        # Обновляем закругленные углы при изменении размера
        QTimer.singleShot(0, self.apply_rounded_corners)
    
    def create_window_control_buttons(self):
        """Создает анимированные кнопки управления окном в главном окне"""
        # Кнопка сворачивания с анимациями
        self.minimize_btn = AnimatedWindowButton("−", self.centralWidget())
        self.minimize_btn.setFixedSize(32, 32)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        self.minimize_btn.clicked.connect(self.showMinimized)
        
        # Кнопка закрытия с анимациями
        self.close_btn = AnimatedWindowButton("×", self.centralWidget())
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.9);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(192, 57, 43, 1.0);
            }
        """)
        self.close_btn.clicked.connect(self.close)
        
        # Показываем кнопки и поднимаем на передний план
        self.minimize_btn.show()
        self.close_btn.show()
        self.minimize_btn.raise_()
        self.close_btn.raise_()
        
        # Устанавливаем высокий z-order
        self.minimize_btn.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.close_btn.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
    
    def position_main_window_controls(self):
        """Позиционирует кнопки управления главным окном"""
        if not self.minimize_btn or not self.close_btn:
            return
            
        window_width = self.width()
        window_height = self.height()
        
        # Позиционируем кнопки управления окном с учетом кнопок действий
        # Кнопки действий занимают ~450px справа, добавляем отступ
        close_x = window_width - 45  # Отступ от правого края
        close_y = 24  # Выравниваем с TopBar
        minimize_x = window_width - 85  # Отступ для кнопки сворачивания
        minimize_y = 24  # Выравниваем с TopBar
        
        self.close_btn.move(close_x, close_y)
        self.minimize_btn.move(minimize_x, minimize_y)
        
        # Поднимаем на передний план
        self.close_btn.raise_()
        self.minimize_btn.raise_()
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("RU-MINETOOLS NEW")
        
        # Убираем системную рамку окна
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Устанавливаем иконку приложения
        icon_path = str(get_asset_path("logo.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Настраиваем плавное появление подсказок
        # (используем стандартные настройки Qt для оптимальной производительности)
        
        # Получаем размер экрана для позиционирования
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # Устанавливаем размер 1200x800
        window_width = 1200
        window_height = 800
        
        # Устанавливаем минимальный размер
        self.setMinimumSize(800, 600)
        
        # Устанавливаем размер окна
        self.resize(window_width, window_height)
        
        # Центрируем окно на экране
        self.move(
            (screen_geometry.width() - window_width) // 2,
            (screen_geometry.height() - window_height) // 2
        )
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Устанавливаем закругленные края для главного окна
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
        """)
        
        # Применяем маску с закругленными углами
        self.apply_rounded_corners()
        
        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Создаем компоненты
        # Сначала создаем content_area
        self.content_area = ContentArea(self)
        
        # Затем создаем sidebar и передаем ему ссылку на content_area
        # Правая часть с верхней панелью и контентом
        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.top_bar = TopBar(self)
        right_layout.addWidget(self.top_bar)
        
        # Убеждаемся, что TopBar всегда на переднем плане
        self.top_bar.raise_()
        

        
        # Создаем sidebar с ссылками на content_area и top_bar
        self.sidebar = Sidebar(self.content_area, self.top_bar)
        main_layout.addWidget(self.sidebar)
        
        right_layout.addWidget(self.content_area)
        
        main_layout.addWidget(right_area)
        
        # Устанавливаем стили для плавных подсказок с закругленными углами
        self.setStyleSheet("""
            QToolTip {
                background: rgba(30, 30, 30, 0.98);
                border: 1px solid rgba(58, 58, 58, 0.6);
                border-radius: 16px;
                padding: 2px;
                color: #e0e0e0;
                font-size: 12px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                max-width: 340px;
                selection-background-color: transparent;
            }
        """)
        
        # Создаем overlay авторизации
        self.create_auth_overlay()
    
    def create_auth_overlay(self):
        """Создает overlay авторизации с блюром фона"""
        # Проверяем, есть ли сохраненная авторизация (обычная или гостевая)
        auth_file = "telegram_auth.json"
        guest_file = "guest_access.json"
        user_data = None
        
        # Сначала проверяем обычную авторизацию
        if os.path.exists(auth_file):
            try:
                with open(auth_file, 'r', encoding='utf-8') as f:
                    auth_data = json.load(f)
                
                # Проверяем срок действия
                expires = datetime.fromisoformat(auth_data["expires"])
                if datetime.now() < expires:
                    user_data = auth_data["user_data"]
                else:
                    # Авторизация истекла
                    os.remove(auth_file)
            except Exception as e:
                logger.error(f"Ошибка загрузки обычной авторизации: {e}")
                if os.path.exists(auth_file):
                    os.remove(auth_file)
        
        # Если обычной авторизации нет, проверяем гостевую
        if not user_data and os.path.exists(guest_file):
            try:
                with open(guest_file, 'r', encoding='utf-8') as f:
                    guest_data = json.load(f)
                
                # Проверяем срок действия гостевого доступа
                expires = datetime.fromisoformat(guest_data["expires"])
                if datetime.now() < expires:
                    user_data = guest_data["user_data"]
                else:
                    # Гостевой доступ истек
                    os.remove(guest_file)
            except Exception as e:
                logger.error(f"Ошибка загрузки гостевого доступа: {e}")
                if os.path.exists(guest_file):
                    os.remove(guest_file)
        
        # Применяем блюр эффект к центральному виджету с анимацией
        self.blur_effect = self.animate_blur_in(self.centralWidget(), target_radius=15, duration=400)
        
        # СНАЧАЛА показываем приветственное окно, потом авторизацию
        self.show_beta_warning_dialog()
        
        # Сохраняем информацию о пользователе для последующей авторизации
        self._pending_user_data = user_data
    
    def animate_blur_in(self, target_widget, target_radius=15, duration=400):
        """Плавно применяет блюр эффект с анимацией"""
        try:
            # Проверяем, что виджет существует и видим
            if not target_widget or not target_widget.isVisible():
                logger.warning("Целевой виджет для блюра не существует или не видим")
                return None
            
            # Создаем блюр эффект
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(0)  # Начинаем с 0
            target_widget.setGraphicsEffect(blur_effect)
            
            # Создаем анимацию для плавного увеличения радиуса
            self.blur_animation = QPropertyAnimation(blur_effect, b"blurRadius")
            self.blur_animation.setDuration(duration)
            self.blur_animation.setStartValue(0)
            self.blur_animation.setEndValue(target_radius)
            self.blur_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.blur_animation.start()
            
            return blur_effect
        except Exception as e:
            logger.error(f"Ошибка в animate_blur_in: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def animate_blur_out(self, target_widget, current_effect, duration=300):
        """Плавно убирает блюр эффект с анимацией"""
        try:
            if not current_effect or not target_widget:
                if target_widget:
                    target_widget.setGraphicsEffect(None)
                return
            
            # Создаем анимацию для плавного уменьшения радиуса
            self.blur_out_animation = QPropertyAnimation(current_effect, b"blurRadius")
            self.blur_out_animation.setDuration(duration)
            self.blur_out_animation.setStartValue(current_effect.blurRadius())
            self.blur_out_animation.setEndValue(0)
            self.blur_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            
            # После завершения анимации удаляем эффект
            def safe_remove_effect():
                try:
                    if target_widget and not target_widget.isHidden():
                        target_widget.setGraphicsEffect(None)
                except RuntimeError:
                    # Виджет уже удален
                    pass
                except Exception as e:
                    logger.error(f"Ошибка удаления эффекта: {e}")
            
            self.blur_out_animation.finished.connect(safe_remove_effect)
            self.blur_out_animation.start()
            
        except Exception as e:
            logger.error(f"Ошибка в animate_blur_out: {e}")
            logger.debug(traceback.format_exc())
            # В случае ошибки принудительно убираем эффект
            try:
                if target_widget:
                    target_widget.setGraphicsEffect(None)
            except:
                pass
    
    def remove_blur_effect(self):
        """Безопасно удаляет блюр эффект с анимацией"""
        try:
            if hasattr(self, 'centralWidget') and self.centralWidget():
                # Используем анимированное удаление блюра
                if hasattr(self, 'blur_effect') and self.blur_effect:
                    self.animate_blur_out(self.centralWidget(), self.blur_effect)
                else:
                    self.centralWidget().setGraphicsEffect(None)
            if hasattr(self, 'blur_effect'):
                # Не удаляем сразу, дадим анимации завершиться
                QTimer.singleShot(350, lambda: setattr(self, 'blur_effect', None))
        except Exception as e:
            logger.error(f"Ошибка удаления блюра: {e}")
    
    def show_welcome_notification(self, message):
        """Показывает приветственное уведомление в левом нижнем углу"""
        # Удаляем предыдущее уведомление если оно существует
        if hasattr(self, 'current_notification') and self.current_notification:
            try:
                self.current_notification.deleteLater()
            except:
                pass
        
        # Создаем временное уведомление в левом нижнем углу
        notification = QLabel(message)
        notification.setParent(self)
        notification.setObjectName("welcomeNotification")
        notification.setStyleSheet("""
            #welcomeNotification {
                background: #4a4a4a;
                color: white;
                font-size: 10px;
                font-weight: normal;
                padding: 18px 22px;
                border-radius: 25px;
                border: 1px solid #666666;
            }
            #welcomeNotification:hover {
                background: #555555;
                cursor: pointer;
            }
        """)
        notification.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notification.setWordWrap(True)
        
        # Делаем уведомление кликабельным для закрытия
        notification.mousePressEvent = lambda event: self.hide_current_notification()
        
        # Сохраняем ссылку на текущее уведомление
        self.current_notification = notification
        
        # Позиционируем в левом нижнем углу (над пользователем Telegram)
        notification.adjustSize()
        notification.move(
            20,  # Отступ слева
            self.height() - notification.height() - 80  # Отступ снизу (над пользователем)
        )
        
        # Подготавливаем уведомление для анимации
        notification.setWindowOpacity(0.0)
        notification.show()
        notification.raise_()
        
        # Создаем группу анимаций для плавного появления
        self.notification_animation_group = QParallelAnimationGroup()
        
        # Анимация прозрачности (fade in) - очень плавная
        self.notification_fade_in = QPropertyAnimation(notification, b"windowOpacity")
        self.notification_fade_in.setDuration(1000)  # Увеличиваем до 1 секунды
        self.notification_fade_in.setStartValue(0.0)
        self.notification_fade_in.setEndValue(1.0)
        self.notification_fade_in.setEasingCurve(QEasingCurve.Type.OutExpo)  # Самая плавная кривая
        
        # Анимация появления из-за нижнего края экрана
        original_pos = notification.pos()
        # Начинаем полностью за пределами экрана (ниже нижнего края)
        start_pos = QPoint(original_pos.x(), self.height() + notification.height())
        notification.move(start_pos)
        
        self.notification_slide_in = QPropertyAnimation(notification, b"pos")
        self.notification_slide_in.setDuration(1200)  # Плавное появление
        self.notification_slide_in.setStartValue(start_pos)
        self.notification_slide_in.setEndValue(original_pos)
        self.notification_slide_in.setEasingCurve(QEasingCurve.Type.OutBack)  # Эффект "отскока"
        
        # Добавляем анимации в группу и запускаем
        self.notification_animation_group.addAnimation(self.notification_fade_in)
        self.notification_animation_group.addAnimation(self.notification_slide_in)
        self.notification_animation_group.start()
        
        # Автоматически скрываем через 4 секунды с плавной анимацией
        def hide_notification():
            if hasattr(self, 'current_notification') and self.current_notification:
                # Создаем группу анимаций для плавного исчезновения
                self.notification_hide_group = QParallelAnimationGroup()
                
                # Анимация прозрачности (fade out) - очень плавное затухание
                self.notification_fade_out = QPropertyAnimation(self.current_notification, b"windowOpacity")
                self.notification_fade_out.setDuration(800)  # Увеличиваем до 0.8 секунды
                self.notification_fade_out.setStartValue(1.0)
                self.notification_fade_out.setEndValue(0.0)
                self.notification_fade_out.setEasingCurve(QEasingCurve.Type.InExpo)  # Самая плавная кривая затухания
                
                # Анимация исчезновения за нижний край экрана
                current_pos = self.current_notification.pos()
                # Уходим полностью за пределы экрана (ниже нижнего края)
                end_pos = QPoint(current_pos.x(), self.height() + self.current_notification.height())
                
                self.notification_slide_out = QPropertyAnimation(self.current_notification, b"pos")
                self.notification_slide_out.setDuration(900)  # Плавное исчезновение
                self.notification_slide_out.setStartValue(current_pos)
                self.notification_slide_out.setEndValue(end_pos)
                self.notification_slide_out.setEasingCurve(QEasingCurve.Type.InBack)  # Эффект "втягивания"
                
                # Удаляем уведомление после завершения анимации
                def cleanup_notification():
                    if hasattr(self, 'current_notification') and self.current_notification:
                        self.current_notification.deleteLater()
                        self.current_notification = None
                
                # Добавляем анимации в группу и запускаем
                self.notification_hide_group.addAnimation(self.notification_fade_out)
                self.notification_hide_group.addAnimation(self.notification_slide_out)
                self.notification_hide_group.finished.connect(cleanup_notification)
                self.notification_hide_group.start()
        
        # Создаем таймер как атрибут класса для предотвращения удаления сборщиком мусора
        self.notification_timer = QTimer()
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(hide_notification)
        self.notification_timer.start(4000)
    
    def hide_current_notification(self):
        """Принудительно скрывает текущее уведомление"""
        if hasattr(self, 'current_notification') and self.current_notification:
            # Останавливаем таймер если он активен
            if hasattr(self, 'notification_timer') and self.notification_timer.isActive():
                self.notification_timer.stop()
            
            # Создаем быструю но плавную анимацию исчезновения при клике
            self.notification_quick_hide_group = QParallelAnimationGroup()
            
            # Быстрая но плавная анимация прозрачности при клике
            self.notification_quick_fade = QPropertyAnimation(self.current_notification, b"windowOpacity")
            self.notification_quick_fade.setDuration(400)  # Увеличиваем для плавности даже при клике
            self.notification_quick_fade.setStartValue(self.current_notification.windowOpacity())
            self.notification_quick_fade.setEndValue(0.0)
            self.notification_quick_fade.setEasingCurve(QEasingCurve.Type.InExpo)  # Плавная кривая
            
            # Быстрое исчезновение за нижний край при клике
            current_pos = self.current_notification.pos()
            # При клике тоже уходим за пределы экрана, но быстрее
            end_pos = QPoint(current_pos.x(), self.height() + self.current_notification.height())
            
            self.notification_quick_slide = QPropertyAnimation(self.current_notification, b"pos")
            self.notification_quick_slide.setDuration(450)  # Быстрее чем автоматическое
            self.notification_quick_slide.setStartValue(current_pos)
            self.notification_quick_slide.setEndValue(end_pos)
            self.notification_quick_slide.setEasingCurve(QEasingCurve.Type.InBack)  # Плавная кривая
            
            # Удаляем уведомление после завершения анимации
            def cleanup_notification():
                if hasattr(self, 'current_notification') and self.current_notification:
                    self.current_notification.deleteLater()
                    self.current_notification = None
            
            # Запускаем группу анимаций
            self.notification_quick_hide_group.addAnimation(self.notification_quick_fade)
            self.notification_quick_hide_group.addAnimation(self.notification_quick_slide)
            self.notification_quick_hide_group.finished.connect(cleanup_notification)
            self.notification_quick_hide_group.start()
    
    def auto_check_updates(self):
        """Автоматическая проверка обновлений при запуске (тихая)"""
        if not UPDATER_AVAILABLE:
            return
        
        # Проверяем настройку автоматической проверки
        if not UPDATE_SETTINGS.get("auto_check", False):
            return
        
        # Проверяем, не запущена ли уже проверка
        if hasattr(self, 'auto_update_checker') and self.auto_update_checker:
            return
        
        # Создаем чекер обновлений
        self.auto_update_checker = StandardUpdateChecker(self)
        
        # Подключаем сигналы (только для доступных обновлений)
        self.auto_update_checker.update_available.connect(self.on_auto_update_available)
        
        # Запускаем тихую проверку
        self.auto_update_checker.check_for_updates(silent=True)
    
    def on_auto_update_available(self, version_info):
        """Обработка автоматически найденного обновления"""
        # Очищаем чекер
        self.auto_update_checker = None
        
        # Показываем индикатор на кнопке обновления
        if hasattr(self, 'top_bar') and hasattr(self.top_bar, 'update_btn'):
            self.top_bar.update_btn.set_update_available(True)
        
        # Показываем уведомление о доступном обновлении
        new_version = version_info.get('tag_name', 'Неизвестно')
        self.show_welcome_notification(
            f"ДОСТУПНО ОБНОВЛЕНИЕ {new_version}!\nНажмите кнопку 'Обновить' для установки"
        )
    
    def safe_show_support_dialog(self):
        """Безопасно показывает окно поддержки проекта с проверками"""
        try:
            logger.info("Вызвана функция safe_show_support_dialog")
            
            # Проверяем, что главное окно еще существует и видимо
            if not self.isVisible() or self.isMinimized():
                logger.info("Главное окно не видимо, пропускаем показ диалога поддержки")
                return
            
            # Проверяем, что нет других активных диалогов
            if hasattr(self, '_support_dialog_active') and self._support_dialog_active:
                logger.info("Диалог поддержки уже активен")
                return
            
            logger.info("Показываем диалог поддержки")
            self._support_dialog_active = True
            self.show_support_dialog()
            
        except Exception as e:
            logger.error(f"Ошибка в safe_show_support_dialog: {e}")
            logger.debug(traceback.format_exc())
            # Сбрасываем флаг в случае ошибки
            if hasattr(self, '_support_dialog_active'):
                self._support_dialog_active = False

    def show_support_dialog(self):
        """Показывает окно поддержки проекта как overlay с блюром"""
        try:
            # Создаем overlay на весь экран
            overlay = QWidget(self)
            overlay.setGeometry(self.rect())
            overlay.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                }
            """)
            
            # Создаем скроллируемую область для контента
            scroll_area = QScrollArea(overlay)
            scroll_area.setGeometry(self.rect())
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: rgba(255, 255, 255, 0.1);
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(187, 134, 252, 0.6);
                    border-radius: 4px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(187, 134, 252, 0.8);
                }
            """)
            
            # Контейнер для контента с адаптивной высотой
            content_widget = QWidget()
            # Устанавливаем адаптивную высоту для корректного отображения
            content_widget.setMinimumHeight(max(600, self.height() - 300))
            scroll_area.setWidget(content_widget)
            
            # Основной layout с уменьшенными отступами
            main_layout = QVBoxLayout(content_widget)
            main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.setContentsMargins(40, 30, 40, 30)
            main_layout.setSpacing(10)
            
            # Заголовок - увеличенный
            title = QLabel("💜 Поддержите проект")
            title.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 26px;
                    font-weight: bold;
                    text-align: center;
                    margin-bottom: 3px;
                }
            """)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(title)
            
            # Добавляем минимальное место перед текстом "Привет"
            main_layout.addSpacing(4)
            
            # Основной текст - компактный как в примере
            intro_text = QLabel("""Привет! Надеюсь, программа вам нравится.

Если вы хотите поддержать разработку, буду очень благодарен!
Программа бесплатная, поэтому я прошу вашей поддержки.

Ваши донаты помогут:
• Добавлять новые функции
• Исправлять баги быстрее
• Поддерживать программу актуальной
• Мотивировать меня :)

Способы поддержки:""")
            
            intro_text.setStyleSheet("""
                QLabel {
                    color: #e0e0e0;
                    font-size: 16px;
                    line-height: 1.9;
                    text-align: center;
                    padding: 10px;
                }
            """)
            intro_text.setWordWrap(True)
            intro_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Устанавливаем адаптивную ширину для корректного переноса
            intro_text.setMaximumWidth(min(800, self.width() - 120))
            intro_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            main_layout.addWidget(intro_text, 0, Qt.AlignmentFlag.AlignCenter)
            
            # Убираем отступ после "Способы поддержки:"
            main_layout.addSpacing(-10)
            
            # Контейнер для ссылок с минимальным spacing
            links_container = QWidget()
            links_layout = QVBoxLayout(links_container)
            links_layout.setSpacing(2)
            links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            links_layout.setContentsMargins(0, 3, 0, 3)
            
            # Boosty ссылка
            boosty_label = QLabel('🎯 Boosty: <a href="https://boosty.to/k1n1maro" style="color: #bb86fc; text-decoration: none;">https://boosty.to/k1n1maro</a>')
            boosty_label.setStyleSheet("""
                QLabel {
                    color: #e0e0e0;
                    font-size: 15px;
                    text-align: center;
                    padding: 2px;
                }
            """)
            boosty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            boosty_label.setOpenExternalLinks(True)
            links_layout.addWidget(boosty_label)
            
            # DonationAlerts ссылка
            donation_label = QLabel('🔔 DonationAlerts: <a href="https://www.donationalerts.com/r/k1n1maro" style="color: #bb86fc; text-decoration: none;">https://www.donationalerts.com/r/k1n1maro</a>')
            donation_label.setStyleSheet("""
                QLabel {
                    color: #e0e0e0;
                    font-size: 15px;
                    text-align: center;
                    padding: 2px;
                }
            """)
            donation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            donation_label.setOpenExternalLinks(True)
            links_layout.addWidget(donation_label)
            
            # Номер карты (копируемый) - разделен на две строки
            card_number_label = QLabel('💳 Номер карты: <span style="color: #bb86fc; cursor: pointer;">2202 2067 3893 4277</span>')
            card_number_label.setStyleSheet("""
                QLabel {
                    color: #e0e0e0;
                    font-size: 15px;
                    text-align: center;
                    padding: 2px;
                }
            """)
            card_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Подсказка на отдельной строке
            card_hint_label = QLabel('(нажмите чтобы скопировать)')
            card_hint_label.setStyleSheet("""
                QLabel {
                    color: #a0a0a0;
                    font-size: 13px;
                    text-align: center;
                    padding: 0px;
                }
            """)
            card_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Добавляем функцию копирования карты
            def copy_card_number():
                try:
                    clipboard = QApplication.clipboard()
                    clipboard.setText("2202206738934277")
                    # Показываем уведомление о копировании
                    card_number_label.setText('💳 Номер карты: <span style="color: #00ff88;">2202 2067 3893 4277</span>')
                    card_hint_label.setText('(скопировано!)')
                    card_hint_label.setStyleSheet("""
                        QLabel {
                            color: #00ff88;
                            font-size: 11px;
                            text-align: center;
                            padding: 0px;
                        }
                    """)
                    # Безопасный таймер - проверяем существование виджетов перед изменением
                    def reset_card_labels():
                        try:
                            if card_number_label and not card_number_label.isHidden():
                                card_number_label.setText('💳 Номер карты: <span style="color: #bb86fc;">2202 2067 3893 4277</span>')
                            if card_hint_label and not card_hint_label.isHidden():
                                card_hint_label.setText('(нажмите чтобы скопировать)')
                                card_hint_label.setStyleSheet("""
                                    QLabel {
                                        color: #a0a0a0;
                                        font-size: 11px;
                                        text-align: center;
                                        padding: 0px;
                                    }
                                """)
                        except RuntimeError:
                            # Виджет уже удален - игнорируем
                            pass
                    
                    QTimer.singleShot(2000, reset_card_labels)
                except Exception as e:
                    logger.error(f"Ошибка копирования номера карты: {e}")
            
            card_number_label.mousePressEvent = lambda event: copy_card_number()
            card_hint_label.mousePressEvent = lambda event: copy_card_number()
            
            links_layout.addWidget(card_number_label)
            links_layout.addWidget(card_hint_label)
            
            # Steam ссылка
            steam_label = QLabel('🎮 Steam профиль: <a href="https://steamcommunity.com/id/kinimaro" style="color: #bb86fc; text-decoration: none;">steamcommunity.com/id/kinimaro</a>')
            steam_label.setStyleSheet("""
                QLabel {
                    color: #e0e0e0;
                    font-size: 15px;
                    text-align: center;
                    padding: 2px;
                }
            """)
            steam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            steam_label.setOpenExternalLinks(True)
            links_layout.addWidget(steam_label)
            
            main_layout.addWidget(links_container)
            
            # Добавляем очень минимальное пространство
            main_layout.addSpacing(3)
            
            # Благодарность
            thanks_label = QLabel("Спасибо за вашу поддержку! 💜")
            thanks_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                    margin-top: 3px;
                    padding: 2px;
                }
            """)
            thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(thanks_label)
            
            # Добавляем очень минимальное пространство перед кнопкой
            main_layout.addSpacing(6)
        
            # Кнопка OK - копируем из окна ошибки обновлений (HoverLiftButton)
            close_btn = QPushButton("OK")
            close_btn.setFixedHeight(56)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #A546FF,
                        stop:0.3 #B855FF,
                        stop:0.7 #D065FF,
                        stop:1 #E06BFF);
                    
                    border-radius: 25px;
                    
                    border-top: 1px solid rgba(255, 255, 255, 0.4);
                    border-left: 1px solid rgba(255, 255, 255, 0.2);
                    border-right: 1px solid rgba(255, 255, 255, 0.1);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.2);
                    
                    color: #ffffff;
                    font-weight: 700;
                    font-size: 16px;
                    padding: 15px 30px;
                    min-height: 20px;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #B855FF,
                        stop:0.3 #C965FF,
                        stop:0.7 #E075FF,
                        stop:1 #F080FF);
                    
                    border-top: 1px solid rgba(255, 255, 255, 0.6);
                    border-left: 1px solid rgba(255, 255, 255, 0.4);
                    border-right: 1px solid rgba(255, 255, 255, 0.2);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #9540E6,
                        stop:0.3 #A650F0,
                        stop:0.7 #C060FF,
                        stop:1 #D565FF);
                    
                    border-top: 1px solid rgba(0, 0, 0, 0.3);
                    border-left: 1px solid rgba(0, 0, 0, 0.2);
                    border-right: 1px solid rgba(255, 255, 255, 0.3);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.4);
                }
            """)
            
            def close_support_dialog():
                try:
                    # Сбрасываем флаг активности диалога
                    if hasattr(self, '_support_dialog_active'):
                        self._support_dialog_active = False
                    overlay.deleteLater()
                except Exception as e:
                    logger.error(f"Ошибка закрытия диалога поддержки: {e}")
            
            close_btn.clicked.connect(close_support_dialog)
            
            # Центрируем кнопку
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            btn_layout.addWidget(close_btn)
            btn_layout.addStretch()
            main_layout.addLayout(btn_layout)
            
            # Начинаем с прозрачности 0 для плавного появления
            overlay.setWindowOpacity(0.0)
            overlay.show()
            overlay.raise_()
            
            # Плавное появление overlay
            overlay_fade_in = QPropertyAnimation(overlay, b"windowOpacity")
            overlay_fade_in.setDuration(400)
            overlay_fade_in.setStartValue(0.0)
            overlay_fade_in.setEndValue(1.0)
            overlay_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            overlay_fade_in.start()
            
            # Применяем блюр к основному интерфейсу с анимацией
            try:
                self.support_blur_effect = self.animate_blur_in(self.centralWidget(), target_radius=15, duration=400)
            except Exception as e:
                logger.error(f"Ошибка применения блюра: {e}")
                self.support_blur_effect = None
            
            # При закрытии overlay удаляем блюр с анимацией
            def cleanup_blur():
                try:
                    if hasattr(self, 'support_blur_effect') and self.support_blur_effect:
                        self.animate_blur_out(self.centralWidget(), self.support_blur_effect, duration=300)
                        # Удаляем ссылку после завершения анимации
                        QTimer.singleShot(350, lambda: delattr(self, 'support_blur_effect') if hasattr(self, 'support_blur_effect') else None)
                    # Сбрасываем флаг активности диалога
                    if hasattr(self, '_support_dialog_active'):
                        self._support_dialog_active = False
                except Exception as e:
                    logger.error(f"Ошибка очистки блюра: {e}")
                    # В случае ошибки принудительно убираем эффект
                    try:
                        self.centralWidget().setGraphicsEffect(None)
                        if hasattr(self, '_support_dialog_active'):
                            self._support_dialog_active = False
                    except:
                        pass
            
            overlay.destroyed.connect(cleanup_blur)
            
        except Exception as e:
            logger.error(f"Критическая ошибка в show_support_dialog: {e}")
            logger.debug(traceback.format_exc())
            # Сбрасываем флаг активности диалога в случае ошибки
            if hasattr(self, '_support_dialog_active'):
                self._support_dialog_active = False
    
    def show_beta_warning_dialog(self):
        """Показывает приветственное окно в стиле авторизации"""
        # Проверяем, не показано ли уже окно
        if hasattr(self, '_welcome_dialog_shown') and self._welcome_dialog_shown:
            return
        
        self._welcome_dialog_shown = True
        
        # Создаем overlay точно как WelcomeBackOverlay
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        
        # Всегда применяем блюр для приветственного окна
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(15)
        self.centralWidget().setGraphicsEffect(blur_effect)
        # Сохраняем ссылку на blur_effect для анимации
        self.blur_effect = blur_effect
        
        # Основной layout
        main_layout = QVBoxLayout(overlay)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        # Центральная карточка в том же стиле что и авторизация
        welcome_card = QFrame()
        welcome_card.setObjectName("authCard")  # Используем тот же стиль что и у авторизации
        welcome_card.setFixedSize(600, 700)  # Тот же размер что и у авторизации
        
        card_layout = QVBoxLayout(welcome_card)
        card_layout.setContentsMargins(50, 30, 50, 30)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Приветственное описание с новым текстом (без заголовка)
        intro_text = QLabel("""<div style="text-align: center;">
<p style="font-size: 28px;"><b>🚀 Добро пожаловать в RU-MINETOOLS!</b></p>

<p style="font-size: 14px;">Спасибо, что ты тут!</p>

<p style="font-size: 14px;"><b>⚠️ ВАЖНОЕ УВЕДОМЛЕНИЕ:</b> Это первая публичная версия приложения для перевода модов и квестов Minecraft. Возможны баги, неполадки и неожиданные ошибки в работе программы.</p>

<p style="font-size: 14px;"><b>🔧 Если вы заметили ошибки или проблемы:</b> Опишите подробно что вы делали когда произошла ошибка, сделайте скриншот экрана если это возможно, напишите мне в Telegram: <a href="https://t.me/angel_its_me" style="color: #4fc3f7; text-decoration: none;">@angel_its_me</a>. Ваша обратная связь очень важна для улучшения приложения!</p>
</div>""")
        
        intro_text.setObjectName("overlayDescription")
        intro_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_text.setWordWrap(True)
        intro_text.setOpenExternalLinks(True)  # Делаем ссылки кликабельными
        card_layout.addWidget(intro_text)
        
        # Уменьшаем отступ между текстом и кнопками
        card_layout.addSpacing(-25)  # Уменьшаем отступ еще больше
        
        # Кнопки точно как в WelcomeBackOverlay
        # Флаг для предотвращения повторного закрытия
        dialog_closing = False
        
        def close_dialog():
            nonlocal dialog_closing
            if dialog_closing:
                return  # Предотвращаем повторное закрытие
            dialog_closing = True
            
            # Сбрасываем флаг показа окна для возможности повторного показа в будущем
            self._welcome_dialog_shown = False
            
            # НЕ убираем блюр - передаем его окну авторизации
            
            # Немедленно скрываем и удаляем overlay
            overlay.hide()
            overlay.deleteLater()
            
            # Показываем окно авторизации после закрытия приветственного
            QTimer.singleShot(100, self.show_auth_overlay)
        
        def open_support():
            import webbrowser
            webbrowser.open("https://t.me/angel_its_me")  # Актуальный username поддержки
            close_dialog()
        
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(-20)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Главная кнопка продолжения
        ok_button = NeonGlowButton("ПОНЯТНО, НАЧНЕМ!")
        ok_button.clicked.connect(close_dialog)
        
        # Запускаем эффект появления кнопки
        QTimer.singleShot(500, ok_button.fade_in)
        ok_button.start_pulse()
        
        buttons_layout.addWidget(ok_button)
        
        # Добавляем отступ между кнопками
        buttons_layout.addSpacing(-30)
        
        # Кнопка поддержки
        support_button = NeonGlowButton("Написать в поддержку")
        support_button.setObjectName("neonGlowBtnGray")
        support_button.clicked.connect(open_support)
        buttons_layout.addWidget(support_button)
        
        card_layout.addLayout(buttons_layout)
        
        # Добавляем отрицательный отступ перед статусом
        card_layout.addSpacing(-25)
        
        # Статус
        status_label = QLabel("Нажмите 'ПОНЯТНО, НАЧНЕМ!' для продолжения")
        status_label.setObjectName("overlayStatus")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setWordWrap(True)
        card_layout.addWidget(status_label)
        
        main_layout.addWidget(welcome_card)
        
        # Применяем те же стили что и у авторизации
        overlay.setStyleSheet(self.get_overlay_styles())
        
        # Показываем overlay
        overlay.show()
        overlay.raise_()
    
    def show_auth_overlay(self):
        """Показывает окно авторизации после приветственного окна"""
        # Создаем соответствующий overlay в зависимости от статуса авторизации
        if hasattr(self, '_pending_user_data') and self._pending_user_data:
            # Пользователь уже авторизован - показываем приветственный экран
            self.auth_overlay = WelcomeBackOverlay(self, self._pending_user_data)
        else:
            # Пользователь не авторизован - показываем экран авторизации
            self.auth_overlay = TelegramAuthOverlay(self)
        
        # Начинаем с прозрачности 0 для плавного появления
        self.auth_overlay.setWindowOpacity(0.0)
        self.auth_overlay.show()
        
        # Поднимаем overlay на передний план
        self.auth_overlay.raise_()
        
        # Плавное появление overlay
        self.overlay_fade_in = QPropertyAnimation(self.auth_overlay, b"windowOpacity")
        self.overlay_fade_in.setDuration(400)
        self.overlay_fade_in.setStartValue(0.0)
        self.overlay_fade_in.setEndValue(1.0)
        self.overlay_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.overlay_fade_in.start()
        
        # Подключаем сигнал для безопасного удаления блюра
        self.auth_overlay.destroyed.connect(self.remove_blur_effect)
    
    def get_overlay_styles(self):
        """Стили без подложки, только текст на прозрачном фоне"""
        return """
        QWidget {
            background-color: transparent;
        }
        
        #authCard {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
        
        #overlayTitle {
            color: #ffffff;
            font-size: 42px;
            font-weight: bold;
            margin: 8px 0px;
        }
        
        #overlaySubtitle {
            color: #b0b0b0;
            font-size: 16px;
            margin-bottom: 15px;
        }
        
        #overlayDescription {
            color: #e0e0e0;
            font-size: 16px;
            line-height: 1.6;
            margin: 15px 0px;
            padding: 10px;
        }
        
        #overlayStatus {
            color: #888888;
            font-size: 13px;
            margin-top: 10px;
        }
        
        /* Стили кнопок как в окне авторизации */
        #neonGlowBtn {
            background: transparent;
            border: none;
        }
        
        #neonGlowBtnInner {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #A546FF,
                stop:0.3 #B855FF,
                stop:0.7 #D065FF,
                stop:1 #E06BFF);
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            outline: 8px solid rgba(165, 70, 255, 0.3);
            outline-offset: 4px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnInnerHover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #B855FF,
                stop:0.3 #C965FF,
                stop:0.7 #E075FF,
                stop:1 #F080FF);
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 1px solid rgba(255, 255, 255, 0.4);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            outline: 12px solid rgba(165, 70, 255, 0.5);
            outline-offset: 6px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnGray {
            background: transparent;
            border: none;
        }
        
        #neonGlowBtnGray #neonGlowBtnInner {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6b7280,
                stop:0.3 #7c8591,
                stop:0.7 #9ca3af,
                stop:1 #a1a8b6);
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            outline: 8px solid rgba(107, 114, 128, 0.3);
            outline-offset: 4px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnGray #neonGlowBtnInnerHover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7c8591,
                stop:0.3 #8d94a2,
                stop:0.7 #a1a8b6,
                stop:1 #b5bcc7);
            border-radius: 25px;
            border-top: 1px solid rgba(255, 255, 255, 0.6);
            border-left: 1px solid rgba(255, 255, 255, 0.4);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            outline: 12px solid rgba(107, 114, 128, 0.5);
            outline-offset: 6px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        /* Стили для pressed состояния */
        #neonGlowBtnInnerPressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9540E6,
                stop:0.3 #A650F0,
                stop:0.7 #C060FF,
                stop:1 #D565FF);
            border-radius: 25px;
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(0, 0, 0, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            outline: 6px solid rgba(165, 70, 255, 0.4);
            outline-offset: 2px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        
        #neonGlowBtnGray #neonGlowBtnInnerPressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #5a6169,
                stop:0.3 #6b7280,
                stop:0.7 #7c8591,
                stop:1 #8d94a2);
            border-radius: 25px;
            border-top: 1px solid rgba(0, 0, 0, 0.3);
            border-left: 1px solid rgba(0, 0, 0, 0.2);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            outline: 6px solid rgba(107, 114, 128, 0.4);
            outline-offset: 2px;
            color: #ffffff;
            font-weight: 700;
            font-size: 18px;
            padding: 18px 35px;
            min-height: 25px;
        }
        """
    
    def setup_animations(self):
        """Настройка анимаций для окна - отключено"""
        pass  # Анимации при запуске отключены
        
    def showEvent(self, event):
        """Показ окна без анимации"""
        super().showEvent(event)
        # Анимации при запуске отключены - окно появляется сразу
        
        # Позиционируем кнопки управления окном
        self.position_main_window_controls()
    
    def resizeEvent(self, event):
        """Обновляем размер overlay при изменении размера окна"""
        super().resizeEvent(event)
        
        # Обновляем размер overlay если он существует
        if hasattr(self, 'auth_overlay') and self.auth_overlay:
            self.auth_overlay.setGeometry(self.centralWidget().rect())
        
        # Обновляем позицию кнопок управления главным окном
        self.position_main_window_controls()
    
    def closeEvent(self, event):
        """Обработка закрытия приложения - полная очистка ресурсов"""
        try:
            # Останавливаем все таймеры уведомлений
            if hasattr(self, 'notification_timer') and self.notification_timer:
                self.notification_timer.stop()
                self.notification_timer.deleteLater()
                self.notification_timer = None
            
            # Останавливаем все анимации уведомлений
            if hasattr(self, 'notification_fade_in') and self.notification_fade_in:
                self.notification_fade_in.stop()
                self.notification_fade_in.deleteLater()
                self.notification_fade_in = None
            
            if hasattr(self, 'notification_fade_out') and self.notification_fade_out:
                self.notification_fade_out.stop()
                self.notification_fade_out.deleteLater()
                self.notification_fade_out = None
            
            # Удаляем текущее уведомление
            if hasattr(self, 'current_notification') and self.current_notification:
                self.current_notification.deleteLater()
                self.current_notification = None
            
            # Останавливаем таймеры обновлений
            if hasattr(self, 'update_timer') and self.update_timer:
                self.update_timer.stop()
                self.update_timer.deleteLater()
                self.update_timer = None
            
            # Останавливаем воркеры перевода
            if hasattr(self, 'translation_worker') and self.translation_worker:
                if self.translation_worker.isRunning():
                    self.translation_worker.cancel()
                    self.translation_worker.wait(3000)  # Ждем максимум 3 секунды
                    if self.translation_worker.isRunning():
                        self.translation_worker.terminate()
                self.translation_worker = None
            
            # Очищаем все активные диалоги
            if hasattr(self, '_active_update_dialog'):
                self._active_update_dialog = False
            
            if hasattr(self, '_active_update_process'):
                self._active_update_process = False
            
            # Очищаем таймер автоматического закрытия
            if hasattr(self, '_close_timer') and self._close_timer:
                self._close_timer.stop()
                self._close_timer.deleteLater()
                self._close_timer = None
            
            # Очищаем кастомный tooltip
            if hasattr(self, 'custom_tooltip') and self.custom_tooltip:
                self.custom_tooltip.deleteLater()
                self.custom_tooltip = None
            
        except Exception as e:
            logger.error(f"Ошибка при очистке ресурсов: {e}")
        
        # Принимаем событие закрытия
        event.accept()
        
        # Принудительно завершаем приложение через небольшую задержку
        QTimer.singleShot(100, self.force_quit_application)
    
    def force_quit_application(self):
        """Принудительно завершает приложение без ошибок PyInstaller"""
        try:
            # Для PyInstaller - используем os._exit() чтобы избежать ошибки DLL
            if getattr(sys, 'frozen', False):
                # Даем время на завершение всех операций
                QTimer.singleShot(50, lambda: os._exit(0))
            else:
                # Для обычного Python
                app = QApplication.instance()
                if app:
                    app.quit()
                else:
                    sys.exit(0)
                    
        except Exception as e:
            logger.error(f"Ошибка при завершении: {e}")
            # В крайнем случае используем os._exit()
            os._exit(0)
    
    def mouseMoveEvent(self, event):
        """Обработчик движения мыши для автоматического скрытия tooltip'ов"""
        # Если есть активный tooltip, проверяем, не ушла ли мышь далеко от него
        if hasattr(self, 'custom_tooltip') and self.custom_tooltip and self.custom_tooltip.isVisible():
            # Получаем глобальную позицию мыши
            global_pos = self.mapToGlobal(event.pos())
            
            # Получаем геометрию tooltip'а
            tooltip_rect = self.custom_tooltip.geometry()
            
            # Добавляем буферную зону вокруг tooltip'а
            buffer = 50
            expanded_rect = tooltip_rect.adjusted(-buffer, -buffer, buffer, buffer)
            
            # Если мышь вышла за пределы буферной зоны, скрываем tooltip
            if not expanded_rect.contains(global_pos):
                self.hide_smooth_tooltip()
        
        super().mouseMoveEvent(event)

def main():
    """Главная функция приложения"""
    # Настраиваем DPI для четкого отображения текста
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Round)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Настраиваем правильное завершение приложения
    app.setQuitOnLastWindowClosed(True)
    
    # Максимальное сглаживание для всех элементов интерфейса
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        # Включаем сглаживание для всех виджетов
        app.setAttribute(Qt.ApplicationAttribute.AA_SynthesizeMouseForUnhandledTouchEvents, True)
        # Улучшенное сглаживание текста
        app.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
        # Сглаживание для кнопок и элементов управления
        app.setAttribute(Qt.ApplicationAttribute.AA_CompressHighFrequencyEvents, True)
    except AttributeError:
        pass  # Атрибуты могут отсутствовать в некоторых версиях
    
    # Дополнительные настройки для сглаживания
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)
        # Включаем программное сглаживание если аппаратное недоступно
        app.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, False)
    except AttributeError:
        pass
    
    # Загружаем пользовательский шрифт с правильными настройками качества
    font_path = str(get_asset_path("sans3.ttf"))
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                font_family = font_families[0]
                # Устанавливаем шрифт для всего приложения с максимальным сглаживанием
                app_font = QFont(font_family)
                app_font.setPointSize(12)  # Увеличиваем размер для лучшей видимости
                app_font.setWeight(QFont.Weight.Normal)  # Устанавливаем нормальную толщину
                app_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)  # Отключаем хинтинг для мягкого сглаживания
                app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)  # Максимальное сглаживание
                app.setFont(app_font)
        else:
            logger.warning("Ошибка загрузки шрифта sans3.ttf")
    else:
        logger.warning(f"Файл {font_path} не найден!")
        logger.warning("ВНИМАНИЕ: Пользовательский шрифт не загружен, используется системный шрифт по умолчанию")
    
    # Применяем стили с загруженным шрифтом
    loaded_font_name = app.font().family()  # Получаем имя загруженного шрифта
    app.setStyleSheet(ModernStyles.get_main_styles(loaded_font_name))
    
    # Создаем и показываем главное окно сразу
    window = None
    try:
        window = ModernGUIInterface()
        window.show()
        
        # Запускаем приложение
        exit_code = app.exec()
        
    except Exception as e:
        logger.error(f"Критическая ошибка приложения: {e}")
        exit_code = 1
    
    finally:
        # Принудительная очистка ресурсов
        try:
            if window:
                window.deleteLater()
            
            # Обрабатываем все отложенные события
            app.processEvents()
            
            # Очищаем все оставшиеся объекты
            app.deleteLater()
            
        except Exception as e:
            logger.error(f"Ошибка при финальной очистке: {e}")
    
    # Специальное завершение для PyInstaller
    if getattr(sys, 'frozen', False):
        os._exit(exit_code)
    else:
        # Завершаем процесс обычным способом
        sys.exit(exit_code)

# ДЕМОНСТРАЦИЯ GLASSMORPHISM PROGRESS BAR

def demo_glassmorphism_progress():
    """
    Демонстрация современного glassmorphism прогресс-бара
    
    Использование:
    progress = GlassmorphismProgressBar()
    progress.setText("Загрузка файлов...")
    progress.setMaximum(100)
    progress.setValue(45)  # Анимированное изменение
    progress.setDarkTheme(True)  # Темная тема
    """
    
    app = QApplication([])
    
    # Создаем окно для демонстрации
    window = QWidget()
    window.setWindowTitle("Glassmorphism Progress Bar Demo")
    window.setFixedSize(500, 300)
    window.setStyleSheet("""
        QWidget {
            background: qlineargradient(45deg, 
                #1a1a2e 0%, 
                #16213e 50%, 
                #0f3460 100%);
        }
    """)
    
    layout = QVBoxLayout(window)
    layout.setSpacing(30)
    layout.setContentsMargins(50, 50, 50, 50)
    
    # Заголовок
    title = QLabel("🎨 Glassmorphism Progress Bar")
    title.setStyleSheet("""
        color: white;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    """)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)
    
    # Прогресс-бар
    progress = GlassmorphismProgressBar()
    progress.setText("Обработка файлов...")
    progress.setMaximum(100)
    layout.addWidget(progress)
    
    # Кнопки управления
    controls = QWidget()
    controls_layout = QHBoxLayout(controls)
    
    # Кнопка запуска
    start_btn = QPushButton("▶ Запустить")
    start_btn.setStyleSheet("""
        QPushButton {
            background: rgba(106, 227, 255, 0.2);
            border: 1px solid rgba(106, 227, 255, 0.5);
            border-radius: 8px;
            color: white;
            padding: 10px 20px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: rgba(106, 227, 255, 0.3);
        }
    """)
    
    # Кнопка сброса
    reset_btn = QPushButton("⟲ Сброс")
    reset_btn.setStyleSheet(start_btn.styleSheet())
    
    # Кнопка темы
    theme_btn = QPushButton("🌙 Тема")
    theme_btn.setStyleSheet(start_btn.styleSheet())
    
    controls_layout.addWidget(start_btn)
    controls_layout.addWidget(reset_btn)
    controls_layout.addWidget(theme_btn)
    layout.addWidget(controls)
    
    # Логика управления
    timer = QTimer()
    current_value = 0
    is_dark = True
    
    def update_progress():
        nonlocal current_value
        current_value += 2
        progress.setValue(current_value)
        progress.setText(f"Обработано: {current_value}%")
        
        if current_value >= 100:
            timer.stop()
            progress.setText("Завершено!")
    
    def start_demo():
        nonlocal current_value
        current_value = 0
        timer.start(50)  # Обновление каждые 50ms
    
    def reset_demo():
        timer.stop()
        progress.setValue(0)
        progress.setText("Готов к запуску...")
    
    def toggle_theme():
        nonlocal is_dark
        is_dark = not is_dark
        progress.setDarkTheme(is_dark)
        theme_btn.setText("🌙 Темная" if is_dark else "☀ Светлая")
    
    # Подключаем события
    timer.timeout.connect(update_progress)
    start_btn.clicked.connect(start_demo)
    reset_btn.clicked.connect(reset_demo)
    theme_btn.clicked.connect(toggle_theme)
    
    # Инициализация
    reset_demo()
    
    window.show()
    app.exec()


    # МЕТОДЫ ДЛЯ РАБОТЫ С JAR ПЕРЕВОДАМИ
    
    def browse_jar_file(self):
        """Выбор JAR файла для перевода"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите JAR файл мода",
            "",
            "JAR файлы (*.jar);;Все файлы (*)"
        )
        
        if file_path:
            self.jar_path_input.setText(file_path)
            
            # Обновляем лог
            welcome_msg = f"""🎯 Переводчик JAR модов Minecraft

📁 Выбран файл: {Path(file_path).name}

🚀 Нажмите "Начать перевод" для запуска
            """
            self.jar_log.setPlainText(welcome_msg.strip())
    
    def browse_jar_folder(self):
        """Выбор папки с JAR файлами для перевода"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с JAR модами",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.jar_path_input.setText(folder_path)
            
            # Подсчитываем JAR файлы
            jar_files = list(Path(folder_path).glob("*.jar"))
            
            # Обновляем лог
            welcome_msg = f"""🎯 Переводчик JAR модов Minecraft

📁 Выбрана папка: {Path(folder_path).name}
🔍 Найдено JAR файлов: {len(jar_files)}

🚀 Нажмите "Начать перевод" для запуска
            """
            self.jar_log.setPlainText(welcome_msg.strip())
    
    def start_jar_translation(self):
        """Запуск перевода JAR модов"""
        input_path = self.jar_path_input.text().strip()
        
        if not input_path:
            QMessageBox.warning(self, "Ошибка", "Выберите JAR файл или папку с модами!")
            return
        
        if not Path(input_path).exists():
            QMessageBox.warning(self, "Ошибка", "Указанный путь не существует!")
            return
        
        # Диалог выбора режима перевода
        reply = QMessageBox.question(
            self,
            "Выберите режим перевода",
            "Как обработать переведенные файлы?\n\n"
            "🔄 ДА - Заменить оригинальные файлы\n"
            "📁 НЕТ - Создать папку 'translated' в той же директории\n\n"
            "Рекомендуется создать отдельную папку для безопасности.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        # Определяем выходную папку в зависимости от выбора
        input_path_obj = Path(input_path)
        if reply == QMessageBox.StandardButton.Yes:
            # Заменить оригиналы - выходная папка та же что и входная
            if input_path_obj.is_file():
                output_path = str(input_path_obj.parent)
            else:
                output_path = input_path
            replace_original = True
        else:
            # Создать папку translated
            if input_path_obj.is_file():
                output_path = str(input_path_obj.parent / "translated")
            else:
                output_path = str(input_path_obj / "translated")
            replace_original = False
        
        # Создаем выходную папку если её нет
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # Подготавливаем аргументы для CLI скрипта (все опции включены по умолчанию)
        args = [
            "--input", input_path,
            "--output", output_path,
            "--src", "en_us",  # Всегда переводим с английского
            "--dst", "ru_ru",  # Всегда переводим на русский
            "--backend", "google",
            "--workers", "2",
            "--translate-patchouli",  # Включено по умолчанию
            "--translate-advancements"  # Включено по умолчанию
        ]
        
        if replace_original:
            args.append("--replace-original")
        
        # Запускаем воркер
        self.jar_translation_worker = JarTranslationWorker(args)
        self.jar_translation_worker.progress_updated.connect(self.on_jar_progress_update)
        self.jar_translation_worker.log_message.connect(self.on_jar_log_message)
        self.jar_translation_worker.finished.connect(self.on_jar_translation_finished)
        
        # Обновляем UI
        self.jar_translate_btn.setEnabled(False)
        self.jar_translate_btn.setText("⏳ Переводим...")
        self.jar_progress.setText("Инициализация перевода...")
        self.jar_progress.setValue(0)
        
        self.jar_log.append("🚀 Запуск перевода JAR модов...")
        self.jar_log.append(f"📥 Источник: {input_path}")
        self.jar_log.append(f"📤 Вывод: {output_path}")
        self.jar_log.append(f"🌐 Языки: en_us → ru_ru")
        self.jar_log.append(f"⚙️ Режим: {'Замена оригиналов' if replace_original else 'Создание новых файлов'}")
        self.jar_log.append(f"📚 Patchouli: включено")
        self.jar_log.append(f"🏆 Достижения: включено")
        self.jar_log.append("")
        
        self.jar_translation_worker.start()
        
        self.jar_log.append("🚀 Запуск перевода JAR модов...")
        self.jar_log.append(f"📥 Источник: {input_path}")
        self.jar_log.append(f"📤 Вывод: {output_path}")
        self.jar_log.append(f"🌐 Языки: {self.jar_src_lang.currentText()} → {self.jar_dst_lang.currentText()}")
        self.jar_log.append("")
        
        self.jar_translation_worker.start()
    
    def on_jar_progress_update(self, progress, message):
        """Обновление прогресса перевода JAR с throttling"""
        # Добавляем throttling для предотвращения "прыжков" прогресс-бара
        current_time = time.time()
        
        # Инициализируем атрибуты throttling если их нет
        if not hasattr(self, '_last_progress_update_time_2'):
            self._last_progress_update_time_2 = 0
            self._last_progress_value_2 = -1
        
        # Минимальный интервал между обновлениями GUI (50ms)
        min_gui_update_interval = 0.05
        time_since_last_update = current_time - self._last_progress_update_time_2
        
        # Обновляем только если прошло достаточно времени ИЛИ прогресс значительно изменился
        should_update_gui = (
            time_since_last_update >= min_gui_update_interval or
            abs(progress - self._last_progress_value_2) >= 5 or  # Изменение на 5% или больше
            progress == 100 or  # Всегда обновляем при 100%
            progress == 0       # Всегда обновляем при 0% (начало нового мода)
        )
        
        if should_update_gui:
            self.jar_progress.setValue(progress)
            self._last_progress_update_time_2 = current_time
            self._last_progress_value_2 = progress
        self.jar_progress.setText(message)
    
    def on_jar_log_message(self, message):
        """Добавление сообщения в лог JAR перевода"""
        self.jar_log.append(message)
        # Автопрокрутка к концу
        scrollbar = self.jar_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_jar_translation_finished(self, success, stats):
        """Завершение перевода JAR модов"""
        try:
            logger.info(f"on_jar_translation_finished (ModernGUIInterface) вызван: success={success}, stats={stats}")
            
            # Возвращаем кнопку в исходное состояние
            self.reset_jar_translate_button()
            
            if success:
                logger.info("Условие success=True выполнено для JAR (ModernGUIInterface), показываем результаты")
                self.jar_progress.setValue(100)
                self.jar_progress.setText("✅ Перевод завершен успешно!")
                
                self.jar_log.append("")
                self.jar_log.append("🎉 ПЕРЕВОД ЗАВЕРШЕН!")
                self.jar_log.append("=" * 50)
                self.jar_log.append(f"📊 Статистика:")
                self.jar_log.append(f"   • JAR обработано: {stats.get('jars_processed', 0)}")
                self.jar_log.append(f"   • JAR с ошибками: {stats.get('jars_failed', 0)}")
                self.jar_log.append(f"   • Файлов переведено: {stats.get('files_translated', 0)}")
                self.jar_log.append(f"   • Строк переведено: {stats.get('strings_translated', 0)}")
                self.jar_log.append(f"   • Строк пропущено: {stats.get('strings_skipped', 0)}")
                if 'cache_hits' in stats:
                    self.jar_log.append(f"   • Попаданий в кэш: {stats['cache_hits']}")
                self.jar_log.append("=" * 50)
                
                # Сбрасываем состояние кнопки паузы
                self.jar_pause_btn.setText("Пауза")
                
                # Сохраняем проект в историю
                jar_path = self.jar_path_input.text().strip()
                if jar_path:
                    if os.path.isfile(jar_path):
                        jar_name = os.path.basename(jar_path)
                        self.save_project_to_history(
                            f"JAR: {jar_name}",
                            os.path.dirname(jar_path),
                            "jar"
                        )
                    else:
                        # Если это папка с несколькими JAR
                        folder_name = os.path.basename(jar_path)
                        self.save_project_to_history(
                            f"JAR папка: {folder_name}",
                            jar_path,
                            "jar_folder"
                        )
                
                # Показываем детальное окно итогов
                self.show_translation_summary(stats, success)
                
                # Показываем окно поддержки после успешного перевода с задержкой
                logger.info("Планируем показ окна поддержки для JAR (ModernGUIInterface) через 1500мс")
                QTimer.singleShot(1500, self.safe_show_support_dialog)
                
            else:
                self.jar_progress.setValue(0)
                self.jar_progress.setText("❌ Ошибка при переводе")
                
                self.jar_log.append("")
                self.jar_log.append("❌ ПЕРЕВОД ЗАВЕРШЕН С ОШИБКАМИ")
                
                # Показываем детальное окно итогов даже при ошибках
                self.show_translation_summary(stats, success)
                
        except Exception as e:
            logger.error(f"Ошибка в on_jar_translation_finished: {e}")
            logger.debug(traceback.format_exc())
            # Все равно сбрасываем кнопку в исходное состояние
            try:
                self.reset_jar_translate_button()
                self.jar_pause_btn.setText("Пауза")
            except:
                pass
    
    def setup_jar_translation_button_animations(self):
        """Настройка анимаций для кнопки перевода JAR (как у кнопки квестов)"""
        # Анимация fade-in при наведении
        self.jar_fade_in_animation = QPropertyAnimation(self.jar_translate_btn, b"windowOpacity")
        self.jar_fade_in_animation.setDuration(200)
        self.jar_fade_in_animation.setStartValue(0.8)
        self.jar_fade_in_animation.setEndValue(1.0)
        self.jar_fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Анимация пульсации
        self.jar_pulse_animation = QPropertyAnimation(self.jar_translate_btn, b"geometry")
        self.jar_pulse_animation.setDuration(1000)
        self.jar_pulse_animation.setLoopCount(-1)  # Бесконечный цикл
        self.jar_pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Подключаем события
        self.jar_translate_btn.enterEvent = lambda event: self.start_jar_translation_fade_in()
        self.jar_translate_btn.leaveEvent = lambda event: None  # Оставляем как есть при уходе
    
    def start_jar_translation_fade_in(self):
        """Запуск анимации fade-in для кнопки JAR перевода"""
        if hasattr(self, 'jar_fade_in_animation'):
            self.jar_fade_in_animation.start()
    
    def start_jar_translation_pulse(self):
        """Запуск анимации пульсации для кнопки JAR перевода"""
        if hasattr(self, 'jar_pulse_animation'):
            original_geometry = self.jar_translate_btn.geometry()
            expanded_geometry = QRect(
                original_geometry.x() - 2,
                original_geometry.y() - 1,
                original_geometry.width() + 4,
                original_geometry.height() + 2
            )
            
            self.jar_pulse_animation.setStartValue(original_geometry)
            self.jar_pulse_animation.setEndValue(expanded_geometry)
            self.jar_pulse_animation.start()
    
    def stop_jar_translation(self):
        """Остановка перевода JAR модов"""
        if hasattr(self, 'jar_translation_worker') and self.jar_translation_worker:
            self.jar_translation_worker.stop()
            self.jar_log.append("⏹️ Остановка перевода...")
            
            # Сброс UI
            self.jar_translate_btn.setEnabled(True)
            self.reset_jar_translate_button()  # Используем функцию сброса
            self.jar_progress.setText("Остановлено пользователем")
    
    def clear_jar_log(self):
        """Очистка лога JAR перевода"""
        self.jar_log.clear()
        
        # Добавляем приветственное сообщение
        welcome_msg = """🎯 Переводчик JAR модов Minecraft

📁 Выберите JAR файл(ы) → 🚀 Нажмите "Начать перевод"
        """
        self.jar_log.setPlainText(welcome_msg.strip())

    def refresh_cache_info(self):
        """Обновляет информацию о кэше переводов"""
        try:
            cache_file = "translation_cache.pkl"
            
            if os.path.exists(cache_file):
                # Получаем размер файла
                file_size = os.path.getsize(cache_file)
                size_mb = file_size / (1024 * 1024)
                
                # Загружаем кэш для подсчета записей
                try:
                    import pickle
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                    cache_count = len(cache_data)
                    
                    # Получаем дату последнего изменения
                    import datetime
                    mod_time = os.path.getmtime(cache_file)
                    mod_date = datetime.datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
                    
                    info_text = f"Записей в кэше: {cache_count:,}\nРазмер файла: {size_mb:.1f} МБ\nПоследнее обновление: {mod_date}"
                    
                except Exception as e:
                    info_text = f"Размер файла: {size_mb:.1f} МБ\nОшибка чтения: {str(e)}"
            else:
                info_text = "Кэш пуст (файл не найден)\nКэш создастся после первого перевода"
            
            self.cache_info_label.setText(info_text)
            
        except Exception as e:
            self.cache_info_label.setText(f"Ошибка получения информации: {str(e)}")
    
    def open_cache_folder(self):
        """Открывает папку с файлом кэша"""
        try:
            cache_file = "translation_cache.pkl"
            cache_dir = os.path.dirname(os.path.abspath(cache_file))
            
            import subprocess
            import sys
            if sys.platform == "win32":
                subprocess.run(["explorer", cache_dir])
            elif sys.platform == "darwin":
                subprocess.run(["open", cache_dir])
            else:
                subprocess.run(["xdg-open", cache_dir])
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{str(e)}")
    
    def clear_translation_cache(self):
        """Очищает кэш переводов с подтверждением"""
        # Получаем информацию о кэше для диалога
        cache_file = "translation_cache.pkl"
        cache_info = "Кэш не найден"
        
        if os.path.exists(cache_file):
            try:
                file_size = os.path.getsize(cache_file)
                size_mb = file_size / (1024 * 1024)
                
                import pickle
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                cache_count = len(cache_data)
                
                cache_info = f"{cache_count:,} переводов ({size_mb:.1f} МБ)"
            except:
                cache_info = f"Файл существует ({file_size} байт)"
        
        # Диалог подтверждения
        reply = QMessageBox.question(
            self,
            "🗑️ Очистка кэша переводов",
            f"Вы уверены что хотите очистить кэш переводов?\n\n"
            f"📊 Текущий кэш: {cache_info}\n\n"
            f"⚠️ ВНИМАНИЕ:\n"
            f"• Все сохраненные переводы будут удалены\n"
            f"• Первые переводы после очистки будут медленнее\n"
            f"• Это действие нельзя отменить\n\n"
            f"💡 Кэш ускоряет повторные переводы в 10-50 раз!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем файл кэша
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                # Очищаем кэш в памяти если модуль загружен
                try:
                    import sys
                    if 'translate_jar_simple' in sys.modules:
                        from translate_jar_simple import TRANSLATION_CACHE
                        TRANSLATION_CACHE.clear()
                except:
                    pass
                
                # Обновляем информацию
                self.refresh_cache_info()
                
                QMessageBox.information(
                    self, 
                    "✅ Готово", 
                    "Кэш переводов успешно очищен!\n\n"
                    "🔄 Новый кэш начнет создаваться при следующем переводе."
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "❌ Ошибка",
                    f"Не удалось очистить кэш:\n{str(e)}"
                )


# МЕТОДЫ УПРАВЛЕНИЯ КЭШЕМ

# Эти методы должны быть в классе ContentArea, но добавляем их здесь временно
# и потом переместим в правильное место

# ВОРКЕР ДЛЯ ПЕРЕВОДА JAR МОДОВ

class SimpleJarTranslationWorker(QThread):
    """Простой воркер для перевода JAR модов на основе translate_jar_simple.py"""
    
    progress_updated = pyqtSignal(int, str)  # progress, message
    log_message = pyqtSignal(str)  # message
    log_colored_message = pyqtSignal(str)  # colored message
    update_mod_line = pyqtSignal(int, str, str)  # jar_index, mod_name, status (для упорядоченного отображения)
    api_warning = pyqtSignal(str)  # API warning message
    finished = pyqtSignal(bool, dict)  # success, stats
    
    def __init__(self, input_path, output_path, replace_original=False, selected_files=None, analysis=None, threads_count=6):
        super().__init__()
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.replace_original = replace_original
        self.selected_files = selected_files  # Список выбранных файлов
        self.analysis = analysis  # Результаты анализа
        self.threads_count = threads_count  # Количество потоков
        self.should_stop = False
        self.is_paused = False  # Состояние паузы
        
        # Для упорядоченного логирования в многопоточном режиме (упрощенная версия)
        self.jar_progress = {}  # {jar_index: progress_percent}
        self.jar_names = {}     # {jar_index: jar_name}
        self.completed_jars = set()  # Завершенные JAR файлы
        
        # Добавляем lock для синхронизации доступа к общим данным
        import threading
        self.progress_lock = threading.Lock()
    
    def stop(self):
        """Остановка перевода"""
        self.should_stop = True
    
    def pause(self):
        """Пауза перевода"""
        self.is_paused = True
    
    def resume(self):
        """Возобновление перевода"""
        self.is_paused = False
    
    def _mark_jar_completed(self, jar_index):
        """Отмечает JAR как завершенный с синхронизацией"""
        with self.progress_lock:
            self.completed_jars.add(jar_index)
    
    def _process_single_jar(self, jar_file, jar_index, total_jars, output_capture, old_stdout):
        """Обрабатывает один JAR файл в однопоточном режиме"""
        try:
            # Проверяем паузу ПЕРЕД началом обработки файла
            while self.is_paused and not self.should_stop:
                self.progress_updated.emit(-1, "На паузе...")
                self.msleep(100)
            
            if self.should_stop:
                return None
            
            # Обновляем основной прогресс
            start_progress = int((jar_index / total_jars) * 100)
            self.progress_updated.emit(start_progress, f"Мод {jar_index+1}/{total_jars}: {jar_file.name}")
            
            # Добавляем заголовок файла
            self.log_message.emit("=" * 60)
            self.log_message.emit(f"📦 [{jar_index+1}/{total_jars}] {jar_file.name}")
            self.log_message.emit("=" * 60)
            
            return self._process_jar_core(jar_file, jar_index, total_jars, output_capture, old_stdout)
            
        except Exception as e:
            self.log_message.emit(f"❌ Ошибка: {e}")
            return {'success': False, 'stats': {}}
    
    def _process_jar_threaded(self, jar_file, jar_index, total_jars):
        """Обрабатывает один JAR файл в многопоточном режиме"""
        try:
            if self.should_stop:
                return {'success': False, 'stats': {}}
            
            # В многопоточном режиме не используем output_capture
            return self._process_jar_core(jar_file, jar_index, total_jars, None, None)
            
        except Exception as e:
            # В многопоточном режиме используем сигналы для логирования
            self.log_message.emit(f"❌ Ошибка в потоке для {jar_file.name}: {e}")
            return {'success': False, 'stats': {}}
    
    def _process_jar_core(self, jar_file, jar_index, total_jars, output_capture, old_stdout):
        """Основная логика обработки JAR файла"""
        import time
        # Импорты уже выполнены в run(), используем глобальные функции
        # Получаем функции из глобального пространства имен модуля
        import sys
        translate_jar_module = sys.modules.get('translate_jar_simple')
        if not translate_jar_module:
            raise ImportError("translate_jar_simple module not loaded")
        
        translate_jar = translate_jar_module.translate_jar
        has_russian_lang = translate_jar_module.has_russian_lang
        has_russian_patchouli = translate_jar_module.has_russian_patchouli
        
        # Проверяем что нужно переводить
        skip_lang = has_russian_lang(jar_file)
        skip_patchouli = has_russian_patchouli(jar_file)
        
        if skip_lang and skip_patchouli:
            self.log_message.emit("⏭️ Пропущен (уже переведен)")
            return {'success': True, 'stats': {'lang_files': 0, 'patchouli_files': 0, 'strings_translated': 0, 'cache_hits': 0, 'new_translations': 0}}
        
        # Переводим JAR - показываем название мода и динамический процент
        jar_name = jar_file.stem.replace('-forge', '').replace('-fabric', '')
        if len(jar_name) > 35:
            jar_name = jar_name[:32] + "..."
        
        # Показываем начальное сообщение
        if self.threads_count == 1:
            # В однопоточном режиме используем старый способ (полное динамическое обновление)
            self.log_colored_message.emit(f"[{jar_index+1}/{total_jars}] {jar_name} - 0%")
        else:
            # В многопоточном режиме используем упорядоченное отображение
            self.log_message.emit(f"🔄 Мод {jar_index+1}/{total_jars}: {jar_name} (многопоточный режим)")
            self.update_mod_line.emit(jar_index, jar_name, "0%")
        
        # Создаем callback для динамического обновления процента мода
        last_progress = [0]  # Используем список для изменяемой переменной в замыкании
        last_update_time = [0]  # Время последнего обновления
        
        def file_progress_callback(progress, current, total):
            current_time = time.time()
            
            # Специальная обработка сигнала перехода между Lang и Patchouli
            if current == 0 and total == 0:
                # Это сигнал перехода (например, 50% при завершении Lang)
                mod_progress = int(progress)
                last_progress[0] = mod_progress  # Обновляем последний прогресс
            else:
                # Обычный прогресс файла
                mod_progress = int(progress)
                
                # Защита от скачков прогресса назад (кроме случаев перехода)
                if mod_progress < last_progress[0] and abs(mod_progress - last_progress[0]) > 5:
                    # Если прогресс упал более чем на 5%, игнорируем это обновление
                    # (возможно, это ошибка в расчете)
                    return
                
                last_progress[0] = mod_progress
            
            # Throttling: ограничиваем частоту обновлений до 10 раз в секунду максимум
            time_since_last_update = current_time - last_update_time[0]
            min_update_interval = 0.1  # 100ms между обновлениями
            
            # Более частые обновления для лучшего отображения прогресса
            should_update = (
                mod_progress % 5 == 0 or   # Каждые 5% вместо каждого процента
                mod_progress == 100 or     # Обязательно при 100%
                mod_progress >= 95 or      # В конце чаще
                current == 1 or            # Первая строка
                (current == 0 and total == 0) or  # Сигналы перехода
                (total <= 20 and current % 5 == 0) or  # Для малых файлов каждые 5 строк
                (total <= 50 and mod_progress % 5 == 0)  # Для средних файлов каждые 5%
            )
            
            # Дополнительная проверка времени для предотвращения спама обновлений
            if should_update and time_since_last_update >= min_update_interval:
                last_update_time[0] = current_time
                
                # Обновляем прогресс этого мода в общем словаре (с синхронизацией)
                with self.progress_lock:
                    self.jar_progress[jar_index] = mod_progress
                    completed_count = len(self.completed_jars)
                    
                    # Находим максимальный прогресс среди активных модов
                    max_active_progress = max(self.jar_progress.values()) if self.jar_progress else 0
                
                # Общий прогресс = завершенные моды + максимальный прогресс активного мода
                completed_progress = (completed_count / total_jars) * 100
                active_mod_progress = (max_active_progress / 100) * (100 / total_jars)
                total_progress = min(completed_progress + active_mod_progress, 100)
                
                self.progress_updated.emit(int(total_progress), f"Мод {jar_index+1}/{total_jars}: {jar_name} - {mod_progress}%")
                
                if self.threads_count == 1:
                    # В однопоточном режиме выводим в лог
                    self.log_colored_message.emit(f"[{jar_index+1}/{total_jars}] {jar_name} - {mod_progress}%")
                else:
                    # В многопоточном режиме обновляем строку
                    self.update_mod_line.emit(jar_index, jar_name, f"{mod_progress}%")
        
        # Создаем callback для проверки остановки И паузы
        def stop_check_callback():
            while self.is_paused and not self.should_stop:
                if output_capture is None:  # Многопоточный режим
                    time.sleep(0.1)
                else:  # Однопоточный режим
                    self.progress_updated.emit(-1, "На паузе...")
                    self.msleep(100)
            return self.should_stop
        
        # Перенаправляем stdout только в однопоточном режиме
        if output_capture and old_stdout:
            sys.stdout = output_capture
        
        try:
            stats = translate_jar(jar_file, self.output_path, 'ru', self.replace_original, file_progress_callback, stop_check_callback)
        finally:
            # Восстанавливаем stdout только в однопоточном режиме
            if output_capture and old_stdout:
                sys.stdout = old_stdout
        
        # Проверяем остановку после перевода файла
        if self.should_stop:
            return None
        
        # Финальное сообщение о завершении мода
        if self.threads_count == 1:
            # В однопоточном режиме используем старый способ
            if stats['lang_files'] > 0 or stats['patchouli_files'] > 0:
                self.log_colored_message.emit(f"[{jar_index+1}/{total_jars}] {jar_name} - 100%")
            elif not (skip_lang and skip_patchouli):
                self.log_colored_message.emit(f"[{jar_index+1}/{total_jars}] {jar_name} - нет файлов")
            # Отмечаем мод как завершенный
            with self.progress_lock:
                self.completed_jars.add(jar_index)
                # Удаляем прогресс завершенного мода из активных
                if jar_index in self.jar_progress:
                    del self.jar_progress[jar_index]
        else:
            # В многопоточном режиме используем упорядоченную систему
            if stats['lang_files'] > 0 or stats['patchouli_files'] > 0:
                # Принудительно показываем 100% перед "переведен"
                self.update_mod_line.emit(jar_index, jar_name, "100%")
                # Небольшая задержка чтобы пользователь увидел 100%
                time.sleep(0.1)
                self.log_message.emit(f"✅ Мод {jar_index+1}/{total_jars}: {jar_name} завершен")
                self.update_mod_line.emit(jar_index, jar_name, "переведен")
            else:
                self.log_message.emit(f"⚪ Мод {jar_index+1}/{total_jars}: {jar_name} пропущен")
                self.update_mod_line.emit(jar_index, jar_name, "нет файлов")
        
        # Отмечаем мод как завершенный для правильного расчета общего прогресса
        with self.progress_lock:
            self.completed_jars.add(jar_index)
            # Удаляем прогресс завершенного мода из активных
            if jar_index in self.jar_progress:
                del self.jar_progress[jar_index]
        
        return {'success': True, 'stats': stats}
    
    def run(self):
        """Выполнение перевода JAR модов"""
        try:
            # Импортируем функции из translate_jar_simple.py в начале
            import sys
            import os
            import time
            from io import StringIO
            
            sys.path.insert(0, str(Path(__file__).parent))
            from translate_jar_simple import (
                translate_jar, load_translation_cache, save_translation_cache, 
                TRANSLATION_CACHE, has_russian_lang, has_russian_patchouli
            )
            
            # Перехватываем print из translate_jar_simple.py
            old_stdout = sys.stdout
            captured_output = StringIO()
            
            class OutputCapture:
                def write(self, text):
                    if text.strip():
                        # Проверяем на API предупреждения
                        text_lower = text.lower()
                        if any(keyword in text_lower for keyword in [
                            "api предупреждение", "api блокировка", "сетевая ошибка", 
                            "лимит исчерпан", "ошибка api", "rate limit", "too many requests",
                            "blocked", "forbidden", "timeout", "connection", "quota", "limit exceeded"
                        ]):
                            # Отправляем как API предупреждение с особым форматированием
                            self.api_warning.emit(text.strip())
                        else:
                            # Обычное сообщение
                            self.log_message.emit(text.strip())
                    captured_output.write(text)
                
                def flush(self):
                    pass
            
            output_capture = OutputCapture()
            output_capture.log_message = self.log_message
            
            # Используем результаты анализа, если они есть
            if self.analysis and self.analysis['need_translation']:
                jar_files = [jar_info['file'] for jar_info in self.analysis['need_translation']]
                stats = self.analysis['stats']
                
                self.log_message.emit("🚀 НАЧИНАЕМ ПЕРЕВОД")
                self.log_message.emit("=" * 60)
                self.log_message.emit(f"📁 Файлов для перевода: {len(jar_files)}")
                self.log_message.emit(f"📄 Lang файлов: {stats['total_lang_files']}")
                self.log_message.emit(f"📚 Patchouli файлов: {stats['total_patchouli_files']}")
                self.log_message.emit(f"📝 Строк для перевода: {stats['total_strings']}")
                self.log_message.emit("=" * 60)
                
            else:
                # Fallback к старой логике, если анализ не был выполнен
                if self.selected_files:
                    jar_files = [Path(f) for f in self.selected_files]
                elif self.input_path.is_file():
                    jar_files = [self.input_path]
                else:
                    jar_files = list(self.input_path.glob('*.jar'))
                
                if not jar_files:
                    self.log_message.emit("❌ JAR файлы не найдены!")
                    self.finished.emit(False, {})
                    return
                
                self.log_message.emit(f"📚 Найдено JAR файлов: {len(jar_files)}")
            
            self.log_message.emit(f"🌐 Язык перевода: ru")
            self.log_message.emit(f"⚙️ Режим: {'Замена оригиналов' if self.replace_original else 'Создание _ru.jar'}")
            self.log_message.emit("")
            
            # Загружаем кэш переводов один раз в начале
            load_translation_cache()
            if len(TRANSLATION_CACHE) > 0:
                self.log_message.emit(f"📦 Загружен кэш: {len(TRANSLATION_CACHE)} переводов")
            else:
                self.log_message.emit("📦 Кэш пуст - будет создан новый")
            # Добавляем информацию о потоках
            self.log_message.emit(f"🧵 Потоков для перевода: {self.threads_count}")
            self.log_message.emit("")
            
            # Статистика
            total_stats = {
                'lang_files': 0, 
                'patchouli_files': 0, 
                'strings_translated': 0,
                'cache_hits': 0,
                'new_translations': 0
            }
            successful = 0
            failed = 0
            
            # МНОГОПОТОЧНАЯ ОБРАБОТКА JAR ФАЙЛОВ
            if self.threads_count == 1:
                # Однопоточный режим (как раньше)
                for i, jar_file in enumerate(jar_files):
                    if self.should_stop:
                        self.log_message.emit("⏹️ Остановка по запросу пользователя")
                        break
                    
                    result = self._process_single_jar(jar_file, i, len(jar_files), output_capture, old_stdout)
                    if result is None:  # Остановка
                        break
                    elif result['success']:
                        successful += 1
                        # Обновляем общую статистику
                        for key in total_stats:
                            total_stats[key] += result['stats'].get(key, 0)
                    else:
                        failed += 1
            else:
                # Многопоточный режим
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                self.log_message.emit(f"🚀 Запуск {self.threads_count} потоков...")
                
                with ThreadPoolExecutor(max_workers=self.threads_count) as executor:
                    # Отправляем задачи в пул потоков
                    future_to_jar = {}
                    for i, jar_file in enumerate(jar_files):
                        if self.should_stop:
                            break
                        future = executor.submit(self._process_jar_threaded, jar_file, i, len(jar_files))
                        future_to_jar[future] = (jar_file, i)
                    
                    # Обрабатываем результаты по мере завершения
                    for future in as_completed(future_to_jar):
                        if self.should_stop:
                            # Отменяем оставшиеся задачи
                            for f in future_to_jar:
                                f.cancel()
                            break
                        
                        jar_file, jar_index = future_to_jar[future]
                        
                        try:
                            result = future.result()
                            if result['success']:
                                successful += 1
                                # Обновляем общую статистику
                                for key in total_stats:
                                    total_stats[key] += result['stats'].get(key, 0)
                            else:
                                failed += 1
                                
                            # Обновляем общий прогресс
                            completed = successful + failed
                            progress = int((completed / len(jar_files)) * 95)  # До 95%
                            self.progress_updated.emit(progress, f"Завершено: {completed}/{len(jar_files)}")
                            
                        except Exception as e:
                            self.log_message.emit(f"❌ Ошибка в потоке для {jar_file.name}: {e}")
                            failed += 1
            
            # Восстанавливаем stdout
            sys.stdout = old_stdout
            
            # Финальная статистика
            final_progress = 100 if not self.should_stop else 50
            self.progress_updated.emit(final_progress, "Завершение...")
            
            self.log_message.emit("")
            self.log_message.emit("🎉 Перевод завершен!")
            self.log_message.emit(f"✅ Успешно: {successful}/{len(jar_files)}")
            if failed > 0:
                self.log_message.emit(f"❌ С ошибками: {failed}")
            
            # Упрощенная сводка по кэшу
            self.log_message.emit("")
            self.log_message.emit("📊 Сводка:")
            if total_stats['new_translations'] > 0:
                self.log_message.emit(f"Переведено заново: {total_stats['new_translations']:,} строк")
            if total_stats['cache_hits'] > 0:
                self.log_message.emit(f"Восстановлено из кэша: {total_stats['cache_hits']:,} строк")
            
            total_processed = total_stats['new_translations'] + total_stats['cache_hits']
            if total_processed > 0:
                cache_efficiency = (total_stats['cache_hits'] / total_processed) * 100
                self.log_message.emit(f"Эффективность кэша: {cache_efficiency:.1f}%")
            
            # Показываем информацию о кэше и сохраняем его
            try:
                from translate_jar_simple import TRANSLATION_CACHE, save_translation_cache
                self.log_message.emit(f"💾 Кэш содержит: {len(TRANSLATION_CACHE)} переводов")
                
                # Сохраняем кэш один раз в конце
                save_translation_cache()
                self.log_message.emit("💾 Кэш сохранен")
            except:
                pass
            
            # Результат
            final_stats = {
                'successful': successful,
                'failed': failed,
                'lang_files': total_stats['lang_files'],
                'patchouli_files': total_stats['patchouli_files'],
                'strings_translated': total_stats['strings_translated']
            }
            
            success = successful > 0 and not self.should_stop
            self.finished.emit(success, final_stats)
            
        except Exception as e:
            # Восстанавливаем stdout в случае критической ошибки
            if 'old_stdout' in locals():
                sys.stdout = old_stdout
            self.log_message.emit(f"❌ Критическая ошибка: {str(e)}")
            import traceback
            self.log_message.emit(f"Детали: {traceback.format_exc()}")
            self.finished.emit(False, {})


if __name__ == "__main__":
    # Запуск основного приложения (раскомментируйте для демо прогресс-бара)
    # demo_glassmorphism_progress()
    main()