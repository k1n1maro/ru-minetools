#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Уведомления системы обновлений с прозрачным фоном и кнопками в стиле приложения
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
    
    def paintEvent(self, event):
        """Переопределяем отрисовку для добавления сглаживания"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)
        
        super().paintEvent(event)
    
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

class UpdateNotificationOverlay(QWidget):
    """Универсальный кастомный диалог для уведомлений обновлений с прозрачным фоном и блюром"""
    
    def __init__(self, parent, title, message, icon_type="info", buttons=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.title = title
        self.message = message
        self.icon_type = icon_type  # "info", "error", "warning", "success"
        self.buttons = buttons or ["OK"]
        self.result = None
        
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
        main_layout.setContentsMargins(20, 20, 20, 20)  # Уменьшено с 30 до 20
        
        # Центральная карточка с прозрачным фоном - оптимальный размер для текста
        self.notification_card = QFrame()
        self.notification_card.setFixedSize(550, 380)  # Увеличено с 450x350 до 550x380 для размещения текста
        self.notification_card.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0);
                border: none;
            }
        """)
        
        card_layout = QVBoxLayout(self.notification_card)
        card_layout.setContentsMargins(15, 10, 15, 10)  # Уменьшены отступы с 30,25 до 20,15
        card_layout.setSpacing(1) # Уменьшены промежутки с 15 до 10
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Иконка
        self.create_icon(card_layout)
        
        # Заголовок
        self.create_title(card_layout)
        
        # Сообщение
        self.create_message(card_layout)
        
        # Кнопки
        self.create_buttons(card_layout)
        
        main_layout.addWidget(self.notification_card)
    
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
    
    def create_icon(self, layout):
        """Создает иконку в зависимости от типа"""
        icon_container = QHBoxLayout()
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        
        # Выбираем иконку и цвет в зависимости от типа
        if self.icon_type == "error":
            icon_text = "❌"
            icon_color = QColor(231, 76, 60)  # Красный
        elif self.icon_type == "warning":
            icon_text = "⚠️"
            icon_color = QColor(241, 196, 15)  # Желтый
        elif self.icon_type == "success":
            icon_text = "✅"
            icon_color = QColor(46, 204, 113)  # Зеленый
        else:  # info
            icon_text = "ℹ️"
            icon_color = QColor(187, 134, 252)  # Фиолетовый
        
        # Пробуем загрузить иконку из файла
        if self.icon_type == "error":
            icon_path = get_resource_path("error.png")
        elif self.icon_type == "warning":
            icon_path = get_resource_path("warning.png")
        elif self.icon_type == "success":
            icon_path = get_resource_path("success.png")
        else:
            icon_path = get_resource_path("info.png")
        
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,  # Вернули оригинальный размер
                                            Qt.TransformationMode.SmoothTransformation)
                
                # Перекрашиваем в нужный цвет
                colored_pixmap = QPixmap(scaled_pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(colored_pixmap.rect(), icon_color)
                painter.end()
                
                icon_label.setPixmap(colored_pixmap)
            else:
                icon_label.setText(icon_text)
                icon_label.setStyleSheet(f"font-size: 50px;")  # Вернули оригинальный размер
        else:
            icon_label.setText(icon_text)
            icon_label.setStyleSheet(f"font-size: 50px;")  # Вернули оригинальный размер
        
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(60, 60)  # Вернули оригинальный размер
        
        icon_container.addWidget(icon_label)
        layout.addLayout(icon_container)
    
    def create_title(self, layout):
        """Создает заголовок"""
        title_label = QLabel(self.title.upper())
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: 800;
            color: #ffffff;
            background-color: transparent;
            margin: 3px 0px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
    
    def create_message(self, layout):
        """Создает сообщение"""
        message_label = QLabel(self.message)
        message_label.setStyleSheet("""
            font-size: 15px;
            color: #e8e8e8;
            background-color: transparent;
            margin: 5px 0px;
            padding: 8px;
            line-height: 1.6;
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setMinimumHeight(60)  # Компактная высота
        message_label.setMaximumWidth(500)   # Увеличена ширина с 400 до 500 для размещения текста
        layout.addWidget(message_label)
    
    def create_buttons(self, layout):
        """Создает кнопки в стиле HoverLiftButton"""
        layout.addSpacing(3)  # Компактный отступ
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)  # Компактный промежуток
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for button_text in self.buttons:
            btn = HoverLiftButton(button_text)
            btn.setFixedHeight(56)  # Вернули оригинальную высоту
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Стиль кнопки в зависимости от текста
            if button_text.lower() in ["ok", "да", "принять", "скачать", "установить"]:
                # Главная кнопка
                btn.setStyleSheet("""
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
            else:
                # Вторичная кнопка
                btn.setStyleSheet("""
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
                        min-width: 100px;
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
            
            btn.clicked.connect(lambda checked, text=button_text: self.button_clicked(text))
            buttons_layout.addWidget(btn)
        
        layout.addLayout(buttons_layout)
    
    def button_clicked(self, button_text):
        """Обработка нажатия кнопки"""
        self.result = button_text
        self.close()
    
    def close(self):
        """Закрывает диалог"""
        self.remove_blur_from_parent()
        self.deleteLater()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.result = "Cancel"
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Enter нажимает первую кнопку
            if self.buttons:
                self.result = self.buttons[0]
                self.close()
        super().keyPressEvent(event)


# Функции для замены стандартных QMessageBox
def show_update_info(parent, title, message):
    """Показывает информационное уведомление"""
    return show_update_notification(parent, title, message, "info", ["OK"])

def show_update_warning(parent, title, message):
    """Показывает предупреждение"""
    return show_update_notification(parent, title, message, "warning", ["OK"])

def show_update_error(parent, title, message):
    """Показывает ошибку"""
    return show_update_notification(parent, title, message, "error", ["OK"])

def show_update_success(parent, title, message):
    """Показывает успешное завершение"""
    return show_update_notification(parent, title, message, "success", ["OK"])

def show_update_question(parent, title, message, buttons=None):
    """Показывает вопрос с кнопками"""
    buttons = buttons or ["Да", "Нет"]
    return show_update_notification(parent, title, message, "info", buttons)

def show_update_notification(parent, title, message, icon_type="info", buttons=None):
    """Показывает уведомление с прозрачным фоном"""
    print(f"🔔 Показ уведомления: {title}")
    
    overlay = UpdateNotificationOverlay(parent, title, message, icon_type, buttons)
    overlay.show()
    
    # Используем QEventLoop для ожидания результата
    loop = QEventLoop()
    
    def check_result():
        if overlay.result is not None:
            loop.quit()
    
    # Проверяем результат каждые 100мс
    timer = QTimer()
    timer.timeout.connect(check_result)
    timer.start(100)
    
    # Ждем закрытия overlay
    loop.exec()
    
    timer.stop()
    result = overlay.result or "Cancel"
    
    print(f"✅ Результат уведомления: {result}")
    return result