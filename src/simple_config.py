#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простая и безопасная система управления конфигурацией
Без шифрования - полагается на .gitignore для защиты секретов
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigError(Exception):
    """Исключения для работы с конфигурацией"""
    pass


class SimpleConfig:
    """
    Простое управление конфигурацией с защитой через .gitignore
    
    Особенности:
    - Секретные файлы исключены из Git через .gitignore
    - Автоматическое создание конфигурации из примера
    - Безопасные права доступа к файлам
    - Валидация обязательных полей
    """
    
    def __init__(self, config_path: str = "config/bot_config.json"):
        self.config_path = Path(config_path)
        self.example_path = self.config_path.with_name(f"{self.config_path.stem}.example.json")
        self._config_data: Optional[Dict[str, Any]] = None
        
        # Обязательные поля конфигурации
        self.REQUIRED_FIELDS = {
            'BOT_TOKEN': 'Токен Telegram бота',
            'CHANNEL_ID': 'ID канала для проверки подписки'
        }
    
    def _create_config_from_example(self) -> None:
        """Создает конфигурацию из примера если она не существует"""
        if self.config_path.exists():
            return
        
        if not self.example_path.exists():
            print(f"❌ Файл примера не найден: {self.example_path}")
            return
        
        try:
            # Читаем пример
            with open(self.example_path, 'r', encoding='utf-8') as f:
                example_data = json.load(f)
            
            print(f"📝 Создаем конфигурацию из примера: {self.config_path}")
            print("⚠️  ВНИМАНИЕ: Необходимо заполнить реальные токены!")
            
            # Создаем папку если не существует
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем конфигурацию
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(example_data, f, ensure_ascii=False, indent=2)
            
            # Устанавливаем безопасные права доступа (только владелец)
            if os.name != 'nt':  # Unix/Linux
                os.chmod(self.config_path, 0o600)
            
            print(f"✅ Создан файл конфигурации: {self.config_path}")
            print("📝 Отредактируйте файл и укажите реальные токены")
            
        except Exception as e:
            raise ConfigError(f"Failed to create config from example: {e}")
    
    def _validate_config(self, config_data: Dict[str, Any]) -> None:
        """
        Валидирует конфигурацию
        
        Args:
            config_data: Данные конфигурации
            
        Raises:
            ConfigError: Если конфигурация невалидна
        """
        missing_fields = []
        placeholder_fields = []
        
        for field, description in self.REQUIRED_FIELDS.items():
            if field not in config_data:
                missing_fields.append(f"{field} ({description})")
            else:
                value = str(config_data[field]).strip()
                # Проверяем на placeholder значения
                if (not value or 
                    value.upper().startswith('YOUR_') or 
                    value.upper().startswith('PLACEHOLDER') or
                    value == 'YOUR_BOT_TOKEN_HERE' or
                    value == 'YOUR_CHANNEL_ID_HERE'):
                    placeholder_fields.append(f"{field} ({description})")
        
        if missing_fields:
            raise ConfigError(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")
        
        if placeholder_fields:
            raise ConfigError(f"Необходимо заполнить реальные значения: {', '.join(placeholder_fields)}")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Загружает конфигурацию
        
        Returns:
            Словарь с конфигурацией
            
        Raises:
            ConfigError: Если не удалось загрузить конфигурацию
        """
        # Создаем конфигурацию из примера если не существует
        self._create_config_from_example()
        
        if not self.config_path.exists():
            raise ConfigError(f"Файл конфигурации не найден: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Валидируем конфигурацию
            self._validate_config(config_data)
            
            self._config_data = config_data
            return config_data
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Ошибка парсинга JSON в {self.config_path}: {e}")
        except Exception as e:
            raise ConfigError(f"Ошибка загрузки конфигурации: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение из конфигурации
        
        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию
            
        Returns:
            Значение конфигурации
        """
        if self._config_data is None:
            try:
                self._config_data = self.load_config()
            except ConfigError:
                return default
        
        return self._config_data.get(key, default)
    
    def is_configured(self) -> bool:
        """
        Проверяет настроена ли конфигурация
        
        Returns:
            True если конфигурация валидна
        """
        try:
            self.load_config()
            return True
        except ConfigError:
            return False
    
    def get_config_status(self) -> Dict[str, Any]:
        """
        Возвращает статус конфигурации
        
        Returns:
            Информация о состоянии конфигурации
        """
        status = {
            'config_exists': self.config_path.exists(),
            'example_exists': self.example_path.exists(),
            'config_path': str(self.config_path),
            'example_path': str(self.example_path),
            'is_configured': False,
            'error': None
        }
        
        try:
            config_data = self.load_config()
            status['is_configured'] = True
            status['fields_count'] = len(config_data)
            status['required_fields_ok'] = all(
                key in config_data and str(config_data[key]).strip() 
                for key in self.REQUIRED_FIELDS.keys()
            )
        except ConfigError as e:
            status['error'] = str(e)
        
        return status


# Глобальный экземпляр для использования в приложении
config = SimpleConfig()


def get_bot_token() -> str:
    """
    Безопасно получает токен бота
    
    Returns:
        Токен бота или пустую строку если не найден
    """
    try:
        token = config.get('BOT_TOKEN', '')
        if not token:
            print("⚠️ BOT_TOKEN не найден в конфигурации")
            print(f"📝 Отредактируйте файл: {config.config_path}")
        return token
    except Exception as e:
        print(f"❌ Ошибка получения токена бота: {e}")
        return ''


def get_channel_id() -> str:
    """
    Безопасно получает ID канала
    
    Returns:
        ID канала или пустую строку если не найден
    """
    try:
        channel_id = config.get('CHANNEL_ID', '')
        if not channel_id:
            print("⚠️ CHANNEL_ID не найден в конфигурации")
            print(f"📝 Отредактируйте файл: {config.config_path}")
        return channel_id
    except Exception as e:
        print(f"❌ Ошибка получения ID канала: {e}")
        return ''


def check_config_status() -> None:
    """Проверяет и выводит статус конфигурации"""
    status = config.get_config_status()
    
    print("📋 Статус конфигурации:")
    print(f"  Файл конфигурации: {'✅' if status['config_exists'] else '❌'} {status['config_path']}")
    print(f"  Файл примера: {'✅' if status['example_exists'] else '❌'} {status['example_path']}")
    print(f"  Конфигурация валидна: {'✅' if status['is_configured'] else '❌'}")
    
    if status['error']:
        print(f"  Ошибка: {status['error']}")
    
    if status['is_configured']:
        print(f"  Полей в конфигурации: {status['fields_count']}")
        print(f"  Обязательные поля: {'✅' if status['required_fields_ok'] else '❌'}")


if __name__ == "__main__":
    # Тестирование системы
    print("📋 Тестирование системы конфигурации")
    
    check_config_status()
    
    # Тестируем получение токенов
    print("\n🔑 Тестирование получения токенов:")
    bot_token = get_bot_token()
    channel_id = get_channel_id()
    
    if bot_token and channel_id:
        print("✅ Токены загружены успешно")
        # Маскируем токены для безопасного вывода
        masked_token = bot_token[:10] + "..." + bot_token[-10:] if len(bot_token) > 20 else "[ТОКЕН]"
        print(f"  Bot Token: {masked_token}")
        print(f"  Channel ID: {channel_id}")
    else:
        print("❌ Не удалось загрузить токены")
        print("📝 Проверьте конфигурацию")