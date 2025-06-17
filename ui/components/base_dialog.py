"""
Модуль: Базовый класс диалогов для PLEX Dynamic Staking Manager
Описание: Базовый класс для всех диалоговых окон с поддержкой CustomTkinter v5.2.1
Автор: GitHub Copilot
"""

import customtkinter as ctk
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from utils.logger import get_logger
from ui.themes.chatgpt_theme import ChatGPTTheme

logger = get_logger("PLEX_BaseDialog")

class BaseDialog(ctk.CTkToplevel, ABC):
    """Базовый класс для всех диалоговых окон"""
    
    def __init__(
        self,
        parent: Optional[ctk.CTk] = None,
        title: str = "PLEX Dialog",
        width: int = 400,
        height: int = 300,
        resizable: bool = False,
        modal: bool = True
    ):
        """
        Инициализация базового диалога
        
        Args:
            parent: Родительское окно
            title: Заголовок диалога
            width: Ширина окна
            height: Высота окна
            resizable: Может ли окно изменять размер
            modal: Модальное ли окно
        """
        super().__init__(parent)
        
        logger.info(f"🔧 Инициализация BaseDialog: {title}")
        
        # Основные настройки
        self.parent = parent
        self.title_text = title
        self.result: Optional[Dict[str, Any]] = None
        self.is_modal = modal
        
        # Применяем тему
        self.theme = ChatGPTTheme()
        self._apply_theme()
        
        # Настройка окна
        self._setup_window(width, height, resizable)
        
        # Центрирование окна
        self._center_window()
        
        # Создание интерфейса
        self._create_interface()
        
        # Настройка модальности
        if modal:
            self._setup_modal()
    
    def _apply_theme(self) -> None:
        """Применение темы к диалогу"""
        colors = self.theme.get_colors()
        self.configure(fg_color=colors['bg_primary'])
    
    def _setup_window(self, width: int, height: int, resizable: bool) -> None:
        """Настройка параметров окна"""
        self.title(self.title_text)
        self.geometry(f"{width}x{height}")
        self.resizable(resizable, resizable)
        
        # Иконка (если есть)
        try:
            self.iconbitmap("assets/plex_icon.ico")
        except:
            pass  # Иконка не обязательна
    
    def _center_window(self) -> None:
        """Центрирование окна на экране"""
        self.update_idletasks()
        
        # Получаем размеры окна
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        
        # Получаем размеры экрана
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Вычисляем позицию для центрирования
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"+{x}+{y}")
    
    def _setup_modal(self) -> None:
        """Настройка модального режима"""
        if self.parent:
            self.transient(self.parent)
            self.grab_set()
        
        # Фокус на диалог
        self.focus_set()
        
        # Обработка закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    @abstractmethod
    def _create_interface(self) -> None:
        """Создание интерфейса диалога (должно быть переопределено в наследниках)"""
        pass
    
    def _on_close(self) -> None:
        """Обработка закрытия диалога"""
        logger.info(f"🔚 Закрытие диалога: {self.title_text}")
        self.result = None
        self._close_dialog()
    
    def _close_dialog(self) -> None:
        """Закрытие диалога"""
        if self.is_modal and self.parent:
            self.grab_release()
        self.destroy()
    
    def show_dialog(self) -> Optional[Dict[str, Any]]:
        """
        Показать диалог и вернуть результат
        
        Returns:
            Результат диалога или None если отменен
        """
        logger.info(f"📱 Показ диалога: {self.title_text}")
        
        if self.is_modal:
            self.wait_window()
        
        return self.result
    
    def accept(self, result: Dict[str, Any]) -> None:
        """
        Принятие диалога с результатом
        
        Args:
            result: Результат диалога
        """
        logger.info(f"✅ Диалог принят: {self.title_text}")
        self.result = result
        self._close_dialog()
    
    def reject(self) -> None:
        """Отклонение диалога"""
        logger.info(f"❌ Диалог отклонен: {self.title_text}")
        self.result = None
        self._close_dialog()

class MessageDialog(BaseDialog):
    """Диалог для показа сообщений"""
    
    def __init__(
        self,
        parent: Optional[ctk.CTk] = None,
        title: str = "Сообщение",
        message: str = "",
        dialog_type: str = "info",  # info, warning, error, question
        width: int = 400,
        height: int = 200
    ):
        self.message = message
        self.dialog_type = dialog_type
        super().__init__(parent, title, width, height)
    
    def _create_interface(self) -> None:
        """Создание интерфейса диалога сообщения"""
        colors = self.theme.get_colors()
        
        # Основной фрейм
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Иконка типа сообщения
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "question": "❓"
        }
        
        icon_label = ctk.CTkLabel(
            main_frame,
            text=icon_map.get(self.dialog_type, "ℹ️"),
            font=("Arial", 24)
        )
        icon_label.pack(pady=(0, 10))
        
        # Текст сообщения
        message_label = ctk.CTkLabel(
            main_frame,
            text=self.message,
            font=("Arial", 12),
            wraplength=350,
            justify="center"
        )
        message_label.pack(pady=(0, 20), fill="x")
        
        # Кнопки
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        if self.dialog_type == "question":
            # Да/Нет кнопки
            yes_button = ctk.CTkButton(
                button_frame,
                text="Да",
                command=lambda: self.accept({"result": True})
            )
            yes_button.pack(side="left", padx=(0, 10))
            
            no_button = ctk.CTkButton(
                button_frame,
                text="Нет",
                command=lambda: self.accept({"result": False})
            )
            no_button.pack(side="right")
        else:
            # Просто ОК
            ok_button = ctk.CTkButton(
                button_frame,
                text="ОК",
                command=lambda: self.accept({"result": True})
            )
            ok_button.pack()

class InputDialog(BaseDialog):
    """Диалог для ввода данных"""
    
    def __init__(
        self,
        parent: Optional[ctk.CTk] = None,
        title: str = "Ввод данных",
        prompt: str = "Введите значение:",
        default_value: str = "",
        width: int = 400,
        height: int = 250
    ):
        self.prompt = prompt
        self.default_value = default_value
        self.entry_var = ctk.StringVar(value=default_value)
        super().__init__(parent, title, width, height)
    
    def _create_interface(self) -> None:
        """Создание интерфейса диалога ввода"""
        # Основной фрейм
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Подсказка
        prompt_label = ctk.CTkLabel(
            main_frame,
            text=self.prompt,
            font=("Arial", 12)
        )
        prompt_label.pack(pady=(0, 10))
        
        # Поле ввода
        self.entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.entry_var,
            font=("Arial", 12)
        )
        self.entry.pack(fill="x", pady=(0, 20))
        self.entry.focus_set()
        
        # Привязка Enter
        self.entry.bind("<Return>", lambda e: self._on_ok())
        self.entry.bind("<Escape>", lambda e: self.reject())
        
        # Кнопки
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")
        
        ok_button = ctk.CTkButton(
            button_frame,
            text="ОК",
            command=self._on_ok
        )
        ok_button.pack(side="left", padx=(0, 10))
        
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Отмена",
            command=self.reject
        )
        cancel_button.pack(side="right")
    
    def _on_ok(self) -> None:
        """Обработка нажатия ОК"""
        value = self.entry_var.get().strip()
        if value:
            self.accept({"value": value})
        else:
            # Показать ошибку если поле пустое
            pass

# Удобные функции для быстрого создания диалогов
def show_info(parent: Optional[ctk.CTk], title: str, message: str) -> None:
    """Показать информационное сообщение"""
    dialog = MessageDialog(parent, title, message, "info")
    dialog.show_dialog()

def show_warning(parent: Optional[ctk.CTk], title: str, message: str) -> None:
    """Показать предупреждение"""
    dialog = MessageDialog(parent, title, message, "warning")
    dialog.show_dialog()

def show_error(parent: Optional[ctk.CTk], title: str, message: str) -> None:
    """Показать ошибку"""
    dialog = MessageDialog(parent, title, message, "error")
    dialog.show_dialog()

def ask_question(parent: Optional[ctk.CTk], title: str, message: str) -> bool:
    """Задать вопрос да/нет"""
    dialog = MessageDialog(parent, title, message, "question")
    result = dialog.show_dialog()
    return result.get("result", False) if result else False

def get_input(
    parent: Optional[ctk.CTk], 
    title: str, 
    prompt: str, 
    default: str = ""
) -> Optional[str]:
    """Получить ввод от пользователя"""
    dialog = InputDialog(parent, title, prompt, default)
    result = dialog.show_dialog()
    return result.get("value") if result else None
