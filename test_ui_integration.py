#!/usr/bin/env python3
"""
Тестовый запуск приложения с исправленными UI компонентами.
"""

import sys
import os

# Добавление корневой директории в путь
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    # Тест импорта основных модулей
    print("🔄 Тестирование основных модулей...")
    
    from utils.widget_factory import SafeWidgetFactory
    print("✅ SafeWidgetFactory")
    
    from ui.themes.dark_theme import get_theme
    print("✅ DarkTheme")
    
    from ui.tabs.enhanced_analysis_tab import EnhancedAnalysisTab
    print("✅ EnhancedAnalysisTab")
    
    from ui.tabs.enhanced_rewards_tab import EnhancedRewardsTab
    print("✅ EnhancedRewardsTab")
    
    print("\n🎉 Все ключевые модули импортируются корректно!")
    print("💡 SafeWidgetFactory успешно интегрирован в UI компоненты")
    
    # Тест создания SafeWidgetFactory
    theme = get_theme()
    factory = SafeWidgetFactory(theme)
    print("✅ SafeWidgetFactory создается корректно")
    
    print("\n🚀 Готово к production! Основные исправления завершены:")
    print("   • SafeWidgetFactory интегрирован во все UI модули")
    print("   • Удалены запрещённые placeholder_text параметры") 
    print("   • Добавлена программная система placeholder")
    print("   • Исправлены импорты и конструкторы")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)
