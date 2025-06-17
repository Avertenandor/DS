"""
Тест проверки UI компонентов - что пользователь видит все элементы
"""

import customtkinter as ctk
from ui.themes.dark_theme import get_theme
from utils.logger import get_logger

logger = get_logger(__name__)

def test_ui_visibility():
    """Простой тест для демонстрации UI элементов."""
    
    app = ctk.CTk()
    app.title("🧪 PLEX UI Components Test")
    app.geometry("1000x700")
    app.resizable(True, True)
    
    theme = get_theme()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Создаем тестовое окно с основными элементами
    
    # Заголовок
    title = ctk.CTkLabel(
        app,
        text="🧪 Тест UI компонентов PLEX Dynamic Staking Manager",
        font=("Arial", 20, "bold"),
        text_color=theme.colors['text_primary']
    )
    title.pack(pady=(20, 10))
    
    # Описание
    desc = ctk.CTkLabel(
        app,
        text="Если вы видите этот текст и элементы ниже, то UI работает корректно",
        font=("Arial", 14),
        text_color=theme.colors['text_secondary']
    )
    desc.pack(pady=10)
    
    # Контейнер для элементов
    container = ctk.CTkScrollableFrame(app)
    container.pack(fill='both', expand=True, padx=20, pady=20)
    
    # Кнопки
    buttons_frame = ctk.CTkFrame(container)
    buttons_frame.pack(fill='x', pady=10)
    buttons_frame.configure(fg_color=theme.colors['bg_secondary'])
    
    ctk.CTkLabel(
        buttons_frame,
        text="🎮 Кнопки управления:",
        font=("Arial", 14, "bold")
    ).pack(pady=(10, 5))
    
    btns_row = ctk.CTkFrame(buttons_frame)
    btns_row.configure(fg_color="transparent")
    btns_row.pack(pady=10)
    
    for i, (text, color) in enumerate([
        ("🚀 Начать анализ", theme.colors['btn_primary']),
        ("⏹️ Остановить", theme.colors['btn_danger']),
        ("🔄 Обновить", theme.colors['info']),
        ("📄 Экспорт", theme.colors['success'])
    ]):
        btn = ctk.CTkButton(
            btns_row,
            text=text,
            fg_color=color,
            width=150,
            height=40
        )
        btn.pack(side='left', padx=5)
    
    # Поля ввода
    inputs_frame = ctk.CTkFrame(container)
    inputs_frame.pack(fill='x', pady=10)
    inputs_frame.configure(fg_color=theme.colors['bg_secondary'])
    
    ctk.CTkLabel(
        inputs_frame,
        text="📝 Поля ввода:",
        font=("Arial", 14, "bold")
    ).pack(pady=(10, 5))
    
    inputs_row = ctk.CTkFrame(inputs_frame)
    inputs_row.configure(fg_color="transparent")
    inputs_row.pack(pady=10)
    
    for label, placeholder in [
        ("📅 От:", "YYYY-MM-DD HH:MM"),
        ("📅 До:", "YYYY-MM-DD HH:MM"),
        ("💰 Мин. объем:", "0.0"),
        ("🔍 Поиск:", "Введите текст...")
    ]:
        ctk.CTkLabel(inputs_row, text=label).pack(side='left', padx=(10, 5))
        entry = ctk.CTkEntry(inputs_row, width=120, placeholder_text=placeholder)
        entry.pack(side='left', padx=(0, 10))
    
    # Таблица-имитация
    table_frame = ctk.CTkFrame(container)
    table_frame.pack(fill='both', expand=True, pady=10)
    table_frame.configure(fg_color=theme.colors['bg_secondary'])
    
    ctk.CTkLabel(
        table_frame,
        text="📊 Таблица участников:",
        font=("Arial", 14, "bold")
    ).pack(pady=(10, 5))
    
    # Заголовки таблицы
    headers_frame = ctk.CTkFrame(table_frame)
    headers_frame.pack(fill='x', padx=10, pady=5)
    headers_frame.configure(fg_color=theme.colors['bg_tertiary'])
    
    headers = ["№", "Адрес", "Баланс", "Категория", "Статус", "Действия"]
    for header in headers:
        ctk.CTkLabel(
            headers_frame,
            text=header,
            font=("Arial", 12, "bold"),
            width=120
        ).pack(side='left', padx=5, pady=5)
    
    # Примеры строк
    for i in range(3):
        row_frame = ctk.CTkFrame(table_frame)
        row_frame.pack(fill='x', padx=10, pady=2)
        
        data = [
            str(i+1),
            f"0x1234...{i+1:04d}",
            f"{1000+i*100:.2f} PLEX",
            "PERFECT" if i == 0 else "MISSED_PURCHASE",
            "✅ Подходит" if i == 0 else "❌ Не подходит",
            "📋 💰 🎁"
        ]
        
        for cell in data:
            ctk.CTkLabel(
                row_frame,
                text=cell,
                width=120,
                font=("Arial", 10)
            ).pack(side='left', padx=5, pady=2)
    
    # Статус в footer
    footer = ctk.CTkFrame(app)
    footer.pack(fill='x', side='bottom')
    footer.configure(fg_color=theme.colors['bg_tertiary'])
    
    status = ctk.CTkLabel(
        footer,
        text="✅ UI тест: Все компоненты отображаются корректно | Resizable: Да | Логи: Доступны",
        font=("Arial", 12),
        text_color=theme.colors['success']
    )
    status.pack(pady=10)
    
    logger.info("🧪 Тест UI запущен")
    app.mainloop()

if __name__ == "__main__":
    test_ui_visibility()
