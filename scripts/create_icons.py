#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание простых иконок для навигации
"""

from PIL import Image, ImageDraw
import os

def create_home_icon():
    """Создает иконку дома"""
    size = (24, 24)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Рисуем домик
    # Крыша (треугольник)
    draw.polygon([(12, 4), (6, 10), (18, 10)], fill=(255, 255, 255, 255))
    # Стены (прямоугольник)
    draw.rectangle([8, 10, 16, 20], fill=(255, 255, 255, 255))
    # Дверь
    draw.rectangle([11, 15, 13, 20], fill=(0, 0, 0, 255))
    
    img.save('pr/home.png')
    print("Создана иконка home.png")

def create_trans_icon():
    """Создает иконку перевода"""
    size = (24, 24)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Рисуем символ перевода (две буквы)
    # Буква A
    draw.polygon([(4, 18), (6, 6), (8, 18)], outline=(255, 255, 255, 255), width=2)
    draw.line([(5, 14), (7, 14)], fill=(255, 255, 255, 255), width=2)
    
    # Стрелка
    draw.line([(10, 12), (14, 12)], fill=(255, 255, 255, 255), width=2)
    draw.polygon([(14, 10), (16, 12), (14, 14)], fill=(255, 255, 255, 255))
    
    # Буква Я (упрощенная)
    draw.rectangle([16, 6, 18, 18], fill=(255, 255, 255, 255))
    draw.rectangle([18, 6, 20, 10], fill=(255, 255, 255, 255))
    draw.rectangle([18, 12, 20, 18], fill=(255, 255, 255, 255))
    draw.line([(16, 12), (20, 18)], fill=(255, 255, 255, 255), width=2)
    
    img.save('pr/trans.png')
    print("Создана иконка trans.png")

if __name__ == "__main__":
    try:
        create_home_icon()
        create_trans_icon()
        print("Иконки созданы успешно!")
    except ImportError:
        print("Для создания иконок нужна библиотека Pillow: pip install Pillow")
    except Exception as e:
        print(f"Ошибка создания иконок: {e}")