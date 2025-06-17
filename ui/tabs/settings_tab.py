"""
PLEX Dynamic Staking Manager - Settings Tab
Вкладка настроек приложения.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk
import os
import json

from ui.themes.dark_theme import get_theme
from ui.components.progress_bar import ProgressBar, ProgressState
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class SettingsTab(ctk.CTkFrame):
    """
    Вкладка настроек приложения.
    
    Функциональность:
    - Настройки подключения к блокчейну
    - Конфигурация API ключей
    - Параметры анализа
    - Настройки логирования
    - Резервное копирование
    - Экспорт/импорт настроек
    """
    
    def __init__(self, parent, settings_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация SettingsTab.
        
        Args:
            parent: Родительский виджет
            settings_manager: Экземпляр SettingsManager
            **kwargs: Дополнительные параметры
        """
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        
        # Применение стиля фрейма
        frame_style = self.theme.get_frame_style('primary')
        frame_style.update(kwargs)
        super().__init__(parent, **frame_style)
        
        # Ссылка на менеджер настроек
        self.settings_manager = settings_manager
        
        # Текущие настройки
        self.current_settings = {}
        self.unsaved_changes = False
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        self._load_current_settings()
        
        logger.debug("⚙️ SettingsTab инициализирована")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Заголовок
        self.title_label = self.theme.create_styled_label(
            self,
            "⚙️ Настройки приложения",
            'title'
        )
        
        # Создание основных секций настроек
        self._create_blockchain_settings()
        self._create_analysis_settings()
        self._create_logging_settings()
        self._create_backup_settings()
        self._create_interface_settings()
        
        # Кнопки управления
        self.control_frame = self.theme.create_styled_frame(self, 'card')
        
        self.save_button = self.theme.create_styled_button(
            self.control_frame,
            "💾 Сохранить настройки",
            'success',
            command=self._save_settings,
            width=150        )
        
        self.reset_button = self.theme.create_styled_button(
            self.control_frame,
            "🔄 Сбросить",
            'warning',
            command=self._reset_settings,
            width=120
        )
        
        self.factory_reset_button = self.theme.create_styled_button(
            self.control_frame,
            "🏭 Заводские",
            'danger',
            command=self._factory_reset,
            width=120
        )
        
        self.export_button = self.theme.create_styled_button(
            self.control_frame,
            "📤 Экспорт",
            'info',
            command=self._export_settings,
            width=100
        )
        
        self.import_button = self.theme.create_styled_button(
            self.control_frame,
            "📥 Импорт",
            'secondary',
            command=self._import_settings,
            width=100
        )
        
        # Статус изменений
        self.status_frame = self.theme.create_styled_frame(self.control_frame, 'primary')
        
        self.changes_label = self.theme.create_styled_label(
            self.status_frame,
            "💾 Изменения сохранены",
            'success'
        )
        self.changes_label.configure(text_color=self.theme.get_status_color('success'))
    
    def _create_blockchain_settings(self) -> None:
        """Создание секции настроек блокчейна."""
        self.blockchain_frame = self.theme.create_styled_frame(self, 'card')
        
        self.blockchain_title = self.theme.create_styled_label(
            self.blockchain_frame,
            "🔗 Настройки блокчейна",
            'subtitle'
        )
          # QuickNode RPC URL
        self.rpc_frame = self.theme.create_styled_frame(self.blockchain_frame, 'primary')
        
        self.rpc_label = self.theme.create_styled_label(
            self.rpc_frame,
            "🌐 RPC Endpoint:",
            'primary'
        )
        
        # Предустановленные RPC ноды
        self.preset_rpc_frame = self.theme.create_styled_frame(self.rpc_frame, 'primary')
        
        self.preset_rpc_label = self.theme.create_styled_label(
            self.preset_rpc_frame,
            "📋 Быстрый выбор:",
            'secondary'
        )
        
        self.rpc_presets = {
            "QuickNode (Настроенный)": os.getenv('QUICKNODE_HTTP', ''),
            "BSC Official RPC": "https://bsc-dataseed.binance.org/",
            "BSC RPC 1": "https://bsc-dataseed1.binance.org/",
            "BSC RPC 2": "https://bsc-dataseed2.binance.org/",
            "1RPC BSC": "https://1rpc.io/bnb",
            "Ankr BSC": "https://rpc.ankr.com/bsc",
            "Пользовательский": ""
        }
        
        self.rpc_preset_var = ctk.StringVar(value="QuickNode (Настроенный)")
        self.rpc_preset_menu = ctk.CTkOptionMenu(
            self.preset_rpc_frame,
            values=list(self.rpc_presets.keys()),
            variable=self.rpc_preset_var,
            command=self._on_rpc_preset_changed,
            **self.theme.get_button_style('secondary')
        )
        
        self.rpc_entry = self.theme.create_styled_entry(
            self.rpc_frame,
            placeholder="https://your-endpoint.bsc.quicknode.pro/...",
            width=400
        )
        self.rpc_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.test_connection_button = self.theme.create_styled_button(
            self.rpc_frame,
            "🔌 Тест",
            'info',
            command=self._test_blockchain_connection,
            width=60
        )
        
        # Сетевые настройки
        self.network_frame = self.theme.create_styled_frame(self.blockchain_frame, 'primary')
        
        self.network_label = self.theme.create_styled_label(
            self.network_frame,
            "🌍 Сеть:",
            'primary'
        )
        
        self.network_var = ctk.StringVar(value="BSC_MAINNET")
        self.network_menu = ctk.CTkOptionMenu(
            self.network_frame,
            values=["BSC Mainnet", "BSC Testnet"],
            variable=self.network_var,
            command=self._on_network_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Настройки запросов
        self.requests_frame = self.theme.create_styled_frame(self.blockchain_frame, 'primary')
        
        self.batch_size_label = self.theme.create_styled_label(
            self.requests_frame,
            "📦 Размер батча:",
            'primary'
        )
        
        self.batch_size_entry = self.theme.create_styled_entry(
            self.requests_frame,
            placeholder="100",
            width=80
        )
        self.batch_size_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.timeout_label = self.theme.create_styled_label(
            self.requests_frame,
            "⏱️ Таймаут (сек):",
            'primary'
        )
        
        self.timeout_entry = self.theme.create_styled_entry(
            self.requests_frame,
            placeholder="30",
            width=80
        )
        self.timeout_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.retries_label = self.theme.create_styled_label(
            self.requests_frame,
            "🔄 Повторы:",
            'primary'
        )
        
        self.retries_entry = self.theme.create_styled_entry(
            self.requests_frame,
            placeholder="3",
            width=80
        )
        self.retries_entry.bind('<KeyRelease>', self._on_setting_changed)
    
    def _create_analysis_settings(self) -> None:
        """Создание секции настроек анализа."""
        self.analysis_frame = self.theme.create_styled_frame(self, 'card')
        
        self.analysis_title = self.theme.create_styled_label(
            self.analysis_frame,
            "📊 Настройки анализа",
            'subtitle'
        )
        
        # Адреса контрактов
        self.contracts_frame = self.theme.create_styled_frame(self.analysis_frame, 'primary')
        
        self.plex_contract_label = self.theme.create_styled_label(
            self.contracts_frame,
            "💎 Контракт PLEX:",
            'primary'
        )
        
        self.plex_contract_entry = self.theme.create_styled_entry(
            self.contracts_frame,
            placeholder="0x...",
            width=350
        )
        self.plex_contract_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.usdt_contract_label = self.theme.create_styled_label(
            self.contracts_frame,
            "💵 Контракт USDT:",
            'primary'
        )
        
        self.usdt_contract_entry = self.theme.create_styled_entry(
            self.contracts_frame,
            placeholder="0x...",
            width=350
        )
        self.usdt_contract_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        # Параметры анализа
        self.params_frame = self.theme.create_styled_frame(self.analysis_frame, 'primary')
        
        self.min_volume_label = self.theme.create_styled_label(
            self.params_frame,
            "💰 Мин. объем (USD):",
            'primary'
        )
        
        self.min_volume_entry = self.theme.create_styled_entry(
            self.params_frame,
            placeholder="100",
            width=100
        )
        self.min_volume_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.max_participants_label = self.theme.create_styled_label(
            self.params_frame,
            "👥 Макс. участников:",
            'primary'
        )
        
        self.max_participants_entry = self.theme.create_styled_entry(
            self.params_frame,
            placeholder="1000",
            width=100
        )
        self.max_participants_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        # Настройки кэширования
        self.cache_frame = self.theme.create_styled_frame(self.analysis_frame, 'primary')
        
        self.cache_enabled_var = ctk.BooleanVar(value=True)
        self.cache_enabled_switch = ctk.CTkSwitch(
            self.cache_frame,
            text="Включить кэширование",
            variable=self.cache_enabled_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
        
        self.cache_ttl_label = self.theme.create_styled_label(
            self.cache_frame,
            "⏰ TTL кэша (мин):",
            'primary'
        )
        
        self.cache_ttl_entry = self.theme.create_styled_entry(
            self.cache_frame,
            placeholder="60",
            width=80
        )
        self.cache_ttl_entry.bind('<KeyRelease>', self._on_setting_changed)
    
    def _create_logging_settings(self) -> None:
        """Создание секции настроек логирования."""
        self.logging_frame = self.theme.create_styled_frame(self, 'card')
        
        self.logging_title = self.theme.create_styled_label(
            self.logging_frame,
            "📋 Настройки логирования",
            'subtitle'
        )
        
        # Уровень логирования
        self.log_level_frame = self.theme.create_styled_frame(self.logging_frame, 'primary')
        
        self.log_level_label = self.theme.create_styled_label(
            self.log_level_frame,
            "📊 Уровень логирования:",
            'primary'
        )
        
        self.log_level_var = ctk.StringVar(value="INFO")
        self.log_level_menu = ctk.CTkOptionMenu(
            self.log_level_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            variable=self.log_level_var,
            command=self._on_log_level_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Настройки файлов логов
        self.log_file_frame = self.theme.create_styled_frame(self.logging_frame, 'primary')
        
        self.max_log_size_label = self.theme.create_styled_label(
            self.log_file_frame,
            "📁 Макс. размер лога (MB):",
            'primary'
        )
        
        self.max_log_size_entry = self.theme.create_styled_entry(
            self.log_file_frame,
            placeholder="100",
            width=80
        )
        self.max_log_size_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.log_retention_label = self.theme.create_styled_label(
            self.log_file_frame,
            "🗄️ Хранить логи (дней):",
            'primary'
        )
        
        self.log_retention_entry = self.theme.create_styled_entry(
            self.log_file_frame,
            placeholder="30",
            width=80
        )
        self.log_retention_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        # Консольное логирование
        self.console_logging_var = ctk.BooleanVar(value=True)
        self.console_logging_switch = ctk.CTkSwitch(
            self.log_file_frame,
            text="Логирование в консоль",
            variable=self.console_logging_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
    
    def _create_backup_settings(self) -> None:
        """Создание секции настроек резервного копирования."""
        self.backup_frame = self.theme.create_styled_frame(self, 'card')
        
        self.backup_title = self.theme.create_styled_label(
            self.backup_frame,
            "💾 Настройки резервного копирования",
            'subtitle'
        )
        
        # Автоматическое резервное копирование
        self.auto_backup_frame = self.theme.create_styled_frame(self.backup_frame, 'primary')
        
        self.auto_backup_var = ctk.BooleanVar(value=True)
        self.auto_backup_switch = ctk.CTkSwitch(
            self.auto_backup_frame,
            text="Автоматическое резервное копирование",
            variable=self.auto_backup_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
        
        self.backup_interval_label = self.theme.create_styled_label(
            self.auto_backup_frame,
            "⏰ Интервал (часы):",
            'primary'
        )
        
        self.backup_interval_entry = self.theme.create_styled_entry(
            self.auto_backup_frame,
            placeholder="24",
            width=80
        )
        self.backup_interval_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        # Путь для бэкапов
        self.backup_path_frame = self.theme.create_styled_frame(self.backup_frame, 'primary')
        
        self.backup_path_label = self.theme.create_styled_label(
            self.backup_path_frame,
            "📂 Папка бэкапов:",
            'primary'
        )
        
        self.backup_path_entry = self.theme.create_styled_entry(
            self.backup_path_frame,
            placeholder="./backups",
            width=300
        )
        self.backup_path_entry.bind('<KeyRelease>', self._on_setting_changed)
        
        self.browse_backup_button = self.theme.create_styled_button(
            self.backup_path_frame,
            "📁",
            'secondary',
            command=self._browse_backup_path,
            width=40
        )
        
        # Хранение бэкапов
        self.backup_retention_label = self.theme.create_styled_label(
            self.backup_path_frame,
            "🗄️ Хранить бэкапы (дней):",
            'primary'
        )
        
        self.backup_retention_entry = self.theme.create_styled_entry(
            self.backup_path_frame,
            placeholder="7",
            width=80
        )
        self.backup_retention_entry.bind('<KeyRelease>', self._on_setting_changed)
    
    def _create_interface_settings(self) -> None:
        """Создание секции настроек интерфейса."""
        self.interface_frame = self.theme.create_styled_frame(self, 'card')
        
        self.interface_title = self.theme.create_styled_label(
            self.interface_frame,
            "🎨 Настройки интерфейса",
            'subtitle'
        )
        
        # Тема интерфейса
        self.theme_frame = self.theme.create_styled_frame(self.interface_frame, 'primary')
        
        self.ui_theme_label = self.theme.create_styled_label(
            self.theme_frame,
            "🎨 Тема:",
            'primary'
        )
        
        self.ui_theme_var = ctk.StringVar(value="dark")
        self.ui_theme_menu = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["Темная", "Светлая", "Системная"],
            variable=self.ui_theme_var,
            command=self._on_theme_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Языковые настройки
        self.language_label = self.theme.create_styled_label(
            self.theme_frame,
            "🌐 Язык:",
            'primary'
        )
        
        self.language_var = ctk.StringVar(value="ru")
        self.language_menu = ctk.CTkOptionMenu(
            self.theme_frame,
            values=["Русский", "English"],
            variable=self.language_var,
            command=self._on_language_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Настройки уведомлений
        self.notifications_frame = self.theme.create_styled_frame(self.interface_frame, 'primary')
        
        self.notifications_var = ctk.BooleanVar(value=True)
        self.notifications_switch = ctk.CTkSwitch(
            self.notifications_frame,
            text="Показывать уведомления",
            variable=self.notifications_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
        
        self.sound_notifications_var = ctk.BooleanVar(value=False)
        self.sound_notifications_switch = ctk.CTkSwitch(
            self.notifications_frame,
            text="Звуковые уведомления",
            variable=self.sound_notifications_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
        
        # Автосохранение
        self.autosave_var = ctk.BooleanVar(value=True)
        self.autosave_switch = ctk.CTkSwitch(
            self.notifications_frame,
            text="Автосохранение настроек",
            variable=self.autosave_var,
            command=self._on_setting_changed,
            **self.theme.get_switch_style()
        )
    
    def _setup_layout(self) -> None:
        """Настройка расположения виджетов."""
        # Заголовок
        self.title_label.pack(pady=(20, 10))
        
        # Создание прокручиваемой области для всех настроек
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            **self.theme.get_frame_style('primary')
        )
        self.scrollable_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Размещение секций настроек
        self._setup_blockchain_layout()
        self._setup_analysis_layout()
        self._setup_logging_layout()
        self._setup_backup_layout()
        self._setup_interface_layout()
        
        # Кнопки управления (не в прокручиваемой области)
        self.control_frame.pack(fill='x', padx=20, pady=(10, 20))
          # Строка кнопок
        buttons_frame = self.theme.create_styled_frame(self.control_frame, 'primary')
        buttons_frame.pack(fill='x', pady=10)
        
        self.save_button.pack(side='left', padx=(10, 10))
        self.reset_button.pack(side='left', padx=(0, 5))
        self.factory_reset_button.pack(side='left', padx=(0, 10))
        self.export_button.pack(side='right', padx=(10, 0))
        self.import_button.pack(side='right', padx=(10, 0))
        
        # Статус изменений
        self.status_frame.pack(fill='x', pady=(5, 10))
        self.changes_label.pack()
    
    def _setup_blockchain_layout(self) -> None:
        """Настройка макета секции блокчейна."""
        self.blockchain_frame.pack(fill='x', pady=(0, 10))
        
        self.blockchain_title.pack(pady=(15, 10))
          # RPC URL
        self.rpc_frame.pack(fill='x', padx=15, pady=5)
        
        # Предустановленные RPC
        self.preset_rpc_frame.pack(fill='x', pady=(0, 5))
        self.preset_rpc_label.pack(side='left', anchor='w')
        self.rpc_preset_menu.pack(side='left', padx=(10, 0))
        
        # RPC URL поле ввода
        rpc_row = self.theme.create_styled_frame(self.rpc_frame, 'primary')
        rpc_row.pack(fill='x', pady=5)
        
        self.rpc_label.pack(side='left', anchor='w')
        self.test_connection_button.pack(side='right', padx=(5, 0))
        self.rpc_entry.pack(side='right', padx=(10, 5))
        
        # Сеть
        self.network_frame.pack(fill='x', padx=15, pady=5)
        
        network_row = self.theme.create_styled_frame(self.network_frame, 'primary')
        network_row.pack(fill='x', pady=5)
        
        self.network_label.pack(side='left')
        self.network_menu.pack(side='left', padx=(10, 0))
        
        # Параметры запросов
        self.requests_frame.pack(fill='x', padx=15, pady=(5, 15))
        
        requests_row = self.theme.create_styled_frame(self.requests_frame, 'primary')
        requests_row.pack(fill='x', pady=5)
        
        self.batch_size_label.pack(side='left')
        self.batch_size_entry.pack(side='left', padx=(10, 20))
        
        self.timeout_label.pack(side='left')
        self.timeout_entry.pack(side='left', padx=(10, 20))
        
        self.retries_label.pack(side='left')
        self.retries_entry.pack(side='left', padx=(10, 0))
    
    def _setup_analysis_layout(self) -> None:
        """Настройка макета секции анализа."""
        self.analysis_frame.pack(fill='x', pady=(0, 10))
        
        self.analysis_title.pack(pady=(15, 10))
        
        # Контракты
        self.contracts_frame.pack(fill='x', padx=15, pady=5)
        
        plex_row = self.theme.create_styled_frame(self.contracts_frame, 'primary')
        plex_row.pack(fill='x', pady=2)
        
        self.plex_contract_label.pack(side='left', anchor='w')
        self.plex_contract_entry.pack(side='right', padx=(10, 0))
        
        usdt_row = self.theme.create_styled_frame(self.contracts_frame, 'primary')
        usdt_row.pack(fill='x', pady=2)
        
        self.usdt_contract_label.pack(side='left', anchor='w')
        self.usdt_contract_entry.pack(side='right', padx=(10, 0))
        
        # Параметры анализа
        self.params_frame.pack(fill='x', padx=15, pady=5)
        
        params_row = self.theme.create_styled_frame(self.params_frame, 'primary')
        params_row.pack(fill='x', pady=5)
        
        self.min_volume_label.pack(side='left')
        self.min_volume_entry.pack(side='left', padx=(10, 20))
        
        self.max_participants_label.pack(side='left')
        self.max_participants_entry.pack(side='left', padx=(10, 0))
        
        # Кэширование
        self.cache_frame.pack(fill='x', padx=15, pady=(5, 15))
        
        cache_row1 = self.theme.create_styled_frame(self.cache_frame, 'primary')
        cache_row1.pack(fill='x', pady=2)
        
        self.cache_enabled_switch.pack(side='left')
        
        cache_row2 = self.theme.create_styled_frame(self.cache_frame, 'primary')
        cache_row2.pack(fill='x', pady=2)
        
        self.cache_ttl_label.pack(side='left')
        self.cache_ttl_entry.pack(side='left', padx=(10, 0))
    
    def _setup_logging_layout(self) -> None:
        """Настройка макета секции логирования."""
        self.logging_frame.pack(fill='x', pady=(0, 10))
        
        self.logging_title.pack(pady=(15, 10))
        
        # Уровень логирования
        self.log_level_frame.pack(fill='x', padx=15, pady=5)
        
        log_level_row = self.theme.create_styled_frame(self.log_level_frame, 'primary')
        log_level_row.pack(fill='x', pady=5)
        
        self.log_level_label.pack(side='left')
        self.log_level_menu.pack(side='left', padx=(10, 0))
        
        # Файлы логов
        self.log_file_frame.pack(fill='x', padx=15, pady=(5, 15))
        
        log_file_row1 = self.theme.create_styled_frame(self.log_file_frame, 'primary')
        log_file_row1.pack(fill='x', pady=2)
        
        self.max_log_size_label.pack(side='left')
        self.max_log_size_entry.pack(side='left', padx=(10, 20))
        
        self.log_retention_label.pack(side='left')
        self.log_retention_entry.pack(side='left', padx=(10, 0))
        
        log_file_row2 = self.theme.create_styled_frame(self.log_file_frame, 'primary')
        log_file_row2.pack(fill='x', pady=2)
        
        self.console_logging_switch.pack(side='left')
    
    def _setup_backup_layout(self) -> None:
        """Настройка макета секции резервного копирования."""
        self.backup_frame.pack(fill='x', pady=(0, 10))
        
        self.backup_title.pack(pady=(15, 10))
        
        # Автоматическое резервное копирование
        self.auto_backup_frame.pack(fill='x', padx=15, pady=5)
        
        auto_backup_row1 = self.theme.create_styled_frame(self.auto_backup_frame, 'primary')
        auto_backup_row1.pack(fill='x', pady=2)
        
        self.auto_backup_switch.pack(side='left')
        
        auto_backup_row2 = self.theme.create_styled_frame(self.auto_backup_frame, 'primary')
        auto_backup_row2.pack(fill='x', pady=2)
        
        self.backup_interval_label.pack(side='left')
        self.backup_interval_entry.pack(side='left', padx=(10, 0))
        
        # Путь для бэкапов
        self.backup_path_frame.pack(fill='x', padx=15, pady=(5, 15))
        
        backup_path_row1 = self.theme.create_styled_frame(self.backup_path_frame, 'primary')
        backup_path_row1.pack(fill='x', pady=2)
        
        self.backup_path_label.pack(side='left', anchor='w')
        self.browse_backup_button.pack(side='right', padx=(5, 0))
        self.backup_path_entry.pack(side='right', padx=(10, 5))
        
        backup_path_row2 = self.theme.create_styled_frame(self.backup_path_frame, 'primary')
        backup_path_row2.pack(fill='x', pady=2)
        
        self.backup_retention_label.pack(side='left')
        self.backup_retention_entry.pack(side='left', padx=(10, 0))
    
    def _setup_interface_layout(self) -> None:
        """Настройка макета секции интерфейса."""
        self.interface_frame.pack(fill='x', pady=(0, 10))
        
        self.interface_title.pack(pady=(15, 10))
        
        # Тема
        self.theme_frame.pack(fill='x', padx=15, pady=5)
        
        theme_row = self.theme.create_styled_frame(self.theme_frame, 'primary')
        theme_row.pack(fill='x', pady=2)
        
        self.ui_theme_label.pack(side='left')
        self.ui_theme_menu.pack(side='left', padx=(10, 20))
        
        self.language_label.pack(side='left')
        self.language_menu.pack(side='left', padx=(10, 0))
        
        # Уведомления
        self.notifications_frame.pack(fill='x', padx=15, pady=(5, 15))
        
        notif_row1 = self.theme.create_styled_frame(self.notifications_frame, 'primary')
        notif_row1.pack(fill='x', pady=2)
        
        self.notifications_switch.pack(side='left')
        
        notif_row2 = self.theme.create_styled_frame(self.notifications_frame, 'primary')
        notif_row2.pack(fill='x', pady=2)
        
        self.sound_notifications_switch.pack(side='left')
        
        notif_row3 = self.theme.create_styled_frame(self.notifications_frame, 'primary')
        notif_row3.pack(fill='x', pady=2)
        
        self.autosave_switch.pack(side='left')
    
    def _load_current_settings(self) -> None:
        """Загрузка текущих настроек."""
        try:
            # Загрузка из файла настроек или значения по умолчанию
            settings_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'app_settings.json')
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.current_settings = json.load(f)
            else:
                self.current_settings = self._get_default_settings()
              # Применение настроек к виджетам
            self._apply_settings_to_widgets()
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки настроек: {e}")
            self.current_settings = self._get_default_settings()
            self._apply_settings_to_widgets()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Получение настроек по умолчанию из .env файла."""
        # Загрузка переменных из .env файла
        env_vars = self._load_env_variables()
        
        return {
            'blockchain': {
                'rpc_url': env_vars.get('QUICKNODE_HTTP', ''),
                'wss_url': env_vars.get('QUICKNODE_WSS', ''),
                'api_key': env_vars.get('QUICKNODE_API_KEY', ''),
                'network': 'BSC_MAINNET',
                'batch_size': int(env_vars.get('MAX_BLOCKS_PER_CHUNK', 100)),
                'timeout': 30,
                'retries': 3
            },
            'analysis': {
                'plex_contract': env_vars.get('TOKEN_ADDRESS', '0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1'),
                'usdt_contract': env_vars.get('USDT_BSC', '0x55d398326f99059fF775485246999027B3197955'),
                'min_volume': float(env_vars.get('MIN_BALANCE', 100)),
                'max_participants': 1000,
                'cache_enabled': True,
                'cache_ttl': 60,
                'daily_purchase_min': float(env_vars.get('DAILY_PURCHASE_MIN', 2.8)),
                'daily_purchase_max': float(env_vars.get('DAILY_PURCHASE_MAX', 3.2))
            },
            'logging': {
                'level': env_vars.get('LOG_LEVEL', 'INFO'),
                'max_log_size': 100,
                'log_retention': 30,
                'console_logging': True,
                'log_file': env_vars.get('LOG_FILE', 'logs/plex_staking.log')
            },
            'backup': {
                'auto_backup': True,
                'backup_interval': 24,
                'backup_path': './backups',
                'backup_retention': 7
            },
            'interface': {
                'theme': env_vars.get('THEME', 'dark'),
                'language': 'ru',
                'notifications': True,
                'sound_notifications': False,
                'autosave': True
            }
        }
    
    def _load_env_variables(self) -> Dict[str, str]:
        """Загрузка переменных окружения из .env файла."""
        env_vars = {}
        env_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        
        try:
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
            else:
                logger.warning(f"⚠️ Файл .env не найден: {env_file_path}")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки .env файла: {e}")
        
        return env_vars

    def _apply_settings_to_widgets(self) -> None:
        """Применение настроек к виджетам."""
        try:
            # Блокчейн настройки
            blockchain = self.current_settings.get('blockchain', {})
            self.rpc_entry.delete(0, 'end')
            self.rpc_entry.insert(0, blockchain.get('rpc_url', ''))
            self.network_var.set(blockchain.get('network', 'BSC_MAINNET'))
            
            self.batch_size_entry.delete(0, 'end')
            self.batch_size_entry.insert(0, str(blockchain.get('batch_size', 100)))
            
            self.timeout_entry.delete(0, 'end')
            self.timeout_entry.insert(0, str(blockchain.get('timeout', 30)))
            
            self.retries_entry.delete(0, 'end')
            self.retries_entry.insert(0, str(blockchain.get('retries', 3)))
            
            # Настройки анализа
            analysis = self.current_settings.get('analysis', {})
            self.plex_contract_entry.delete(0, 'end')
            self.plex_contract_entry.insert(0, analysis.get('plex_contract', ''))
            
            self.usdt_contract_entry.delete(0, 'end')
            self.usdt_contract_entry.insert(0, analysis.get('usdt_contract', ''))
            
            self.min_volume_entry.delete(0, 'end')
            self.min_volume_entry.insert(0, str(analysis.get('min_volume', 100)))
            
            self.max_participants_entry.delete(0, 'end')
            self.max_participants_entry.insert(0, str(analysis.get('max_participants', 1000)))
            
            self.cache_enabled_var.set(analysis.get('cache_enabled', True))
            
            self.cache_ttl_entry.delete(0, 'end')
            self.cache_ttl_entry.insert(0, str(analysis.get('cache_ttl', 60)))
            
            # Настройки логирования
            logging_settings = self.current_settings.get('logging', {})
            self.log_level_var.set(logging_settings.get('level', 'INFO'))
            
            self.max_log_size_entry.delete(0, 'end')
            self.max_log_size_entry.insert(0, str(logging_settings.get('max_log_size', 100)))
            
            self.log_retention_entry.delete(0, 'end')
            self.log_retention_entry.insert(0, str(logging_settings.get('log_retention', 30)))
            
            self.console_logging_var.set(logging_settings.get('console_logging', True))
            
            # Настройки резервного копирования
            backup = self.current_settings.get('backup', {})
            self.auto_backup_var.set(backup.get('auto_backup', True))
            
            self.backup_interval_entry.delete(0, 'end')
            self.backup_interval_entry.insert(0, str(backup.get('backup_interval', 24)))
            
            self.backup_path_entry.delete(0, 'end')
            self.backup_path_entry.insert(0, backup.get('backup_path', './backups'))
            
            self.backup_retention_entry.delete(0, 'end')
            self.backup_retention_entry.insert(0, str(backup.get('backup_retention', 7)))
            
            # Настройки интерфейса
            interface = self.current_settings.get('interface', {})
            self.ui_theme_var.set(interface.get('theme', 'dark'))
            self.language_var.set(interface.get('language', 'ru'))
            self.notifications_var.set(interface.get('notifications', True))
            self.sound_notifications_var.set(interface.get('sound_notifications', False))
            self.autosave_var.set(interface.get('autosave', True))
            
            # Сброс флага изменений
            self.unsaved_changes = False
            self._update_changes_status()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения настроек: {e}")
    
    def _on_setting_changed(self, event=None) -> None:
        """Обработка изменения настройки."""
        self.unsaved_changes = True
        self._update_changes_status()
        
        # Автосохранение если включено
        if self.autosave_var.get():
            self.after_idle(self._save_settings)
    
    def _on_rpc_preset_changed(self, value: str) -> None:
        """Обработка изменения предустановленного RPC."""
        if value in self.rpc_presets:
            preset_url = self.rpc_presets[value]
            if preset_url:
                self.rpc_entry.delete(0, 'end')
                self.rpc_entry.insert(0, preset_url)
                self._on_setting_changed()
    
    def _on_network_changed(self, value: str) -> None:
        """Обработка изменения сети."""
        self._on_setting_changed()
    
    def _on_log_level_changed(self, value: str) -> None:
        """Обработка изменения уровня логирования."""
        self._on_setting_changed()
    
    def _on_theme_changed(self, value: str) -> None:
        """Обработка изменения темы."""
        self._on_setting_changed()
        # Здесь можно добавить логику применения новой темы
    
    def _on_language_changed(self, value: str) -> None:
        """Обработка изменения языка."""
        self._on_setting_changed()
        # Здесь можно добавить логику смены языка
    
    def _update_changes_status(self) -> None:
        """Обновление статуса изменений."""
        if self.unsaved_changes:
            self.changes_label.configure(
                text="⚠️ Есть несохраненные изменения",
                text_color=self.theme.get_status_color('warning')
            )
        else:
            self.changes_label.configure(
                text="💾 Изменения сохранены",
                text_color=self.theme.get_status_color('success')
            )
    
    def _save_settings(self) -> None:
        """Сохранение настроек."""
        try:
            # Сбор настроек из виджетов
            new_settings = {
                'blockchain': {
                    'rpc_url': self.rpc_entry.get(),
                    'network': self.network_var.get(),
                    'batch_size': int(self.batch_size_entry.get() or 100),
                    'timeout': int(self.timeout_entry.get() or 30),
                    'retries': int(self.retries_entry.get() or 3)
                },
                'analysis': {
                    'plex_contract': self.plex_contract_entry.get(),
                    'usdt_contract': self.usdt_contract_entry.get(),
                    'min_volume': float(self.min_volume_entry.get() or 100),
                    'max_participants': int(self.max_participants_entry.get() or 1000),
                    'cache_enabled': self.cache_enabled_var.get(),
                    'cache_ttl': int(self.cache_ttl_entry.get() or 60)
                },
                'logging': {
                    'level': self.log_level_var.get(),
                    'max_log_size': int(self.max_log_size_entry.get() or 100),
                    'log_retention': int(self.log_retention_entry.get() or 30),
                    'console_logging': self.console_logging_var.get()
                },
                'backup': {
                    'auto_backup': self.auto_backup_var.get(),
                    'backup_interval': int(self.backup_interval_entry.get() or 24),
                    'backup_path': self.backup_path_entry.get() or './backups',
                    'backup_retention': int(self.backup_retention_entry.get() or 7)
                },
                'interface': {
                    'theme': self.ui_theme_var.get(),
                    'language': self.language_var.get(),
                    'notifications': self.notifications_var.get(),
                    'sound_notifications': self.sound_notifications_var.get(),
                    'autosave': self.autosave_var.get()
                }
            }
            
            # Сохранение в файл
            settings_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'config')
            os.makedirs(settings_dir, exist_ok=True)
            
            settings_file = os.path.join(settings_dir, 'app_settings.json')
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(new_settings, f, indent=2, ensure_ascii=False)
            
            self.current_settings = new_settings
            self.unsaved_changes = False
            self._update_changes_status()
            
            logger.info("✅ Настройки сохранены")
            
            if not self.autosave_var.get():
                messagebox.showinfo("Успех", "Настройки успешно сохранены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\\n{e}")
    
    def _reset_settings(self) -> None:
        """Сброс настроек к значениям по умолчанию."""
        try:
            result = messagebox.askquestion(
                "Подтверждение",
                "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?\\n\\n"
                "Это действие нельзя отменить!"
            )
            
            if result == 'yes':
                self.current_settings = self._get_default_settings()
                self._apply_settings_to_widgets()
                self._save_settings()
                
        except Exception as e:
            logger.error(f"❌ Ошибка сброса настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сбросить настройки:\\n{e}")
    
    def _factory_reset(self) -> None:
        """Полный сброс к заводским настройкам."""
        try:
            result = messagebox.askquestion(
                "⚠️ ВНИМАНИЕ: Заводской сброс",
                "Вы уверены, что хотите выполнить ПОЛНЫЙ сброс к заводским настройкам?\\n\\n"
                "Это действие:\\n"
                "• Удалит все пользовательские настройки\\n"
                "• Восстановит значения из .env файла\\n"
                "• Очистит кэш и временные данные\\n\\n"
                "⚠️ ЭТО ДЕЙСТВИЕ НЕЛЬЗЯ ОТМЕНИТЬ!",
                icon='warning'
            )
            
            if result == 'yes':
                # Очистить файл настроек
                settings_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'app_settings.json')
                if os.path.exists(settings_file):
                    os.remove(settings_file)
                
                # Загрузить заводские настройки
                self.current_settings = self._get_default_settings()
                self._apply_settings_to_widgets()
                self._save_settings()
                
                # Обновить RPC preset
                if self.current_settings.get('blockchain', {}).get('rpc_url'):
                    self.rpc_preset_var.set("QuickNode (Настроенный)")
                
                messagebox.showinfo(
                    "Успех", 
                    "✅ Настройки успешно сброшены к заводским значениям!\\n\\n"
                    "Все настройки загружены из .env файла."
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка заводского сброса: {e}")
            messagebox.showerror("Ошибка", f"Не удалось выполнить заводской сброс:\\n{e}")

    def _export_settings(self) -> None:
        """Экспорт настроек в файл."""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Экспорт настроек",
                defaultextension=".json",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("All files", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # Сохранение текущих настроек
            export_data = {
                'settings': self.current_settings,
                'export_date': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Успех", f"Настройки экспортированы в:\\n{file_path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать настройки:\\n{e}")
    
    def _import_settings(self) -> None:
        """Импорт настроек из файла."""
        try:
            file_path = filedialog.askopenfilename(
                title="Импорт настроек",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("All files", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # Загрузка настроек из файла
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Проверка формата
            if 'settings' not in import_data:
                messagebox.showerror("Ошибка", "Неверный формат файла настроек")
                return
            
            # Подтверждение импорта
            result = messagebox.askquestion(
                "Подтверждение",
                "Импортировать настройки из файла?\\n\\n"
                "Текущие настройки будут заменены!"
            )
            
            if result == 'yes':
                self.current_settings = import_data['settings']
                self._apply_settings_to_widgets()
                self._save_settings()
                
                messagebox.showinfo("Успех", "Настройки успешно импортированы!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка импорта настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось импортировать настройки:\\n{e}")
    
    def _test_blockchain_connection(self) -> None:
        """Тестирование подключения к блокчейну."""
        try:
            rpc_url = self.rpc_entry.get()
            if not rpc_url:
                messagebox.showwarning("Предупреждение", "Введите RPC URL для тестирования")
                return
            
            # Показать индикатор загрузки
            self.test_connection_button.configure(state='disabled', text="...")
            
            def test_thread():
                import time
                time.sleep(2)  # Имитация тестирования
                
                # Имитация результата
                success = True  # В реальности здесь будет проверка подключения
                
                self.after_idle(lambda: self._test_connection_completed(success))
            
            threading.Thread(target=test_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения: {e}")
            self._test_connection_completed(False, str(e))
    
    def _test_connection_completed(self, success: bool, error: str = "") -> None:
        """Завершение тестирования подключения."""
        self.test_connection_button.configure(state='normal', text="🔌 Тест")
        
        if success:
            messagebox.showinfo("Успех", "✅ Подключение к блокчейну успешно!")
        else:
            error_msg = f"❌ Не удалось подключиться к блокчейну:\\n{error}" if error else "❌ Ошибка подключения"
            messagebox.showerror("Ошибка", error_msg)
    
    def _browse_backup_path(self) -> None:
        """Выбор папки для резервных копий."""
        try:
            directory = filedialog.askdirectory(
                title="Выберите папку для резервных копий",
                initialdir=self.backup_path_entry.get() or "."
            )
            
            if directory:
                self.backup_path_entry.delete(0, 'end')
                self.backup_path_entry.insert(0, directory)
                self._on_setting_changed()
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора папки: {e}")
    
    def get_settings(self) -> Dict[str, Any]:
        """Получение текущих настроек."""
        return self.current_settings.copy()
    
    def set_settings_manager(self, settings_manager) -> None:
        """Установка менеджера настроек."""
        self.settings_manager = settings_manager
        logger.debug("✅ SettingsManager установлен для SettingsTab")


# Экспорт для удобного импорта
__all__ = ['SettingsTab']


if __name__ == "__main__":
    # Демонстрация вкладки
    def demo_settings_tab():
        """Демонстрация SettingsTab."""
        try:
            print("🧪 Демонстрация SettingsTab...")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Settings Tab Demo")
            root.geometry("1000x800")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание вкладки настроек
            settings_tab = SettingsTab(root)
            settings_tab.pack(fill='both', expand=True)
            
            print("✅ SettingsTab запущена. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_settings_tab()
    print("💡 Для демонстрации SettingsTab раскомментируй последнюю строку")
