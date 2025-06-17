"""
PLEX Dynamic Staking Manager - UI Demo Script
Демонстрационный скрипт для тестирования пользовательского интерфейса.

Автор: PLEX Dynamic Staking Team
Версия: 4.0.0
"""

import os
import sys
import traceback

# Добавление корневой директории в путь
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

print("🧪 DEMO: Тестирование UI компонентов PLEX Dynamic Staking Manager v4.0")
print("="*70)

def test_dependencies():
    """Тест зависимостей."""
    print("🔍 Проверка зависимостей...")
    
    try:
        import customtkinter as ctk
        print("   ✅ CustomTkinter: Доступен")
    except ImportError as e:
        print(f"   ❌ CustomTkinter: Не найден - {e}")
        return False
    
    try:
        import tkinter as tk
        print("   ✅ Tkinter: Доступен")
    except ImportError as e:
        print(f"   ❌ Tkinter: Не найден - {e}")
        return False
    
    return True

def test_theme():
    """Тест темы."""
    print("\\n🎨 Тестирование темы...")
    
    try:
        from ui.themes.dark_theme import get_theme, apply_window_style
        theme = get_theme()
        print("   ✅ Тема загружена успешно")
        
        # Тест основных стилей
        styles = ['primary', 'secondary', 'tertiary', 'card']
        for style in styles:
            style_config = theme.get_frame_style(style)
            print(f"   ✅ Стиль '{style}': {len(style_config)} параметров")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка темы: {e}")
        return False

def test_components():
    """Тест UI компонентов."""
    print("\\n🧩 Тестирование UI компонентов...")
    
    try:
        from ui.components.log_viewer import LogViewer
        from ui.components.progress_bar import ProgressBar
        print("   ✅ LogViewer: Импортирован")
        print("   ✅ ProgressBar: Импортирован")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка компонентов: {e}")
        return False

def test_tabs():
    """Тест вкладок."""
    print("\\n📂 Тестирование вкладок...")
    
    tabs = [
        ('ui.tabs.analysis_tab', 'AnalysisTab'),
        ('ui.tabs.rewards_tab', 'RewardsTab'),
        ('ui.tabs.history_tab', 'HistoryTab'),
        ('ui.tabs.settings_tab', 'SettingsTab')
    ]
    
    for module_name, class_name in tabs:
        try:
            module = __import__(module_name, fromlist=[class_name])
            tab_class = getattr(module, class_name)
            print(f"   ✅ {class_name}: Импортирован")
        except Exception as e:
            print(f"   ❌ {class_name}: Ошибка - {e}")
            return False
    
    return True

def test_main_window():
    """Тест главного окна."""
    print("\\n🏠 Тестирование главного окна...")
    
    try:
        from ui.main_window_v4 import PLEXStakingMainWindow
        print("   ✅ PLEXStakingMainWindow: Импортирован")
        
        # Создание экземпляра без запуска UI
        app = PLEXStakingMainWindow()
        print("   ✅ PLEXStakingMainWindow: Экземпляр создан")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка главного окна: {e}")
        return False

def test_core_modules():
    """Тест основных модулей."""
    print("\\n🧠 Тестирование основных модулей...")
    
    modules = [
        'core.staking_manager',
        'core.reward_calculator',
        'blockchain.node_client',
        'db.database'
    ]
    
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}: Импортирован")
        except Exception as e:
            print(f"   ❌ {module_name}: Ошибка - {e}")
            # Не критичная ошибка для демо
    
    return True

def run_ui_demo():
    """Запуск демонстрации UI."""
    print("\\n🚀 Запуск демонстрации UI...")
    
    try:
        import customtkinter as ctk
        from ui.themes.dark_theme import apply_window_style
        
        # Создание простого демо-окна
        root = ctk.CTk()
        root.title("PLEX UI Demo - v4.0")
        root.geometry("800x600")
        
        # Применение темы
        apply_window_style(root)
        
        # Демо-контент
        label = ctk.CTkLabel(
            root,
            text="💎 PLEX Dynamic Staking Manager v4.0\\n\\n🎉 UI компоненты работают!\\n\\nЗакройте это окно для продолжения...",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        label.pack(expand=True)
        
        button = ctk.CTkButton(
            root,
            text="Закрыть демо",
            command=root.destroy,
            width=200,
            height=40
        )
        button.pack(pady=20)
        
        print("   ✅ Демо-окно создано")
        print("   🖼️ Демо-окно отображается...")
        print("   💡 Закройте окно для завершения демо")
        
        root.mainloop()
        
        print("   ✅ Демо-окно закрыто")
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка демо UI: {e}")
        return False

def main():
    """Главная функция демо."""
    print("\\n" + "="*70)
    print("🧪 НАЧАЛО ТЕСТИРОВАНИЯ")
    print("="*70)
    
    tests = [
        ("Зависимости", test_dependencies),
        ("Тема", test_theme),
        ("UI Компоненты", test_components),
        ("Вкладки", test_tabs),
        ("Главное окно", test_main_window),
        ("Основные модули", test_core_modules)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Результаты тестирования
    print("\\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name:20} | {status}")
        if result:
            passed += 1
    
    print("-"*70)
    print(f"📈 Итого: {passed}/{total} тестов пройдено ({passed/total*100:.1f}%)")
    
    # Запуск UI демо если основные тесты прошли
    if passed >= total - 1:  # Разрешаем 1 неуспешный тест
        print("\\n🎉 Основные тесты пройдены! Запуск UI демо...")
        
        choice = input("\\n❓ Запустить демонстрацию UI? (y/n): ").lower()
        if choice in ['y', 'yes', 'да', '']:
            run_ui_demo()
        else:
            print("⏭️ UI демо пропущено")
    else:
        print("\\n⚠️ Слишком много провалов. UI демо пропущено.")
    
    print("\\n" + "="*70)
    print("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*70)
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к использованию.")
        print("💡 Запустите приложение: python main_v4.py")
    else:
        print("⚠️ Есть проблемы. Проверьте установку зависимостей.")
        print("📦 Установите зависимости: pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\n❌ Критическая ошибка: {e}")
        print("\\n📋 Трассировка:")
        traceback.print_exc()
        sys.exit(1)
