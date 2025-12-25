#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание ПРАВИЛЬНЫХ иконок для RU-MINETOOLS
По инструкциям: 16×16, 32×32, 48×48, 64×64, 128×128, 256×256 в одном ICO
"""

import os
import sys
from pathlib import Path

def create_app_icons():
    """Создает иконки приложения из logow.jpg ПРАВИЛЬНО"""
    try:
        from PIL import Image
    except ImportError:
        print("❌ Для создания иконок нужна библиотека Pillow")
        print("Установите: pip install Pillow")
        return False
    
    # Пути к файлам
    assets_dir = Path("assets")
    icons_dir = assets_dir / "icons"
    logo_path = assets_dir / "logow.PNG"  # Используем logow.PNG как оригинал
    
    # Создаем папку icons если её нет
    icons_dir.mkdir(exist_ok=True)
    
    # Проверяем наличие logow.PNG
    if not logo_path.exists():
        print(f"❌ Не найден файл: {logo_path}")
        print("Поместите logow.PNG в папку assets/")
        return False
    
    print(f"📖 Загружаем логотип: {logo_path}")
    
    try:
        # Загружаем оригинальный логотип
        original_logo = Image.open(logo_path)
        
        # Конвертируем в RGBA если нужно (для прозрачности)
        if original_logo.mode != 'RGBA':
            original_logo = original_logo.convert('RGBA')
        
        print(f"📏 Размер оригинала: {original_logo.size}")
        
        # ПРАВИЛЬНЫЕ размеры для Windows ICO (по инструкциям)
        ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        print("🎨 Создаем app_icon.ico с ПРАВИЛЬНЫМИ размерами...")
        
        # Создаем app_icon.ico с правильными размерами
        app_icon_path = icons_dir / "app_icon.ico"
        original_logo.save(
            app_icon_path,
            format='ICO',
            sizes=ico_sizes  # Все размеры в одном файле - это важно!
        )
        print(f"✅ Создан: {app_icon_path} с размерами: {ico_sizes}")
        
        # Создаем также простую версию icon.ico
        icon_path = icons_dir / "icon.ico"
        original_logo.save(
            icon_path,
            format='ICO',
            sizes=ico_sizes
        )
        print(f"✅ Создан: {icon_path}")
        
        # Создаем PNG версии для разных нужд
        print("🎨 Создаем PNG версии...")
        png_sizes = [16, 32, 48, 64, 128, 256]
        for size in png_sizes:
            resized = original_logo.resize((size, size), Image.Resampling.LANCZOS)
            png_path = icons_dir / f"app_icon_{size}.png"
            resized.save(png_path, format='PNG')
            print(f"✅ Создан: {png_path}")
        
        print("\n🎉 Иконки созданы ПРАВИЛЬНО!")
        print(f"📁 Папка с иконками: {icons_dir.absolute()}")
        
        # Показываем созданные файлы
        print("\n📦 Созданные файлы:")
        for icon_file in sorted(icons_dir.glob("*")):
            if icon_file.is_file():
                size_kb = icon_file.stat().st_size / 1024
                print(f"  📄 {icon_file.name} ({size_kb:.1f} KB)")
        
        print("\n✅ Теперь иконки будут четкими во всех размерах!")
        print("🔧 ICO содержит все размеры: 16×16, 32×32, 48×48, 64×64, 128×128, 256×256")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания иконок: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_simple_icons():
    """Создает простые иконки если нет Pillow"""
    print("🎨 Создание простых текстовых иконок...")
    
    icons_dir = Path("assets/icons")
    icons_dir.mkdir(exist_ok=True)
    
    # Создаем простой README с инструкциями
    readme_content = """# Иконки приложения

## 📁 Отсутствующие иконки

Для создания иконок приложения выполните:

```bash
pip install Pillow
python scripts/create_icons.py
```

## 📋 Необходимые файлы:

- `app_icon.ico` - Основная иконка приложения (используется в EXE)
- `icon.ico` - Альтернативная иконка

## 🔧 Правильные размеры ICO:

16×16, 32×32, 48×48, 64×64, 128×128, 256×256 - все в одном файле!

## 🌐 Онлайн конвертеры (НЕ рекомендуется):

- https://convertio.co/png-ico/
- https://www.icoconverter.com/
- https://favicon.io/favicon-converter/

⚠️ Лучше использовать Python + Pillow для правильного результата!
"""
    
    readme_path = icons_dir / "README.md"
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"✅ Создан: {readme_path}")
    
    return True

def main():
    """Основная функция"""
    print("🚀 Создание ПРАВИЛЬНЫХ иконок для RU-MINETOOLS")
    print("=" * 50)
    print("📋 Размеры: 16×16, 32×32, 48×48, 64×64, 128×128, 256×256")
    print("🔧 Источник: logow.PNG (1024×1024)")
    print("=" * 50)
    
    # Проверяем, что мы в корне проекта
    if not Path("assets").exists():
        print("❌ Папка assets не найдена!")
        print("Запустите скрипт из корня проекта")
        return
    
    # Пытаемся создать полноценные иконки
    if create_app_icons():
        print("\n🎯 Иконки готовы для сборки EXE!")
        print("Теперь можно запускать: python scripts/build_simple_exe.py")
    else:
        print("\n⚠️ Создаем простые заглушки...")
        create_simple_icons()
        print("\n💡 Для полноценных иконок установите Pillow и повторите")

if __name__ == "__main__":
    main()