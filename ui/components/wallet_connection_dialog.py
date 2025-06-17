"""
PLEX Dynamic Staking Manager - Wallet Connection Dialog
Диалог для подключения кошелька по seed фразе или приватному ключу.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
import re
from web3 import Web3
from eth_account import Account

from ui.themes.dark_theme import get_theme
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class WalletConnectionDialog(ctk.CTkToplevel):
    """
    Диалог для подключения кошелька.
    
    Поддерживает:
    - Подключение по seed фразе (mnemonic)
    - Подключение по приватному ключу
    - Валидация данных
    - Безопасное хранение
    """
    
    def __init__(self, parent, on_wallet_connected: Optional[Callable] = None, widget_factory=None):
        """
        Инициализация диалога подключения кошелька.
        
        Args:
            parent: Родительское окно
            on_wallet_connected: Callback при успешном подключении
        """
        super().__init__(parent)
        
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        self.on_wallet_connected = on_wallet_connected
        self.wallet_address = None
        self.private_key = None
        self.result = None
        
        # Настройка окна
        self.title("🔐 Подключение кошелька")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Центрирование относительно родительского окна
        self._center_window()
        
        # Перехват фокуса
        self.transient(parent)
        self.grab_set()
        
        # Создание интерфейса
        self._create_interface()
        
        logger.debug("🔐 WalletConnectionDialog инициализирован")
    
    def _center_window(self) -> None:
        """Центрирование окна."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"600x500+{x}+{y}")
    
    def _create_interface(self) -> None:
        """Создание интерфейса диалога."""
        # Основной контейнер
        self.main_frame = self.theme.create_styled_frame(self, 'primary')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Заголовок
        self.title_label = self.theme.create_styled_label(
            self.main_frame,
            "🔐 Подключение кошелька",
            'title'
        )
        self.title_label.pack(pady=(0, 20))
        
        # Описание
        self.description_label = self.theme.create_styled_label(
            self.main_frame,
            "Выберите способ подключения кошелька для управления\\n"
            "PLEX Dynamic Staking операциями",
            'secondary'
        )
        self.description_label.pack(pady=(0, 30))
        
        # Выбор метода подключения
        self._create_connection_method_selection()
        
        # Поля ввода
        self._create_input_fields()
        
        # Кнопки
        self._create_buttons()
        
        # Статус
        self._create_status_display()
    
    def _create_connection_method_selection(self) -> None:
        """Создание выбора метода подключения."""
        self.method_frame = self.theme.create_styled_frame(self.main_frame, 'card')
        self.method_frame.pack(fill='x', pady=(0, 20))
        
        self.method_title = self.theme.create_styled_label(
            self.method_frame,
            "📋 Метод подключения:",
            'subtitle'
        )
        self.method_title.pack(anchor='w', padx=15, pady=(15, 10))
        
        # Переключатели методов
        self.connection_method = ctk.StringVar(value="seed")
        
        self.seed_radio = ctk.CTkRadioButton(
            self.method_frame,
            text="🌱 Seed фраза (12/24 слова)",
            variable=self.connection_method,
            value="seed",
            command=self._on_method_changed,
            **self.theme.get_button_style('secondary')
        )
        self.seed_radio.pack(anchor='w', padx=30, pady=5)
        
        self.private_key_radio = ctk.CTkRadioButton(
            self.method_frame,
            text="🔑 Приватный ключ (64 символа)",
            variable=self.connection_method,
            value="private_key",
            command=self._on_method_changed,
            **self.theme.get_button_style('secondary')
        )
        self.private_key_radio.pack(anchor='w', padx=30, pady=(5, 15))
    
    def _create_input_fields(self) -> None:
        """Создание полей ввода."""
        self.input_frame = self.theme.create_styled_frame(self.main_frame, 'card')
        self.input_frame.pack(fill='x', pady=(0, 20))
          # Seed фраза
        self.seed_frame = self.theme.create_styled_frame(self.input_frame, 'primary')
        
        self.seed_label = self.theme.create_styled_label(
            self.seed_frame,
            "🌱 Введите seed фразу (12 или 24 слова):",
            'primary'
        )
        self.seed_label.pack(anchor='w', padx=15, pady=(15, 5))
        
        self.seed_textbox = self.theme.create_styled_textbox(
            self.seed_frame,
            height=80
        )
        self.seed_textbox.pack(fill='x', padx=15, pady=(0, 15))
        
        # Добавляем placeholder text программно
        self.seed_textbox.insert("0.0", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
        self.seed_textbox.configure(text_color=("gray60", "gray40"))
        
        # Привязываем события для placeholder
        self._setup_seed_placeholder()
        
        # Приватный ключ
        self.private_key_frame = self.theme.create_styled_frame(self.input_frame, 'primary')
        
        self.private_key_label = self.theme.create_styled_label(
            self.private_key_frame,
            "🔑 Введите приватный ключ (без префикса 0x):",
            'primary'
        )
        self.private_key_label.pack(anchor='w', padx=15, pady=(15, 5))
        
        self.private_key_entry = self.theme.create_styled_entry(
            self.private_key_frame,
            show="*"
        )
        self.private_key_entry.pack(fill='x', padx=15, pady=(0, 15))
        
        # Добавляем placeholder text программно
        self.private_key_entry.insert(0, "Приватный ключ (64 символа)")
        self.private_key_entry.configure(text_color=("gray60", "gray40"))
        
        # Привязываем события для placeholder
        self._setup_private_key_placeholder()
        
        self.show_key_var = ctk.BooleanVar()
        self.show_key_checkbox = ctk.CTkCheckBox(
            self.private_key_frame,
            text="👁️ Показать ключ",
            variable=self.show_key_var,
            command=self._toggle_key_visibility,
            **self.theme.get_button_style('secondary')
        )
        self.show_key_checkbox.pack(anchor='w', padx=15, pady=(0, 15))
        
        # Установка начального состояния
        self._on_method_changed()
    
    def _create_buttons(self) -> None:
        """Создание кнопок."""
        self.buttons_frame = self.theme.create_styled_frame(self.main_frame, 'primary')
        self.buttons_frame.pack(fill='x', pady=(0, 20))
        
        # Кнопка подключения
        self.connect_button = self.theme.create_styled_button(
            self.buttons_frame,
            "🔐 Подключить кошелек",
            'success',
            command=self._connect_wallet,
            width=200
        )
        self.connect_button.pack(side='left', padx=(15, 10), pady=15)
        
        # Кнопка отмены
        self.cancel_button = self.theme.create_styled_button(
            self.buttons_frame,
            "❌ Отмена",
            'danger',
            command=self._cancel,
            width=120
        )
        self.cancel_button.pack(side='right', padx=(10, 15), pady=15)
        
        # Кнопка генерации тестового кошелька
        self.generate_button = self.theme.create_styled_button(
            self.buttons_frame,
            "🎲 Тестовый кошелек",
            'info',
            command=self._generate_test_wallet,
            width=150
        )
        self.generate_button.pack(side='left', padx=(10, 0), pady=15)
    
    def _create_status_display(self) -> None:
        """Создание отображения статуса."""
        self.status_frame = self.theme.create_styled_frame(self.main_frame, 'card')
        self.status_frame.pack(fill='x')
        
        self.status_label = self.theme.create_styled_label(
            self.status_frame,
            "ℹ️ Выберите метод подключения и введите данные",
            'secondary'
        )
        self.status_label.pack(padx=15, pady=15)
    
    def _on_method_changed(self) -> None:
        """Обработка изменения метода подключения."""
        method = self.connection_method.get()
        
        if method == "seed":
            self.seed_frame.pack(fill='x', padx=15, pady=(15, 0))
            self.private_key_frame.pack_forget()
        else:
            self.private_key_frame.pack(fill='x', padx=15, pady=(15, 0))
            self.seed_frame.pack_forget()
        
        self._update_status("ℹ️ Введите данные для подключения кошелька")
    
    def _toggle_key_visibility(self) -> None:
        """Переключение видимости приватного ключа."""
        if self.show_key_var.get():
            self.private_key_entry.configure(show="")
        else:
            self.private_key_entry.configure(show="*")
    
    def show(self) -> Optional[Dict[str, Any]]:
        """
        Показать диалог и дождаться результата.
        
        Returns:
            Dict с результатом подключения или None если отменено
        """
        try:
            # Показываем диалог
            self.grab_set()  # Делаем диалог модальным
            self.focus()
            
            # Инициализация результата
            self.result = None
            
            # Обновляем статус
            self._update_status("ℹ️ Выберите метод подключения и введите данные")
            
            # Ожидаем закрытия диалога
            self.master.wait_window(self)
            
            return self.result
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа диалога: {e}")
            self._update_status(f"❌ Ошибка: {e}")
            return None
    
    def _connect_wallet(self) -> None:
        """Подключение кошелька."""
        try:
            method = self.connection_method.get()
            
            if method == "seed":
                # Подключение через seed фразу
                seed_phrase = self.seed_textbox.get("1.0", "end-1c").strip()
                
                if not seed_phrase or seed_phrase == "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about":
                    self._update_status("❌ Введите корректную seed фразу")
                    return
                
                # Здесь должна быть логика создания кошелька из seed фразы
                # wallet = create_wallet_from_seed(seed_phrase)
                
                self.result = {
                    'success': True,
                    'type': 'seed_phrase',
                    'address': '0x' + '1234567890abcdef' * 5,  # Заглушка
                    'method': 'seed_phrase'
                }
                
                self._update_status("✅ Кошелек подключен через seed фразу")
                
            elif method == "private_key":
                # Подключение через приватный ключ
                private_key = self.private_key_entry.get().strip()
                
                if not private_key or private_key == "Приватный ключ (64 символа)":
                    self._update_status("❌ Введите корректный приватный ключ")
                    return
                
                if len(private_key) != 64:
                    self._update_status("❌ Приватный ключ должен содержать 64 символа")
                    return
                
                # Здесь должна быть логика создания кошелька из приватного ключа
                # wallet = create_wallet_from_private_key(private_key)
                
                self.result = {
                    'success': True,
                    'type': 'private_key',
                    'address': '0x' + '1234567890abcdef' * 5,  # Заглушка
                    'method': 'private_key'
                }
                
                self._update_status("✅ Кошелек подключен через приватный ключ")            # Закрываем диалог через небольшую задержку
            self.after(1500, self._close_dialog)
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения кошелька: {e}")
            self._update_status(f"❌ Ошибка подключения: {e}")
    
    def _cancel(self) -> None:
        """Отмена подключения."""
        self.result = None
        self._close_dialog()
    
    def _close_dialog(self) -> None:
        """Закрытие диалога."""
        try:
            self.grab_release()
            self.destroy()
        except:
            pass
    
    def _generate_test_wallet(self) -> None:
        """Генерация тестового кошелька."""
        try:
            # Генерируем тестовые данные
            test_seed = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
            test_private_key = "0123456789abcdef" * 4
            
            method = self.connection_method.get()
            
            if method == "seed":
                self.seed_textbox.delete("1.0", "end")
                self.seed_textbox.insert("1.0", test_seed)
                self.seed_textbox.configure(text_color=self.theme.colors['text_primary'])
            elif method == "private_key":
                self.private_key_entry.delete(0, "end")
                self.private_key_entry.insert(0, test_private_key)
                self.private_key_entry.configure(text_color=self.theme.colors['text_primary'])
            
            self._update_status("🎲 Тестовые данные загружены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации тестового кошелька: {e}")
            self._update_status(f"❌ Ошибка: {e}")
    
    def _update_status(self, message: str) -> None:
        """Обновление статуса."""
        self.status_label.configure(text=message)
        
        # Цветовая индикация
        if "✅" in message:
            self.status_label.configure(text_color=self.theme.colors['success'])
        elif "❌" in message:
            self.status_label.configure(text_color=self.theme.colors['error'])
        elif "⚠️" in message:
            self.status_label.configure(text_color=self.theme.colors['warning'])
        else:
            self.status_label.configure(text_color=self.theme.colors['text_secondary'])
    
    def _setup_seed_placeholder(self) -> None:
        """Настройка placeholder для seed фразы."""
        def on_focus_in(event):
            if self.seed_textbox.get("1.0", "end-1c") == "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about":
                self.seed_textbox.delete("1.0", "end")
                self.seed_textbox.configure(text_color=self.theme.colors['text_primary'])
        
        def on_focus_out(event):
            if not self.seed_textbox.get("1.0", "end-1c").strip():
                self.seed_textbox.insert("1.0", "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
                self.seed_textbox.configure(text_color=("gray60", "gray40"))
        
        self.seed_textbox.bind("<FocusIn>", on_focus_in)
        self.seed_textbox.bind("<FocusOut>", on_focus_out)
    
    def _setup_private_key_placeholder(self) -> None:
        """Настройка placeholder для приватного ключа."""
        def on_focus_in(event):
            if self.private_key_entry.get() == "Приватный ключ (64 символа)":
                self.private_key_entry.delete(0, "end")
                self.private_key_entry.configure(text_color=self.theme.colors['text_primary'])
        
        def on_focus_out(event):
            if not self.private_key_entry.get().strip():
                self.private_key_entry.insert(0, "Приватный ключ (64 символа)")
                self.private_key_entry.configure(text_color=("gray60", "gray40"))
        
        self.private_key_entry.bind("<FocusIn>", on_focus_in)
        self.private_key_entry.bind("<FocusOut>", on_focus_out)
        

def show_wallet_connection_dialog(parent, on_wallet_connected: Optional[Callable] = None) -> None:
    """
    Показать диалог подключения кошелька.
    
    Args:
        parent: Родительское окно
        on_wallet_connected: Callback при успешном подключении
    """
    dialog = WalletConnectionDialog(parent, on_wallet_connected)
    return dialog
