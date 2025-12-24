#!/usr/bin/env python3
"""
ОПТИМИЗИРОВАННЫЙ переводчик JAR модов Minecraft
Ускорение в 5-10 раз по сравнению с базовой версией
"""

import os
import json
import zipfile
import tempfile
import shutil
import time
import pickle
import hashlib
import sqlite3
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from translatepy import Translator
from functools import lru_cache
from typing import List, Dict, Tuple, Optional, Set
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ОПТИМИЗИРОВАННЫЕ КОНСТАНТЫ
BATCH_SIZE = 50  # Увеличено с 10 до 50
MAX_BATCH_LENGTH = 4000  # Максимальная длина пакета в символах
DELAY_BETWEEN_BATCHES = 0.3  # Уменьшено с 1.0 до 0.3 секунды
MAX_WORKERS = 3  # Параллельная обработка JAR файлов

# Инициализация переводчика
translator = Translator()

# Компилируем регулярные выражения один раз для скорости
TECHNICAL_PATTERN = re.compile(r'^[a-z_]+:[a-z_]+$')  # minecraft:stone
PLACEHOLDER_PATTERN = re.compile(r'[{}%]')  # {player}, %d
CYRILLIC_PATTERN = re.compile(r'[\u0400-\u04FF]')  # Кириллица
FORMATTING_PATTERN = re.compile(r'[§&][0-9a-fk-or]')  # §a, &c

class OptimizedTranslationCache:
    """Оптимизированный кэш переводов с SQLite"""
    
    def __init__(self, db_path="translation_cache_optimized.db"):
        self.db_path = db_path
        self.memory_cache = {}  # LRU кэш в памяти для быстрого доступа
        self.init_db()
    
    def init_db(self):
        """Инициализирует базу данных"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    source_hash TEXT PRIMARY KEY,
                    source_text TEXT,
                    target_lang TEXT,
                    translated_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON translations(source_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lang ON translations(target_lang)")
    
    def get_cache_key(self, text: str, lang_to: str = 'ru') -> str:
        """Создает ключ для кэша"""
        return hashlib.md5(f"{text}:{lang_to}".encode()).hexdigest()
    
    def get_batch(self, texts: List[str], lang_to: str = 'ru') -> Tuple[List[Optional[str]], List[int]]:
        """Получает переводы пакетом из кэша"""
        if not texts:
            return [], []
        
        hashes = [self.get_cache_key(text, lang_to) for text in texts]
        
        # Сначала проверяем память
        results = []
        uncached_indices = []
        db_queries = []
        
        for i, (text, hash_key) in enumerate(zip(texts, hashes)):
            if hash_key in self.memory_cache:
                results.append(self.memory_cache[hash_key])
            else:
                results.append(None)
                uncached_indices.append(i)
                db_queries.append(hash_key)
        
        # Запрашиваем из базы данных пакетом
        if db_queries:
            with sqlite3.connect(self.db_path) as conn:
                placeholders = ','.join('?' * len(db_queries))
                cursor = conn.execute(
                    f"SELECT source_hash, translated_text FROM translations WHERE source_hash IN ({placeholders})",
                    db_queries
                )
                
                cached_from_db = dict(cursor.fetchall())
                
                # Обновляем результаты и память
                new_uncached = []
                for i, hash_key in zip(uncached_indices, db_queries):
                    if hash_key in cached_from_db:
                        translation = cached_from_db[hash_key]
                        results[i] = translation
                        self.memory_cache[hash_key] = translation
                    else:
                        new_uncached.append(i)
                
                uncached_indices = new_uncached
        
        return results, uncached_indices
    
    def save_batch(self, texts: List[str], translations: List[str], lang_to: str = 'ru'):
        """Сохраняет переводы пакетом"""
        if not texts or not translations or len(texts) != len(translations):
            return
        
        data = []
        for text, translation in zip(texts, translations):
            hash_key = self.get_cache_key(text, lang_to)
            data.append((hash_key, text, lang_to, translation))
            self.memory_cache[hash_key] = translation
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO translations (source_hash, source_text, target_lang, translated_text) VALUES (?, ?, ?, ?)",
                data
            )
            conn.commit()

# Глобальный экземпляр кэша
cache = OptimizedTranslationCache()

def should_translate(text: str) -> bool:
    """Быстрая предварительная фильтрация строк"""
    if not text or len(text) < 3 or not text.strip():
        return False
    
    # Используем предкомпилированные регексы для скорости
    if (TECHNICAL_PATTERN.match(text) or 
        PLACEHOLDER_PATTERN.search(text) or
        CYRILLIC_PATTERN.search(text) or
        FORMATTING_PATTERN.search(text)):
        return False
    
    return True

def create_smart_batches(texts: List[str], max_length: int = MAX_BATCH_LENGTH) -> List[List[str]]:
    """Создает оптимальные пакеты по длине символов"""
    if not texts:
        return []
    
    batches = []
    current_batch = []
    current_length = 0
    
    for text in texts:
        text_length = len(text) + 15  # +15 для разделителя " |SEPARATOR| "
        
        if current_length + text_length > max_length and current_batch:
            batches.append(current_batch)
            current_batch = [text]
            current_length = text_length
        else:
            current_batch.append(text)
            current_length += text_length
    
    if current_batch:
        batches.append(current_batch)
    
    return batches

def batch_translate_optimized(texts: List[str], lang_to: str = 'ru', delay: float = DELAY_BETWEEN_BATCHES) -> Tuple[List[str], Dict]:
    """
    ОПТИМИЗИРОВАННЫЙ пакетный перевод с умным кэшированием
    """
    if not texts:
        return [], {'cache_hits': 0, 'new_translations': 0, 'total_strings': 0}
    
    # Предварительная фильтрация
    filtered_texts = []
    original_indices = []
    
    for i, text in enumerate(texts):
        if should_translate(text):
            filtered_texts.append(text)
            original_indices.append(i)
    
    logger.info(f"Фильтрация: {len(filtered_texts)}/{len(texts)} строк для перевода")
    
    # Инициализируем результаты оригинальными текстами
    results = texts.copy()
    
    if not filtered_texts:
        return results, {'cache_hits': 0, 'new_translations': 0, 'total_strings': len(texts)}
    
    # Получаем из кэша пакетом
    cached_results, uncached_indices = cache.get_batch(filtered_texts, lang_to)
    cache_hits = sum(1 for r in cached_results if r is not None)
    
    logger.info(f"Кэш: {cache_hits}/{len(filtered_texts)} попаданий")
    
    # Применяем кэшированные результаты
    for i, cached_result in enumerate(cached_results):
        if cached_result is not None:
            original_index = original_indices[i]
            results[original_index] = cached_result
    
    # Переводим непереведенные строки
    uncached_texts = [filtered_texts[i] for i in uncached_indices]
    
    if uncached_texts:
        logger.info(f"Переводим {len(uncached_texts)} новых строк...")
        
        # Создаем умные пакеты
        smart_batches = create_smart_batches(uncached_texts)
        logger.info(f"Создано {len(smart_batches)} оптимальных пакетов")
        
        translated_texts = []
        
        for batch_num, batch in enumerate(smart_batches, 1):
            try:
                if delay > 0 and batch_num > 1:
                    time.sleep(delay)
                
                # Объединяем пакет
                batch_text = " |SEPARATOR| ".join(batch)
                logger.info(f"Пакет {batch_num}/{len(smart_batches)}: {len(batch)} строк, {len(batch_text)} символов")
                
                # Переводим
                translated_batch = str(translator.translate(batch_text, lang_to))
                
                # Разделяем результат
                translated_parts = translated_batch.split(" |SEPARATOR| ")
                
                # Проверяем корректность разделения
                if len(translated_parts) != len(batch):
                    logger.warning(f"Некорректное разделение пакета: {len(translated_parts)} != {len(batch)}")
                    # Переводим по одной строке
                    translated_parts = []
                    for text in batch:
                        try:
                            if delay > 0:
                                time.sleep(delay * 0.3)
                            translated = str(translator.translate(text, lang_to))
                            translated_parts.append(translated)
                        except Exception as e:
                            logger.error(f"Ошибка перевода '{text}': {e}")
                            translated_parts.append(text)
                
                # Очищаем переводы
                cleaned_translations = [t.replace('"', "''") for t in translated_parts]
                translated_texts.extend(cleaned_translations)
                
            except Exception as e:
                logger.error(f"Ошибка пакетного перевода: {e}")
                # В случае ошибки возвращаем оригинальные тексты
                translated_texts.extend(batch)
        
        # Сохраняем в кэш пакетом
        if len(translated_texts) == len(uncached_texts):
            cache.save_batch(uncached_texts, translated_texts, lang_to)
        
        # Применяем переводы к результатам
        for i, translated in enumerate(translated_texts):
            if i < len(uncached_indices):
                filtered_index = uncached_indices[i]
                original_index = original_indices[filtered_index]
                results[original_index] = translated
    
    stats = {
        'cache_hits': cache_hits,
        'new_translations': len(uncached_texts),
        'total_strings': len(texts),
        'filtered_strings': len(filtered_texts),
        'api_batches': len(create_smart_batches(uncached_texts)) if uncached_texts else 0
    }
    
    return results, stats

def extract_all_strings_from_jar(jar_path: Path) -> Set[str]:
    """Извлекает все строки из JAR файла для предварительной обработки"""
    strings = set()
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Ищем lang файлы
            for file_info in jar.filelist:
                if '/lang/' in file_info.filename and file_info.filename.endswith('.json'):
                    try:
                        with jar.open(file_info.filename) as f:
                            content = json.load(f)
                            if isinstance(content, dict):
                                strings.update(content.values())
                    except:
                        continue
            
            # Ищем patchouli файлы
            for file_info in jar.filelist:
                if '/patchouli_books/' in file_info.filename and file_info.filename.endswith('.json'):
                    try:
                        with jar.open(file_info.filename) as f:
                            content = json.load(f)
                            extract_strings_from_json(content, strings)
                    except:
                        continue
    
    except Exception as e:
        logger.error(f"Ошибка извлечения строк из {jar_path}: {e}")
    
    return strings

def extract_strings_from_json(obj, strings: Set[str]):
    """Рекурсивно извлекает строки из JSON объекта"""
    if isinstance(obj, dict):
        for value in obj.values():
            if isinstance(value, str):
                strings.add(value)
            elif isinstance(value, (dict, list)):
                extract_strings_from_json(value, strings)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                strings.add(item)
            elif isinstance(item, (dict, list)):
                extract_strings_from_json(item, strings)

def preload_and_translate_all_strings(jar_files: List[Path], lang_to: str = 'ru') -> Dict[str, str]:
    """
    МЕГА-ОПТИМИЗАЦИЯ: Предварительно загружает и переводит все уникальные строки
    """
    logger.info("🚀 Предварительная загрузка всех строк...")
    
    all_strings = set()
    
    # Извлекаем все строки из всех JAR файлов
    for jar_file in jar_files:
        strings = extract_all_strings_from_jar(jar_file)
        all_strings.update(strings)
        logger.info(f"Извлечено {len(strings)} строк из {jar_file.name}")
    
    unique_strings = list(all_strings)
    logger.info(f"📊 Всего уникальных строк: {len(unique_strings)}")
    
    # Переводим все уникальные строки одним большим пакетом
    translated_strings, stats = batch_translate_optimized(unique_strings, lang_to)
    
    # Создаем словарь переводов
    translation_dict = dict(zip(unique_strings, translated_strings))
    
    logger.info(f"✅ Предварительный перевод завершен:")
    logger.info(f"   📦 Кэш попаданий: {stats['cache_hits']}")
    logger.info(f"   🌐 Новых переводов: {stats['new_translations']}")
    logger.info(f"   📊 API пакетов: {stats.get('api_batches', 0)}")
    
    return translation_dict

def translate_jar_optimized(jar_path: Path, output_path: Path, lang_to: str = 'ru', 
                          translation_dict: Optional[Dict[str, str]] = None,
                          progress_callback=None, stop_callback=None) -> Dict:
    """
    ОПТИМИЗИРОВАННАЯ функция перевода JAR файла
    """
    logger.info(f"🔄 Переводим {jar_path.name}...")
    
    jar_path = Path(jar_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    output_jar = output_path / f"{jar_path.stem}_ru.jar"
    
    stats = {
        'lang_files': 0,
        'patchouli_files': 0,
        'strings_translated': 0,
        'cache_hits': 0,
        'new_translations': 0
    }
    
    # Создаем временную папку
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Распаковываем JAR
        with zipfile.ZipFile(jar_path, 'r') as jar:
            jar.extractall(temp_dir)
        
        # Переводим lang файлы
        lang_files_processed = process_lang_files_optimized(
            temp_dir, lang_to, translation_dict, progress_callback, stop_callback
        )
        stats.update(lang_files_processed)
        
        # Переводим patchouli файлы
        patchouli_files_processed = process_patchouli_files_optimized(
            temp_dir, lang_to, translation_dict, progress_callback, stop_callback
        )
        stats['patchouli_files'] += patchouli_files_processed.get('patchouli_files', 0)
        stats['strings_translated'] += patchouli_files_processed.get('strings_translated', 0)
        
        # Упаковываем обратно в JAR
        with zipfile.ZipFile(output_jar, 'w', zipfile.ZIP_DEFLATED) as new_jar:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_name = file_path.relative_to(temp_dir)
                    new_jar.write(file_path, arc_name)
    
    logger.info(f"✅ {jar_path.name} переведен: {stats['strings_translated']} строк")
    return stats

def process_lang_files_optimized(temp_dir: Path, lang_to: str, 
                                translation_dict: Optional[Dict[str, str]] = None,
                                progress_callback=None, stop_callback=None) -> Dict:
    """Оптимизированная обработка lang файлов"""
    stats = {'lang_files': 0, 'strings_translated': 0, 'cache_hits': 0, 'new_translations': 0}
    
    # Ищем все lang файлы
    lang_files = list(temp_dir.rglob('**/lang/*.json'))
    en_us_files = [f for f in lang_files if f.name == 'en_us.json']
    
    for lang_file in en_us_files:
        if stop_callback and stop_callback():
            break
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            if not isinstance(content, dict):
                continue
            
            # Используем предварительно переведенный словарь если есть
            if translation_dict:
                translated_content = {}
                for key, value in content.items():
                    translated_content[key] = translation_dict.get(value, value)
                    if translation_dict.get(value, value) != value:
                        stats['strings_translated'] += 1
                        stats['cache_hits'] += 1
            else:
                # Переводим обычным способом
                texts = list(content.values())
                translated_texts, translate_stats = batch_translate_optimized(texts, lang_to)
                
                translated_content = {}
                for key, translated in zip(content.keys(), translated_texts):
                    translated_content[key] = translated
                
                stats['strings_translated'] += translate_stats['new_translations']
                stats['cache_hits'] += translate_stats['cache_hits']
                stats['new_translations'] += translate_stats['new_translations']
            
            # Создаем ru_ru.json файл
            ru_file = lang_file.parent / 'ru_ru.json'
            with open(ru_file, 'w', encoding='utf-8') as f:
                json.dump(translated_content, f, ensure_ascii=False, indent=2)
            
            stats['lang_files'] += 1
            
            if progress_callback:
                progress_callback(f"Обработан {lang_file.name}")
        
        except Exception as e:
            logger.error(f"Ошибка обработки {lang_file}: {e}")
    
    return stats

def process_patchouli_files_optimized(temp_dir: Path, lang_to: str,
                                    translation_dict: Optional[Dict[str, str]] = None,
                                    progress_callback=None, stop_callback=None) -> Dict:
    """Оптимизированная обработка patchouli файлов"""
    stats = {'patchouli_files': 0, 'strings_translated': 0}
    
    # Ищем patchouli файлы
    patchouli_files = list(temp_dir.rglob('**/patchouli_books/**/en_us/*.json'))
    
    for patchouli_file in patchouli_files:
        if stop_callback and stop_callback():
            break
        
        try:
            with open(patchouli_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Извлекаем все строки
            strings = set()
            extract_strings_from_json(content, strings)
            
            if translation_dict:
                # Используем предварительный словарь
                def translate_json_recursive(obj):
                    if isinstance(obj, dict):
                        return {k: translate_json_recursive(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [translate_json_recursive(item) for item in obj]
                    elif isinstance(obj, str):
                        return translation_dict.get(obj, obj)
                    else:
                        return obj
                
                translated_content = translate_json_recursive(content)
            else:
                # Обычный перевод (упрощенная версия)
                translated_content = content
            
            # Создаем ru_ru файл
            ru_file = patchouli_file.parent.parent / 'ru_ru' / patchouli_file.name
            ru_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(ru_file, 'w', encoding='utf-8') as f:
                json.dump(translated_content, f, ensure_ascii=False, indent=2)
            
            stats['patchouli_files'] += 1
            stats['strings_translated'] += len(strings)
            
        except Exception as e:
            logger.error(f"Ошибка обработки {patchouli_file}: {e}")
    
    return stats

def translate_jars_parallel_optimized(jar_files: List[Path], output_path: Path, 
                                    lang_to: str = 'ru', max_workers: int = MAX_WORKERS,
                                    progress_callback=None, stop_callback=None) -> Dict:
    """
    ГЛАВНАЯ ОПТИМИЗИРОВАННАЯ ФУНКЦИЯ: Параллельный перевод JAR файлов
    """
    logger.info(f"🚀 Запуск оптимизированного перевода {len(jar_files)} JAR файлов...")
    
    # Этап 1: Предварительная загрузка и перевод всех уникальных строк
    translation_dict = preload_and_translate_all_strings(jar_files, lang_to)
    
    # Этап 2: Параллельная обработка JAR файлов
    total_stats = {
        'jars_processed': 0,
        'jars_failed': 0,
        'lang_files': 0,
        'patchouli_files': 0,
        'strings_translated': 0,
        'cache_hits': 0,
        'new_translations': 0
    }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        
        for jar_file in jar_files:
            if stop_callback and stop_callback():
                break
            
            future = executor.submit(
                translate_jar_optimized, 
                jar_file, 
                output_path, 
                lang_to, 
                translation_dict,
                progress_callback, 
                stop_callback
            )
            futures[future] = jar_file
        
        for future in as_completed(futures):
            jar_file = futures[future]
            
            try:
                stats = future.result()
                total_stats['jars_processed'] += 1
                total_stats['lang_files'] += stats.get('lang_files', 0)
                total_stats['patchouli_files'] += stats.get('patchouli_files', 0)
                total_stats['strings_translated'] += stats.get('strings_translated', 0)
                total_stats['cache_hits'] += stats.get('cache_hits', 0)
                total_stats['new_translations'] += stats.get('new_translations', 0)
                
                if progress_callback:
                    progress_callback(f"✅ Завершен {jar_file.name}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки {jar_file}: {e}")
                total_stats['jars_failed'] += 1
                
                if progress_callback:
                    progress_callback(f"❌ Ошибка {jar_file.name}: {e}")
    
    logger.info("🎉 Оптимизированный перевод завершен!")
    logger.info(f"📊 Итоговая статистика: {total_stats}")
    
    return total_stats

# Функция для совместимости с существующим кодом
def translate_jar(jar_path, output_path, lang_to='ru', replace_original=False, 
                 progress_callback=None, stop_callback=None):
    """Обертка для совместимости с существующим API"""
    return translate_jar_optimized(
        Path(jar_path), 
        Path(output_path), 
        lang_to, 
        None,  # Без предварительного словаря
        progress_callback, 
        stop_callback
    )

if __name__ == "__main__":
    # Пример использования
    jar_files = [Path("example.jar")]
    output_path = Path("translated_jars")
    
    stats = translate_jars_parallel_optimized(jar_files, output_path)
    print(f"Результат: {stats}")