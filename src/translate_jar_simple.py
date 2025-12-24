#!/usr/bin/env python3
"""
Простой переводчик JAR модов Minecraft
Аналогично main.py для квестов
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с кэшированием и батчингом
"""

import os
import json
import zipfile
import tempfile
import shutil
import time
import pickle
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from translatepy import Translator
from functools import lru_cache

translator = Translator()

# Глобальный кэш переводов
TRANSLATION_CACHE = {}
CACHE_FILE = "translation_cache.pkl"

def load_translation_cache():
    """Загружает кэш переводов из файла"""
    global TRANSLATION_CACHE
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'rb') as f:
                loaded_cache = pickle.load(f)
                TRANSLATION_CACHE.update(loaded_cache)  # Используем update вместо присваивания
            print(f"📦 Загружен кэш: {len(TRANSLATION_CACHE)} переводов")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки кэша: {e}")
        TRANSLATION_CACHE = {}

def save_translation_cache():
    """Сохраняет кэш переводов в файл"""
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(TRANSLATION_CACHE, f)
        print(f"💾 Сохранен кэш: {len(TRANSLATION_CACHE)} переводов")
    except Exception as e:
        print(f"⚠️ Ошибка сохранения кэша: {e}")

def get_cache_key(text, lang_to):
    """Создает ключ для кэша"""
    return hashlib.md5(f"{text}:{lang_to}".encode()).hexdigest()

def analyze_jar_files(jar_files, progress_callback=None):
    """
    Анализирует JAR файлы перед переводом и возвращает статистику
    
    Returns:
        dict: {
            'total_files': int,
            'need_translation': list,  # JAR файлы, которые нуждаются в переводе
            'already_translated': list,  # JAR файлы, которые уже переведены
            'no_files': list,  # JAR файлы без lang/patchouli файлов
            'no_strings': list,  # JAR файлы без строк для перевода
            'stats': {
                'total_lang_files': int,
                'total_patchouli_files': int,
                'total_strings': int
            }
        }
    """
    result = {
        'total_files': len(jar_files),
        'need_translation': [],
        'already_translated': [],
        'no_files': [],
        'no_strings': [],
        'stats': {
            'total_lang_files': 0,
            'total_patchouli_files': 0,
            'total_strings': 0
        }
    }
    
    for i, jar_file in enumerate(jar_files):
        if progress_callback:
            progress = (i / len(jar_files)) * 100
            progress_callback(progress, f"Анализ {jar_file.name}...")
        
        try:
            jar_info = {
                'file': jar_file,
                'lang_files': 0,
                'patchouli_files': 0,
                'strings_to_translate': 0,
                'already_translated_strings': 0,
                'status': 'unknown',
                'has_lang_files': False,
                'has_patchouli_files': False,
                'has_russian_lang': False,
                'has_russian_patchouli': False
            }
            
            # Проверяем наличие файлов и переводов
            lang_files = find_lang_files(jar_file)
            en_us_lang_files = [f for f in lang_files if 'en_us.json' in f]
            patchouli_files = find_patchouli_files(jar_file)
            
            jar_info['has_lang_files'] = len(en_us_lang_files) > 0
            jar_info['has_patchouli_files'] = len(patchouli_files) > 0
            jar_info['has_russian_lang'] = has_russian_lang(jar_file)
            jar_info['has_russian_patchouli'] = has_russian_patchouli(jar_file)
            
            # Если нет ни lang, ни patchouli файлов - нечего переводить
            if not jar_info['has_lang_files'] and not jar_info['has_patchouli_files']:
                jar_info['status'] = 'no_files'
                result['no_files'].append(jar_info)
                continue
            
            # Функция для подсчета переведенных строк (рекурсивная)
            def count_translated_strings(obj):
                count = 0
                if isinstance(obj, dict):
                    for value in obj.values():
                        if isinstance(value, str) and any('\u0400' <= char <= '\u04FF' for char in value):
                            count += 1
                        elif isinstance(value, (dict, list)):
                            count += count_translated_strings(value)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, str) and any('\u0400' <= char <= '\u04FF' for char in item):
                            count += 1
                        elif isinstance(item, (dict, list)):
                            count += count_translated_strings(item)
                return count
            
            # Анализируем Lang файлы
            if jar_info['has_lang_files']:
                jar_info['lang_files'] = len(en_us_lang_files)
                
                # Анализируем содержимое lang файлов
                with zipfile.ZipFile(jar_file, 'r') as jar:
                    for lang_file in en_us_lang_files:
                        try:
                            with jar.open(lang_file) as f:
                                content = json.load(f)
                            
                            file_strings = count_strings_in_json(content)
                            jar_info['strings_to_translate'] += file_strings
                            
                            # Подсчитываем уже переведенные строки (рекурсивно)
                            jar_info['already_translated_strings'] += count_translated_strings(content)
                                        
                        except Exception:
                            continue
            
            # Анализируем Patchouli файлы
            if jar_info['has_patchouli_files']:
                jar_info['patchouli_files'] = len(patchouli_files)
                
                # Анализируем содержимое patchouli файлов
                with zipfile.ZipFile(jar_file, 'r') as jar:
                    for patchouli_file in patchouli_files:
                        try:
                            with jar.open(patchouli_file) as f:
                                content = json.load(f)
                            
                            file_strings = count_strings_in_json(content)
                            jar_info['strings_to_translate'] += file_strings
                            
                            # Подсчитываем уже переведенные строки (рекурсивно)
                            jar_info['already_translated_strings'] += count_translated_strings(content)
                                        
                        except Exception:
                            continue
            
            # Определяем статус файла на основе более точной логики
            if jar_info['strings_to_translate'] == 0:
                # Есть файлы, но нет строк для перевода
                jar_info['status'] = 'no_strings'
                result['no_strings'].append(jar_info)
                
            elif jar_info['already_translated_strings'] == jar_info['strings_to_translate'] and jar_info['already_translated_strings'] > 0:
                # Все строки уже переведены (и есть переведенные строки)
                jar_info['status'] = 'already_translated'
                result['already_translated'].append(jar_info)
                
            else:
                # Проверяем наличие готовых ru_ru файлов только если нет переведенных строк в en_us
                if jar_info['already_translated_strings'] == 0:
                    # Нет переведенных строк в en_us файлах, проверяем готовые ru_ru файлы
                    has_complete_translation = True
                    
                    # Если есть lang файлы, должен быть ru_ru.json
                    if jar_info['has_lang_files'] and not jar_info['has_russian_lang']:
                        has_complete_translation = False
                    
                    # Если есть patchouli файлы, должна быть ru_ru папка
                    if jar_info['has_patchouli_files'] and not jar_info['has_russian_patchouli']:
                        has_complete_translation = False
                    
                    if has_complete_translation and (jar_info['has_russian_lang'] or jar_info['has_russian_patchouli']):
                        # Есть готовые ru_ru файлы для всех типов контента
                        jar_info['status'] = 'already_translated'
                        result['already_translated'].append(jar_info)
                    else:
                        # Нуждается в переводе
                        jar_info['status'] = 'need_translation'
                        result['need_translation'].append(jar_info)
                        
                        # Добавляем к общей статистике
                        result['stats']['total_lang_files'] += jar_info['lang_files']
                        result['stats']['total_patchouli_files'] += jar_info['patchouli_files']
                        result['stats']['total_strings'] += jar_info['strings_to_translate']
                else:
                    # Есть частично переведенные строки - нуждается в переводе
                    jar_info['status'] = 'need_translation'
                    result['need_translation'].append(jar_info)
                    
                    # Добавляем к общей статистике только непереведенные строки
                    result['stats']['total_lang_files'] += jar_info['lang_files']
                    result['stats']['total_patchouli_files'] += jar_info['patchouli_files']
                    result['stats']['total_strings'] += (jar_info['strings_to_translate'] - jar_info['already_translated_strings'])
                
        except Exception as e:
            # В случае ошибки помечаем как проблемный файл
            jar_info = {
                'file': jar_file,
                'status': 'error',
                'error': str(e)
            }
            result['no_files'].append(jar_info)
    
    if progress_callback:
        progress_callback(100, "Анализ завершен")
    
    return result

def translate_batch(texts, lang_to, delay=0.0):
    """Переводит пакет строк с кэшированием и задержками"""
    results = []
    uncached_texts = []
    uncached_indices = []
    cache_hits = 0  # Счетчик попаданий в кэш
    
    # Проверяем кэш для каждой строки
    for i, text in enumerate(texts):
        if not text or not text.strip():
            results.append(text)
            continue
            
        # Пропускаем уже переведенный текст (кириллица)
        if any('\u0400' <= char <= '\u04FF' for char in text):
            results.append(text)
            continue
            
        # Пропускаем технические строки (расширенная фильтрация для скорости)
        if (':' in text and len(text) < 50 and not ' ' in text) or \
           '{' in text or '}' in text or len(text) < 3 or \
           text.startswith('#') or text.startswith('//') or \
           text.isdigit() or text.replace('.', '').replace(',', '').isdigit() or \
           len(text.split()) == 1 and len(text) < 10:
            results.append(text)
            continue
        
        cache_key = get_cache_key(text, lang_to)
        if cache_key in TRANSLATION_CACHE:
            # Используем кэшированный перевод
            results.append(TRANSLATION_CACHE[cache_key])
            cache_hits += 1  # Увеличиваем счетчик попаданий
        else:
            # Добавляем в список для перевода
            results.append(None)  # Placeholder
            uncached_texts.append(text)
            uncached_indices.append(i)
    
    # Переводим непереведенные строки пакетом
    if uncached_texts:
        try:
            # Задержка перед запросом к API
            if delay > 0:
                time.sleep(delay)
            
            # Измеряем время API запроса для адаптивной оптимизации
            start_time = time.time()
            
            # Объединяем строки для пакетного перевода с коротким разделителем
            batch_text = " |SEP| ".join(uncached_texts)
            translated_batch = str(translator.translate(batch_text, lang_to))
            
            # Записываем время ответа API
            api_response_time = time.time() - start_time
            
            # Разделяем результат обратно
            translated_parts = translated_batch.split(" |SEP| ")
            
            # Если количество не совпадает, переводим по одной
            if len(translated_parts) != len(uncached_texts):
                translated_parts = []
                for text in uncached_texts:
                    # Убираем задержку для максимальной скорости
                    try:
                        translated = str(translator.translate(text, lang_to))
                        translated_parts.append(translated)
                    except Exception:
                        translated_parts.append(text)
            
            # Сохраняем в кэш и результаты
            for i, (original, translated) in enumerate(zip(uncached_texts, translated_parts)):
                cache_key = get_cache_key(original, lang_to)
                cleaned_translation = translated.replace('"', "''")
                TRANSLATION_CACHE[cache_key] = cleaned_translation
                results[uncached_indices[i]] = cleaned_translation
                
        except Exception as e:
            error_msg = str(e).lower()
            api_warning = None
            
            # Определяем тип ошибки API
            if "rate limit" in error_msg or "too many requests" in error_msg:
                api_warning = "⚠️ API ПРЕДУПРЕЖДЕНИЕ: Превышен лимит запросов! Рекомендуется уменьшить количество потоков"
            elif "blocked" in error_msg or "forbidden" in error_msg:
                api_warning = "🚫 API БЛОКИРОВКА: Доступ заблокирован! Попробуйте позже или смените IP"
            elif "timeout" in error_msg or "connection" in error_msg:
                api_warning = "🌐 СЕТЕВАЯ ОШИБКА: Проблемы с подключением к серверу переводов"
            elif "quota" in error_msg or "limit exceeded" in error_msg:
                api_warning = "📊 ЛИМИТ ИСЧЕРПАН: Превышена дневная квота API"
            else:
                api_warning = f"❌ ОШИБКА API: {str(e)}"
            
            print(f"⚠️ Ошибка пакетного перевода: {e}")
            if api_warning:
                print(api_warning)
            
            # В случае ошибки возвращаем оригинальные строки
            for i, original in zip(uncached_indices, uncached_texts):
                results[i] = original
            
            # Возвращаем информацию об ошибке
            return results, {
                'cache_hits': cache_hits,
                'new_translations': 0,
                'total_strings': len([t for t in texts if t and t.strip()]),
                'api_warning': api_warning,
                'api_error': True,
                'api_response_time': 0
            }
    
    # Возвращаем результаты и статистику кэша
    return results, {
        'cache_hits': cache_hits,
        'new_translations': len(uncached_texts),
        'total_strings': len([t for t in texts if t and t.strip()]),
        'api_warning': None,
        'api_error': False,
        'api_response_time': api_response_time if uncached_texts else 0
    }

@lru_cache(maxsize=5000)
def translate_to(string, lang_to):
    """Простой перевод как в main.py (оставлен для совместимости)"""
    if not string or not string.strip():
        return string
    
    try:
        # Пропускаем строки, которые уже на русском
        if any(char in string for char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
            return string
            
        # Пропускаем технические строки (ID, ключи)
        if (':' in string and len(string) < 50 and not ' ' in string):
            return string
            
        # Пропускаем строки с фигурными скобками (плейсхолдеры)
        if '{' in string or '}' in string:
            return string
        
        # Пропускаем очень короткие строки
        if len(string) < 3:
            return string
        
        # Проверяем кэш
        cache_key = get_cache_key(string, lang_to)
        if cache_key in TRANSLATION_CACHE:
            return TRANSLATION_CACHE[cache_key]
            
        # Переводим
        translated = translator.translate(string, lang_to)
        result = str(translated).replace('"', "''")
        
        # Сохраняем в кэш
        TRANSLATION_CACHE[cache_key] = result
        return result
        
    except Exception as e:
        return string

def count_strings_in_json(content):
    """Подсчитывает количество строк для перевода в JSON объекте"""
    if not isinstance(content, dict):
        return 0
    
    count = 0
    for key, value in content.items():
        if isinstance(value, str):
            count += 1
        elif isinstance(value, dict):
            count += count_strings_in_json(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    count += 1
                elif isinstance(item, dict):
                    count += count_strings_in_json(item)
    
    return count

def translate_json_file(content, lang_to, progress_callback=None, stop_callback=None):
    """Переводит JSON файл (lang или patchouli) с отслеживанием прогресса по строкам и батчингом"""
    if not isinstance(content, dict):
        return content, 0, {'cache_hits': 0, 'new_translations': 0, 'total_strings': 0}
    
    # Собираем все строки для перевода
    all_strings = []
    string_paths = []  # Пути к строкам в JSON структуре
    
    def collect_strings(obj, path=""):
        """Рекурсивно собирает все строки для перевода"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    all_strings.append(value)
                    string_paths.append(current_path)
                elif isinstance(value, (dict, list)):
                    collect_strings(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, str):
                    all_strings.append(item)
                    string_paths.append(current_path)
                elif isinstance(item, (dict, list)):
                    collect_strings(item, current_path)
    
    # Собираем все строки
    collect_strings(content)
    total_strings = len(all_strings)
    
    if total_strings == 0:
        return content, 0, {'cache_hits': 0, 'new_translations': 0, 'total_strings': 0}
    
    # НЕ выводим "Найдено строк" - это будет в callback
    
    # Минимальный размер батча: 5 строк для максимальной отзывчивости
    batch_size = 5
    translated_strings = []
    strings_processed = 0
    
    # Общая статистика кэша для всего файла
    total_cache_stats = {'cache_hits': 0, 'new_translations': 0, 'total_strings': 0}
    
    for i in range(0, len(all_strings), batch_size):
        # Проверяем остановку перед каждым пакетом
        if stop_callback and stop_callback():
            # Если остановка запрошена, возвращаем частично переведенный контент
            break
            
        batch = all_strings[i:i + batch_size]
        
        # Переводим пакет без задержки для максимальной скорости
        batch_translated, cache_stats = translate_batch(batch, lang_to, delay=0.0)
        translated_strings.extend(batch_translated)
        
        # Накапливаем общую статистику
        total_cache_stats['cache_hits'] += cache_stats['cache_hits']
        total_cache_stats['new_translations'] += cache_stats['new_translations']
        total_cache_stats['total_strings'] += cache_stats['total_strings']
        
        # Адаптивная корректировка размера батча убрана - используем фиксированный размер
        # для стабильности и частых обновлений прогресса
        
        # Проверяем API предупреждения
        if cache_stats.get('api_warning'):
            # Передаем предупреждение через callback
            if progress_callback:
                progress_callback(-1, strings_processed, total_strings, cache_stats, api_warning=cache_stats['api_warning'])
        
        strings_processed += len(batch)
        
        # Обновляем прогресс каждый пакет для лучшей отзывчивости
        if progress_callback and (i // batch_size % 1 == 0 or strings_processed >= total_strings):
            progress = (strings_processed / total_strings) * 100 if total_strings > 0 else 0
            # Передаем статистику кэша в callback
            progress_callback(progress, strings_processed, total_strings, cache_stats)
    
    # Применяем переводы обратно к JSON структуре
    def apply_translations(obj, path=""):
        """Рекурсивно применяет переводы к JSON структуре"""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    # Находим перевод для этой строки
                    try:
                        string_index = string_paths.index(current_path)
                        result[key] = translated_strings[string_index]
                    except ValueError:
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = apply_translations(value, current_path)
                else:
                    result[key] = value
            return result
        elif isinstance(obj, list):
            result = []
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, str):
                    # Находим перевод для этой строки
                    try:
                        string_index = string_paths.index(current_path)
                        result.append(translated_strings[string_index])
                    except ValueError:
                        result.append(item)
                elif isinstance(item, (dict, list)):
                    result.append(apply_translations(item, current_path))
                else:
                    result.append(item)
            return result
        else:
            return obj
    
    translated_content = apply_translations(content)
    
    # Подсчитываем реально переведенные строки (не равные оригиналу)
    actually_translated = sum(1 for orig, trans in zip(all_strings, translated_strings) if orig != trans)
    
    return translated_content, actually_translated, total_cache_stats

def find_lang_files(jar_path):
    """Находит языковые файлы в JAR"""
    lang_files = []
    
    with zipfile.ZipFile(jar_path, 'r') as jar:
        for file_info in jar.infolist():
            path = file_info.filename
            
            # Ищем assets/*/lang/*.json
            if '/lang/' in path and path.endswith('.json'):
                lang_files.append(path)
    
    return lang_files

def find_patchouli_files(jar_path):
    """Находит файлы Patchouli в JAR"""
    patchouli_files = []
    
    with zipfile.ZipFile(jar_path, 'r') as jar:
        for file_info in jar.infolist():
            path = file_info.filename
            
            # Ищем файлы в структуре: assets/*/patchouli_books/**/en_us/**/*.json
            # Может быть любая глубина между patchouli_books и en_us
            if (path.startswith('assets/') and 
                '/patchouli_books/' in path and 
                '/en_us/' in path and 
                path.endswith('.json') and
                not file_info.is_dir()):
                patchouli_files.append(path)
    
    return patchouli_files

def debug_jar_structure(jar_path, show_patchouli_only=True):
    """Отладочная функция для просмотра структуры JAR файла"""
    print(f"🔍 Структура JAR: {jar_path.name}")
    
    with zipfile.ZipFile(jar_path, 'r') as jar:
        patchouli_paths = []
        lang_paths = []
        
        for file_info in jar.infolist():
            path = file_info.filename
            
            if '/patchouli_books/' in path:
                patchouli_paths.append(path)
            elif '/lang/' in path and path.endswith('.json'):
                lang_paths.append(path)
        
        if show_patchouli_only:
            if patchouli_paths:
                print("📚 Patchouli пути:")
                for path in sorted(patchouli_paths)[:10]:  # Показываем первые 10
                    print(f"   {path}")
                if len(patchouli_paths) > 10:
                    print(f"   ... и еще {len(patchouli_paths) - 10} файлов")
            else:
                print("📚 Patchouli файлы не найдены")
        
        if lang_paths:
            print("📄 Lang пути:")
            for path in sorted(lang_paths):
                print(f"   {path}")
        else:
            print("📄 Lang файлы не найдены")
    
    print()

def has_russian_lang(jar_path):
    """Проверяет есть ли уже ru_ru.json в lang"""
    with zipfile.ZipFile(jar_path, 'r') as jar:
        for file_info in jar.infolist():
            if '/lang/ru_ru.json' in file_info.filename:
                return True
    return False

def has_russian_patchouli(jar_path):
    """Проверяет есть ли уже ru_ru папка в patchouli"""
    with zipfile.ZipFile(jar_path, 'r') as jar:
        for file_info in jar.infolist():
            path = file_info.filename
            # Ищем файлы в структуре: assets/*/patchouli_books/**/ru_ru/**/*.json
            if (path.startswith('assets/') and 
                '/patchouli_books/' in path and 
                '/ru_ru/' in path and 
                path.endswith('.json')):
                return True
    return False

def translate_jar(jar_path, output_path, lang_to='ru', replace_original=False, progress_callback=None, stop_callback=None):
    """
    Переводит JAR мод с отслеживанием прогресса по строкам
    ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с кэшированием и батчингом
    
    Args:
        jar_path: путь к JAR файлу
        output_path: папка для сохранения
        lang_to: целевой язык (ru)
        replace_original: True = заменить оригинал, False = создать _ru.jar
        progress_callback: функция для обновления прогресса (progress, current, total)
        stop_callback: функция для проверки остановки (возвращает True если нужно остановиться)
    """
    # НЕ загружаем кэш здесь - он должен быть загружен один раз в начале
    
    jar_path = Path(jar_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Определяем имя выходного файла
    if replace_original:
        output_jar = output_path / jar_path.name
    else:
        output_jar = output_path / f"{jar_path.stem}_ru.jar"
    
    # Статистика
    stats = {
        'lang_files': 0,
        'patchouli_files': 0,
        'strings_translated': 0,
        'cache_hits': 0,
        'new_translations': 0
    }
    
    # Проверяем что нужно переводить
    skip_lang = has_russian_lang(jar_path)
    skip_patchouli = has_russian_patchouli(jar_path)
    
    if skip_lang and skip_patchouli:
        return stats
    
    # Создаем временную папку
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Распаковываем JAR
        with zipfile.ZipFile(jar_path, 'r') as jar:
            jar.extractall(temp_dir)
        
        # 1. ПЕРЕВОДИМ LANG ФАЙЛЫ
        if not skip_lang:
            lang_files = find_lang_files(jar_path)
            en_us_lang_files = [f for f in lang_files if 'en_us.json' in f]
            
            if not en_us_lang_files:
                print("📄 Lang: ❌ Нет файлов для перевода (en_us.json не найден)")
            else:
                print(f"📄 Lang: найдено {len(en_us_lang_files)} файлов для перевода")
                
                for i, lang_file in enumerate(en_us_lang_files):
                    # Проверяем остановку перед каждым файлом
                    if stop_callback and stop_callback():
                        break
                        
                    lang_file_path = temp_dir / lang_file
                    
                    try:
                        with open(lang_file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        # Подсчитываем строки для этого файла
                        file_strings = count_strings_in_json(content)
                        
                        if file_strings == 0:
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) ⚠️ Нет строк для перевода")
                            continue
                        
                        # Проверяем, сколько строк уже переведено (на русском)
                        already_translated = 0
                        for key, value in content.items() if isinstance(content, dict) else []:
                            if isinstance(value, str) and any('\u0400' <= char <= '\u04FF' for char in value):
                                already_translated += 1
                        
                        if already_translated == file_strings:
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) ✅ Все строки уже переведены ({file_strings}/{file_strings})")
                            continue
                        elif already_translated > 0:
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) 🔄 Частично переведен ({already_translated}/{file_strings} строк)")
                        
                        # Выводим начальное сообщение один раз
                        print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) 0.0% - 0/{file_strings} строк")
                        
                        # Создаем callback для отслеживания прогресса файла
                        def file_progress_callback(progress, current, total, cache_stats=None, api_warning=None):
                            if progress_callback:
                                # Рассчитываем общий прогресс Lang части
                                # Прогресс файла: от 0% до 100%
                                # Прогресс всех файлов: (i + progress/100) / len(en_us_lang_files)
                                file_progress_ratio = (i + progress / 100) / len(en_us_lang_files)
                                # Lang занимает 0-50% от общего прогресса
                                adjusted_progress = file_progress_ratio * 50
                                progress_callback(adjusted_progress, current, total)
                            
                            # Если есть API предупреждение, выводим его
                            if api_warning:
                                print(api_warning)
                                return
                            
                            # Формируем информативную строку прогресса
                            cache_info = ""
                            if cache_stats:
                                parts = []
                                if cache_stats['cache_hits'] > 0:
                                    parts.append(f"кэш: {cache_stats['cache_hits']}")
                                if cache_stats['new_translations'] > 0:
                                    parts.append(f"новых: {cache_stats['new_translations']}")
                                if parts:
                                    cache_info = f" ({', '.join(parts)})"
                            
                            # Обновляем ту же строку
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) {progress:.1f}% - {current}/{total} строк{cache_info}")
                        
                        # Переводим с отслеживанием прогресса и проверкой остановки
                        translated, translated_count, file_cache_stats = translate_json_file(content, lang_to, file_progress_callback, stop_callback)
                        
                        # Проверяем остановку после перевода
                        if stop_callback and stop_callback():
                            break
                        
                        # Сохраняем как ru_ru.json
                        ru_file_path = lang_file_path.parent / 'ru_ru.json'
                        with open(ru_file_path, 'w', encoding='utf-8') as f:
                            json.dump(translated, f, ensure_ascii=False, indent=2)
                        
                        # Формируем финальное сообщение без смайликов
                        if translated_count > 0:
                            cache_info = ""
                            if file_cache_stats['cache_hits'] > 0:
                                cache_info += f" (из кэша: {file_cache_stats['cache_hits']})"
                            if file_cache_stats['new_translations'] > 0:
                                cache_info += f" (новых: {file_cache_stats['new_translations']})"
                            
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) Переведено {translated_count} строк{cache_info}")
                        else:
                            print(f"📄 Lang ({i+1}/{len(en_us_lang_files)}) Нет новых строк для перевода")
                        
                        stats['lang_files'] += 1
                        stats['strings_translated'] += translated_count
                        stats['cache_hits'] += file_cache_stats['cache_hits']
                        stats['new_translations'] += file_cache_stats['new_translations']
                        
                    except Exception as e:
                        print(f"❌ Ошибка в {lang_file}: {e}")
        else:
            print("📄 Lang: ⏭️ Пропущено (уже есть ru_ru.json)")
        
        # Сигнализируем о завершении Lang части (50% общего прогресса)
        # Вызываем только если есть callback и не пропущены оба типа файлов
        if progress_callback and not (skip_lang and skip_patchouli):
            progress_callback(50, 0, 0)  # 50% завершено, переходим к Patchouli
        
        # 2. ПЕРЕВОДИМ PATCHOULI
        if not skip_patchouli:
            patchouli_files = find_patchouli_files(jar_path)
            
            if not patchouli_files:
                print("📚 Patchouli: ❌ Нет файлов для перевода (en_us папка не найдена)")
            else:
                print(f"📚 Patchouli: найдено {len(patchouli_files)} файлов для перевода")
                
                for i, patchouli_file in enumerate(patchouli_files):
                    # Проверяем остановку перед каждым файлом
                    if stop_callback and stop_callback():
                        break
                        
                    patchouli_file_path = temp_dir / patchouli_file
                    
                    try:
                        with open(patchouli_file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        # Подсчитываем строки для этого файла
                        file_strings = count_strings_in_json(content)
                        
                        if file_strings == 0:
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) ⚠️ Нет строк для перевода")
                            continue
                        
                        # Проверяем, сколько строк уже переведено (на русском)
                        already_translated = 0
                        def count_translated_strings(obj):
                            nonlocal already_translated
                            if isinstance(obj, dict):
                                for value in obj.values():
                                    if isinstance(value, str) and any('\u0400' <= char <= '\u04FF' for char in value):
                                        already_translated += 1
                                    elif isinstance(value, (dict, list)):
                                        count_translated_strings(value)
                            elif isinstance(obj, list):
                                for item in obj:
                                    if isinstance(item, str) and any('\u0400' <= char <= '\u04FF' for char in item):
                                        already_translated += 1
                                    elif isinstance(item, (dict, list)):
                                        count_translated_strings(item)
                        
                        count_translated_strings(content)
                        
                        if already_translated == file_strings:
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) ✅ Все строки уже переведены ({file_strings}/{file_strings})")
                            continue
                        elif already_translated > 0:
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) 🔄 Частично переведен ({already_translated}/{file_strings} строк)")
                        
                        # Выводим начальное сообщение один раз
                        print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) 0.0% - 0/{file_strings} строк")
                        
                        # Создаем callback для отслеживания прогресса файла
                        def file_progress_callback(progress, current, total, cache_stats=None, api_warning=None):
                            if progress_callback:
                                # Рассчитываем общий прогресс Patchouli части
                                # Прогресс файла: от 0% до 100%
                                # Прогресс всех файлов: (i + progress/100) / len(patchouli_files)
                                file_progress_ratio = (i + progress / 100) / len(patchouli_files)
                                # Patchouli занимает 50-100% от общего прогресса
                                adjusted_progress = 50 + (file_progress_ratio * 50)
                                progress_callback(adjusted_progress, current, total)
                            
                            # Если есть API предупреждение, выводим его
                            if api_warning:
                                print(api_warning)
                                return
                            
                            # Формируем информативную строку прогресса
                            cache_info = ""
                            if cache_stats:
                                parts = []
                                if cache_stats['cache_hits'] > 0:
                                    parts.append(f"кэш: {cache_stats['cache_hits']}")
                                if cache_stats['new_translations'] > 0:
                                    parts.append(f"новых: {cache_stats['new_translations']}")
                                if parts:
                                    cache_info = f" ({', '.join(parts)})"
                            
                            # Обновляем ту же строку
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) {progress:.1f}% - {current}/{total} строк{cache_info}")
                        
                        # Переводим с отслеживанием прогресса и проверкой остановки
                        translated, translated_count, file_cache_stats = translate_json_file(content, lang_to, file_progress_callback, stop_callback)
                        
                        # Проверяем остановку после перевода
                        if stop_callback and stop_callback():
                            break
                        
                        # Создаем ru_ru версию
                        ru_file = patchouli_file.replace('/en_us/', '/ru_ru/')
                        ru_file_path = temp_dir / ru_file
                        ru_file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(ru_file_path, 'w', encoding='utf-8') as f:
                            json.dump(translated, f, ensure_ascii=False, indent=2)
                        
                        # Формируем финальное сообщение без смайликов
                        if translated_count > 0:
                            cache_info = ""
                            if file_cache_stats['cache_hits'] > 0:
                                cache_info += f" (из кэша: {file_cache_stats['cache_hits']})"
                            if file_cache_stats['new_translations'] > 0:
                                cache_info += f" (новых: {file_cache_stats['new_translations']})"
                            
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) Переведено {translated_count} строк{cache_info}")
                        else:
                            print(f"📚 Patchouli ({i+1}/{len(patchouli_files)}) Нет новых строк для перевода")
                        
                        stats['patchouli_files'] += 1
                        stats['strings_translated'] += translated_count
                        stats['cache_hits'] += file_cache_stats['cache_hits']
                        stats['new_translations'] += file_cache_stats['new_translations']
                        
                    except Exception as e:
                        print(f"❌ Ошибка в {patchouli_file}: {e}")
        else:
            print("📚 Patchouli: ⏭️ Пропущено (уже есть ru_ru папка)")
        
        # Упаковываем обратно в JAR
        with zipfile.ZipFile(output_jar, 'w', zipfile.ZIP_DEFLATED) as jar_out:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_dir)
                    jar_out.write(file_path, arcname)
    
    return stats

def main():
    import sys
    
    if len(sys.argv) < 3:
        print("Использование: python translate_jar_simple.py <input_jar_or_folder> <output_folder> [--replace-original]")
        return
    
    # Загружаем кэш переводов
    load_translation_cache()
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    replace_original = '--replace-original' in sys.argv
    
    # Находим JAR файлы
    if input_path.is_file():
        jar_files = [input_path]
    else:
        jar_files = list(input_path.glob('*.jar'))
    
    if not jar_files:
        print("❌ JAR файлы не найдены!")
        return
    
    print(f"📚 Найдено JAR файлов: {len(jar_files)}")
    print(f"🌐 Язык перевода: ru")
    print(f"⚙️ Режим: {'Замена оригиналов' if replace_original else 'Создание _ru.jar'}")
    print(f"🚀 ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: кэширование + батчинг + задержки")
    print()
    
    # Переводим
    total_stats = {'lang_files': 0, 'patchouli_files': 0, 'strings_translated': 0}
    successful = 0
    
    for jar_file in jar_files:
        try:
            stats = translate_jar(jar_file, output_path, 'ru', replace_original)
            total_stats['lang_files'] += stats['lang_files']
            total_stats['patchouli_files'] += stats['patchouli_files']
            total_stats['strings_translated'] += stats['strings_translated']
            successful += 1
        except Exception as e:
            print(f"❌ Ошибка при обработке {jar_file.name}: {e}")
    
    # Сохраняем кэш в конце
    save_translation_cache()
    
    print()
    print("🎉 Перевод завершен!")
    print(f"✅ Успешно: {successful}/{len(jar_files)}")
    print(f"📄 Lang файлов: {total_stats['lang_files']}")
    print(f"📚 Patchouli файлов: {total_stats['patchouli_files']}")
    print(f"📝 Строк переведено: {total_stats['strings_translated']}")
    print(f"💾 Кэш содержит: {len(TRANSLATION_CACHE)} переводов")

if __name__ == '__main__':
    main()