"""
Модуль: SafeWidgetFactory для безопасного создания CustomTkinter виджетов
Описание: Фильтрует неподдерживаемые параметры, предотвращает runtime ошибки
Зависимости: customtkinter, logging
Автор: GitHub Copilot
"""

import logging
from typing import Dict, Any, Set, Optional, Callable
import customtkinter as ctk
from config.constants import UI_COLORS

logger = logging.getLogger(__name__)


class SafeWidgetFactory:
    """
    Фабрика для безопасного создания CustomTkinter виджетов.
    
    Автоматически фильтрует неподдерживаемые параметры для CustomTkinter v5.2.1
    и предотвращает runtime ошибки типа "unexpected keyword argument".
    """
    
    # Поддерживаемые параметры для каждого типа виджета CustomTkinter v5.2.1
    SAFE_PARAMS: Dict[str, Set[str]] = {
        'CTkEntry': {
            'height', 'width', 'corner_radius', 'fg_color', 'border_color', 
            'text_color', 'font', 'state', 'textvariable', 'justify', 'show'
        },
        'CTkButton': {
            'height', 'width', 'corner_radius', 'fg_color', 'hover_color', 
            'text_color', 'font', 'command', 'state', 'text', 'image',
            'compound', 'anchor'
        },
        'CTkTextbox': {
            'height', 'width', 'corner_radius', 'fg_color', 'text_color',
            'font', 'state', 'wrap', 'spacing1', 'spacing2', 'spacing3'
        },
        'CTkLabel': {
            'height', 'width', 'corner_radius', 'fg_color', 'text_color',
            'font', 'text', 'image', 'compound', 'anchor', 'justify'
        },
        'CTkFrame': {
            'height', 'width', 'corner_radius', 'fg_color', 'border_color',
            'border_width'
        },
        'CTkCheckBox': {
            'height', 'width', 'corner_radius', 'fg_color', 'hover_color',
            'text_color', 'font', 'text', 'variable', 'command', 'state'
        },
        'CTkRadioButton': {
            'height', 'width', 'corner_radius', 'fg_color', 'hover_color',
            'text_color', 'font', 'text', 'variable', 'value', 'command', 'state'
        },
        'CTkProgressBar': {
            'height', 'width', 'corner_radius', 'fg_color', 'progress_color',
            'orientation', 'mode', 'determinate_speed', 'indeterminate_speed'
        },
        'CTkSlider': {
            'height', 'width', 'corner_radius', 'fg_color', 'progress_color',
            'button_color', 'button_hover_color', 'from_', 'to', 'number_of_steps',
            'orientation', 'state', 'variable', 'command'
        },
        'CTkOptionMenu': {
            'height', 'width', 'corner_radius', 'fg_color', 'button_color',
            'button_hover_color', 'text_color', 'font', 'values', 'variable',
            'command', 'state', 'anchor'
        },
        'CTkComboBox': {
            'height', 'width', 'corner_radius', 'fg_color', 'border_color',
            'button_color', 'button_hover_color', 'text_color', 'font',
            'values', 'variable', 'command', 'state', 'justify'
        },
        'CTkScrollableFrame': {
            'height', 'width', 'corner_radius', 'fg_color', 'border_color',
            'border_width', 'scrollbar_fg_color', 'scrollbar_button_color',
            'scrollbar_button_hover_color', 'orientation'
        },
        'CTkTabview': {
            'height', 'width', 'corner_radius', 'fg_color', 'border_color',
            'border_width', 'segmented_button_fg_color', 'segmented_button_selected_color',
            'segmented_button_selected_hover_color', 'segmented_button_unselected_color',
            'segmented_button_unselected_hover_color', 'text_color', 'text_color_disabled'
        },
        'CTkToplevel': {
            'fg_color'
        }
    }
    
    def __init__(self, theme=None):
        """
        Инициализация SafeWidgetFactory с темой.
        
        Args:
            theme: Объект темы для получения цветов и стилей
        """
        self.theme = theme
        logger.debug("🏭 SafeWidgetFactory инициализирована с темой")
    
    def create_entry(self, parent, **kwargs) -> ctk.CTkEntry:
        """Создает безопасный CTkEntry виджет."""
        return self.create_widget(ctk.CTkEntry, parent, **kwargs)
    
    def create_button(self, parent, **kwargs) -> ctk.CTkButton:
        """Создает безопасный CTkButton виджет."""
        return self.create_widget(ctk.CTkButton, parent, **kwargs)
    
    def create_textbox(self, parent, **kwargs) -> ctk.CTkTextbox:
        """Создает безопасный CTkTextbox виджет."""
        return self.create_widget(ctk.CTkTextbox, parent, **kwargs)
    
    def create_label(self, parent, **kwargs) -> ctk.CTkLabel:
        """Создает безопасный CTkLabel виджет."""
        return self.create_widget(ctk.CTkLabel, parent, **kwargs)
    
    def create_frame(self, parent, **kwargs) -> ctk.CTkFrame:
        """Создает безопасный CTkFrame виджет."""
        return self.create_widget(ctk.CTkFrame, parent, **kwargs)
    
    def setup_placeholder(self, widget, placeholder_text: str, is_textbox: bool = False) -> None:
        """Настраивает placeholder для виджета."""
        self._setup_placeholder(widget, placeholder_text, is_textbox)
    
    # Параметры, которые требуют специальной обработки
    SPECIAL_HANDLING = {
        'placeholder_text': '_setup_placeholder',
        'hover_color': '_validate_hover_support',
        'border_width': '_validate_border_support'    }
    
    def create_widget(self, widget_class, parent, **kwargs) -> Any:
        """
        Создает виджет только с поддерживаемыми параметрами.
        
        Args:
            widget_class: Класс виджета CustomTkinter
            parent: Родительский элемент
            **kwargs: Параметры виджета
            
        Returns:
            Созданный виджет
        """
        widget_name = widget_class.__name__
        safe_params = self.SAFE_PARAMS.get(widget_name, set())
        
        # Разделяем параметры на безопасные и требующие специальной обработки
        safe_kwargs = {}
        special_kwargs = {}
        removed_params = []
        
        for key, value in kwargs.items():
            if key in safe_params:
                safe_kwargs[key] = value
            elif key in self.SPECIAL_HANDLING:
                special_kwargs[key] = value
            else:
                removed_params.append(key)
        
        # Логируем удаленные параметры
        if removed_params:
            logger.warning(f"🔧 Удалены неподдерживаемые параметры для {widget_name}: {removed_params}")
        
        # Создаем виджет с безопасными параметрами
        try:
            widget = widget_class(parent, **safe_kwargs)
            logger.debug(f"✅ Создан {widget_name} с параметрами: {list(safe_kwargs.keys())}")
            
            # Применяем специальную обработку
            self._apply_special_handling(widget, widget_name, special_kwargs)
            
            return widget
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания {widget_name}: {e}")
            logger.error(f"   Параметры: {safe_kwargs}")
            raise
    
    def _apply_special_handling(self, widget, widget_name: str, special_kwargs: Dict[str, Any]) -> None:
        """Применяет специальную обработку для параметров, требующих дополнительной логики."""
        
        # Placeholder text - программная реализация
        if 'placeholder_text' in special_kwargs:
            placeholder_text = special_kwargs['placeholder_text']
            is_textbox = widget_name == 'CTkTextbox'
            self._setup_placeholder(widget, placeholder_text, is_textbox)
        
        # Hover color - только для поддерживающих виджетов
        if 'hover_color' in special_kwargs and widget_name in ['CTkButton', 'CTkCheckBox', 'CTkRadioButton']:
            try:
                widget.configure(hover_color=special_kwargs['hover_color'])
            except Exception as e:                logger.warning(f"⚠️ Не удалось установить hover_color для {widget_name}: {e}")
    
    def _setup_placeholder(self, widget, placeholder_text: str, is_textbox: bool = False) -> None:
        """
        Программная реализация placeholder для Entry и Textbox.
        
        CustomTkinter v5.2.1 не поддерживает нативный placeholder_text,
        поэтому реализуем через события focus in/out.
        """
        # Цвета для placeholder
        PLACEHOLDER_COLOR = "#666666"
        NORMAL_COLOR = UI_COLORS.get('text_primary', "#ECECEC")
        
        def on_focus_in(event):
            if is_textbox:
                current = widget.get("1.0", "end-1c")
            else:
                current = widget.get()
                
            if current == placeholder_text:
                if is_textbox:
                    widget.delete("1.0", "end")
                else:
                    widget.delete(0, "end")
                widget.configure(text_color=NORMAL_COLOR)
        
        def on_focus_out(event):
            if is_textbox:
                current = widget.get("1.0", "end-1c")
            else:
                current = widget.get()
                
            if not current.strip():
                if is_textbox:
                    widget.insert("1.0", placeholder_text)
                else:
                    widget.insert(0, placeholder_text)
                widget.configure(text_color=PLACEHOLDER_COLOR)
        
        # Привязываем события
        widget.bind("<FocusIn>", on_focus_in)
        widget.bind("<FocusOut>", on_focus_out)
        
        # Устанавливаем начальный placeholder
        on_focus_out(None)
        
        logger.debug(f"✅ Placeholder установлен: '{placeholder_text}'")
    
    @classmethod
    def create_styled_entry(cls, parent, placeholder: str = "", **kwargs) -> ctk.CTkEntry:
        """Удобный метод для создания Entry с placeholder."""
        kwargs['placeholder_text'] = placeholder
        return cls.create_widget(ctk.CTkEntry, parent, **kwargs)
    
    @classmethod
    def create_styled_textbox(cls, parent, placeholder: str = "", **kwargs) -> ctk.CTkTextbox:
        """Удобный метод для создания Textbox с placeholder."""
        kwargs['placeholder_text'] = placeholder
        return cls.create_widget(ctk.CTkTextbox, parent, **kwargs)
    
    @classmethod
    def create_styled_button(cls, parent, text: str, **kwargs) -> ctk.CTkButton:
        """Удобный метод для создания Button."""
        kwargs['text'] = text
        return cls.create_widget(ctk.CTkButton, parent, **kwargs)
    
    @classmethod
    def create_styled_label(cls, parent, text: str, **kwargs) -> ctk.CTkLabel:
        """Удобный метод для создания Label."""
        kwargs['text'] = text
        return cls.create_widget(ctk.CTkLabel, parent, **kwargs)
    
    @classmethod
    def create_styled_frame(cls, parent, **kwargs) -> ctk.CTkFrame:
        """Удобный метод для создания Frame."""
        return cls.create_widget(ctk.CTkFrame, parent, **kwargs)
    
    @classmethod
    def validate_color(cls, color: Optional[str]) -> str:
        """
        Валидация цвета - всегда возвращает валидный цвет.
        
        Args:
            color: Цвет для валидации
            
        Returns:
            Валидный цвет (никогда не None)
        """
        if not color or not isinstance(color, str):
            return UI_COLORS.get('text_secondary', '#A0A0A0')
        
        # Проверяем hex формат
        if color.startswith('#') and len(color) in [4, 7]:
            return color
        
        # Проверяем именованные цвета
        named_colors = ['red', 'green', 'blue', 'white', 'black', 'gray', 'yellow', 'orange', 'purple']
        if color.lower() in named_colors:
            return color
        
        # Возвращаем дефолтный цвет для неизвестных
        logger.warning(f"⚠️ Неизвестный цвет '{color}', используется дефолтный")
        return UI_COLORS.get('text_secondary', '#A0A0A0')
    
    @classmethod
    def get_safe_params_for_widget(cls, widget_name: str) -> Set[str]:
        """Получить список безопасных параметров для виджета."""
        return cls.SAFE_PARAMS.get(widget_name, set()).copy()
    
    @classmethod
    def is_param_safe(cls, widget_name: str, param_name: str) -> bool:
        """Проверить, безопасен ли параметр для виджета."""
        safe_params = cls.SAFE_PARAMS.get(widget_name, set())
        return param_name in safe_params or param_name in cls.SPECIAL_HANDLING


# Удобные функции для быстрого доступа
def create_safe_widget(widget_class, parent, **kwargs):
    """Быстрый доступ к SafeWidgetFactory.create_widget"""
    return SafeWidgetFactory.create_widget(widget_class, parent, **kwargs)


def setup_placeholder(widget, placeholder_text: str, is_textbox: bool = False):
    """Быстрый доступ к настройке placeholder"""
    SafeWidgetFactory._setup_placeholder(widget, placeholder_text, is_textbox)


# Экспорт
__all__ = [
    'SafeWidgetFactory',
    'create_safe_widget', 
    'setup_placeholder'
]


if __name__ == "__main__":
    # Тестирование SafeWidgetFactory
    import tkinter as tk
    
    print("🧪 Тестирование SafeWidgetFactory...")
    
    # Тест поддерживаемых параметров
    safe_params = SafeWidgetFactory.get_safe_params_for_widget('CTkEntry')
    print(f"✅ Безопасные параметры для CTkEntry: {safe_params}")
    
    # Тест валидации цвета
    test_colors = ["#FF0000", "red", "#invalid", None, "", "unknown"]
    for color in test_colors:
        validated = SafeWidgetFactory.validate_color(color)
        print(f"🎨 Цвет '{color}' -> '{validated}'")
    
    # Тест проверки параметров
    test_params = ["height", "width", "placeholder_text", "invalid_param"]
    for param in test_params:
        is_safe = SafeWidgetFactory.is_param_safe('CTkEntry', param)
        status = "✅" if is_safe else "❌"
        print(f"{status} Параметр '{param}' для CTkEntry: {is_safe}")
    
    print("✅ Тестирование SafeWidgetFactory завершено успешно")
