#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленные диалоги обновлений без наложения окон и с компактными отступами
"""

import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pathlib import Path

# Импортируем утилиты для работы с ресурсами
from utils import get_asset_path

def get_resource_path(filename):
    """Получает правильный путь к ресурсу (совместимость)"""
    return get_asset_path(filename)

class HoverLiftButton(QPushButton):
    """Кнопка с анимацией подъема при наведении мыши"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        # Анимация для hover эффекта (подъем вверх)
        self.hover_animation = QPropertyAnimation(self, b"pos")
        self.hover_animation.setDuration(150)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.original_pos = None
        self.is_hovered = False
    
    def enterEvent(self, event):
        """Анимация при наведении - подъем вверх"""
        self.is_hovered = True
        
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos is None:
            self.original_pos = self.pos()
        
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

class Modern3DButton(QPushButton):
    """3D кнопка в стиле авторизации"""
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("modern3DBtn")
        
        # Создаем внутренний layout для 3D эффекта
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Тень
        self.shadow = QPushButton()
        self.shadow.setObjectName("modern3DBtnShadow")
        self.shadow.setFixedHeight(4)
        layout.addWidget(self.shadow)
        
        # Основная кнопка
        self.inner_btn = QPushButton(text)
        self.inner_btn.setObjectName("modern3DBtnInner")
        self.inner_btn.clicked.connect(self.clicked.emit)
        layout.addWidget(self.inner_btn)
        
        # Отключаем стандартную обработку кликов
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

class ModernUpdateConfirmDialog(QDialog):
    """Компактный диалог подтверждения обновления"""
    
    def __init__(self, parent, version_info):
        super().__init__(parent)
        self.version_info = version_info
        self.result_value = False
        
        # Настройка диалога
        self.setWindowTitle("Обновление доступно")
        self.setModal(True)
        self.setFixedSize(500, 450)  # Компактный размер
        
        # Черный фон как в авторизации
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                border: 2px solid #bb86fc;
                border-radius: 15px;
            }
        """)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация компактного интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)  # Минимальные отступы
        layout.setSpacing(-5)  # Минимальные промежутки
        
        # Заголовок
        self.create_header(layout)
        
        # Информация об обновлении
        self.create_update_info(layout)
        
        # Кнопки
        self.create_buttons(layout)
    
    def create_header(self, layout):
        """Создает компактный заголовок"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(1)  # Уменьшено с 5 до 3
        
        # Иконка обновления (меньше)
        icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                icon_label.setPixmap(colored_pixmap)
        else:
            icon_label.setText("🔄")
            icon_label.setStyleSheet("font-size: 60px;")
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # Заголовок
        title_label = QLabel("ОБНОВЛЕНИЕ ДОСТУПНО")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Новая версия готова к установке")
        subtitle_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_update_info(self, layout):
        """Создает компактную информацию об обновлении"""
        info_text = self.format_version_info()
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("""
            font-size: 12px;
            color: #e8e8e8;
            background-color: transparent;
            line-height: 1.4;
            padding: 10px;
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setMaximumHeight(120)  # Ограничиваем высоту
        layout.addWidget(info_label)
    
    def format_version_info(self):
        """Форматирует информацию о версии"""
        try:
            from config.update_config import CURRENT_VERSION
        except ImportError:
            CURRENT_VERSION = "1.0.0"
        
        new_version = self.version_info.get('tag_name', 'Неизвестно')
        release_date = self.version_info.get('published_at', '')
        
        # Форматируем дату
        release_date_formatted = ''
        if release_date:
            from datetime import datetime
            try:
                date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                release_date_formatted = f"📅 {date_obj.strftime('%d.%m.%Y')}"
            except:
                pass
        
        # Описание изменений (короткое)
        changes = self.version_info.get('body', '')
        if changes:
            if len(changes) > 80:
                changes = changes[:80] + '...'
        else:
            changes = "Улучшения и исправления"
        
        return f"""Текущая: {CURRENT_VERSION} → Новая: {new_version}

{release_date_formatted}

✦ {changes}
✦ Улучшенная производительность"""
    
    def create_buttons(self, layout):
        """Создает компактные кнопки"""
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        # 3D кнопка обновления
        self.update_btn = Modern3DButton("СКАЧАТЬ И УСТАНОВИТЬ")
        self.update_btn.setFixedHeight(45)  # Компактная высота
        self.update_btn.clicked.connect(self.accept_update)
        buttons_layout.addWidget(self.update_btn)
        
        # Обычная кнопка "Позже"
        self.later_btn = QPushButton("Позже")
        self.later_btn.setFixedHeight(35)  # Еще более компактная
        self.later_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
                border-color: #2a2a2a;
            }
        """)
        self.later_btn.clicked.connect(self.reject_update)
        buttons_layout.addWidget(self.later_btn)
        
        layout.addLayout(buttons_layout)
        
        # Применяем стили для 3D кнопки
        self.setStyleSheet(self.styleSheet() + """
        #modern3DBtn {
            background: transparent;
            border: none;
        }
        
        #modern3DBtnInner {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f5f0ff, stop:0.05 #e6ccff, stop:0.15 #d1a7ff,
                stop:0.45 #bb86fc, stop:0.55 #a855f7, stop:0.85 #9333ea,
                stop:0.95 #7c3aed, stop:1 #6b21a8);
            
            border-top: 2px solid rgba(255, 255, 255, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(0, 0, 0, 0.2);
            border-bottom: 2px solid rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            
            color: #ffffff;
            font-weight: 800;
            font-size: 12px;
            padding: 8px 20px;
        }
        
        #modern3DBtnInner:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #faf8ff, stop:0.05 #f0e6ff, stop:0.15 #e6ccff,
                stop:0.45 #d1a7ff, stop:0.55 #bb86fc, stop:0.85 #a855f7,
                stop:0.95 #9333ea, stop:1 #7c3aed);
        }
        
        #modern3DBtnInner:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6b21a8, stop:0.05 #7c3aed, stop:0.15 #9333ea,
                stop:0.45 #a855f7, stop:0.55 #bb86fc, stop:0.85 #d1a7ff,
                stop:0.95 #e6ccff, stop:1 #f5f0ff);
        }
        
        #modern3DBtnShadow {
            background: qradial-gradient(ellipse at center,
                rgba(107, 33, 168, 0.4) 0%, rgba(107, 33, 168, 0.2) 60%, transparent 80%);
            border: none;
            border-radius: 15px;
            margin: 0px 10px;
        }
        """)
    
    def accept_update(self):
        """Пользователь согласился на обновление"""
        print("✅ Пользователь согласился на обновление")
        self.result_value = True
        self.accept()
    
    def reject_update(self):
        """Пользователь отказался от обновления"""
        print("❌ Пользователь отказался от обновления")
        self.result_value = False
        self.reject()
    
    def exec(self):
        """Переопределяем exec для возврата результата"""
        super().exec()
        return self.result_value

class ModernUpdateProgressDialog(QDialog):
    """Компактный диалог прогресса обновления"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent, title="Обновление приложения", message="Подготовка к обновлению..."):
        super().__init__(parent)
        self.title = title
        self.message = message
        
        # Настройка диалога
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(450, 300)  # Компактный размер
        
        # Черный фон как в авторизации
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0a;
                border: 2px solid #bb86fc;
                border-radius: 15px;
            }
        """)
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация компактного интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)  # Компактные отступы
        layout.setSpacing(10)  # Маленькие промежутки
        
        # Заголовок
        self.create_header(layout)
        
        # Прогресс
        self.create_progress_content(layout)
        
        # Кнопка отмены
        self.create_cancel_button(layout)
    
    def create_header(self, layout):
        """Создает компактный заголовок"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(5)
        
        # Иконка загрузки (меньше)
        self.icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                self.icon_label.setPixmap(colored_pixmap)
        else:
            self.icon_label.setText("⏳")
            self.icon_label.setStyleSheet("font-size: 50px;")
        
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)
        
        # Название
        title_label = QLabel(self.title.upper())
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Пожалуйста, подождите...")
        subtitle_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_progress_content(self, layout):
        """Создает компактное содержимое прогресса"""
        # Сообщение о статусе
        self.message_label = QLabel(self.message)
        self.message_label.setStyleSheet("""
            font-size: 12px;
            color: #e8e8e8;
            background-color: transparent;
        """)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                text-align: center;
                color: #ffffff;
                font-weight: 700;
                font-size: 10px;
                min-height: 20px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #bb86fc, stop:0.5 #d1a7ff, stop:1 #bb86fc);
                border-radius: 6px;
                margin: 2px;
            }
        """)
        self.progress_bar.setVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Статус текст
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 10px;
            color: #bb86fc;
            background-color: transparent;
            margin: 5px 0px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(True)
        layout.addWidget(self.status_label)
    
    def create_cancel_button(self, layout):
        """Создает компактную кнопку отмены"""
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setFixedHeight(30)  # Компактная высота
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 700;
                padding: 6px 15px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
                border-color: #2a2a2a;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_update)
        layout.addWidget(self.cancel_btn)
    
    def show_progress(self):
        """Показывает прогресс бар (уже показан)"""
        pass
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            try:
                self.progress_bar.setValue(value)
            except RuntimeError:
                return
        
        if status_text and hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(status_text)
            except RuntimeError:
                return
    
    def cancel_update(self):
        """Отмена обновления"""
        print("❌ Пользователь отменил обновление")
        self.cancelled.emit()
        self.reject()

# Функции для интеграции с существующей системой
def show_modern_update_dialog(parent, version_info):
    """Показывает компактный диалог обновления"""
    print("🎭 Показ компактного диалога обновления...")
    
    dialog = ModernUpdateConfirmDialog(parent, version_info)
    result = dialog.exec()
    
    print(f"✅ Результат диалога: {result}")
    return result

def show_modern_progress_dialog(parent, title, message):
    """Показывает компактный диалог прогресса"""
    print("📥 Показ компактного диалога прогресса...")
    
    dialog = ModernUpdateProgressDialog(parent, title, message)
    dialog.show()
    dialog.show_progress()
    
    return dialog

class ModernUpdateConfirmOverlay(QMainWindow):
    """Окно подтверждения обновления в стиле авторизации"""
    
    update_accepted = pyqtSignal()
    update_rejected = pyqtSignal()
    
    def __init__(self, parent, version_info):
        super().__init__(parent)
        self.parent_widget = parent
        self.version_info = version_info
        
        # Настройка окна как стандартного Windows окна
        self.setWindowTitle("Обновление доступно")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setModal(True) if hasattr(self, 'setModal') else None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса в стиле авторизации"""
        self.setFixedSize(600, 800)
        
        # Черный фон как в авторизации
        self.setStyleSheet("QMainWindow { background-color: #0a0a0a; }")
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(50, 10, 50, 50)
        
        # Центральная карточка обновления
        self.update_card = QFrame()
        self.update_card.setObjectName("authCard")
        
        card_layout = QVBoxLayout(self.update_card)
        card_layout.setContentsMargins(50, 30, 50, 30)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        self.create_header(card_layout)
        
        # Информация об обновлении
        self.create_update_info(card_layout)
        
        # Кнопки
        self.create_buttons(card_layout)
        
        main_layout.addWidget(self.update_card)
        
        # Применяем стили
        self.setStyleSheet(self.get_overlay_styles())
    
    def create_header(self, layout):
        """Создает заголовок в стиле авторизации"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(2)
        
        # Иконка обновления
        icon_container = QHBoxLayout()
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                icon_label.setPixmap(colored_pixmap)
        else:
            icon_label.setText("🔄")
            icon_label.setStyleSheet("font-size: 100px;")
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(140, 140)
        
        icon_container.addWidget(icon_label)
        header_layout.addLayout(icon_container)
        
        # Название
        title_label = QLabel("ОБНОВЛЕНИЕ ДОСТУПНО")
        title_label.setObjectName("overlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Новая версия готова к установке")
        subtitle_label.setObjectName("overlaySubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_update_info(self, layout):
        """Создает информацию об обновлении"""
        info_text = self.format_version_info()
        
        info_label = QLabel(info_text)
        info_label.setObjectName("overlayDescription")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
    
    def format_version_info(self):
        """Форматирует информацию о версии"""
        try:
            from config.update_config import CURRENT_VERSION
        except ImportError:
            CURRENT_VERSION = "1.0.0"
        
        new_version = self.version_info.get('tag_name', 'Неизвестно')
        release_date = self.version_info.get('published_at', '')
        
        # Форматируем дату
        release_date_formatted = ''
        if release_date:
            from datetime import datetime
            try:
                date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                release_date_formatted = f"📅 {date_obj.strftime('%d.%m.%Y')}"
            except:
                pass
        
        # Описание изменений
        changes = self.version_info.get('body', '')
        if changes:
            if len(changes) > 150:
                changes = changes[:150] + '...'
        else:
            changes = "Улучшения и исправления ошибок"
        
        return f"""Текущая версия: {CURRENT_VERSION}
Новая версия: {new_version}

{release_date_formatted}

✦ {changes}
✦ Улучшенная производительность
✦ Исправления ошибок"""
    
    def create_buttons(self, layout):
        """Создает кнопки в стиле авторизации"""
        layout.addSpacing(-8)
        
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(25)
        
        # 3D кнопка обновления
        self.update_btn = Modern3DButton("СКАЧАТЬ И УСТАНОВИТЬ")
        self.update_btn.clicked.connect(self.accept_update)
        buttons_layout.addWidget(self.update_btn)
        
        # Обычная кнопка "Позже"
        self.later_btn = QPushButton("Позже")
        self.later_btn.setObjectName("overlayLaterBtn")
        self.later_btn.clicked.connect(self.reject_update)
        buttons_layout.addWidget(self.later_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_overlay_styles(self):
        """Стили для окна в стиле авторизации"""
        return """
        QMainWindow {
            background-color: #0a0a0a;
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
        
        #modern3DBtn {
            background: transparent;
            border: none;
        }
        
        #modern3DBtnInner {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f5f0ff,
                stop:0.05 #e6ccff,
                stop:0.15 #d1a7ff,
                stop:0.45 #bb86fc,
                stop:0.55 #a855f7,
                stop:0.85 #9333ea,
                stop:0.95 #7c3aed,
                stop:1 #6b21a8);
            
            border-top: 2px solid rgba(255, 255, 255, 0.3);
            border-left: 1px solid rgba(255, 255, 255, 0.2);
            border-right: 1px solid rgba(0, 0, 0, 0.2);
            border-bottom: 2px solid rgba(0, 0, 0, 0.3);
            
            border-radius: 25px;
            outline: 3px solid rgba(187, 134, 252, 0.4);
            outline-offset: 2px;
            
            color: #ffffff;
            font-weight: 800;
            font-size: 16px;
            padding: 22px 40px;
            min-height: 35px;
        }
        
        #modern3DBtnInner:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #faf8ff,
                stop:0.05 #f0e6ff,
                stop:0.15 #e6ccff,
                stop:0.45 #d1a7ff,
                stop:0.55 #bb86fc,
                stop:0.85 #a855f7,
                stop:0.95 #9333ea,
                stop:1 #7c3aed);
            
            border-top: 2px solid rgba(255, 255, 255, 0.4);
            border-left: 1px solid rgba(255, 255, 255, 0.3);
            border-right: 1px solid rgba(0, 0, 0, 0.3);
            border-bottom: 2px solid rgba(0, 0, 0, 0.4);
            
            outline: 4px solid rgba(187, 134, 252, 0.7);
            outline-offset: 3px;
        }
        
        #modern3DBtnInner:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6b21a8,
                stop:0.05 #7c3aed,
                stop:0.15 #9333ea,
                stop:0.45 #a855f7,
                stop:0.55 #bb86fc,
                stop:0.85 #d1a7ff,
                stop:0.95 #e6ccff,
                stop:1 #f5f0ff);
            
            border-top: 2px solid rgba(0, 0, 0, 0.4);
            border-left: 1px solid rgba(0, 0, 0, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.3);
            border-bottom: 2px solid rgba(255, 255, 255, 0.4);
            
            outline: 2px solid rgba(187, 134, 252, 0.3);
            outline-offset: 1px;
        }
        
        #modern3DBtnShadow {
            background: qradial-gradient(ellipse at center,
                rgba(107, 33, 168, 0.4) 0%,
                rgba(107, 33, 168, 0.3) 30%,
                rgba(107, 33, 168, 0.2) 60%,
                transparent 80%);
            border: none;
            border-radius: 25px;
            margin: 0px 20px;
        }
        
        #overlayLaterBtn {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            padding: 15px 25px;
            min-height: 25px;
        }
        
        #overlayLaterBtn:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        #overlayLaterBtn:pressed {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
        }
        """
    
    def accept_update(self):
        """Пользователь согласился на обновление"""
        print("✅ Пользователь согласился на обновление в окне")
        self.update_accepted.emit()
        self.close()
    
    def reject_update(self):
        """Пользователь отказался от обновления"""
        print("❌ Пользователь отказался от обновления в окне")
        self.update_rejected.emit()
        self.close()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if not hasattr(self, '_closing'):
            self._closing = True
            self.update_rejected.emit()
        event.accept()

class ModernUpdateProgressOverlay(QMainWindow):
    """Окно прогресса обновления в стиле авторизации"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent, title="Обновление приложения", message="Подготовка к обновлению..."):
        super().__init__(parent)
        self.parent_widget = parent
        self.title = title
        self.message = message
        
        # Настройка окна как стандартного Windows окна
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setModal(True) if hasattr(self, 'setModal') else None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса в стиле авторизации"""
        self.setFixedSize(600, 600)
        
        # Черный фон как в авторизации
        self.setStyleSheet("QMainWindow { background-color: #0a0a0a; }")
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.setContentsMargins(50, 30, 50, 30)
        
        # Центральная карточка прогресса
        self.progress_card = QFrame()
        self.progress_card.setObjectName("authCard")
        
        card_layout = QVBoxLayout(self.progress_card)
        card_layout.setContentsMargins(50, 30, 50, 30)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        self.create_header(card_layout)
        
        # Прогресс
        self.create_progress_content(card_layout)
        
        # Кнопка отмены
        self.create_cancel_button(card_layout)
        
        main_layout.addWidget(self.progress_card)
        
        # Применяем стили
        self.setStyleSheet(self.get_overlay_styles())
    
    def create_header(self, layout):
        """Создает заголовок в стиле авторизации"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(2)
        
        # Иконка загрузки (анимированная)
        icon_container = QHBoxLayout()
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                self.icon_label.setPixmap(colored_pixmap)
        else:
            self.icon_label.setText("⏳")
            self.icon_label.setStyleSheet("font-size: 100px;")
        
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(120, 120)
        
        # Добавляем анимацию пульсации
        self.pulse_animation = QPropertyAnimation(self.icon_label, b"windowOpacity")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setStartValue(0.5)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.start()
        
        icon_container.addWidget(self.icon_label)
        header_layout.addLayout(icon_container)
        
        # Название
        title_label = QLabel(self.title.upper())
        title_label.setObjectName("overlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Пожалуйста, подождите...")
        subtitle_label.setObjectName("overlaySubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_progress_content(self, layout):
        """Создает содержимое прогресса"""
        # Сообщение о статусе
        self.message_label = QLabel(self.message)
        self.message_label.setObjectName("overlayDescription")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Прогресс бар в стиле авторизации
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("overlayProgressBar")
        self.progress_bar.setVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Статус текст
        self.status_label = QLabel("")
        self.status_label.setObjectName("overlayStatusText")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(True)
        layout.addWidget(self.status_label)
    
    def create_cancel_button(self, layout):
        """Создает кнопку отмены"""
        layout.addSpacing(-8)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("overlayLaterBtn")
        self.cancel_btn.clicked.connect(self.cancel_update)
        layout.addWidget(self.cancel_btn)
    
    def get_overlay_styles(self):
        """Стили для окна в стиле авторизации"""
        return """
        QMainWindow {
            background-color: #0a0a0a;
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
        
        #overlayStatusText {
            font-size: 13px;
            color: #bb86fc;
            background-color: transparent;
            margin: 10px 0px;
        }
        
        #overlayProgressBar {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            text-align: center;
            color: #ffffff;
            font-weight: 700;
            font-size: 12px;
            min-height: 24px;
            padding: 2px;
        }
        
        #overlayProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.5 #d1a7ff, stop:1 #bb86fc);
            border-radius: 8px;
            margin: 2px;
        }
        
        #overlayLaterBtn {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            padding: 15px 25px;
            min-height: 25px;
        }
        
        #overlayLaterBtn:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        #overlayLaterBtn:pressed {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
        }
        """
    
    def show_progress(self):
        """Показывает прогресс бар (уже показан)"""
        pass
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            try:
                self.progress_bar.setValue(value)
            except RuntimeError:
                return
        
        if status_text and hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(status_text)
            except RuntimeError:
                return
    
    def cancel_update(self):
        """Отмена обновления"""
        print("❌ Пользователь отменил обновление в окне")
        self.cancelled.emit()
        self.close()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Останавливаем анимацию пульсации
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.stop()
        
        if not hasattr(self, '_closing'):
            self._closing = True
            self.cancelled.emit()
        event.accept()

# Функции для интеграции с существующей системой
def show_modern_update_dialog(parent, version_info):
    """Показывает современное окно обновления в стиле авторизации"""
    print("🎭 Показ современного окна обновления в стиле авторизации...")
    
    dialog = ModernUpdateConfirmOverlay(parent, version_info)
    dialog.show()
    
    # Используем QEventLoop для ожидания результата
    loop = QEventLoop()
    result = [False]
    
    def on_accepted():
        result[0] = True
        loop.quit()
    
    def on_rejected():
        result[0] = False
        loop.quit()
    
    dialog.update_accepted.connect(on_accepted)
    dialog.update_rejected.connect(on_rejected)
    
    loop.exec()
    
    print(f"✅ Результат современного диалога: {result[0]}")
    return result[0]

def show_modern_progress_dialog(parent, title, message):
    """Показывает современное окно прогресса в стиле авторизации"""
    print("📥 Показ современного окна прогресса в стиле авторизации...")
    
    dialog = ModernUpdateProgressOverlay(parent, title, message)
    dialog.show()
    dialog.show_progress()
    
    return dialog
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject_update()
        super().keyPressEvent(event)
        
        # Информация о версии
        version_text = self.format_version_info()
        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setWordWrap(True)
        version_label.setStyleSheet("""
            font-size: 14px; 
            color: #cbd5e1; 
            line-height: 1.6;
            margin: 10px 20px;
        """)
        version_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Кнопка "Скачать и установить"
        self.update_btn = self.create_update_button("📥 Скачать и установить")
        self.update_btn.clicked.connect(self.accept_update)
        buttons_layout.addWidget(self.update_btn)
        
        # Кнопка "Позже"
        self.later_btn = self.create_cancel_button("⏰ Позже")
        self.later_btn.clicked.connect(self.reject_update)
        buttons_layout.addWidget(self.later_btn)
        
        layout.addLayout(buttons_layout)
    
    def format_version_info(self):
        """Форматирует информацию о версии"""
        try:
            from config.update_config import CURRENT_VERSION
        except ImportError:
            CURRENT_VERSION = "1.0.0"
        
        new_version = self.version_info.get('tag_name', 'Неизвестно')
        release_date = self.version_info.get('published_at', '')
        
        # Форматируем дату
        release_date_formatted = ''
        if release_date:
            from datetime import datetime
            try:
                date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                release_date_formatted = f"📅 {date_obj.strftime('%d.%m.%Y')}"
            except:
                pass
        
        # Описание изменений
        changes = self.version_info.get('body', '')
        if changes:
            if len(changes) > 200:
                changes = changes[:200] + '...'
            changes = changes.replace('\n', '<br>')
        else:
            changes = "Описание изменений недоступно"
        
        return f"""
        <b>Новая версия: {new_version}</b><br>
        <i>Текущая версия: {CURRENT_VERSION}</i><br><br>
        {release_date_formatted}<br><br>
        <b>Изменения:</b><br>
        {changes}
        """
    
    def create_update_button(self, text):
        """Создает кнопку обновления в стиле приложения"""
        from modern_gui_interface import HoverLiftButton
        btn = HoverLiftButton(text)
        btn.setFixedSize(200, 50)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF, stop:0.3 #B855FF, stop:0.7 #D065FF, stop:1 #E06BFF);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B855FF, stop:0.3 #C965FF, stop:0.7 #E075FF, stop:1 #F080FF);
            }
        """)
        return btn
    
    def create_cancel_button(self, text):
        """Создает кнопку отмены в стиле приложения"""
        from modern_gui_interface import HoverLiftButton
        btn = HoverLiftButton(text)
        btn.setFixedSize(140, 50)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b7280, stop:0.3 #7c8591, stop:0.7 #9ca3af, stop:1 #a1a8b6);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c8591, stop:0.3 #8d94a2, stop:0.7 #a1a8b6, stop:1 #b5bcc7);
            }
        """)
        return btn
    
    def apply_blur_to_parent(self):
        """Применяет блюр к родительскому виджету"""
        if hasattr(self.parent_widget, 'animate_blur_in'):
            self.blur_effect = self.parent_widget.animate_blur_in(
                self.parent_widget.centralWidget(), 
                target_radius=15, 
                duration=400
            )
    
    def remove_blur_from_parent(self):
        """Убирает блюр с родительского виджета"""
        if hasattr(self.parent_widget, 'animate_blur_out') and hasattr(self, 'blur_effect'):
            self.parent_widget.animate_blur_out(
                self.parent_widget.centralWidget(), 
                self.blur_effect, 
                duration=300
            )
    
    def accept_update(self):
        """Пользователь согласился на обновление"""
        print("✅ Пользователь согласился на обновление в overlay")
        self.update_accepted.emit()
        self.close_overlay()
    
    def reject_update(self):
        """Пользователь отказался от обновления"""
        print("❌ Пользователь отказался от обновления в overlay")
        self.update_rejected.emit()
        self.close_overlay()
    
    def close_overlay(self):
        """Закрывает overlay с анимацией"""
        self.remove_blur_from_parent()
        
        # Анимация исчезновения
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.deleteLater)
        self.fade_animation.start()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject_update()
        super().keyPressEvent(event)


class ModernUpdateProgressOverlay(QWidget):
    """Overlay для прогресса обновления в стиле приложения"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent, title="Обновление приложения", message="Подготовка к обновлению..."):
        super().__init__(parent)
        self.parent_widget = parent
        
        # Настройка overlay
        self.setGeometry(parent.rect())
        self.setStyleSheet("background-color: transparent;")
        
        self.setup_ui(title, message)
        self.apply_blur_to_parent()
    
    def setup_ui(self, title, message):
        """Создает интерфейс overlay"""
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Контейнер для диалога
        dialog_container = QWidget()
        dialog_container.setFixedSize(600, 400)
        dialog_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(26, 26, 46, 0.95),
                    stop:0.5 rgba(22, 33, 62, 0.95),
                    stop:1 rgba(15, 52, 96, 0.95));
                border-radius: 20px;
                border: 2px solid rgba(165, 70, 255, 0.3);
            }
        """)
        
        # Layout для контейнера
        container_layout = QVBoxLayout(dialog_container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(30)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.create_progress_content(container_layout, title, message)
        
        layout.addWidget(dialog_container)
    
    def create_progress_content(self, layout, title, message):
        """Создает содержимое диалога прогресса"""
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
        self.message_label.setStyleSheet("""
            font-size: 14px; 
            color: #cbd5e1; 
            line-height: 1.6;
            margin: 10px 20px;
        """)
        layout.addWidget(self.message_label)
        
        # Прогресс бар
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
                    stop:0 #A546FF, stop:0.3 #B855FF, stop:0.7 #D065FF, stop:1 #E06BFF);
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
        
        # Кнопка отмены
        self.cancel_btn = self.create_cancel_button("❌ Отмена")
        self.cancel_btn.clicked.connect(self.cancel_update)
        layout.addWidget(self.cancel_btn, 0, Qt.AlignmentFlag.AlignCenter)
    
    def create_cancel_button(self, text):
        """Создает кнопку отмены"""
        from modern_gui_interface import HoverLiftButton
        btn = HoverLiftButton(text)
        btn.setFixedSize(140, 50)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b7280, stop:0.3 #7c8591, stop:0.7 #9ca3af, stop:1 #a1a8b6);
                border-radius: 25px;
                border-top: 1px solid rgba(255, 255, 255, 0.4);
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c8591, stop:0.3 #8d94a2, stop:0.7 #a1a8b6, stop:1 #b5bcc7);
            }
        """)
        return btn
    
    def show_progress(self):
        """Показывает прогресс бар"""
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.cancel_btn.setText("❌ Отмена")
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        # Проверяем что виджеты еще существуют
        if hasattr(self, 'progress_bar') and self.progress_bar:
            try:
                self.progress_bar.setValue(value)
            except RuntimeError:
                # Виджет уже удален
                return
        
        if status_text and hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(status_text)
            except RuntimeError:
                # Виджет уже удален
                return
    
    def apply_blur_to_parent(self):
        """Применяет блюр к родительскому виджету"""
        if hasattr(self.parent_widget, 'animate_blur_in'):
            self.blur_effect = self.parent_widget.animate_blur_in(
                self.parent_widget.centralWidget(), 
                target_radius=15, 
                duration=400
            )
    
    def remove_blur_from_parent(self):
        """Убирает блюр с родительского виджета"""
        if hasattr(self.parent_widget, 'animate_blur_out') and hasattr(self, 'blur_effect'):
            self.parent_widget.animate_blur_out(
                self.parent_widget.centralWidget(), 
                self.blur_effect, 
                duration=300
            )
    
    def cancel_update(self):
        """Отмена обновления"""
        print("❌ Пользователь отменил обновление в overlay")
        self.cancelled.emit()
        self.close_overlay()
    
    def close_overlay(self):
        """Закрывает overlay с анимацией"""
        self.remove_blur_from_parent()
        
        # Анимация исчезновения
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.deleteLater)
        self.fade_animation.start()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_update()
        super().keyPressEvent(event)


# Функции для интеграции с существующей системой
def show_modern_update_dialog(parent, version_info):
    """Показывает современный диалог обновления"""
    print("🎭 Показ современного overlay диалога обновления...")
    
    overlay = ModernUpdateConfirmOverlay(parent, version_info)
    overlay.show()
    
    # Используем QEventLoop для ожидания результата
    loop = QEventLoop()
    result = [False]  # Используем список для изменения из замыкания
    
    def on_accepted():
        result[0] = True
        loop.quit()
    
    def on_rejected():
        result[0] = False
        loop.quit()
    
    overlay.update_accepted.connect(on_accepted)
    overlay.update_rejected.connect(on_rejected)
    
    loop.exec()
    
    print(f"✅ Результат современного диалога: {result[0]}")
    return result[0]


def show_modern_progress_dialog(parent, title, message):
    """Показывает современный диалог прогресса"""
    print("📥 Показ современного overlay диалога прогресса...")
    
    overlay = ModernUpdateProgressOverlay(parent, title, message)
    overlay.show()
    overlay.show_progress()
    
    return overlay


class ModernUpdateProgressOverlay(QMainWindow):
    """Окно прогресса обновления в стиле авторизации"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent, title="Обновление приложения", message="Подготовка к обновлению..."):
        super().__init__(parent)
        self.parent_widget = parent
        self.title = title
        self.message = message
        
        # Настройка окна как стандартного Windows окна
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.setModal(True) if hasattr(self, 'setModal') else None
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса в стиле авторизации"""
        # Устанавливаем размер окна
        self.setFixedSize(600, 600)
        
        # Черный фон как в авторизации
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0a;
            }
        """)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.setContentsMargins(50, 30, 50, 30)
        
        # Центральная карточка прогресса
        self.progress_card = QFrame()
        self.progress_card.setObjectName("progressCard")
        
        card_layout = QVBoxLayout(self.progress_card)
        card_layout.setContentsMargins(50, 30, 50, 30)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        self.create_header(card_layout)
        
        # Прогресс
        self.create_progress_content(card_layout)
        
        # Кнопка отмены
        self.create_cancel_button(card_layout)
        
        main_layout.addWidget(self.progress_card)
        
        # Применяем стили
        self.setStyleSheet(self.get_overlay_styles())
    
    def create_header(self, layout):
        """Создает заголовок в стиле авторизации"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(2)
        
        # Иконка загрузки (анимированная)
        icon_container = QHBoxLayout()
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))  # #bb86fc
                painter.end()
                
                self.icon_label.setPixmap(colored_pixmap)
        else:
            self.icon_label.setText("⏳")
            self.icon_label.setStyleSheet("font-size: 100px;")
        
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(120, 120)
        
        # Добавляем анимацию пульсации вместо вращения (так как rotation не поддерживается)
        self.pulse_animation = QPropertyAnimation(self.icon_label, b"windowOpacity")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setStartValue(0.5)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)  # Бесконечно
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.start()
        
        icon_container.addWidget(self.icon_label)
        header_layout.addLayout(icon_container)
        
        # Название
        title_label = QLabel(self.title.upper())
        title_label.setObjectName("overlayTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Пожалуйста, подождите...")
        subtitle_label.setObjectName("overlaySubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_progress_content(self, layout):
        """Создает содержимое прогресса"""
        # Сообщение о статусе
        self.message_label = QLabel(self.message)
        self.message_label.setObjectName("overlayDescription")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        # Прогресс бар в стиле авторизации
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("overlayProgressBar")
        self.progress_bar.setVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Статус текст
        self.status_label = QLabel("")
        self.status_label.setObjectName("overlayStatusText")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(True)
        layout.addWidget(self.status_label)
    
    def create_cancel_button(self, layout):
        """Создает кнопку отмены"""
        layout.addSpacing(-8)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("overlayLaterBtn")
        self.cancel_btn.clicked.connect(self.cancel_update)
        layout.addWidget(self.cancel_btn)
    
    def get_overlay_styles(self):
        """Стили для окна в стиле авторизации"""
        return """
        QMainWindow {
            background-color: #0a0a0a;
        }
        
        #progressCard {
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
        
        #overlayStatusText {
            font-size: 13px;
            color: #bb86fc;
            background-color: transparent;
            margin: 10px 0px;
        }
        
        #overlayProgressBar {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            text-align: center;
            color: #ffffff;
            font-weight: 700;
            font-size: 12px;
            min-height: 24px;
            padding: 2px;
        }
        
        #overlayProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #bb86fc, stop:0.5 #d1a7ff, stop:1 #bb86fc);
            border-radius: 8px;
            margin: 2px;
        }
        
        #overlayLaterBtn {
            background-color: #2a2a2a;
            border: 2px solid #4a4a4a;
            border-radius: 12px;
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            padding: 15px 25px;
            min-height: 25px;
        }
        
        #overlayLaterBtn:hover {
            background-color: #3a3a3a;
            border-color: #5a5a5a;
        }
        
        #overlayLaterBtn:pressed {
            background-color: #1a1a1a;
            border-color: #2a2a2a;
        }
        """
    
    def show_progress(self):
        """Показывает прогресс бар (уже показан)"""
        pass
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        # Проверяем что виджеты еще существуют
        if hasattr(self, 'progress_bar') and self.progress_bar:
            try:
                self.progress_bar.setValue(value)
            except RuntimeError:
                return
        
        if status_text and hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(status_text)
            except RuntimeError:
                return
    
    def cancel_update(self):
        """Отмена обновления"""
        print("❌ Пользователь отменил обновление в окне")
        self.cancelled.emit()
        self.close()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Останавливаем анимацию пульсации
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.stop()
        
        if not hasattr(self, '_closing'):
            self._closing = True
            self.cancelled.emit()
        event.accept()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_update()
        super().keyPressEvent(event)


# Функции для интеграции с существующей системой
def show_modern_update_dialog(parent, version_info):
    """Показывает современное окно обновления в стиле авторизации"""
    print("🎭 Показ современного окна обновления в стиле авторизации...")
    
    dialog = ModernUpdateConfirmOverlay(parent, version_info)
    dialog.show()
    
    # Используем QEventLoop для ожидания результата
    loop = QEventLoop()
    result = [False]  # Используем список для изменения из замыкания
    
    def on_accepted():
        result[0] = True
        loop.quit()
    
    def on_rejected():
        result[0] = False
        loop.quit()
    
    dialog.update_accepted.connect(on_accepted)
    dialog.update_rejected.connect(on_rejected)
    
    loop.exec()
    
    print(f"✅ Результат современного диалога: {result[0]}")
    return result[0]


def show_modern_progress_dialog(parent, title, message):
    """Показывает современное окно прогресса в стиле авторизации"""
    print("📥 Показ современного окна прогресса в стиле авторизации...")
    
    dialog = ModernUpdateProgressOverlay(parent, title, message)
    dialog.show()
    dialog.show_progress()
    
    return dialog
    
    def enterEvent(self, event):
        """Анимация при наведении - подъем вверх"""
        self.is_hovered = True
        
        if self.hover_animation.state() == QPropertyAnimation.State.Running:
            self.hover_animation.stop()
            
        if self.original_pos is None:
            self.original_pos = self.pos()
        
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

class ModernUpdateConfirmOverlay(QWidget):
    """Кастомный диалог подтверждения обновления с прозрачным фоном и блюром"""
    
    update_accepted = pyqtSignal()
    update_rejected = pyqtSignal()
    
    def __init__(self, parent, version_info):
        super().__init__(parent)
        self.parent_widget = parent
        self.version_info = version_info
        
        # Делаем overlay на весь экран родителя
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Прозрачный фон
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
        
        # Применяем блюр к родительскому виджету
        self.apply_blur_to_parent()
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса с прозрачным фоном"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.setContentsMargins(30, 30, 30, 30)  # Компактные отступы
        
        # Центральная карточка с прозрачным фоном - увеличиваем размер
        self.update_card = QFrame()
        self.update_card.setFixedSize(700, 800)  # Увеличено с 600x700 до 700x800
        self.update_card.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0);
                border: none;
            }
        """)
        
        card_layout = QVBoxLayout(self.update_card)
        card_layout.setContentsMargins(15, 10, 15, 10)  # Компактные отступы
        card_layout.setSpacing(6)  # Компактные промежутки
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        self.create_header(card_layout)
        
        # Информация об обновлении
        self.create_update_info(card_layout)
        
        # Кнопки
        self.create_buttons(card_layout)
        
        main_layout.addWidget(self.update_card)
    
    def apply_blur_to_parent(self):
        """Применяет блюр к родительскому виджету"""
        if hasattr(self.parent_widget, 'animate_blur_in'):
            self.blur_effect = self.parent_widget.animate_blur_in(
                self.parent_widget.centralWidget(), 
                target_radius=15, 
                duration=400
            )
        elif hasattr(self.parent_widget, 'centralWidget'):
            # Создаем блюр эффект вручную
            from PyQt6.QtWidgets import QGraphicsBlurEffect
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(15)
            self.parent_widget.centralWidget().setGraphicsEffect(self.blur_effect)
    
    def remove_blur_from_parent(self):
        """Убирает блюр с родительского виджета"""
        if hasattr(self.parent_widget, 'animate_blur_out') and hasattr(self, 'blur_effect'):
            self.parent_widget.animate_blur_out(
                self.parent_widget.centralWidget(), 
                self.blur_effect, 
                duration=300
            )
        elif hasattr(self.parent_widget, 'centralWidget') and hasattr(self, 'blur_effect'):
            self.parent_widget.centralWidget().setGraphicsEffect(None)
    
    def create_header(self, layout):
        """Создает заголовок"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(5)  # Компактный промежуток
        
        # Иконка обновления
        icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                icon_label.setPixmap(colored_pixmap)
        else:
            icon_label.setText("🔄")
            icon_label.setStyleSheet("font-size: 80px;")
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # Заголовок
        title_label = QLabel("ОБНОВЛЕНИЕ ДОСТУПНО")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Новая версия готова к установке")
        subtitle_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_update_info(self, layout):
        """Создает информацию об обновлении"""
        info_text = self.format_version_info()
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("""
            font-size: 15px;
            color: #e8e8e8;
            background-color: transparent;
            line-height: 1.8;
            padding: 8px;
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setMinimumHeight(200)  # Минимальная высота для текста
        info_label.setMaximumWidth(580)   # Максимальная ширина для лучшего переноса
        layout.addWidget(info_label)
    
    def format_version_info(self):
        """Форматирует информацию о версии"""
        try:
            from config.update_config import CURRENT_VERSION
        except ImportError:
            CURRENT_VERSION = "1.0.0"
        
        new_version = self.version_info.get('tag_name', 'Неизвестно')
        release_date = self.version_info.get('published_at', '')
        
        # Форматируем дату
        release_date_formatted = ''
        if release_date:
            from datetime import datetime
            try:
                date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                release_date_formatted = f"📅 {date_obj.strftime('%d.%m.%Y')}"
            except:
                pass
        
        # Описание изменений
        changes = self.version_info.get('body', '')
        if changes:
            if len(changes) > 150:
                changes = changes[:150] + '...'
        else:
            changes = "Улучшения и исправления ошибок"
        
        return f"""Текущая версия: {CURRENT_VERSION}
Новая версия: {new_version}

{release_date_formatted}

✦ {changes}
✦ Улучшенная производительность
✦ Исправления ошибок"""
    
    def create_buttons(self, layout):
        """Создает кнопки в стиле приложения"""
        layout.addSpacing(8)  # Компактный отступ
        
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)  # Компактный промежуток
        
        # Главная кнопка обновления в стиле HoverLiftButton
        self.update_btn = HoverLiftButton("СКАЧАТЬ И УСТАНОВИТЬ")
        self.update_btn.setFixedHeight(60)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.clicked.connect(self.accept_update)
        
        # Применяем стили как у кнопки "НАЧАТЬ ПЕРЕВОД"
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
        
        buttons_layout.addWidget(self.update_btn)
        
        # Кнопка "Позже" в стиле вторичных кнопок
        self.later_btn = HoverLiftButton("Позже")
        self.later_btn.setFixedHeight(56)
        self.later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.later_btn.clicked.connect(self.reject_update)
        
        # Стиль вторичной кнопки
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
                font-size: 16px;
                padding: 15px 30px;
                min-height: 20px;
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
        
        buttons_layout.addWidget(self.later_btn)
        
        layout.addLayout(buttons_layout)
    
    def accept_update(self):
        """Пользователь согласился на обновление"""
        print("✅ Пользователь согласился на обновление")
        self.update_accepted.emit()
        self.close()
    
    def reject_update(self):
        """Пользователь отказался от обновления"""
        print("❌ Пользователь отказался от обновления")
        self.update_rejected.emit()
        self.close()
    
    def close(self):
        """Закрывает диалог"""
        self.remove_blur_from_parent()
        self.deleteLater()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject_update()
        super().keyPressEvent(event)

class ModernUpdateProgressOverlay(QWidget):
    """Кастомный диалог прогресса обновления с прозрачным фоном и блюром"""
    
    cancelled = pyqtSignal()
    
    def __init__(self, parent, title="Обновление приложения", message="Подготовка к обновлению..."):
        super().__init__(parent)
        self.parent_widget = parent
        self.title = title
        self.message = message
        
        # Делаем overlay на весь экран родителя
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Прозрачный фон
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
        
        # Применяем блюр к родительскому виджету
        self.apply_blur_to_parent()
        
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса с прозрачным фоном"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        main_layout.setContentsMargins(30, 30, 30, 30)  # Компактные отступы
        
        # Центральная карточка с прозрачным фоном - увеличиваем размер
        self.progress_card = QFrame()
        self.progress_card.setFixedSize(700, 600)  # Увеличено с 600x500 до 700x600
        self.progress_card.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0);
                border: none;
            }
        """)
        
        card_layout = QVBoxLayout(self.progress_card)
        card_layout.setContentsMargins(15, 10, 15, 10)  # Компактные отступы
        card_layout.setSpacing(6)  # Компактные промежутки
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Заголовок
        self.create_header(card_layout)
        
        # Прогресс
        self.create_progress_content(card_layout)
        
        # Кнопка отмены
        self.create_cancel_button(card_layout)
        
        main_layout.addWidget(self.progress_card)
    
    def apply_blur_to_parent(self):
        """Применяет блюр к родительскому виджету"""
        if hasattr(self.parent_widget, 'animate_blur_in'):
            self.blur_effect = self.parent_widget.animate_blur_in(
                self.parent_widget.centralWidget(), 
                target_radius=15, 
                duration=400
            )
        elif hasattr(self.parent_widget, 'centralWidget'):
            # Создаем блюр эффект вручную
            from PyQt6.QtWidgets import QGraphicsBlurEffect
            self.blur_effect = QGraphicsBlurEffect()
            self.blur_effect.setBlurRadius(15)
            self.parent_widget.centralWidget().setGraphicsEffect(self.blur_effect)
    
    def remove_blur_from_parent(self):
        """Убирает блюр с родительского виджета"""
        if hasattr(self.parent_widget, 'animate_blur_out') and hasattr(self, 'blur_effect'):
            self.parent_widget.animate_blur_out(
                self.parent_widget.centralWidget(), 
                self.blur_effect, 
                duration=300
            )
        elif hasattr(self.parent_widget, 'centralWidget') and hasattr(self, 'blur_effect'):
            self.parent_widget.centralWidget().setGraphicsEffect(None)
    
    def create_header(self, layout):
        """Создает заголовок"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(5)  # Компактный промежуток
        
        # Иконка загрузки (анимированная)
        self.icon_label = QLabel()
        icon_path = get_resource_path("upd.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в фиолетовый
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), QColor(187, 134, 252))
                painter.end()
                
                self.icon_label.setPixmap(colored_pixmap)
        else:
            self.icon_label.setText("⏳")
            self.icon_label.setStyleSheet("font-size: 70px;")
        
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)
        
        # Добавляем анимацию пульсации
        self.pulse_animation = QPropertyAnimation(self.icon_label, b"windowOpacity")
        self.pulse_animation.setDuration(1500)
        self.pulse_animation.setStartValue(0.5)
        self.pulse_animation.setEndValue(1.0)
        self.pulse_animation.setLoopCount(-1)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_animation.start()
        
        # Заголовок
        title_label = QLabel(self.title.upper())
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Пожалуйста, подождите...")
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #bb86fc;
            background-color: transparent;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_progress_content(self, layout):
        """Создает содержимое прогресса"""
        # Сообщение о статусе
        self.message_label = QLabel(self.message)
        self.message_label.setStyleSheet("""
            font-size: 15px;
            color: #e8e8e8;
            background-color: transparent;
            padding: 6px;
        """)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumHeight(40)  # Компактная высота
        layout.addWidget(self.message_label)
        
        # Прогресс бар в стиле приложения - увеличиваем высоту
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(42, 42, 42, 0.8);
                border: 2px solid rgba(74, 74, 74, 0.8);
                border-radius: 15px;
                text-align: center;
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                min-height: 30px;
                padding: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #A546FF, stop:0.5 #D065FF, stop:1 #E06BFF);
                border-radius: 12px;
                margin: 3px;
            }
        """)
        self.progress_bar.setVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Статус текст
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #bb86fc;
            background-color: transparent;
            margin: 15px 0px;
            padding: 10px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(True)
        self.status_label.setMinimumHeight(60)  # Минимальная высота
        layout.addWidget(self.status_label)
    
    def create_cancel_button(self, layout):
        """Создает кнопку отмены"""
        layout.addSpacing(5)  # Компактный отступ
        
        self.cancel_btn = HoverLiftButton("Отмена")
        self.cancel_btn.setFixedHeight(56)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_update)
        
        # Стиль кнопки отмены
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
                font-size: 16px;
                padding: 15px 30px;
                min-height: 20px;
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
        
        layout.addWidget(self.cancel_btn)
    
    def show_progress(self):
        """Показывает прогресс бар (уже показан)"""
        pass
    
    def update_progress(self, value, status_text=""):
        """Обновляет прогресс"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            try:
                self.progress_bar.setValue(value)
            except RuntimeError:
                return
        
        if status_text and hasattr(self, 'status_label') and self.status_label:
            try:
                self.status_label.setText(status_text)
            except RuntimeError:
                return
    
    def cancel_update(self):
        """Отмена обновления"""
        print("❌ Пользователь отменил обновление")
        self.cancelled.emit()
        self.close()
    
    def close(self):
        """Закрывает диалог"""
        # Останавливаем анимацию пульсации
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.stop()
        
        self.remove_blur_from_parent()
        self.deleteLater()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_update()
        super().keyPressEvent(event)

# Функции для интеграции с существующей системой
def show_modern_update_dialog(parent, version_info):
    """Показывает кастомный диалог обновления с прозрачным фоном"""
    print("🎭 Показ кастомного диалога обновления с прозрачным фоном...")
    
    overlay = ModernUpdateConfirmOverlay(parent, version_info)
    overlay.show()
    
    # Используем QEventLoop для ожидания результата
    loop = QEventLoop()
    result = [False]
    
    def on_accepted():
        result[0] = True
        loop.quit()
    
    def on_rejected():
        result[0] = False
        loop.quit()
    
    overlay.update_accepted.connect(on_accepted)
    overlay.update_rejected.connect(on_rejected)
    
    loop.exec()
    
    print(f"✅ Результат кастомного диалога: {result[0]}")
    return result[0]

def show_modern_progress_dialog(parent, title, message):
    """Показывает кастомный диалог прогресса с прозрачным фоном"""
    print("📥 Показ кастомного диалога прогресса с прозрачным фоном...")
    
    overlay = ModernUpdateProgressOverlay(parent, title, message)
    overlay.show()
    overlay.show_progress()
    
    return overlay
