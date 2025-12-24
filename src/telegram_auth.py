#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram авторизация для RU-MINETOOLS
Проверка подписки на канал перед входом в приложение
"""

import sys
import os
import json
import asyncio
import webbrowser
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPalette, QFontDatabase

# Для работы с Telegram Bot API
import requests
import hashlib
import hmac
import urllib.parse

class TelegramAuthWindow(QMainWindow):
    """Окно авторизации через Telegram"""
    
    # Сигнал для успешной авторизации
    auth_success = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Настройки Telegram бота (замените на свои)
        self.BOT_TOKEN = "YOUR_BOT_TOKEN"  # Токен вашего бота
        self.CHANNEL_USERNAME = "@your_channel"  # Имя канала для проверки подписки
        self.CHANNEL_ID = "-1001234567890"  # ID канала (получить через @userinfobot)
        
        # Файл для сохранения данных авторизации
        self.auth_file = "telegram_auth.json"
        
        self.user_data = None
        self.init_ui()
        
        # Проверяем сохраненную авторизацию
        self.check_saved_auth()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("RU-MINETOOLS - Авторизация")
        self.setFixedSize(500, 400)
        
        # Центрируем окно
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.move(
            (screen_geometry.width() - 500) // 2,
            (screen_geometry.height() - 400) // 2
        )
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Логотип и заголовок
        self.create_header(layout)
        
        # Описание
        self.create_description(layout)
        
        # Кнопки
        self.create_buttons(layout)
        
        # Статус
        self.create_status(layout)
        
        # Применяем стили
        self.setStyleSheet(self.get_styles())
    
    def create_header(self, layout):
        """Создает заголовок с логотипом"""
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(15)
        
        # Логотип
        logo_label = QLabel()
        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("🎮")
            logo_label.setStyleSheet("font-size: 48px;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Заголовок
        title_label = QLabel("RU-MINETOOLS")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel("Авторизация через Telegram")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addLayout(header_layout)
    
    def create_description(self, layout):
        """Создает описание процесса авторизации"""
        desc_frame = QFrame()
        desc_frame.setObjectName("descFrame")
        desc_layout = QVBoxLayout(desc_frame)
        desc_layout.setContentsMargins(20, 20, 20, 20)
        desc_layout.setSpacing(10)
        
        desc_text = QLabel(
            f"Для доступа к приложению необходимо:\n\n"
            f"1. Подписаться на канал {self.CHANNEL_USERNAME}\n"
            f"2. Авторизоваться через Telegram\n"
            f"3. Подтвердить подписку"
        )
        desc_text.setObjectName("description")
        desc_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc_text.setWordWrap(True)
        desc_layout.addWidget(desc_text)
        
        layout.addWidget(desc_frame)
    
    def create_buttons(self, layout):
        """Создает кнопки действий"""
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Кнопка подписки на канал
        self.subscribe_btn = QPushButton("📢 Подписаться на канал")
        self.subscribe_btn.setObjectName("subscribeButton")
        self.subscribe_btn.clicked.connect(self.open_channel)
        buttons_layout.addWidget(self.subscribe_btn)
        
        # Кнопка авторизации через Telegram
        self.auth_btn = QPushButton("🔐 Войти через Telegram")
        self.auth_btn.setObjectName("authButton")
        self.auth_btn.clicked.connect(self.start_telegram_auth)
        buttons_layout.addWidget(self.auth_btn)
        
        # Кнопка проверки подписки
        self.check_btn = QPushButton("✅ Проверить подписку")
        self.check_btn.setObjectName("checkButton")
        self.check_btn.clicked.connect(self.check_subscription)
        self.check_btn.setEnabled(False)
        buttons_layout.addWidget(self.check_btn)
        
        layout.addLayout(buttons_layout)
    
    def create_status(self, layout):
        """Создает область статуса"""
        self.status_label = QLabel("Нажмите 'Подписаться на канал' для начала")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def open_channel(self):
        """Открывает канал в браузере"""
        channel_url = f"https://t.me/{self.CHANNEL_USERNAME[1:]}"  # Убираем @
        webbrowser.open(channel_url)
        
        self.status_label.setText("Канал открыт в браузере. После подписки нажмите 'Войти через Telegram'")
        self.auth_btn.setEnabled(True)
    
    def start_telegram_auth(self):
        """Запускает процесс авторизации через Telegram"""
        # В реальном приложении здесь будет Telegram Login Widget
        # Для демонстрации используем упрощенный подход
        
        self.status_label.setText("Открываем Telegram для авторизации...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        
        # Имитируем процесс авторизации
        QTimer.singleShot(2000, self.simulate_auth_success)
    
    def simulate_auth_success(self):
        """Имитирует успешную авторизацию (для демонстрации)"""
        # В реальном приложении здесь будут данные от Telegram
        self.user_data = {
            "id": 123456789,
            "first_name": "Иван",
            "last_name": "Иванов",
            "username": "ivan_ivanov",
            "auth_date": int(datetime.now().timestamp())
        }
        
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Авторизация успешна! Привет, {self.user_data['first_name']}!")
        self.check_btn.setEnabled(True)
        self.auth_btn.setText("✅ Авторизован")
        self.auth_btn.setEnabled(False)
    
    def check_subscription(self):
        """Проверяет подписку на канал"""
        if not self.user_data:
            self.show_error("Сначала необходимо авторизоваться")
            return
        
        self.status_label.setText("Проверяем подписку на канал...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # Запускаем проверку в отдельном потоке
        self.check_thread = SubscriptionCheckThread(
            self.BOT_TOKEN, 
            self.CHANNEL_ID, 
            self.user_data["id"]
        )
        self.check_thread.result_ready.connect(self.on_subscription_checked)
        self.check_thread.start()
    
    def on_subscription_checked(self, is_subscribed):
        """Обработка результата проверки подписки"""
        self.progress_bar.setVisible(False)
        
        if is_subscribed:
            self.status_label.setText("✅ Подписка подтверждена! Добро пожаловать!")
            self.save_auth_data()
            
            # Задержка перед закрытием окна
            QTimer.singleShot(1500, self.auth_success.emit)
        else:
            self.status_label.setText("❌ Подписка не найдена. Подпишитесь на канал и попробуйте снова.")
            self.show_error("Для доступа к приложению необходимо подписаться на канал")
    
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
            print(f"Ошибка сохранения авторизации: {e}")
    
    def check_saved_auth(self):
        """Проверяет сохраненную авторизацию"""
        if not os.path.exists(self.auth_file):
            return
        
        try:
            with open(self.auth_file, 'r', encoding='utf-8') as f:
                auth_data = json.load(f)
            
            # Проверяем срок действия
            expires = datetime.fromisoformat(auth_data["expires"])
            if datetime.now() < expires:
                self.user_data = auth_data["user_data"]
                self.status_label.setText(f"Добро пожаловать, {self.user_data['first_name']}!")
                
                # Автоматически входим в приложение
                QTimer.singleShot(1000, self.auth_success.emit)
            else:
                # Авторизация истекла
                os.remove(self.auth_file)
                
        except Exception as e:
            print(f"Ошибка загрузки авторизации: {e}")
            if os.path.exists(self.auth_file):
                os.remove(self.auth_file)
    
    def show_error(self, message):
        """Показывает сообщение об ошибке"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Ошибка авторизации")
        msg_box.setText(message)
        msg_box.setStyleSheet(self.get_styles())
        msg_box.exec()
    
    def get_styles(self):
        """Возвращает стили для окна авторизации"""
        return """
        QMainWindow {
            background-color: #0a0a0a;
            color: #ffffff;
        }
        
        QWidget {
            background-color: transparent;
            color: #ffffff;
            font-family: "Segoe UI", "Arial", sans-serif;
        }
        
        #title {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }
        
        #subtitle {
            font-size: 14px;
            font-weight: 400;
            color: #b0b0b0;
        }
        
        #descFrame {
            background-color: #0f0f0f;
            border: 1px solid #1a1a1a;
            border-radius: 12px;
        }
        
        #description {
            font-size: 13px;
            color: #e0e0e0;
            line-height: 1.4;
        }
        
        QPushButton {
            background-color: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            padding: 12px 20px;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #2a2a2a;
            border-color: #3a3a3a;
        }
        
        QPushButton:pressed {
            background-color: #333333;
        }
        
        QPushButton:disabled {
            background-color: #0f0f0f;
            border-color: #1a1a1a;
            color: #666666;
        }
        
        #subscribeButton {
            background-color: #1e88e5;
            border-color: #1976d2;
        }
        
        #subscribeButton:hover {
            background-color: #1976d2;
            border-color: #1565c0;
        }
        
        #authButton {
            background-color: #00acc1;
            border-color: #0097a7;
        }
        
        #authButton:hover {
            background-color: #0097a7;
            border-color: #00838f;
        }
        
        #checkButton {
            background-color: #43a047;
            border-color: #388e3c;
        }
        
        #checkButton:hover {
            background-color: #388e3c;
            border-color: #2e7d32;
        }
        
        #status {
            font-size: 13px;
            color: #b0b0b0;
        }
        
        #progressBar {
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            background-color: #1a1a1a;
            height: 8px;
        }
        
        #progressBar::chunk {
            background-color: #bb86fc;
            border-radius: 3px;
        }
        
        QMessageBox {
            background-color: #0a0a0a;
            color: #ffffff;
        }
        
        QMessageBox QPushButton {
            min-width: 80px;
        }
        """


class SubscriptionCheckThread(QThread):
    """Поток для проверки подписки на канал"""
    
    result_ready = pyqtSignal(bool)
    
    def __init__(self, bot_token, channel_id, user_id):
        super().__init__()
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.user_id = user_id
    
    def run(self):
        """Проверяет подписку пользователя на канал"""
        try:
            # Для демонстрации всегда возвращаем True
            # В реальном приложении здесь будет запрос к Telegram Bot API
            
            # Имитируем задержку сетевого запроса
            self.msleep(2000)
            
            # Реальный код для проверки подписки:
            # url = f"https://api.telegram.org/bot{self.bot_token}/getChatMember"
            # params = {
            #     "chat_id": self.channel_id,
            #     "user_id": self.user_id
            # }
            # response = requests.get(url, params=params)
            # data = response.json()
            # 
            # if data["ok"]:
            #     status = data["result"]["status"]
            #     is_subscribed = status in ["member", "administrator", "creator"]
            #     self.result_ready.emit(is_subscribed)
            # else:
            #     self.result_ready.emit(False)
            
            # Для демонстрации
            self.result_ready.emit(True)
            
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            self.result_ready.emit(False)


def main():
    """Тестирование окна авторизации"""
    app = QApplication(sys.argv)
    
    auth_window = TelegramAuthWindow()
    auth_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()