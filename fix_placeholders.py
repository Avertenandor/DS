#!/usr/bin/env python3
"""
Скрипт для автоматической замены placeholder_text на SafeWidgetFactory
во всех UI файлах проекта.
"""

import os
import re
import sys
from pathlib import Path

def fix_file(file_path):
    """Исправляет один файл."""
    print(f"🔧 Обрабатывается: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Добавляем импорт SafeWidgetFactory (если нет)
        if 'from utils.widget_factory import SafeWidgetFactory' not in content:
            # Ищем место для вставки импорта
            import_pattern = r'(from utils\.logger import get_logger\n)'
            if re.search(import_pattern, content):
                content = re.sub(
                    import_pattern, 
                    r'\1from utils.widget_factory import SafeWidgetFactory\n', 
                    content
                )
                print(f"   ✅ Добавлен импорт SafeWidgetFactory")
        
        # 2. Добавляем widget_factory в конструктор (если нет)
        if 'widget_factory=' not in content and 'self.widget_factory' not in content:
            # Паттерн для конструктора
            constructor_pattern = r'def __init__\(self, parent([^)]*)\):'
            if re.search(constructor_pattern, content):
                content = re.sub(
                    constructor_pattern,
                    r'def __init__(self, parent\1, widget_factory=None):',
                    content
                )
                
                # Добавляем инициализацию widget_factory
                theme_pattern = r'(self\.theme = get_theme\(\)\n)'
                if re.search(theme_pattern, content):
                    content = re.sub(
                        theme_pattern,
                        r'\1        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)\n',
                        content
                    )
                    print(f"   ✅ Добавлен widget_factory в конструктор")
        
        # 3. Заменяем ctk.CTkEntry с placeholder_text на SafeWidgetFactory
        entry_pattern = r'(\s+)(\w+) = ctk\.CTkEntry\(\s*([^,]+),\s*placeholder_text="([^"]+)",?\s*([^)]*)\)'
        
        def replace_entry(match):
            indent = match.group(1)
            var_name = match.group(2)
            parent = match.group(3)
            placeholder = match.group(4)
            other_params = match.group(5).strip()
            
            if other_params and other_params.endswith(','):
                other_params = other_params[:-1]
            
            result = f'{indent}{var_name} = self.widget_factory.create_entry(\n'
            result += f'{indent}    {parent}'
            if other_params:
                result += f',\n{indent}    {other_params}'
            result += f'\n{indent})\n'
            result += f'{indent}self.widget_factory.setup_placeholder({var_name}, "{placeholder}")'
            
            return result
        
        old_content = content
        content = re.sub(entry_pattern, replace_entry, content, flags=re.MULTILINE)
        
        if old_content != content:
            print(f"   ✅ Заменены CTkEntry с placeholder_text")
        
        # Сохраняем только если были изменения
        if original_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Файл сохранен")
            return True
        else:
            print(f"   ⏭️ Изменения не требуются")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def main():
    """Основная функция."""
    base_dir = Path(__file__).parent
    ui_dir = base_dir / "ui"
    
    print("🚀 Автоматическое исправление placeholder_text во всех UI файлах")
    print(f"📁 Директория: {ui_dir}")
    print()
    
    fixed_count = 0
    total_count = 0
    
    # Обрабатываем все .py файлы в ui/
    for py_file in ui_dir.rglob("*.py"):
        total_count += 1
        if fix_file(py_file):
            fixed_count += 1
    
    print()
    print(f"📊 Результат: исправлено {fixed_count} из {total_count} файлов")
    
    if fixed_count > 0:
        print("🎉 Автоматические исправления завершены!")
        print("💡 Не забудьте передать widget_factory в конструкторы вкладок в main_window_v4.py")
    else:
        print("✅ Все файлы уже корректны")

if __name__ == "__main__":
    main()
