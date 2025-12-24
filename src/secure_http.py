#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Безопасный HTTP клиент с SSL verification и retry механизмами
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any
import time


class SecureHTTPError(Exception):
    """Исключения для безопасного HTTP клиента"""
    pass


class SecureHTTPClient:
    """
    Безопасный HTTP клиент с:
    - SSL verification
    - Retry механизмы
    - Таймауты
    - Защита от MITM атак
    """
    
    def __init__(self, 
                 connect_timeout: float = 5.0,
                 read_timeout: float = 10.0,
                 max_retries: int = 3,
                 backoff_factor: float = 1.0):
        """
        Инициализация безопасного HTTP клиента
        
        Args:
            connect_timeout: Таймаут подключения в секундах
            read_timeout: Таймаут чтения в секундах  
            max_retries: Максимальное количество повторов
            backoff_factor: Фактор увеличения задержки между повторами
        """
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.session = self._create_secure_session(max_retries, backoff_factor)
    
    def _create_secure_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        """
        Создает безопасную сессию с SSL verification и retry
        
        Args:
            max_retries: Максимальное количество повторов
            backoff_factor: Фактор увеличения задержки
            
        Returns:
            Настроенная сессия requests
        """
        session = requests.Session()
        
        # Включаем SSL verification
        session.verify = True
        
        # Настраиваем retry стратегию
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP коды для повтора
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Безопасные методы
            raise_on_status=False  # Не поднимаем исключение, обрабатываем сами
        )
        
        # Создаем адаптер с retry
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Устанавливаем безопасные заголовки
        session.headers.update({
            'User-Agent': 'RU-MINETOOLS/1.0 (Secure HTTP Client)',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            timeout: Optional[float] = None, **kwargs) -> requests.Response:
        """
        Безопасный GET запрос
        
        Args:
            url: URL для запроса
            params: Параметры запроса
            timeout: Кастомный таймаут (если None - используется дефолтный)
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            Response объект
            
        Raises:
            SecureHTTPError: При ошибках безопасности или сети
        """
        # Используем кастомный таймаут или дефолтный
        if timeout is None:
            timeout = (self.connect_timeout, self.read_timeout)
        elif isinstance(timeout, (int, float)):
            timeout = (self.connect_timeout, timeout)
        
        try:
            # Выполняем запрос
            response = self.session.get(
                url=url,
                params=params,
                timeout=timeout,
                **kwargs
            )
            
            # Проверяем статус ответа
            if response.status_code >= 400:
                raise SecureHTTPError(
                    f"HTTP {response.status_code}: {response.reason} for URL: {url}"
                )
            
            return response
            
        except requests.exceptions.SSLError as e:
            raise SecureHTTPError(f"SSL verification failed for {url}: {e}")
        except requests.exceptions.Timeout as e:
            raise SecureHTTPError(f"Request timeout for {url}: {e}")
        except requests.exceptions.ConnectionError as e:
            raise SecureHTTPError(f"Connection error for {url}: {e}")
        except requests.exceptions.RequestException as e:
            raise SecureHTTPError(f"Request failed for {url}: {e}")
    
    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None,
                 timeout: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """
        Безопасный GET запрос с автоматическим парсингом JSON
        
        Args:
            url: URL для запроса
            params: Параметры запроса
            timeout: Кастомный таймаут
            **kwargs: Дополнительные параметры
            
        Returns:
            Распарсенный JSON как словарь
            
        Raises:
            SecureHTTPError: При ошибках запроса или парсинга JSON
        """
        try:
            response = self.get(url, params, timeout, **kwargs)
            return response.json()
        except ValueError as e:
            raise SecureHTTPError(f"Invalid JSON response from {url}: {e}")
    
    def close(self):
        """Закрывает сессию и освобождает ресурсы"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Поддержка context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из context manager"""
        self.close()


# Глобальный экземпляр для использования в приложении
secure_http = SecureHTTPClient()


def safe_get(url: str, params: Optional[Dict[str, Any]] = None, 
             timeout: Optional[float] = None, **kwargs) -> Optional[requests.Response]:
    """
    Безопасная обертка для GET запросов с обработкой ошибок
    
    Args:
        url: URL для запроса
        params: Параметры запроса
        timeout: Таймаут запроса
        **kwargs: Дополнительные параметры
        
    Returns:
        Response объект или None при ошибке
    """
    try:
        return secure_http.get(url, params, timeout, **kwargs)
    except SecureHTTPError as e:
        print(f"❌ Ошибка HTTP запроса: {e}")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка HTTP запроса: {e}")
        return None


def safe_get_json(url: str, params: Optional[Dict[str, Any]] = None,
                  timeout: Optional[float] = None, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Безопасная обертка для GET запросов с JSON ответом
    
    Args:
        url: URL для запроса
        params: Параметры запроса
        timeout: Таймаут запроса
        **kwargs: Дополнительные параметры
        
    Returns:
        Распарсенный JSON или None при ошибке
    """
    try:
        return secure_http.get_json(url, params, timeout, **kwargs)
    except SecureHTTPError as e:
        print(f"❌ Ошибка HTTP JSON запроса: {e}")
        return None
    except Exception as e:
        print(f"❌ Неожиданная ошибка HTTP JSON запроса: {e}")
        return None


if __name__ == "__main__":
    # Тестирование безопасного HTTP клиента
    print("🔒 Тестирование безопасного HTTP клиента")
    
    # Тест 1: Обычный HTTPS запрос
    print("\n🧪 Тест 1: HTTPS запрос к httpbin.org")
    response = safe_get("https://httpbin.org/get", timeout=5)
    if response:
        print(f"✅ Успешно: {response.status_code}")
    else:
        print("❌ Ошибка запроса")
    
    # Тест 2: JSON запрос
    print("\n🧪 Тест 2: JSON запрос")
    json_data = safe_get_json("https://httpbin.org/json", timeout=5)
    if json_data:
        print(f"✅ JSON получен: {len(json_data)} полей")
    else:
        print("❌ Ошибка JSON запроса")
    
    # Тест 3: Запрос с параметрами
    print("\n🧪 Тест 3: Запрос с параметрами")
    params = {"test": "value", "param": "123"}
    response = safe_get("https://httpbin.org/get", params=params, timeout=5)
    if response:
        print(f"✅ Запрос с параметрами: {response.status_code}")
    else:
        print("❌ Ошибка запроса с параметрами")
    
    # Тест 4: Обработка ошибок (несуществующий домен)
    print("\n🧪 Тест 4: Обработка ошибок")
    response = safe_get("https://nonexistent-domain-12345.com", timeout=2)
    if response is None:
        print("✅ Ошибка корректно обработана")
    else:
        print("❌ Ошибка не обработана")
    
    print("\n✅ Тестирование завершено")