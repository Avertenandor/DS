#!/usr/bin/env python3
"""
Скрипт для замены ctk.CTkEntry с placeholder_text на SafeWidgetFactory.
"""

import os
import re
from pathlib import Path

def replace_placeholder_entries(file_path):
    """Заменяет ctk.CTkEntry с placeholder_text на SafeWidgetFactory."""
    print(f"🔧 Обрабатывается: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Паттерн для поиска ctk.CTkEntry с placeholder_text
        # Поддерживает многострочные объявления
        pattern = r'(\s*)(\w+)\s*=\s*ctk\.CTkEntry\(\s*([^,)]+)(?:,\s*placeholder_text\s*=\s*"([^"]+)")?([^)]*)\)'
        
        def replace_match(match):
            nonlocal changes_made
            indent = match.group(1)
            var_name = match.group(2)
            parent = match.group(3).strip()
            placeholder = match.group(4)  # Может быть None
            remaining_params = match.group(5)
            
            if not placeholder:
                return match.group(0)  # Не трогаем entry без placeholder_text
            
            changes_made = True
            
            # Очищаем лишние запятые и переносы строк из оставшихся параметров
            if remaining_params:
                remaining_params = remaining_params.strip()
                if remaining_params.startswith(','):
                    remaining_params = remaining_params[1:].strip()
                if remaining_params.endswith(','):
                    remaining_params = remaining_params[:-1].strip()
            
            # Формируем новый код
            result = f'{indent}{var_name} = self.widget_factory.create_entry(\n'
            result += f'{indent}    {parent}'
            
            if remaining_params:
                # Разбиваем параметры по запятым и добавляем их с правильным отступом
                params = [p.strip() for p in remaining_params.split(',') if p.strip()]
                for param in params:
                    result += f',\n{indent}    {param}'
            
            result += f'\n{indent})\n'
            result += f'{indent}self.widget_factory.setup_placeholder({var_name}, "{placeholder}")'
            
            return result
        
        # Применяем замену
        content = re.sub(pattern, replace_match, content, flags=re.MULTILINE | re.DOTALL)
        
        # Сохраняем файл если были изменения
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ Заменены CTkEntry с placeholder_text")
            return True
        else:
            print(f"   ⏭️ placeholder_text не найден")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def main():
    """Основная функция."""
    base_dir = Path(__file__).parent
    ui_dir = base_dir / "ui"
    
    print("🚀 Замена CTkEntry с placeholder_text на SafeWidgetFactory")
    print(f"📁 Директория: {ui_dir}")
    print()
    
    # Список файлов с placeholder_text (из предыдущего поиска)
    files_to_fix = [
        "ui/main_window.py",
        "ui/main_window_v2.py", 
        "ui/themes/dark_theme.py",
        "ui/tabs/analysis_tab.py",
        "ui/tabs/enhanced_analysis_tab.py",
        "ui/tabs/enhanced_rewards_tab.py",
        "ui/tabs/enhanced_history_tab.py"
    ]
    
    fixed_count = 0
    
    for relative_path in files_to_fix:
        file_path = base_dir / relative_path
        if file_path.exists():
            if replace_placeholder_entries(file_path):
                fixed_count += 1
        else:
            print(f"❌ Файл не найден: {file_path}")
    
    print()
    print(f"📊 Результат: исправлено {fixed_count} файлов")
    print("🎉 Замена placeholder_text завершена!")

if __name__ == "__main__":
    main()
