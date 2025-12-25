#!/usr/bin/env python3
"""
Улучшенный переводчик с поддержкой терминологии и контекста
"""

import json
import re
from pathlib import Path
from translatepy import Translator

class EnhancedTranslator:
    def __init__(self):
        self.translator = Translator()
        self.terms_dict = self.load_terms()
        
    def load_terms(self):
        """Загружает словарь терминов"""
        try:
            terms_path = Path("config/minecraft_terms.json")
            if terms_path.exists():
                with open(terms_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Не удалось загрузить словарь терминов: {e}")
        return {"minecraft_terms": {}, "mod_specific": {}}
    
    def apply_terminology(self, text):
        """Применяет терминологический словарь"""
        result = text
        
        # Применяем Minecraft термины
        for en_term, ru_term in self.terms_dict.get("minecraft_terms", {}).items():
            # Заменяем целые слова (с границами)
            pattern = r'\b' + re.escape(en_term) + r'\b'
            result = re.sub(pattern, ru_term, result, flags=re.IGNORECASE)
        
        # Применяем модовые термины
        for en_term, ru_term in self.terms_dict.get("mod_specific", {}).items():
            pattern = r'\b' + re.escape(en_term) + r'\b'
            result = re.sub(pattern, ru_term, result, flags=re.IGNORECASE)
            
        return result
    
    def detect_mod_context(self, jar_name, file_path=""):
        """Определяет контекст мода по имени файла"""
        jar_lower = jar_name.lower()
        
        # Популярные моды и их контексты
        mod_contexts = {
            'thermal': 'thermal expansion mod (industrial machinery)',
            'mekanism': 'mekanism mod (advanced technology)',
            'immersive': 'immersive engineering mod (industrial)',
            'tinkers': 'tinkers construct mod (tool crafting)',
            'botania': 'botania mod (magical flowers)',
            'thaumcraft': 'thaumcraft mod (magic research)',
            'applied': 'applied energistics mod (digital storage)',
            'industrial': 'industrial craft mod (technology)',
            'buildcraft': 'buildcraft mod (automation)',
            'forestry': 'forestry mod (bees and trees)',
            'railcraft': 'railcraft mod (trains and rails)',
            'computercraft': 'computercraft mod (computers)',
            'create': 'create mod (mechanical contraptions)',
            'pneumatic': 'pneumaticcraft mod (compressed air)',
            'blood': 'blood magic mod (ritual magic)',
            'astral': 'astral sorcery mod (star magic)',
            'extra': 'extra utilities mod (useful blocks)',
            'ender': 'ender io mod (conduits and machines)'
        }
        
        for mod_key, context in mod_contexts.items():
            if mod_key in jar_lower:
                return context
                
        return "minecraft mod"
    
    def should_translate(self, text, key=""):
        """Улучшенная проверка нужно ли переводить"""
        if not text or not text.strip():
            return False
            
        # Пропускаем уже переведенные (кириллица)
        if re.search(r'[а-яё]', text, re.IGNORECASE):
            return False
        
        # ВАЖНО: Пропускаем названия модов в синем цвете (§9 и §1)
        # §9 - blue (основной цвет названий модов)
        # §1 - dark_blue (альтернативный синий)
        if re.search(r'§[91]', text):
            return False
            
        # Пропускаем форматирование (но разрешаем другие цвета)
        # Исключаем только форматирование: k(obfuscated), l(bold), m(strikethrough), n(underline), o(italic), r(reset)
        if re.search(r'§[klmnor]', text):
            return False
        
        # ВАЖНО: Пропускаем названия групп предметов модов (itemGroup)
        # Эти строки часто являются названиями модов и должны оставаться на английском
        if key and 'itemgroup' in key.lower():
            return False
        
        # ВАЖНО: Пропускаем известные названия модов (независимо от цветовых кодов)
        # Убираем цветовые коды для проверки
        clean_text = re.sub(r'§[0-9a-fk-or]', '', text).strip()
        
        # Список известных названий модов (должны оставаться на английском)
        mod_names = [
            'simple hats', 'thermal expansion', 'industrial craft', 'applied energistics',
            'tinkers construct', 'immersive engineering', 'mekanism', 'botania',
            'thaumcraft', 'buildcraft', 'forestry', 'railcraft', 'computercraft',
            'create', 'pneumaticcraft', 'blood magic', 'astral sorcery', 
            'extra utilities', 'ender io', 'jei', 'nei', 'waila', 'hwyla',
            'journeymap', 'optifine', 'forge', 'fabric', 'quark', 'biomes o plenty',
            'twilight forest', 'galacticraft', 'ic2', 'ae2', 'refined storage',
            'storage drawers', 'iron chests', 'chisel', 'carpenter blocks',
            'bibliocraft', 'decocraft', 'furniture mod', 'mr crayfish',
            'vehicle mod', 'flans mod', 'pixelmon', 'orespawn', 'lucky blocks',
            'mo creatures', 'dragons', 'fossils', 'jurassicraft', 'advent of ascension',
            'divine rpg', 'aether', 'tropicraft', 'erebus', 'betweenlands',
            'abyssal craft', 'blood arsenal', 'draconic evolution', 'project e',
            'equivalent exchange', 'big reactors', 'extreme reactors', 'nuclearcraft',
            'tech reborn', 'gregtech', 'endercore', 'cofh core', 'redstone flux',
            'tesla', 'energy', 'rf tools', 'mcjtylib', 'deep resonance',
            'compact machines', 'dimensional doors', 'mystcraft', 'rftools dimensions'
        ]
        
        # Проверяем точное совпадение с названиями модов
        if clean_text.lower() in mod_names:
            return False
        
        # Проверяем частичное совпадение для составных названий
        for mod_name in mod_names:
            if len(mod_name.split()) > 1 and mod_name in clean_text.lower():
                return False
        
        # Пропускаем технические строки
        technical_patterns = [
            r'^[a-z_]+\.[a-z_]+(\.[a-z_]+)*$',  # mod.item.name
            r'^\$\{.*\}$',                       # ${variables}
            r'^#[0-9A-Fa-f]{6,8}$',             # #FF0000 (цвета)
            r'^\d+(\.\d+)?[a-z%]*$',            # числа: 100, 1.5x, 50%
            r'^[A-Z_]+$',                       # КОНСТАНТЫ
            r'^minecraft:[a-z_]+$',             # minecraft:stone
            r'^[a-z]+:[a-z_]+$',                # mod:item
            r'^\[[^\]]+\]$',                    # [tags]
            r'^<[^>]+>$',                       # <components>
            r'^\([^)]+\)$',                     # (parameters)
        ]
        
        for pattern in technical_patterns:
            if re.match(pattern, text.strip()):
                return False
        
        # Пропускаем очень короткие строки
        if len(text.strip()) < 3:
            return False
            
        # Пропускаем строки только из символов
        if re.match(r'^[^a-zA-Z]*$', text):
            return False
            
        return True
    
    def translate_with_context(self, text, mod_context="minecraft mod"):
        """Переводит с учетом контекста мода"""
        if not self.should_translate(text):
            return text
            
        try:
            # Добавляем контекст для лучшего перевода
            context_text = f"[{mod_context}] {text}"
            
            # Переводим
            translated = str(self.translator.translate(context_text, 'ru'))
            
            # Убираем контекст из результата если он остался
            if translated.startswith('['):
                bracket_end = translated.find(']')
                if bracket_end != -1:
                    translated = translated[bracket_end + 1:].strip()
            
            # Применяем терминологический словарь
            translated = self.apply_terminology(translated)
            
            # Очищаем кавычки
            translated = translated.replace('"', "''")
            
            return translated
            
        except Exception as e:
            print(f"⚠️ Ошибка перевода '{text}': {e}")
            return text
    
    def translate_batch_enhanced(self, texts, mod_context="minecraft mod"):
        """Улучшенный пакетный перевод"""
        results = []
        
        # Фильтруем что нужно переводить
        to_translate = []
        indices = []
        
        for i, text in enumerate(texts):
            if self.should_translate(text):
                to_translate.append(text)
                indices.append(i)
                results.append(None)  # placeholder
            else:
                results.append(text)  # оставляем как есть
        
        # Переводим пакетом если есть что переводить
        if to_translate:
            try:
                # Объединяем с разделителем
                batch_text = f"[{mod_context}] " + " |SEP| ".join(to_translate)
                translated_batch = str(self.translator.translate(batch_text, 'ru'))
                
                # Убираем контекст
                if translated_batch.startswith('['):
                    bracket_end = translated_batch.find(']')
                    if bracket_end != -1:
                        translated_batch = translated_batch[bracket_end + 1:].strip()
                
                # Разделяем обратно
                translated_parts = translated_batch.split(" |SEP| ")
                
                # Если количество не совпадает, переводим по одной
                if len(translated_parts) != len(to_translate):
                    translated_parts = []
                    for text in to_translate:
                        translated_parts.append(self.translate_with_context(text, mod_context))
                
                # Применяем терминологию и сохраняем результаты
                for i, translated in enumerate(translated_parts):
                    if i < len(indices):
                        cleaned = self.apply_terminology(translated.replace('"', "''"))
                        results[indices[i]] = cleaned
                        
            except Exception as e:
                print(f"⚠️ Ошибка пакетного перевода: {e}")
                # Fallback - переводим по одной
                for i, text in enumerate(to_translate):
                    if i < len(indices):
                        results[indices[i]] = self.translate_with_context(text, mod_context)
        
        return results

# Пример использования
if __name__ == "__main__":
    translator = EnhancedTranslator()
    
    # Тестовые строки
    test_strings = [
        "Thermal Expansion Machine",
        "Advanced Solar Panel", 
        "Crafting Recipe",
        "minecraft:stone",
        "item.thermal.machine_frame.name",
        "Smelts ores into ingots"
    ]
    
    print("🧪 Тестирование улучшенного переводчика:")
    for text in test_strings:
        translated = translator.translate_with_context(text, "thermal expansion mod")
        print(f"'{text}' → '{translated}'")