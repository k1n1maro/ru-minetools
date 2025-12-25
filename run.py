#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска RU-MINETOOLS
"""

import sys
import os
from pathlib import Path

# Добавляем пути к модулям
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "config"))

# Запускаем главное приложение
if __name__ == "__main__":
    from modern_gui_interface import main
    main()
