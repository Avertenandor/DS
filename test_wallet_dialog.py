#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации окна кошелька и логов.
"""

import tkinter as tk
import customtkinter as ctk

def test_wallet_dialog():
    """Тест диалога кошелька."""
    try:
        import sys
        import os
        sys.path.insert(0, os.getcwd())
        
        from ui.components.wallet_connection_dialog import WalletConnectionDialog
        from ui.themes.dark_theme import get_theme
        
        # Создание тестового окна
        root = ctk.CTk()
        root.title("Тест диалога кошелька")
        root.geometry("400x200")
        
        theme = get_theme()
        
        def show_wallet():
            dialog = WalletConnectionDialog(root)
            result = dialog.show()
            if result:
                print(f"✅ Результат: {result}")
            else:
                print("❌ Диалог отменен")
        
        button = theme.create_styled_button(
            root, 
            "🔐 Открыть диалог кошелька",
            'primary',
            command=show_wallet,
            width=250
        )
        button.pack(expand=True)
        
        print("✅ Тестовое окно создано")
        root.mainloop()
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")

if __name__ == "__main__":
    print("🧪 Запуск теста диалога кошелька...")
    test_wallet_dialog()
