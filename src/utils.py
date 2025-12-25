#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для работы с ресурсами в новой структуре проекта
"""

import sys
import os
from pathlib import Path

def get_resource_path(filename, resource_type="assets"):
    """
    Получает правильный путь к ресурсу для скомпилированной и обычной версии
    
    Args:
        filename: имя файла ресурса
        resource_type: тип ресурса (assets, config)
    """
    if getattr(sys, 'frozen', False):
        # Скомпилированная версия (PyInstaller)
        base_path = Path(sys._MEIPASS)
    else:
        # Обычная версия - ищем относительно корня проекта
        current_file = Path(__file__).resolve()
        
        # Поднимаемся до корня проекта (где есть папки src, assets, config)
        project_root = current_file.parent
        while project_root.parent != project_root:
            if (project_root / "src").exists() and (project_root / "assets").exists():
                break
            project_root = project_root.parent
        
        base_path = project_root
    
    # Формируем путь к ресурсу
    resource_path = base_path / resource_type / filename
    
    if resource_path.exists():
        return resource_path
    
    # Если не найден, пробуем в корне
    fallback_path = base_path / filename
    if fallback_path.exists():
        return fallback_path
    
    # Возвращаем оригинальный путь как последний вариант
    return base_path / resource_type / filename

def get_config_path(filename):
    """Получает путь к конфигурационному файлу"""
    return get_resource_path(filename, "config")

def get_asset_path(filename):
    """Получает путь к файлу ресурсов"""
    return get_resource_path(filename, "assets")
