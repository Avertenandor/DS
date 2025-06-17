"""
PLEX Dynamic Staking Manager - Dark Theme
Темная тема в стиле ChatGPT для CustomTkinter интерфейса.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

from typing import Dict, Tuple, Any
import customtkinter as ctk

# Цветовая палитра в стиле ChatGPT Dark
CHATGPT_COLORS = {
    # Основные цвета фона
    'bg_primary': '#171717',      # Основной фон (темно-серый)
    'bg_secondary': '#212121',    # Вторичный фон (чуть светлее)
    'bg_tertiary': '#2a2a2a',     # Третичный фон (для карточек)
    'bg_hover': '#343434',        # Фон при наведении
    'bg_active': '#404040',       # Активное состояние
    
    # Цвета текста
    'text_primary': '#ffffff',    # Основной текст (белый)
    'text_secondary': '#b4b4b4',  # Вторичный текст (серый)
    'text_muted': '#737373',      # Приглушенный текст
    'text_accent': '#10a37f',     # Акцентный текст (зеленый ChatGPT)
    
    # Цвета границ
    'border_primary': '#404040',  # Основные границы
    'border_secondary': '#505050', # Вторичные границы
    'border_accent': '#10a37f',   # Акцентные границы
    
    # Цвета для кнопок
    'btn_primary': '#10a37f',     # Основная кнопка (зеленый)
    'btn_primary_hover': '#0d8f6b', # Наведение на основную кнопку
    'btn_secondary': '#343434',   # Вторичная кнопка
    'btn_secondary_hover': '#404040', # Наведение на вторичную кнопку
    'btn_danger': '#ef4444',      # Опасная кнопка (красный)
    'btn_danger_hover': '#dc2626', # Наведение на опасную кнопку
    
    # Цвета для статусов
    'success': '#22c55e',         # Успех (зеленый)
    'warning': '#f59e0b',         # Предупреждение (желтый)
    'error': '#ef4444',           # Ошибка (красный)
    'info': '#3b82f6',            # Информация (синий)
      # Цвета для прогресс баров
    'progress_bg': '#404040',     # Фон прогресс бара
    'progress_fill': '#10a37f',   # Заливка прогресс бара
    
    # Акцентный цвет (для обратной совместимости)
    'accent': '#10a37f',          # Основной акцентный цвет
    
    # Цвета для входных полей
    'input_bg': '#2a2a2a',        # Фон поля ввода
    'input_border': '#404040',    # Граница поля ввода
    'input_focus': '#10a37f',     # Фокус поля ввода
    
    # Цвета для скроллбаров
    'scrollbar_bg': '#2a2a2a',    # Фон скроллбара
    'scrollbar_thumb': '#505050', # Ползунок скроллбара
    'scrollbar_hover': '#606060', # Наведение на ползунок
}

# PLEX брендинг
PLEX_COLORS = {
    'plex_primary': '#9d4edd',    # Основной цвет PLEX (фиолетовый)
    'plex_secondary': '#7c3aed',  # Вторичный цвет PLEX
    'plex_accent': '#8b5cf6',     # Акцентный цвет PLEX
    'plex_light': '#c084fc',      # Светлый PLEX
    'plex_dark': '#6b21a8',       # Темный PLEX
}

# Объединенная палитра
THEME_COLORS = {**CHATGPT_COLORS, **PLEX_COLORS}


class DarkTheme:
    """
    Темная тема для PLEX Dynamic Staking Manager.
    Стилизована под ChatGPT с элементами брендинга PLEX.
    """
    
    def __init__(self):
        """Инициализация темной темы."""
        self.colors = THEME_COLORS.copy()
        self._setup_ctk_theme()
    
    def _setup_ctk_theme(self) -> None:
        """Настройка CustomTkinter темы."""
        # Установка темного режима
        ctk.set_appearance_mode("dark")
        
        # Пользовательская тема
        ctk.set_default_color_theme("blue")  # Базовая тема
        
        # Дополнительная настройка цветов будет в методах компонентов
    
    def get_window_style(self) -> Dict[str, Any]:
        """
        Получение стиля для главного окна.
        
        Returns:
            Dict: Параметры стиля окна
        """
        return {
            'fg_color': self.colors['bg_primary'],
            'corner_radius': 0,
        }
    
    def get_frame_style(self, variant: str = 'primary') -> Dict[str, Any]:
        """
        Получение стиля для фреймов.
        
        Args:
            variant: Вариант стиля ('primary', 'secondary', 'card')
              Returns:
            Dict: Параметры стиля фрейма
        """
        styles = {
            'primary': {
                'fg_color': self.colors['bg_primary'],
                'corner_radius': 8,
            },
            'secondary': {
                'fg_color': self.colors['bg_secondary'],
                'corner_radius': 8,
            },
            'card': {
                'fg_color': self.colors['bg_tertiary'],
                'corner_radius': 12,
            }
        }
        
        return styles.get(variant, styles['primary'])
    
    def get_button_style(self, variant: str = 'primary') -> Dict[str, Any]:
        """
        Получение стиля для кнопок.
        
        Args:
            variant: Вариант стиля ('primary', 'secondary', 'danger', 'plex')
              Returns:
            Dict: Параметры стиля кнопки
        """
        styles = {
            'primary': {
                'fg_color': self.colors['btn_primary'],
                'text_color': self.colors['text_primary'],
                'corner_radius': 8,
                'font': ('Segoe UI', 12, 'normal'),
            },
            'secondary': {
                'fg_color': self.colors['btn_secondary'],
                'text_color': self.colors['text_primary'],
                'corner_radius': 8,
                'font': ('Segoe UI', 12, 'normal'),
            },
            'danger': {
                'fg_color': self.colors['btn_danger'],
                'text_color': self.colors['text_primary'],
                'corner_radius': 8,
                'font': ('Segoe UI', 12, 'normal'),
            },
            'plex': {
                'fg_color': self.colors['plex_primary'],
                'text_color': self.colors['text_primary'],
                'corner_radius': 8,
                'font': ('Segoe UI', 12, 'bold'),
            }
        }
        
        return styles.get(variant, styles['primary'])
    
    def get_label_style(self, variant: str = 'primary') -> Dict[str, Any]:
        """
        Получение стиля для лейблов.
        
        Args:
            variant: Вариант стиля ('primary', 'secondary', 'muted', 'accent', 'title')
            
        Returns:
            Dict: Параметры стиля лейбла
        """
        styles = {
            'primary': {
                'text_color': self.colors['text_primary'],
                'font': ('Segoe UI', 12, 'normal'),
            },
            'secondary': {
                'text_color': self.colors['text_secondary'],
                'font': ('Segoe UI', 11, 'normal'),
            },
            'muted': {
                'text_color': self.colors['text_muted'],
                'font': ('Segoe UI', 10, 'normal'),
            },
            'accent': {
                'text_color': self.colors['text_accent'],
                'font': ('Segoe UI', 12, 'normal'),
            },
            'title': {
                'text_color': self.colors['text_primary'],
                'font': ('Segoe UI', 18, 'bold'),
            },
            'subtitle': {
                'text_color': self.colors['text_secondary'],
                'font': ('Segoe UI', 14, 'normal'),
            }
        }
        
        return styles.get(variant, styles['primary'])
    
    def get_entry_style(self) -> Dict[str, Any]:
        """
        Получение стиля для полей ввода.
          Returns:
            Dict: Параметры стиля поля ввода
        """
        return {
            'fg_color': self.colors['input_bg'],
            'text_color': self.colors['text_primary'],
            'placeholder_text_color': self.colors['text_muted'],
            'corner_radius': 6,
            'font': ('Consolas', 11, 'normal'),
        }
    
    def get_textbox_style(self) -> Dict[str, Any]:
        """
        Получение стиля для текстовых областей.
          Returns:
            Dict: Параметры стиля текстовой области
        """
        return {
            'fg_color': self.colors['input_bg'],
            'text_color': self.colors['text_primary'],
            'corner_radius': 8,
            'font': ('Consolas', 10, 'normal'),
            'scrollbar_button_color': self.colors['scrollbar_thumb'],
        }
    
    def get_progressbar_style(self) -> Dict[str, Any]:
        """
        Получение стиля для прогресс-баров.
          Returns:
            Dict: Параметры стиля прогресс-бара
        """
        return {
            'fg_color': self.colors['progress_bg'],
            'corner_radius': 10,
            'height': 8,
        }
    
    def get_progress_style(self) -> Dict[str, Any]:
        """
        Получение стиля для прогресс-баров (алиас для get_progressbar_style).
        
        Returns:
            Dict: Параметры стиля прогресс-бара
        """
        return self.get_progressbar_style()
    
    def get_tabview_style(self) -> Dict[str, Any]:
        """
        Получение стиля для вкладок.
          Returns:
            Dict: Параметры стиля вкладок
        """
        return {
            'fg_color': self.colors['bg_secondary'],
            'segmented_button_fg_color': self.colors['bg_tertiary'],
            'segmented_button_selected_color': self.colors['btn_primary'],
            'segmented_button_unselected_color': self.colors['bg_tertiary'],
            'text_color': self.colors['text_primary'],
            'corner_radius': 8,
        }
    
    def get_switch_style(self) -> Dict[str, Any]:
        """
        Получение стиля для переключателей.        Returns:
            Dict: Параметры стиля переключателя
        """
        return {
            'fg_color': self.colors['border_primary'],
            'button_color': self.colors['text_primary'],
        }
    
    def get_scrollbar_style(self) -> Dict[str, Any]:
        """Получение стиля для скроллбаров."""
        return {
            'fg_color': self.colors['scrollbar_bg'],
            'button_color': self.colors['scrollbar_thumb'],
            'corner_radius': 6,
        }
    
    def get_status_color(self, status: str) -> str:
        """Получение цвета для статуса."""
        try:
            if not isinstance(status, str):
                status = str(status)
                
            status_colors = {
                'success': self.colors['success'],
                'warning': self.colors['warning'],
                'error': self.colors['error'],
                'info': self.colors['info'],
                'plex': self.colors['plex_primary'],
            }
            
            color = status_colors.get(status, self.colors['text_primary'])
            return str(color) if color else '#ffffff'
            
        except Exception:
            return '#ffffff'
    
    def apply_hover_effect(self, widget, hover_color: str = None) -> None:
        """
        Применение эффекта наведения к виджету.
        
        Args:
            widget: CustomTkinter виджет
            hover_color: Цвет при наведении
        """
        if hover_color is None:
            hover_color = self.colors['bg_hover']
        
        original_color = widget.cget('fg_color')
        
        def on_enter(event):
            widget.configure(fg_color=hover_color)
        
        def on_leave(event):
            widget.configure(fg_color=original_color)
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def create_styled_frame(self, parent, variant: str = 'primary', **kwargs) -> ctk.CTkFrame:
        """
        Создание стилизованного фрейма.
        
        Args:
            parent: Родительский виджет
            variant: Вариант стиля
            **kwargs: Дополнительные параметры
            
        Returns:
            CTkFrame: Стилизованный фрейм
        """
        style = self.get_frame_style(variant)
        style.update(kwargs)
        return ctk.CTkFrame(parent, **style)
    
    def create_styled_button(self, parent, text: str, variant: str = 'primary', **kwargs) -> ctk.CTkButton:
        """
        Создание стилизованной кнопки.
        
        Args:
            parent: Родительский виджет
            text: Текст кнопки
            variant: Вариант стиля
            **kwargs: Дополнительные параметры
            
        Returns:
            CTkButton: Стилизованная кнопка
        """
        style = self.get_button_style(variant)
        style.update(kwargs)
        return ctk.CTkButton(parent, text=text, **style)
    
    def create_styled_label(self, parent, text: str, variant: str = 'primary', **kwargs) -> ctk.CTkLabel:
        """
        Создание стилизованного лейбла.
        
        Args:
            parent: Родительский виджет
            text: Текст лейбла
            variant: Вариант стиля
            **kwargs: Дополнительные параметры            
        Returns:
            CTkLabel: Стилизованный лейбл
        """
        style = self.get_label_style(variant)
        style.update(kwargs)
        return ctk.CTkLabel(parent, text=text, **style)
    
    def create_styled_entry(self, parent, placeholder: str = "", **kwargs) -> ctk.CTkEntry:
        """Создание стилизованного поля ввода."""
        style = self.get_entry_style()
        style.update(kwargs)
        
        try:
            return ctk.CTkEntry(parent, placeholder_text=placeholder, **style)
        except TypeError:
            entry = ctk.CTkEntry(parent, **style)
            if placeholder:
                entry.insert(0, placeholder)
                entry.configure(text_color=("gray60", "gray40"))
            return entry
    
    def create_styled_textbox(self, parent, **kwargs) -> ctk.CTkTextbox:
        """
        Создание стилизованной текстовой области.
        
        Args:
            parent: Родительский виджет
            **kwargs: Дополнительные параметры
            
        Returns:
            CTkTextbox: Стилизованная текстовая область
        """
        style = self.get_textbox_style()
        style.update(kwargs)
        return ctk.CTkTextbox(parent, **style)
    
    def create_styled_progressbar(self, parent, **kwargs) -> ctk.CTkProgressBar:
        """
        Создание стилизованного прогресс-бара.
        
        Args:
            parent: Родительский виджет
            **kwargs: Дополнительные параметры
            
        Returns:
            CTkProgressBar: Стилизованный прогресс-бар
        """
        style = self.get_progressbar_style()
        style.update(kwargs)
        return ctk.CTkProgressBar(parent, **style)
    
    def get_text_style(self) -> Dict[str, Any]:
        """
        Получение стиля для текстовых полей.
        
        Returns:
            Dict: Параметры стиля текстового поля
        """
        return self.get_textbox_style()


# Глобальный экземпляр темы
_theme_instance: DarkTheme = None


def get_theme() -> DarkTheme:
    """
    Получение глобального экземпляра темы.
    
    Returns:
        DarkTheme: Экземпляр темной темы
    """
    global _theme_instance
    
    if _theme_instance is None:
        _theme_instance = DarkTheme()
    
    return _theme_instance


# Удобные функции для быстрого доступа к стилям
def get_colors() -> Dict[str, str]:
    """Получение цветовой палитры."""
    return get_theme().colors


def apply_window_style(window) -> None:
    """Применение стиля к главному окну."""
    style = get_theme().get_window_style()
    window.configure(**style)


# Экспорт для удобного импорта
__all__ = [
    'DarkTheme',
    'get_theme',
    'get_colors',
    'apply_window_style',
    'THEME_COLORS',
    'CHATGPT_COLORS',
    'PLEX_COLORS'
]


if __name__ == "__main__":
    # Демонстрация темы
    def demo_theme():
        """Демонстрация темной темы."""
        try:
            import tkinter as tk
            
            print("🎨 Демонстрация темной темы PLEX Dynamic Staking Manager")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Theme Demo")
            root.geometry("800x600")
            
            # Применение темы
            theme = get_theme()
            apply_window_style(root)
            
            # Демонстрационные элементы
            main_frame = theme.create_styled_frame(root, 'card')
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Заголовок
            title = theme.create_styled_label(main_frame, "PLEX Dynamic Staking Manager", 'title')
            title.pack(pady=(20, 10))
            
            subtitle = theme.create_styled_label(main_frame, "Демонстрация темной темы", 'subtitle')
            subtitle.pack(pady=(0, 30))
            
            # Кнопки
            btn_frame = theme.create_styled_frame(main_frame, 'primary')
            btn_frame.pack(fill='x', padx=20, pady=10)
            
            btn_primary = theme.create_styled_button(btn_frame, "Основная кнопка", 'primary')
            btn_primary.pack(side='left', padx=(0, 10))
            
            btn_plex = theme.create_styled_button(btn_frame, "PLEX кнопка", 'plex')
            btn_plex.pack(side='left', padx=(0, 10))
            
            btn_danger = theme.create_styled_button(btn_frame, "Опасная кнопка", 'danger')
            btn_danger.pack(side='left')
            
            # Поле ввода
            entry = theme.create_styled_entry(main_frame, "Введите адрес кошелька...")
            entry.pack(fill='x', padx=20, pady=10)
            
            # Текстовая область
            textbox = theme.create_styled_textbox(main_frame)
            textbox.pack(fill='both', expand=True, padx=20, pady=10)
            textbox.insert('0.0', "Это демонстрация темной темы PLEX Dynamic Staking Manager.\n\n"
                                "Цветовая схема вдохновлена ChatGPT с элементами брендинга PLEX.\n\n"
                                "Основные цвета:\n"
                                f"- Фон: {theme.colors['bg_primary']}\n"
                                f"- Текст: {theme.colors['text_primary']}\n"
                                f"- Акцент: {theme.colors['text_accent']}\n"
                                f"- PLEX: {theme.colors['plex_primary']}")
            
            # Прогресс-бар
            progress = theme.create_styled_progressbar(main_frame)
            progress.pack(fill='x', padx=20, pady=10)
            progress.set(0.7)
            
            print("✅ Демо окно создано. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_theme()
    print("💡 Для демонстрации темы раскомментируй последнюю строку")
