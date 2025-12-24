#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Современная система обновлений для RU-MINETOOLS
Адаптированная из L4D2-Addon-Manager
"""

import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import os
import time
from pathlib import Path
from urllib.request import urlopen, urlretrieve, Request
from urllib.error import URLError, HTTPError
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Импортируем утилиты для работы с ресурсами
from utils import get_asset_path

def get_resource_path(filename):
    """Получает правильный путь к ресурсу (совместимость)"""
    return get_asset_path(filename)

# Конфигурация обновлений
try:
    from config.update_config import (
        GITHUB_REPO, GITHUB_API_URL, CURRENT_VERSION, 
        UPDATE_CHECK_INTERVAL, UPDATE_SETTINGS
    )
except ImportError:
    GITHUB_REPO = "your-username/ru-minetools"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    CURRENT_VERSION = "1.0.0"
    UPDATE_CHECK_INTERVAL = 24 * 60 * 60 * 1000
    UPDATE_SETTINGS = {"auto_check": True, "silent_check": True}


class ModernUpdateWorker(QThread):
    """Современный worker для обновлений"""
    
    progress_updated = pyqtSignal(int, str)
    download_completed = pyqtSignal(str)
    install_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, download_url, version, file_type='zip', version_info=None):
        super().__init__()
        self.download_url = download_url
        self.version = version
        self.file_type = file_type  # 'exe' или 'zip'
        self.version_info = version_info  # Информация о релизе
        self.is_cancelled = False
        self.current_phase = "download"  # download, install
    
    def cancel(self):
        self.is_cancelled = True
    
    def run(self):
        try:
            # Фаза скачивания
            self.current_phase = "download"
            self.progress_updated.emit(5, "Подготовка к загрузке...")
            
            if self.is_cancelled:
                return
            
            temp_dir = Path(tempfile.mkdtemp())
            
            # Определяем имя файла в зависимости от типа
            if self.file_type == 'exe':
                filename = f"ru-minetools-v{self.version}.exe"
            else:
                filename = f"update_v{self.version}.zip"
                
            temp_file = temp_dir / filename
            
            self.progress_updated.emit(10, "Загрузка обновления...")
            
            def progress_hook(block_num, block_size, total_size):
                if self.is_cancelled:
                    return
                downloaded = block_num * block_size
                if total_size > 0:
                    progress = 10 + int((downloaded / total_size) * 40)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    self.progress_updated.emit(
                        progress, 
                        f"Загружено: {mb_downloaded:.1f} МБ из {mb_total:.1f} МБ"
                    )
            
            if self.is_cancelled:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            urlretrieve(self.download_url, temp_file, progress_hook)
            
            if self.is_cancelled:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
            
            self.progress_updated.emit(50, "Загрузка завершена")
            self.download_completed.emit(str(temp_file))
            
            # Фаза установки
            self.current_phase = "install"
            
            if self.is_cancelled:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return
                
            self.install_update(temp_file)
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка обновления: {str(e)}")
        finally:
            # Поток завершается автоматически при выходе из run()
            print("🔄 Завершение потока обновления...")
    
    def install_update(self, update_file):
        """Устанавливает обновление"""
        try:
            self.progress_updated.emit(55, "Подготовка к установке...")
            
            if self.file_type == 'exe':
                # Для EXE файлов - простая замена
                self.install_exe_update(update_file)
            else:
                # Для ZIP файлов - извлечение и установка
                self.install_zip_update(update_file)
                
        except Exception as e:
            self.error_occurred.emit(f"Ошибка установки: {str(e)}")
    
    def install_exe_update(self, exe_file):
        """Устанавливает обновление из EXE файла"""
        try:
            self.progress_updated.emit(60, "Подготовка к замене EXE файла...")
            
            # Получаем путь к текущему EXE файлу
            if getattr(sys, 'frozen', False):
                # Запущено из скомпилированного EXE
                current_exe = Path(sys.executable)
            else:
                # Запущено из Python скрипта - создаем фиктивный путь для тестирования
                current_exe = Path(__file__).parent / "ru-minetools.exe"
            
            print(f"🔄 Текущий EXE: {current_exe}")
            print(f"📥 Новый EXE: {exe_file}")
            
            # Проверяем права доступа
            if current_exe.exists():
                try:
                    # Пробуем создать временный файл в той же папке
                    test_file = current_exe.parent / "test_write_access.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                except PermissionError:
                    # Нет прав для записи - используем альтернативный метод
                    self.progress_updated.emit(65, "Недостаточно прав - создание скрипта обновления...")
                    return self.create_update_script(exe_file, current_exe, self.version_info)
            
            # Создаем резервную копию текущего EXE
            backup_exe = current_exe.with_suffix('.exe.backup')
            if current_exe.exists():
                self.progress_updated.emit(70, "Создание резервной копии...")
                try:
                    shutil.copy2(current_exe, backup_exe)
                    print(f"💾 Резервная копия: {backup_exe}")
                except PermissionError:
                    print("⚠️ Не удалось создать резервную копию - продолжаем без неё")
            
            self.progress_updated.emit(80, "Замена исполняемого файла...")
            
            try:
                # Заменяем EXE файл
                if current_exe.exists():
                    current_exe.unlink()  # Удаляем старый
                
                shutil.copy2(exe_file, current_exe)  # Копируем новый
                print(f"✅ EXE файл заменен: {current_exe}")
                
                self.progress_updated.emit(95, "Очистка временных файлов...")
                
                # Удаляем временный файл
                Path(exe_file).unlink(missing_ok=True)
                
                self.progress_updated.emit(100, "Обновление EXE завершено")
                self.install_completed.emit()
                
            except PermissionError as e:
                print(f"❌ Ошибка прав доступа: {e}")
                # Создаем скрипт обновления как fallback
                self.create_update_script(exe_file, current_exe, self.version_info)
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка установки EXE: {str(e)}")
    
    def create_update_script(self, new_exe_path, current_exe_path, version_info=None):
        """Создает простой и надежный скрипт для обновления"""
        try:
            self.progress_updated.emit(70, "Создание скрипта обновления...")
            
            # Получаем имена файлов
            new_exe = Path(new_exe_path)
            current_exe = Path(current_exe_path)
            backup_exe = current_exe.with_suffix('.backup')
            
            # Получаем версию из релиза для создания имени файла
            version = "unknown"
            if version_info and 'tag_name' in version_info:
                version = version_info['tag_name'].replace('v', '')  # Убираем 'v' из версии
            
            # Создаем постоянное место для нового файла с именем версии
            permanent_new_exe = current_exe.parent / f"ru-minetools-v{version}.exe"
            
            print(f"📝 Создание скрипта обновления:")
            print(f"   Новый файл (временный): {new_exe}")
            print(f"   Новый файл (постоянный): {permanent_new_exe}")
            print(f"   Текущий файл: {current_exe}")
            print(f"   Резервная копия: {backup_exe}")
            print(f"   Версия: {version}")
            
            # Копируем новый файл в постоянное место
            shutil.copy2(new_exe, permanent_new_exe)
            print(f"✅ Новый файл скопирован в постоянное место")
            
            # Создаем упрощенный batch скрипт
            batch_content = f'''@echo off
chcp 65001 >nul
title Обновление до v{version}
color 0A

echo.
echo ========================================
echo   ОБНОВЛЕНИЕ RU-MINETOOLS до v{version}
echo ========================================

echo Ожидание закрытия программы...
timeout /t 3 /nobreak >nul

:wait_loop
tasklist /fi "imagename eq {current_exe.name}" 2>nul | find /i "{current_exe.name}" >nul
if not errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo ✓ Программа закрыта

if not exist "{permanent_new_exe}" (
    echo ✗ Ошибка: новый файл не найден
    goto error_exit
)

echo.
echo ========================================
echo   ЗАМЕНА ФАЙЛА НА НОВУЮ ВЕРСИЮ
echo ========================================

if exist "{current_exe}" (
    del "{current_exe}" >nul 2>&1
    echo ✓ Старая версия удалена: {current_exe.name}
)

echo ✓ Новая версия создана: {permanent_new_exe.name}

echo.
echo Запуск новой версии...
start "" "{permanent_new_exe}"

echo.
echo ========================================
echo     ОБНОВЛЕНИЕ ЗАВЕРШЕНО!
echo ========================================
echo ✓ Файл: {permanent_new_exe.name}
echo ✓ Папка: {current_exe.parent}
echo.
echo Нажмите любую клавишу для закрытия...
pause >nul
exit

:error_exit
echo.
echo ✗ Ошибка обновления!
if exist "{current_exe}" (
    start "" "{current_exe}"
    echo ✓ Запущена старая версия
)
echo.
pause >nul
exit
'''
            
            # Сохраняем batch скрипт с UTF-8 кодировкой
            script_path = new_exe.parent / "update_ru_minetools.bat"
            script_path.write_text(batch_content, encoding='utf-8')
            
            self.progress_updated.emit(85, "Запуск скрипта обновления...")
            
            # Запускаем batch скрипт
            import subprocess
            try:
                # Запускаем в новом окне консоли
                subprocess.Popen([str(script_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                print(f"✅ Скрипт обновления запущен: {script_path}")
                self.progress_updated.emit(95, "Скрипт обновления создан и запущен")
                self.install_completed.emit()
                
            except Exception as e:
                print(f"❌ Ошибка запуска скрипта: {e}")
                self.error_occurred.emit(f"Ошибка запуска скрипта обновления: {str(e)}")
            
        except Exception as e:
            error_msg = f"Ошибка создания скрипта обновления: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
    
    def install_zip_update(self, update_file):
        """Устанавливает обновление из ZIP файла (старая логика)"""
    def install_zip_update(self, update_file):
        """Устанавливает обновление из ZIP файла (старая логика)"""
        try:
            self.progress_updated.emit(55, "Подготовка к установке...")
            
            app_dir = Path(__file__).parent
            backup_dir = app_dir.parent / f"{app_dir.name}_backup"
            
            # Создаем резервную копию
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            
            self.progress_updated.emit(60, "Создание резервной копии...")
            shutil.copytree(app_dir, backup_dir)
            
            self.progress_updated.emit(70, "Извлечение файлов...")
            
            # Извлекаем во временную папку
            temp_extract_dir = app_dir.parent / "temp_update"
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
            
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            self.progress_updated.emit(80, "Установка файлов...")
            
            # Находим папку с обновлением
            update_source = None
            for item in temp_extract_dir.iterdir():
                if item.is_dir() and (item / "modern_gui_interface.py").exists():
                    update_source = item
                    break
            
            if not update_source:
                update_source = temp_extract_dir
            
            # Сохраняем конфигурацию
            config_backup = None
            config_file = app_dir / "config.json"
            if config_file.exists():
                config_backup = config_file.read_text(encoding='utf-8')
            
            # Удаляем старые файлы (кроме конфига)
            for item in app_dir.iterdir():
                if item.name not in ["config.json", "user_data.json"]:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            
            self.progress_updated.emit(90, "Копирование новых файлов...")
            
            # Копируем новые файлы
            for item in update_source.iterdir():
                dest = app_dir / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    shutil.copytree(item, dest)
            
            # Восстанавливаем конфигурацию
            if config_backup:
                config_file.write_text(config_backup, encoding='utf-8')
            
            self.progress_updated.emit(95, "Очистка временных файлов...")
            
            # Удаляем временные файлы
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            shutil.rmtree(backup_dir, ignore_errors=True)
            Path(update_file).unlink(missing_ok=True)
            
            self.progress_updated.emit(100, "Обновление установлено")
            self.install_completed.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"Ошибка установки ZIP: {str(e)}")


class CustomProgressDialog(QMainWindow):
    """Окно прогресса в стиле приложения"""
    
    rejected = pyqtSignal()  # Сигнал отмены
    
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.parent_widget = parent
        
        # Настройка окна как обычного Windows окна
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setModal(True) if hasattr(self, 'setModal') else None
        
        # Устанавливаем фон окна в стиле приложения
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
            }
        """)
        
        self.setup_ui(title, message)
    
    def setup_ui(self, title, message):
        """Создает интерфейс в стиле приложения"""
        self.setFixedSize(700, 420)  # Уменьшили высоту без иконки
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: 700; 
            color: #E06BFF;
            margin: 20px 0px 10px 0px;
        """)
        layout.addWidget(title_label)
        
        # Сообщение
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(600)
        self.message_label.setStyleSheet("""
            font-size: 14px; 
            color: #cbd5e1; 
            line-height: 1.6;
            margin: 10px 20px;
        """)
        self.message_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.message_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Прогресс бар в стиле приложения
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(165, 70, 255, 0.6);
                border-radius: 12px;
                background: rgba(20, 20, 20, 0.8);
                text-align: center;
                color: white;
                font-weight: 700;
                font-size: 12px;
                min-height: 24px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF,
                    stop:0.3 #B855FF,
                    stop:0.7 #D065FF,
                    stop:1 #E06BFF);
                border-radius: 8px;
                margin: 2px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Статус текст
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 13px; 
            color: #94a3b8;
            margin: 5px 0px;
        """)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        layout.addSpacing(10)
        
        # Кнопка отмены в стиле приложения
        from modern_gui_interface import HoverLiftButton
        self.cancel_btn = HoverLiftButton("Отмена")
        self.cancel_btn.setFixedSize(140, 50)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
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
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c8591,
                    stop:0.3 #8d94a2,
                    stop:0.7 #a1a8b6,
                    stop:1 #b5bcc7);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a6169,
                    stop:0.3 #6b7280,
                    stop:0.7 #7c8591,
                    stop:1 #8d94a2);
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel)
        layout.addWidget(self.cancel_btn, 0, Qt.AlignmentFlag.AlignCenter)
    
    def on_cancel(self):
        """Обработка нажатия кнопки отмены"""
        print("❌ Пользователь нажал отмену в диалоге прогресса")
        self.rejected.emit()
        self.close()
    
    def show_progress(self):
        """Показывает прогресс бар"""
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.cancel_btn.setText("Отмена")
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        self.progress_bar.setValue(value)
        if status_text:
            self.status_label.setText(status_text)
    
    def hide_progress(self):
        """Скрывает прогресс бар"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
    
    def show_with_animation(self):
        """Показывает окно"""
        self.show()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        event.accept()


class StandardUpdateChecker(QObject):
    """Чекер обновлений"""
    
    update_available = pyqtSignal(dict)
    no_updates = pyqtSignal()
    check_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
    
    def check_for_updates(self, silent=False):
        """Проверяет обновления"""
        try:
            print(f"🔍 Проверка обновлений: {GITHUB_API_URL}")
            
            # Создаем запрос с правильными заголовками
            from urllib.request import Request
            request = Request(GITHUB_API_URL)
            request.add_header('User-Agent', 'RU-MINETOOLS/1.0.0 (Update Checker)')
            request.add_header('Accept', 'application/vnd.github.v3+json')
            
            response = urlopen(request, timeout=10)
            data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', '').replace('v', '')
            print(f"📦 Найдена версия: {latest_version}, текущая: {CURRENT_VERSION}")
            
            if self.is_newer_version(latest_version, CURRENT_VERSION):
                print("✅ Доступно обновление!")
                self.update_available.emit(data)
            else:
                print("ℹ️ Обновлений нет")
                self.no_updates.emit()
                if not silent:
                    self.show_no_updates_message()
        
        except Exception as e:
            error_msg = f"Ошибка проверки обновлений: {str(e)}"
            print(f"❌ {error_msg}")
            
            # В тихом режиме просто логируем ошибку, не показываем диалоги
            if silent:
                print(f"🔄 Тихая проверка обновлений: {str(e)}")
                return
            
            # В обычном режиме отправляем сигнал ошибки
            self.check_error.emit(error_msg)
            
            # Показываем ошибку только если нет других активных диалогов
            QTimer.singleShot(100, self.show_error_message)
    
    def is_newer_version(self, latest, current):
        """Сравнивает версии"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
        except:
            return False
    
    def show_no_updates_message(self):
        """Показывает сообщение об отсутствии обновлений"""
        try:
            from update_notifications import show_update_info
            show_update_info(
                self.parent_widget,
                "Обновления не найдены",
                f"У вас установлена последняя версия {CURRENT_VERSION}"
            )
        except ImportError:
            # Fallback к стандартному диалогу
            QMessageBox.information(
                self.parent_widget,
                "Обновления не найдены",
                f"У вас установлена последняя версия {CURRENT_VERSION}"
            )
    
    def show_error_message(self):
        """Показывает сообщение об ошибке (только если нет других диалогов)"""
        # Проверяем, нет ли уже открытых диалогов
        if hasattr(self.parent_widget, 'current_notification') and self.parent_widget.current_notification:
            print("⚠️ Диалог уже открыт, пропускаем показ ошибки")
            return
            
        # Проверяем активные окна
        app = QApplication.instance()
        if app:
            active_windows = [w for w in app.allWidgets() if isinstance(w, (QDialog, QMessageBox)) and w.isVisible()]
            if active_windows:
                print(f"⚠️ Найдено {len(active_windows)} активных диалогов, пропускаем показ ошибки")
                return
        
        # Дополнительная проверка на активные overlay диалоги
        if hasattr(self.parent_widget, '_active_update_dialog') and self.parent_widget._active_update_dialog:
            print("⚠️ Активный диалог обновления найден, пропускаем показ ошибки")
            return
        
        try:
            from update_notifications import show_update_error
            show_update_error(
                self.parent_widget,
                "Ошибка проверки обновлений",
                "Не удалось проверить обновления.\nПроверьте подключение к интернету."
            )
        except ImportError:
            # Fallback к стандартному диалогу
            QMessageBox.warning(
                self.parent_widget,
                "Ошибка проверки обновлений",
                "Не удалось проверить обновления. Проверьте подключение к интернету."
            )

def show_update_available_dialog(parent, version_info):
    """Показывает диалог о доступном обновлении в стиле overlay"""
    print("🎭 Показ современного overlay диалога обновления...")
    
    # Проверяем, нет ли уже активного диалога обновления
    if hasattr(parent, '_active_update_dialog') and parent._active_update_dialog:
        print("⚠️ Диалог обновления уже активен, пропускаем показ нового")
        return False
    
    # Проверяем другие активные диалоги
    app = QApplication.instance()
    if app:
        active_windows = [w for w in app.allWidgets() if isinstance(w, (QDialog, QMessageBox)) and w.isVisible()]
        if active_windows:
            print(f"⚠️ Найдено {len(active_windows)} активных диалогов, пропускаем показ диалога обновления")
            return False
    
    try:
        from modern_update_overlays import show_modern_update_dialog
        
        # Устанавливаем флаг активного диалога
        parent._active_update_dialog = True
        
        try:
            result = show_modern_update_dialog(parent, version_info)
            return result
        finally:
            # Сбрасываем флаг после закрытия диалога
            parent._active_update_dialog = False
            
    except ImportError:
        print("❌ Не удалось загрузить современные overlay - используем старый диалог")
        # Fallback к старому диалогу
        parent._active_update_dialog = True
        try:
            result = show_legacy_update_dialog(parent, version_info)
            return result
        finally:
            parent._active_update_dialog = False

def show_legacy_update_dialog(parent, version_info):
    """Показывает старый диалог обновления (fallback)"""
def show_legacy_update_dialog(parent, version_info):
    """Показывает старый диалог обновления (fallback)"""
    print("🎭 Показ старого диалога обновления...")
    
    # Формируем информацию о версии
    new_version = version_info.get('tag_name', 'Неизвестно')
    release_date = version_info.get('published_at', '')
    release_date_formatted = ''
    if release_date:
        from datetime import datetime
        try:
            date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
            release_date_formatted = f"Дата выпуска: {date_obj.strftime('%d.%m.%Y')}"
        except:
            release_date_formatted = ''
    
    # Описание изменений
    changes = version_info.get('body', '')
    if changes:
        # Ограничиваем длину описания
        if len(changes) > 300:
            changes = changes[:300] + '...'
        changes = changes.replace('\n', '<br>')
    else:
        changes = "Описание изменений недоступно"
    
    # Формируем сообщение
    message = f"""
    <b>Доступна новая версия: {new_version}</b><br>
    <i>Текущая версия: {CURRENT_VERSION}</i><br><br>
    {release_date_formatted}<br><br>
    <b>Изменения:</b><br>
    {changes}
    """
    
    print("📋 Создание старого диалога...")
    
    # Создаем диалог с кнопками
    dialog = CustomUpdateConfirmDialog(parent, "Доступно обновление", message, version_info)
    
    print("⏳ Ожидание ответа пользователя...")
    result = dialog.exec()
    
    print(f"✅ Результат старого диалога: {result}")
    
    return result


class CustomUpdateConfirmDialog(QMainWindow):
    """Окно подтверждения обновления"""
    
    finished = pyqtSignal()  # Сигнал завершения для QMainWindow
    
    def __init__(self, parent, title, message, version_info):
        super().__init__(parent)
        self.parent_widget = parent
        self.version_info = version_info
        self.result_value = False
        
        # Настройка окна как обычного Windows окна
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        
        # Устанавливаем фон окна в стиле приложения
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
            }
        """)
        
        self.setup_ui(title, message)
        
        # Показываем окно
        self.show()
    
    def setup_ui(self, title, message):
        """Создает интерфейс"""
        self.setFixedSize(700, 650)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Иконка обновления
        icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                # Стандартный размер 120x120
                scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый цвет (#E06BFF)
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(224, 107, 255))  # #E06BFF
                painter.end()
                
                icon_label.setPixmap(colored_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: 700; 
            color: #E06BFF;
            margin: 10px 0px;
        """)
        layout.addWidget(title_label)
        
        # Сообщение
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(600)
        message_label.setStyleSheet("""
            font-size: 14px; 
            color: #cbd5e1; 
            line-height: 1.6;
            margin: 10px 20px 20px 20px;
        """)
        message_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(message_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(10)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from modern_gui_interface import HoverLiftButton
        
        # Кнопка "Скачать и установить" в стиле приложения
        self.update_btn = HoverLiftButton("Скачать и установить")
        self.update_btn.setFixedSize(200, 50)
        self.update_btn.setStyleSheet("""
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
                font-size: 14px;
                padding: 8px 16px;
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
        self.update_btn.clicked.connect(self.accept_update)
        buttons_layout.addWidget(self.update_btn)
        
        # Кнопка "Позже" в стиле приложения
        self.later_btn = HoverLiftButton("Позже")
        self.later_btn.setFixedSize(140, 50)
        self.later_btn.setStyleSheet("""
            QPushButton {
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
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c8591,
                    stop:0.3 #8d94a2,
                    stop:0.7 #a1a8b6,
                    stop:1 #b5bcc7);
                border-top: 1px solid rgba(255, 255, 255, 0.6);
                border-left: 1px solid rgba(255, 255, 255, 0.4);
                border-right: 1px solid rgba(255, 255, 255, 0.2);
                border-bottom: 1px solid rgba(0, 0, 0, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a6169,
                    stop:0.3 #6b7280,
                    stop:0.7 #7c8591,
                    stop:1 #8d94a2);
                border-top: 1px solid rgba(0, 0, 0, 0.3);
                border-left: 1px solid rgba(0, 0, 0, 0.2);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-bottom: 1px solid rgba(255, 255, 255, 0.4);
            }
        """)
        self.later_btn.clicked.connect(self.reject_update)
        buttons_layout.addWidget(self.later_btn)
        
        layout.addLayout(buttons_layout)
    
    def exec(self):
        """Переопределяем exec для возврата результата"""
        # Для QMainWindow используем exec() через QEventLoop
        from PyQt6.QtCore import QEventLoop
        self.event_loop = QEventLoop()
        self.finished.connect(self.event_loop.quit)
        self.event_loop.exec()
        return self.result_value
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        print(f"🚪 closeEvent вызван, текущий result_value: {self.result_value}")
        # НЕ сбрасываем result_value - оставляем как есть
        if hasattr(self, 'event_loop') and self.event_loop.isRunning():
            print("🔄 Завершение event_loop из closeEvent...")
            self.event_loop.quit()
        event.accept()
    
    def accept_update(self):
        """Пользователь согласился на обновление"""
        print("✅ Пользователь нажал 'Скачать и установить'")
        self.result_value = True
        print(f"🔧 Установлен result_value = {self.result_value}")
        if hasattr(self, 'event_loop'):
            print("🔄 Завершение event_loop...")
            self.event_loop.quit()
        print("🚪 Закрытие диалога...")
        self.close()
    
    def reject_update(self):
        """Пользователь отказался от обновления"""
        print("❌ Пользователь нажал 'Позже'")
        self.result_value = False
        print(f"🔧 Установлен result_value = {self.result_value}")
        if hasattr(self, 'event_loop'):
            print("🔄 Завершение event_loop...")
            self.event_loop.quit()
        print("🚪 Закрытие диалога...")
        self.close()


def cleanup_update_process(parent):
    """Очищает флаг активного процесса обновления"""
    if hasattr(parent, '_active_update_process'):
        parent._active_update_process = False
        print("🧹 Флаг активного процесса обновления очищен")


def cleanup_worker(progress_dialog, worker, parent):
    """Очищает ссылку на worker после завершения потока"""
    print("🧹 Начало очистки worker...")
    
    # Ждем завершения потока если он еще работает
    if worker.isRunning():
        print("⏳ Worker еще работает, ждем завершения...")
        worker.wait(5000)  # Ждем максимум 5 секунд
        
        if worker.isRunning():
            print("⚠️ Worker не завершился за 5 секунд, принудительно завершаем...")
            worker.terminate()
            worker.wait(2000)  # Ждем еще 2 секунды после terminate
    
    # Очищаем ссылку на worker
    if hasattr(progress_dialog, 'update_worker'):
        progress_dialog.update_worker = None
        print("🧹 Worker очищен после завершения потока")
    
    # Очищаем флаг активного процесса
    cleanup_update_process(parent)
    
    print("✅ Очистка worker завершена")


def on_download_completed(progress_dialog, file_path):
    """Обработка завершения загрузки"""
    progress_dialog.update_progress(100, "Загрузка завершена. Установка...")


def on_install_completed(progress_dialog, parent):
    """Обработка завершения установки"""
    print("🎉 Установка завершена, закрываем диалог прогресса...")
    
    # СНАЧАЛА закрываем диалог прогресса и ждем его полного закрытия
    if hasattr(progress_dialog, 'close'):
        progress_dialog.close()
    
    # Очищаем флаг активного процесса
    cleanup_update_process(parent)
    
    # Ждем немного чтобы диалог прогресса точно закрылся
    QTimer.singleShot(500, lambda: show_success_dialog(parent))


def show_success_dialog(parent):
    """Показывает диалог успешного обновления с задержкой"""
    print("✅ Показ диалога успешного обновления...")
    
    try:
        from update_notifications import show_update_success
        result = show_update_success(
            parent,
            "Обновление готово к установке",
            "Скрипт обновления создан и запущен!\n\n" +
            "📋 Что происходит:\n" +
            "• Скрипт ждет закрытия программы\n" +
            "• УДАЛЯЕТ старый EXE файл полностью\n" +
            "• СОЗДАЕТ новый EXE файл\n" +
            "• Запускает новую версию программы\n\n" +
            "🔄 Программа автоматически закроется через 3 секунды\n" +
            "После этого запустится НОВЫЙ EXE файл\n\n" +
            "✅ Это устраняет ошибку Python DLL!"
        )
    except ImportError:
        # Fallback к стандартному диалогу
        result = QMessageBox.information(
            parent,
            "Обновление готово к установке",
            "Скрипт обновления создан и запущен!\n\n" +
            "📋 Что происходит:\n" +
            "• Скрипт ждет закрытия программы\n" +
            "• УДАЛЯЕТ старый EXE файл полностью\n" +
            "• СОЗДАЕТ новый EXE файл\n" +
            "• Запускает новую версию программы\n\n" +
            "🔄 Программа автоматически закроется через 3 секунды\n" +
            "После этого запустится НОВЫЙ EXE файл\n\n" +
            "✅ Это устраняет ошибку Python DLL!"
        )
    
    # Автоматически закрываем программу через 3 секунды
    print("🔄 Запуск таймера автоматического закрытия...")
    
    def close_application():
        print("🚪 Автоматическое закрытие программы для завершения обновления...")
        
        # Для PyInstaller используем os._exit() чтобы избежать ошибки DLL
        if getattr(sys, 'frozen', False):
            print("🔧 PyInstaller обнаружен - используем os._exit()")
            os._exit(0)
        else:
            # Для обычного Python
            if hasattr(parent, 'close'):
                parent.close()
            else:
                QApplication.quit()
    
    # Создаем таймер для автоматического закрытия
    close_timer = QTimer()
    close_timer.setSingleShot(True)
    close_timer.timeout.connect(close_application)
    close_timer.start(3000)  # 3 секунды
    
    # Сохраняем ссылку на таймер, чтобы он не был удален сборщиком мусора
    if hasattr(parent, '_close_timer'):
        parent._close_timer = close_timer
    else:
        # Если нет возможности сохранить в parent, сохраняем глобально
        globals()['_update_close_timer'] = close_timer


def on_update_error(progress_dialog, parent, error_message):
    """Обработка ошибки обновления"""
    # Закрываем диалог прогресса
    if hasattr(progress_dialog, 'close'):
        # Современное окно
        progress_dialog.close()
    else:
        # Старый диалог
        progress_dialog.close()
    
    # Очищаем флаг активного процесса
    cleanup_update_process(parent)
    
    try:
        from update_notifications import show_update_error
        show_update_error(
            parent,
            "Ошибка обновления",
            f"Произошла ошибка при обновлении:\n{error_message}"
        )
    except ImportError:
        # Fallback к стандартному диалогу
        QMessageBox.critical(
            parent,
            "Ошибка обновления",
            f"Произошла ошибка при обновлении:\n{error_message}"
        )


def start_update_process(parent, version_info):
    """Запускает процесс обновления с CustomProgressDialog"""
    
    print("🚀 Запуск процесса обновления...")
    print(f"📦 Информация о релизе: {version_info.get('tag_name', 'Неизвестно')}")
    
    # Проверяем, нет ли уже активного процесса обновления
    if hasattr(parent, '_active_update_process') and parent._active_update_process:
        print("⚠️ Процесс обновления уже активен, пропускаем запуск нового")
        return
    
    # Получаем ссылку на скачивание (ищем EXE или ZIP файл)
    download_url = None
    file_type = None
    assets = version_info.get('assets', [])
    print(f"📄 Найдено assets: {len(assets)}")
    
    for asset in assets:
        asset_name = asset['name']
        print(f"🔍 Проверяем asset: {asset_name}")
        
        # Приоритет: сначала ищем EXE файлы, потом ZIP
        if asset_name.endswith('.exe'):
            download_url = asset['browser_download_url']
            file_type = 'exe'
            print(f"✅ Найден EXE файл: {asset_name}")
            print(f"🔗 URL: {download_url}")
            break
        elif asset_name.endswith('.zip'):
            download_url = asset['browser_download_url']
            file_type = 'zip'
            print(f"✅ Найден ZIP файл: {asset_name}")
            print(f"🔗 URL: {download_url}")
            # Не прерываем цикл, продолжаем искать EXE
    
    if not download_url:
        print("❌ EXE или ZIP файл не найден!")
        try:
            from update_notifications import show_update_error
            show_update_error(
                parent,
                "Ошибка обновления",
                "Не найден файл для загрузки в релизе.\nОжидается .exe или .zip файл."
            )
        except ImportError:
            # Fallback к стандартному диалогу
            QMessageBox.warning(
                parent,
                "Ошибка обновления",
                "Не найден файл для загрузки в релизе.\nОжидается .exe или .zip файл."
            )
        return
    
    print(f"📦 Тип файла для обновления: {file_type}")
    
    # Устанавливаем флаг активного процесса
    parent._active_update_process = True
    
    print("📥 Создание диалога прогресса...")
    print("📥 Создание современного диалога прогресса...")
    
    # Создаем современный диалог прогресса
    try:
        from modern_update_overlays import show_modern_progress_dialog
        progress_dialog = show_modern_progress_dialog(
            parent,
            "🔄 Обновление приложения",
            "Подготовка к обновлению..."
        )
        print("✅ Использован современный overlay диалог прогресса")
    except ImportError:
        print("❌ Не удалось загрузить современный overlay - используем старый диалог")
        # Fallback к старому диалогу
        progress_dialog = CustomProgressDialog(
            parent,
            "Обновление приложения",
            "Подготовка к обновлению..."
        )
        progress_dialog.show_progress()
        progress_dialog.show_with_animation()
    
    print("🔧 Создание worker для загрузки...")
    
    # Создаем worker для загрузки
    worker = ModernUpdateWorker(download_url, version_info.get('tag_name', ''), file_type, version_info)
    
    # Сохраняем ссылку на worker в progress_dialog чтобы избежать удаления сборщиком мусора
    progress_dialog.update_worker = worker
    
    print("🔌 Подключение сигналов...")
    
    # Подключаем сигналы
    worker.progress_updated.connect(lambda value, text: progress_dialog.update_progress(value, text))
    worker.download_completed.connect(lambda path: on_download_completed(progress_dialog, path))
    worker.install_completed.connect(lambda: on_install_completed(progress_dialog, parent))
    worker.error_occurred.connect(lambda error: on_update_error(progress_dialog, parent, error))
    
    # Подключаем завершение потока для очистки - используем правильный сигнал
    worker.finished.connect(lambda: cleanup_worker(progress_dialog, worker, parent))
    
    # Подключаем отмену (проверяем тип диалога)
    if hasattr(progress_dialog, 'cancelled'):
        # Современный overlay диалог
        progress_dialog.cancelled.connect(worker.cancel)
        progress_dialog.cancelled.connect(lambda: cleanup_update_process(parent))
    elif hasattr(progress_dialog, 'rejected'):
        # Старый диалог
        progress_dialog.rejected.connect(worker.cancel)
        progress_dialog.rejected.connect(lambda: cleanup_update_process(parent))
    
    print("📺 Показ диалога прогресса...")
    
    # Показываем прогресс (если это старый диалог)
    if hasattr(progress_dialog, 'show_progress') and not hasattr(progress_dialog, 'cancelled'):
        progress_dialog.show_progress()
        progress_dialog.show_with_animation()
    
    print("🚀 Запуск worker...")
    worker.start()
    
    print("✅ Процесс обновления запущен!")


def cleanup_update_process(parent):
    """Очищает флаг активного процесса обновления"""
    if hasattr(parent, '_active_update_process'):
        parent._active_update_process = False
        print("🧹 Флаг активного процесса обновления очищен")


def cleanup_worker(progress_dialog, worker, parent):
    """Очищает ссылку на worker после завершения потока"""
    print("🧹 Начало очистки worker...")
    
    # Ждем завершения потока если он еще работает
    if worker.isRunning():
        print("⏳ Worker еще работает, ждем завершения...")
        worker.wait(5000)  # Ждем максимум 5 секунд
        
        if worker.isRunning():
            print("⚠️ Worker не завершился за 5 секунд, принудительно завершаем...")
            worker.terminate()
            worker.wait(2000)  # Ждем еще 2 секунды после terminate
    
    # Очищаем ссылку на worker
    if hasattr(progress_dialog, 'update_worker'):
        progress_dialog.update_worker = None
        print("🧹 Worker очищен после завершения потока")
    
    # Очищаем флаг активного процесса
    cleanup_update_process(parent)
    
    print("✅ Очистка worker завершена")


def on_download_completed(progress_dialog, file_path):
    """Обработка завершения загрузки"""
    progress_dialog.update_progress(100, "Загрузка завершена. Установка...")


def on_install_completed(progress_dialog, parent):
    """Обработка завершения установки"""
    print("🎉 Установка завершена, закрываем диалог прогресса...")
    
    # СНАЧАЛА закрываем диалог прогресса и ждем его полного закрытия
    if hasattr(progress_dialog, 'close'):
        progress_dialog.close()
    
    # Очищаем флаг активного процесса
    cleanup_update_process(parent)
    
    # Ждем немного чтобы диалог прогресса точно закрылся
    QTimer.singleShot(500, lambda: show_success_dialog(parent))


def show_success_dialog(parent):
    """Показывает диалог успешного обновления с задержкой"""
    print("✅ Показ диалога успешного обновления...")
    
    try:
        from update_notifications import show_update_success
        result = show_update_success(
            parent,
            "Обновление готово к установке",
            "Скрипт обновления создан и запущен!\n\n" +
            "📋 Что происходит:\n" +
            "• Скрипт ждет закрытия программы\n" +
            "• УДАЛЯЕТ старый EXE файл полностью\n" +
            "• СОЗДАЕТ новый EXE файл\n" +
            "• Запускает новую версию программы\n\n" +
            "🔄 Программа автоматически закроется через 3 секунды\n" +
            "После этого запустится НОВЫЙ EXE файл\n\n" +
            "✅ Это устраняет ошибку Python DLL!"
        )
    except ImportError:
        # Fallback к стандартному диалогу
        result = QMessageBox.information(
            parent,
            "Обновление готово к установке",
            "Скрипт обновления создан и запущен!\n\n" +
            "📋 Что происходит:\n" +
            "• Скрипт ждет закрытия программы\n" +
            "• УДАЛЯЕТ старый EXE файл полностью\n" +
            "• СОЗДАЕТ новый EXE файл\n" +
            "• Запускает новую версию программы\n\n" +
            "🔄 Программа автоматически закроется через 3 секунды\n" +
            "После этого запустится НОВЫЙ EXE файл\n\n" +
            "✅ Это устраняет ошибку Python DLL!"
        )
    
    # Автоматически закрываем программу через 3 секунды
    print("🔄 Запуск таймера автоматического закрытия...")
    
    def close_application():
        print("🚪 Автоматическое закрытие программы для завершения обновления...")
        
        # Для PyInstaller используем os._exit() чтобы избежать ошибки DLL
        if getattr(sys, 'frozen', False):
            print("🔧 PyInstaller обнаружен - используем os._exit()")
            os._exit(0)
        else:
            # Для обычного Python
            if hasattr(parent, 'close'):
                parent.close()
            else:
                QApplication.quit()
    
    # Создаем таймер для автоматического закрытия
    close_timer = QTimer()
    close_timer.setSingleShot(True)
    close_timer.timeout.connect(close_application)
    close_timer.start(3000)  # 3 секунды
    
    # Сохраняем ссылку на таймер, чтобы он не был удален сборщиком мусора
    if hasattr(parent, '_close_timer'):
        parent._close_timer = close_timer
    else:
        # Если нет возможности сохранить в parent, сохраняем глобально
        globals()['_update_close_timer'] = close_timer