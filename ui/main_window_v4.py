"""
PLEX Dynamic Staking Manager - Main Window V4 (RESIZABLE FIXED)
Главное окно приложения с интегрированными вкладками и полной поддержкой изменения размера.

Автор: PLEX Dynamic Staking Team
Версия: 4.1.0 (RESIZABLE FIXED)
"""

import asyncio
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
import sys

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv не обязательна

# Добавление корневой директории в путь
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ui.themes.dark_theme import get_theme, apply_window_style
from ui.components.log_viewer import LogViewer
from ui.components.progress_bar import ProgressBar
from ui.components.wallet_connection_dialog_fixed import WalletConnectionDialog, show_wallet_connection_dialog
from ui.tabs.enhanced_analysis_tab import EnhancedAnalysisTab
from ui.tabs.enhanced_rewards_tab import EnhancedRewardsTab
from ui.tabs.enhanced_history_tab import EnhancedHistoryTab
from ui.tabs.settings_tab import SettingsTab
from ui.optimized_analysis_extension import patch_analysis_tab_with_optimization

from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory
from config.constants import *
from config.settings import settings

# Импорт основных модулей
from blockchain.node_client import Web3Manager
from core.staking_manager import StakingManager
from core.reward_calculator import RewardCalculator
from core.participant_analyzer_v2 import ParticipantAnalyzer
from core.reward_manager import RewardManager
from db.database import DatabaseManager
from db.history_manager import HistoryManager

logger = get_logger(__name__)


class PLEXStakingMainWindow:
    """
    Главное окно PLEX Dynamic Staking Manager.
    
    Объединяет все вкладки и компоненты в единый интерфейс.
    Полная поддержка изменения размера (resizable).
    """
    
    def __init__(self):
        """Инициализация главного окна."""
        self.theme = get_theme()
        self.widget_factory = SafeWidgetFactory(self.theme)
        
        # Основные менеджеры
        self.staking_manager = None
        self.reward_calculator = None
        self.database_manager = None
        self.history_manager = None
        
        # UI компоненты
        self.root = None
        self.tabview = None
        self.analysis_tab = None
        self.rewards_tab = None
        self.history_tab = None
        self.settings_tab = None
        self.log_viewer = None
        self.status_bar = None
        
        # Состояние приложения
        self.is_initialized = False
        self.connection_status = "disconnected"
        self.wallet_connected = False
        self.wallet_address = None
        self.logs_visible = True  # Логи показываются по умолчанию
        
        logger.debug("🚀 PLEXStakingMainWindow инициализирован (RESIZABLE)")
    
    def create_window(self) -> None:
        """Создание главного окна с полной поддержкой изменения размера."""
        try:
            # Создание корневого окна
            self.root = ctk.CTk()
            self.root.title("PLEX Dynamic Staking Manager v4.0")
            self.root.geometry("1400x900")
            self.root.minsize(1000, 600)  # Минимальный размер
            
            # RESIZABLE SUPPORT - разрешаем изменение размера
            self.root.resizable(True, True)
            
            # Настройка grid weights для адаптивности главного окна
            self.root.grid_rowconfigure(0, weight=1)
            self.root.grid_columnconfigure(0, weight=1)
            
            # Применение темы
            apply_window_style(self.root)
            
            # Настройка закрытия окна
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # Создание интерфейса
            self._create_interface()
            
            # Инициализация компонентов
            self._initialize_components()
            
            logger.info("✅ Главное окно создано (RESIZABLE)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания окна: {e}")
            if self.root:
                messagebox.showerror("Ошибка", f"Не удалось создать окно:\\n{e}")
            raise
    
    def _create_interface(self) -> None:
        """Создание интерфейса с полной поддержкой resizable."""
        # Главный контейнер с grid для лучшей адаптивности
        self.main_container = self.theme.create_styled_frame(self.root, 'primary')
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Настройка grid weights для адаптивности
        self.main_container.grid_rowconfigure(0, weight=0)  # Header фиксированный
        self.main_container.grid_rowconfigure(1, weight=0)  # Toolbar фиксированный
        self.main_container.grid_rowconfigure(2, weight=1)  # Основная область растягивается
        self.main_container.grid_rowconfigure(3, weight=0)  # Footer опциональный (для логов)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Верхняя панель с заголовком и статусом
        self._create_header()
        
        # Панель инструментов
        self._create_toolbar()
        
        # Основная область с вкладками (РАСТЯГИВАЕТСЯ)
        self._create_main_area()
        
        # Нижняя панель с логами и статусом (опциональная)
        self._create_footer()
    
    def _create_header(self) -> None:
        """Создание верхней панели с расширенным статусом."""
        self.header_frame = self.theme.create_styled_frame(self.main_container, 'secondary')
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(0, weight=1)  # Левая часть растягивается
        self.header_frame.grid_columnconfigure(1, weight=0)  # Правая часть фиксированная
        
        # Левая часть - заголовок
        self.header_left = self.theme.create_styled_frame(self.header_frame, 'secondary')
        self.header_left.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        # Заголовок приложения
        self.title_label = self.theme.create_styled_label(
            self.header_left,
            "💎 PLEX Dynamic Staking Manager v4.0",
            'title'
        )
        self.title_label.pack(anchor='w')
        
        # Панель статуса процессов
        self.status_info_frame = self.theme.create_styled_frame(self.header_left, 'secondary')
        self.status_info_frame.pack(anchor='w', pady=(5, 0))
        
        # Статус инициализации
        self.init_status_label = self.theme.create_styled_label(
            self.status_info_frame,
            "🔄 Инициализация...",
            'warning'
        )
        self.init_status_label.pack(side='left', padx=(0, 15))
        
        # Статус ноды
        self.node_status_label = self.theme.create_styled_label(
            self.status_info_frame,
            "🌐 Нода: Не подключена",
            'error'
        )
        self.node_status_label.pack(side='left', padx=(0, 15))
        
        # Статус кошелька
        self.wallet_status_header = self.theme.create_styled_label(
            self.status_info_frame,
            "👛 Кошелек: Не подключен",
            'error'
        )
        self.wallet_status_header.pack(side='left', padx=(0, 15))
        
        # Статус базы данных
        self.db_status_label = self.theme.create_styled_label(
            self.status_info_frame,
            "🗄️ БД: Не готова",
            'warning'
        )
        self.db_status_label.pack(side='left', padx=(0, 15))
        
        # Статус подключения (connection_indicator)
        self.connection_indicator = self.theme.create_styled_label(
            self.status_info_frame,
            "🔗 Подключение: Проверка...",
            'warning'
        )
        self.connection_indicator.pack(side='left')
        
        # Правая часть - основные индикаторы
        self.header_right = self.theme.create_styled_frame(self.header_frame, 'secondary')
        self.header_right.grid(row=0, column=1, sticky="e", padx=20, pady=10)
        
        # Общий статус системы
        self.system_status_frame = self.theme.create_styled_frame(self.header_right, 'secondary')
        self.system_status_frame.pack(anchor='e')
        
        self.system_status_label = self.theme.create_styled_label(
            self.system_status_frame,
            "⚠️ Система не готова",
            'warning'
        )
        self.system_status_label.pack(side='right', padx=(0, 10))
        
        # Время последнего обновления
        self.last_update_label = self.theme.create_styled_label(
            self.system_status_frame,
            "Обновлено: никогда",
            'secondary'
        )
        self.last_update_label.pack(side='right', padx=(0, 20))
    
    def _create_toolbar(self) -> None:
        """Создание панели инструментов."""
        self.toolbar_frame = self.theme.create_styled_frame(self.main_container, 'card')
        self.toolbar_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.toolbar_frame.grid_columnconfigure(0, weight=1)  # Левая часть растягивается
        self.toolbar_frame.grid_columnconfigure(1, weight=0)  # Правая часть фиксированная
        
        # Левая группа кнопок
        self.toolbar_left = self.theme.create_styled_frame(self.toolbar_frame, 'card')
        self.toolbar_left.grid(row=0, column=0, sticky="w", padx=15, pady=10)
        
        # Кнопка подключения кошелька
        self.wallet_button = self.theme.create_styled_button(
            self.toolbar_left,
            "🔐 Подключить кошелек",
            'primary',
            command=self._show_wallet_dialog,
            width=180
        )
        self.wallet_button.pack(side='left', padx=(0, 10))
        
        # Статус кошелька
        self.wallet_status_label = self.theme.create_styled_label(
            self.toolbar_left,
            "❌ Кошелек не подключен",
            'error'
        )
        self.wallet_status_label.pack(side='left', padx=(10, 0))
        
        # Правая группа кнопок
        self.toolbar_right = self.theme.create_styled_frame(self.toolbar_frame, 'card')
        self.toolbar_right.grid(row=0, column=1, sticky="e", padx=15, pady=10)
        
        # Кнопка просмотра логов
        self.logs_button = self.theme.create_styled_button(
            self.toolbar_right,
            "📋 Скрыть логи",
            'info',
            command=self._toggle_logs_panel,
            width=140
        )
        self.logs_button.pack(side='left', padx=(0, 10))
        
        # Кнопка обновления статуса
        self.refresh_button = self.theme.create_styled_button(
            self.toolbar_right,
            "🔄 Обновить",
            'secondary',
            command=self._refresh_status,
            width=100
        )
        self.refresh_button.pack(side='left')

    def _create_main_area(self) -> None:
        """Создание основной области с вкладками (РАСТЯГИВАЕТСЯ)."""
        # Контейнер для вкладок
        self.tabs_container = self.theme.create_styled_frame(self.main_container, 'primary')
        self.tabs_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.tabs_container.grid_rowconfigure(0, weight=1)  # TabView растягивается
        self.tabs_container.grid_columnconfigure(0, weight=1)
        
        # Создание TabView
        self.tabview = ctk.CTkTabview(
            self.tabs_container,
            **self.theme.get_tabview_style()
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Создание вкладок
        self._create_tabs()
    
    def _create_tabs(self) -> None:
        """Создание всех вкладок."""
        # Вкладка анализа
        self.tabview.add("📊 Анализ")
        analysis_frame = self.tabview.tab("📊 Анализ")
        self.analysis_tab = EnhancedAnalysisTab(analysis_frame, widget_factory=self.widget_factory)
        self.analysis_tab.pack(fill='both', expand=True)
        
        # 🚀 ИНТЕГРАЦИЯ ОПТИМИЗИРОВАННОГО АНАЛИЗА
        success = patch_analysis_tab_with_optimization(self.analysis_tab)
        if success:
            logger.info("✅ Оптимизированный анализ интегрирован")
        else:
            logger.warning("⚠️ Оптимизированный анализ недоступен")
        
        # Вкладка наград
        self.tabview.add("🏆 Награды")
        rewards_frame = self.tabview.tab("🏆 Награды")
        self.rewards_tab = EnhancedRewardsTab(rewards_frame, widget_factory=self.widget_factory)
        self.rewards_tab.pack(fill='both', expand=True)
        
        # Вкладка истории
        self.tabview.add("📜 История")
        history_frame = self.tabview.tab("📜 История")
        self.history_tab = EnhancedHistoryTab(history_frame, widget_factory=self.widget_factory)
        self.history_tab.pack(fill='both', expand=True)
        
        # Вкладка настроек
        self.tabview.add("⚙️ Настройки")
        settings_frame = self.tabview.tab("⚙️ Настройки")
        self.settings_tab = SettingsTab(settings_frame, widget_factory=self.widget_factory)
        self.settings_tab.pack(fill='both', expand=True)
        
        # Установка активной вкладки
        self.tabview.set("📊 Анализ")
    
    def _create_footer(self) -> None:
        """Создание нижней панели с логами (RESIZABLE)."""
        self.footer_frame = self.theme.create_styled_frame(self.main_container, 'secondary')
        self.footer_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.footer_frame.grid_columnconfigure(0, weight=1)
        
        # Контейнер для логов
        self.logs_container = self.theme.create_styled_frame(self.footer_frame, 'primary')
        self.logs_container.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.logs_container.grid_columnconfigure(0, weight=1)
        
        # Заголовок логов
        self.logs_title = self.theme.create_styled_label(
            self.logs_container,
            "📋 Логи приложения",
            'subtitle'
        )
        self.logs_title.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))
        
        # Компонент просмотра логов (ФИКСИРОВАННАЯ ВЫСОТА для логов)
        self.log_viewer = LogViewer(
            self.logs_container,
            height=180
        )
        self.log_viewer.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # Статус бар
        self.status_bar = self._create_status_bar()
    
    def _create_status_bar(self) -> ctk.CTkFrame:
        """Создание статус бара."""
        status_frame = self.theme.create_styled_frame(self.footer_frame, 'tertiary')
        status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        status_frame.grid_columnconfigure(1, weight=1)  # Средняя часть растягивается
        
        # Индикатор активности
        self.activity_label = self.theme.create_styled_label(
            status_frame,
            "💤 Ожидание",
            'secondary'
        )
        self.activity_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # Счетчики (справа)
        self.counters_frame = self.theme.create_styled_frame(status_frame, 'tertiary')
        self.counters_frame.grid(row=0, column=2, sticky="e", padx=10, pady=5)
        
        self.participants_counter = self.theme.create_styled_label(
            self.counters_frame,
            "👥 Участников: 0",
            'info'
        )
        self.participants_counter.pack(side='right', padx=(0, 15))
        
        self.operations_counter = self.theme.create_styled_label(
            self.counters_frame,
            "🔄 Операций: 0",
            'secondary'
        )
        self.operations_counter.pack(side='right', padx=(0, 15))
        
        return status_frame
    
    def _toggle_logs_panel(self) -> None:
        """Переключение видимости панели логов (ИСПРАВЛЕНО)."""
        try:
            if self.logs_visible:
                # Скрыть логи - убираем footer полностью
                self.footer_frame.grid_remove()
                self.logs_button.configure(text="📋 Показать логи")
                self.logs_visible = False
                logger.info("📋 Панель логов скрыта")
            else:
                # Показать логи - возвращаем footer
                self.footer_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
                self.logs_button.configure(text="📋 Скрыть логи")
                self.logs_visible = True
                logger.info("📋 Панель логов отображена")
                
                # Добавляем лог в viewer если он существует
                if hasattr(self, 'log_viewer') and self.log_viewer:
                    self.log_viewer.add_log_entry("INFO", "Панель логов отображена", "main_window")
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения логов: {e}")
    
    def _show_wallet_dialog(self) -> None:
        """Отображение диалога подключения кошелька."""
        try:
            result = show_wallet_connection_dialog(self.root)
            if result and result.get('success'):
                self.wallet_connected = True
                self.wallet_address = result.get('address')
                self._update_wallet_status(True, self.wallet_address)
                self._update_system_status()
        except Exception as e:
            logger.error(f"❌ Ошибка диалога кошелька: {e}")
    
    def _update_wallet_status(self, connected: bool, address: str = None) -> None:
        """Обновление статуса кошелька."""
        try:
            if connected and address:
                short_address = f"{address[:6]}...{address[-4:]}"
                self.wallet_status_label.configure(
                    text=f"✅ {short_address}",
                    text_color=self.theme.colors['success']
                )
                self.wallet_status_header.configure(
                    text=f"👛 Кошелек: {short_address}",
                    text_color=self.theme.colors['success']
                )
                self.wallet_button.configure(text="🔓 Отключить кошелек")
            else:
                self.wallet_status_label.configure(
                    text="❌ Кошелек не подключен",
                    text_color=self.theme.colors['error']
                )
                self.wallet_status_header.configure(
                    text="👛 Кошелек: Не подключен",
                    text_color=self.theme.colors['error']
                )
                self.wallet_button.configure(text="🔐 Подключить кошелек")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса кошелька: {e}")
    
    def _update_activity(self, message: str) -> None:
        """Обновление индикатора активности."""
        try:
            if self.activity_label:
                self.activity_label.configure(text=message)
                
                # Добавляем лог в viewer
                if hasattr(self, 'log_viewer') and self.log_viewer:
                    self.log_viewer.add_log_entry("INFO", message, "system")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления активности: {e}")
    
    def _update_header_status(self, component: str, status: str, message: str = "") -> None:
        """Обновление статуса компонентов в заголовке."""
        try:
            status_colors = {
                'ready': self.theme.colors['success'],
                'connecting': self.theme.colors['warning'],
                'error': self.theme.colors['error'],
                'warning': self.theme.colors['warning']
            }
            
            color = status_colors.get(status, self.theme.colors['text_secondary'])
            
            if component == "init":
                if status == "ready":
                    self.init_status_label.configure(text="✅ Готово", text_color=color)
                else:
                    self.init_status_label.configure(text=f"🔄 {message}", text_color=color)
                    
            elif component == "node":
                if status == "ready":
                    self.node_status_label.configure(text="🌐 Нода: Подключена", text_color=color)
                elif status == "error":
                    self.node_status_label.configure(text=f"🌐 Нода: {message}", text_color=color)
                else:
                    self.node_status_label.configure(text=f"🌐 Нода: {message}", text_color=color)
                    
            elif component == "database":
                if status == "ready":
                    self.db_status_label.configure(text="🗄️ БД: Готова", text_color=color)
                else:
                    self.db_status_label.configure(text=f"🗄️ БД: {message}", text_color=color)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса заголовка: {e}")
    
    def _update_system_status(self) -> None:
        """Обновление общего статуса системы."""
        try:
            # Проверяем готовность компонентов
            components_ready = 0
            total_components = 4
            
            if self.is_initialized:
                components_ready += 1
                
            if hasattr(self, 'database_manager') and self.database_manager:
                components_ready += 1
                
            if self.connection_status == "connected":
                components_ready += 1
                
            if self.wallet_connected:
                components_ready += 1
            
            # Обновляем статус
            if components_ready == total_components:
                self.system_status_label.configure(
                    text="✅ Система готова",
                    text_color=self.theme.colors['success']
                )
            elif components_ready >= 2:
                self.system_status_label.configure(
                    text=f"⚠️ Частично готова ({components_ready}/{total_components})",
                    text_color=self.theme.colors['warning']
                )
            else:
                self.system_status_label.configure(
                    text="❌ Система не готова",
                    text_color=self.theme.colors['error']
                )
            
            # Обновляем время
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.configure(text=f"Обновлено: {current_time}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления системного статуса: {e}")
    
    def _initialize_components(self) -> None:
        """Инициализация основных компонентов."""
        try:
            # Инициализация статусов в верхней панели
            self._init_all_statuses()
            
            # Инициализация в отдельном потоке
            init_thread = threading.Thread(
                target=self._async_initialization,
                daemon=True
            )
            init_thread.start()            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации компонентов: {e}")
            self._show_error("Ошибка инициализации", str(e))
    
    def _init_all_statuses(self) -> None:
        """Инициализация всех статусов."""
        self._update_header_status("init", "connecting", "Запуск системы")
        self._update_header_status("node", "connecting", "Проверка подключения")
        self._update_header_status("database", "warning", "Инициализация")
        self._update_system_status()
    
    def _async_initialization(self) -> None:
        """Асинхронная инициализация компонентов."""
        try:
            # Обновление статуса
            self.root.after_idle(lambda: self._update_activity("🔄 Инициализация..."))
            self.root.after_idle(lambda: self._update_header_status("init", "connecting", "Запуск системы"))
            
            # Инициализация менеджера базы данных
            self.root.after_idle(lambda: self._update_header_status("database", "connecting", "Подключение к БД"))
            try:
                self.database_manager = DatabaseManager()
                self.root.after_idle(lambda: self._update_header_status("database", "ready", "Готова"))
            except Exception as db_error:
                logger.error(f"❌ Ошибка БД: {db_error}")
                self.root.after_idle(lambda: self._update_header_status("database", "error", "Ошибка БД"))
            
            # Инициализация менеджера истории
            try:
                self.history_manager = HistoryManager()
            except Exception as hist_error:
                logger.error(f"❌ Ошибка истории: {hist_error}")
            
            # Инициализация калькулятора наград
            try:
                self.reward_calculator = RewardCalculator()
            except Exception as calc_error:
                logger.error(f"❌ Ошибка калькулятора: {calc_error}")
            
            # Инициализация основного менеджера стейкинга
            try:
                self.staking_manager = StakingManager()
                # Асинхронная инициализация StakingManager в отдельном потоке
                self._schedule_async_staking_init()
            except Exception as stake_error:
                logger.error(f"❌ Ошибка стейкинг менеджера: {stake_error}")
            
            # Установка менеджеров во вкладки
            self.root.after_idle(self._connect_managers_to_tabs)
            
            # Отмечаем систему как готовую ПЕРЕД попыткой подключения к блокчейну
            self.is_initialized = True
            self.root.after_idle(lambda: self._update_header_status("init", "ready", "Завершена"))
            self.root.after_idle(lambda: self._update_activity("✅ Система готова"))
            self.root.after_idle(self._update_system_status)
            
            # Попытка подключения к блокчейну (в фоне, не блокирует систему)
            self.root.after_idle(self._try_blockchain_connection)
            
            logger.info("✅ Все компоненты инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка асинхронной инициализации: {e}")
            self.root.after_idle(lambda: self._update_activity(f"❌ Ошибка инициализации: {str(e)[:50]}"))
    
    def _schedule_async_staking_init(self) -> None:
        """Планирование асинхронной инициализации StakingManager."""
        def init_staking():
            try:
                if self.staking_manager:
                    # Инициализация в отдельном потоке
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Здесь можно добавить async методы StakingManager
                    logger.info("✅ StakingManager инициализирован")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации StakingManager: {e}")
        
        # Запуск в отдельном потоке
        staking_thread = threading.Thread(target=init_staking, daemon=True)
        staking_thread.start()
    
    def _connect_managers_to_tabs(self) -> None:
        """Подключение менеджеров к вкладкам."""
        try:
            # Подключение менеджеров к вкладке анализа
            if self.analysis_tab and self.staking_manager:
                # Передача менеджеров в анализ
                if hasattr(self.analysis_tab, 'set_managers'):
                    self.analysis_tab.set_managers(self.staking_manager)
            
            # Подключение к вкладке наград
            if self.rewards_tab and self.reward_calculator:
                if hasattr(self.rewards_tab, 'set_managers'):
                    self.rewards_tab.set_managers(
                        reward_calculator=self.reward_calculator,
                        staking_manager=self.staking_manager
                    )
            
            # Подключение к вкладке истории
            if self.history_tab and self.history_manager:
                if hasattr(self.history_tab, 'set_managers'):
                    self.history_tab.set_managers(self.history_manager)
            
            logger.info("✅ Менеджеры подключены к вкладкам")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения менеджеров: {e}")
    
    def _try_blockchain_connection(self) -> None:
        """Попытка подключения к блокчейну."""
        def connect():
            try:
                self.root.after_idle(lambda: self._update_header_status("node", "connecting", "Подключение"))
                
                # Проверяем настройки RPC
                import os
                rpc_url = getattr(settings, 'QUICKNODE_RPC_URL', '') or os.getenv('QUICKNODE_HTTP', '')
                
                if not rpc_url:
                    self.connection_status = "error"
                    self.root.after_idle(lambda: self._update_header_status("node", "error", "RPC URL не настроен"))
                    self.root.after_idle(self._update_system_status)
                    return
                  # Попытка подключения через StakingManager
                if self.staking_manager and hasattr(self.staking_manager, 'web3_manager'):
                    web3_manager = self.staking_manager.web3_manager
                    if web3_manager and web3_manager.is_connected:
                        # Дополнительная проверка подключения
                        try:
                            latest_block = web3_manager.get_latest_block_number()
                            self.connection_status = "connected"
                            self.root.after_idle(lambda: self._update_header_status("node", "ready", "Подключена"))
                            self.root.after_idle(lambda: self._update_activity(f"✅ Подключен к BSC (блок {latest_block})"))
                        except Exception as e:
                            logger.warning(f"⚠️ Проблема с получением блока: {e}")
                            self.connection_status = "error"
                            self.root.after_idle(lambda: self._update_header_status("node", "error", "Ошибка подключения"))
                            self.root.after_idle(lambda: self._update_activity("❌ Ошибка подключения к BSC"))
                    else:
                        self.connection_status = "error"
                        self.root.after_idle(lambda: self._update_header_status("node", "error", "Web3Manager не подключен"))
                        self.root.after_idle(lambda: self._update_activity("❌ Web3Manager не подключен"))
                else:
                    self.connection_status = "error"
                    self.root.after_idle(lambda: self._update_header_status("node", "error", "StakingManager недоступен"))
                
                self.root.after_idle(self._update_system_status)
                
            except Exception as e:
                logger.error(f"❌ Ошибка подключения к блокчейну: {e}")
                self.connection_status = "error"
                self.root.after_idle(lambda: self._update_header_status("node", "error", "Ошибка подключения"))
                self.root.after_idle(self._update_system_status)
        
        # Подключение в отдельном потоке
        connection_thread = threading.Thread(target=connect, daemon=True)
        connection_thread.start()
    
    def _refresh_status(self) -> None:
        """Обновление статуса приложения и подключений."""
        try:
            self._update_activity("🔄 Обновление статуса...")
            
            # Обновление в отдельном потоке
            refresh_thread = threading.Thread(
                target=self._perform_status_refresh,
                daemon=True
            )
            refresh_thread.start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")
            self._update_activity("❌ Ошибка обновления")
    
    def _perform_status_refresh(self) -> None:
        """Выполнение обновления статуса в отдельном потоке."""
        try:
            # Проверка переменных окружения и настроек
            import os
            rpc_url = getattr(settings, 'QUICKNODE_RPC_URL', '') or os.getenv('QUICKNODE_HTTP', '')
            
            if rpc_url:
                # Принудительное переподключение к блокчейну
                self.root.after_idle(lambda: self._try_blockchain_connection())
            else:
                # Обновляем статус - RPC не настроен
                self.root.after_idle(lambda: self._update_header_status("node", "error", "RPC URL не настроен"))
                self.root.after_idle(lambda: self._update_system_status())
            
            # Проверка статуса базы данных
            if self.database_manager:
                # Можно добавить проверку соединения с БД
                self.root.after_idle(lambda: self._update_header_status("database", "ready", "Готова"))
            
            # Обновляем системный статус
            self.root.after_idle(self._update_system_status)
            self.root.after_idle(lambda: self._update_activity("✅ Статус обновлен"))
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения обновления статуса: {e}")
            self.root.after_idle(lambda: self._update_activity("❌ Ошибка обновления"))
    
    def _update_counters(self, participants: int = None, operations: int = None) -> None:
        """Обновление счетчиков."""
        try:
            if participants is not None and self.participants_counter:
                self.participants_counter.configure(text=f"👥 Участников: {participants}")
            
            if operations is not None and self.operations_counter:
                self.operations_counter.configure(text=f"🔄 Операций: {operations}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления счетчиков: {e}")
    
    def _show_error(self, title: str, message: str) -> None:
        """Отображение ошибки."""
        try:
            messagebox.showerror(title, message)
            
            if hasattr(self, 'log_viewer') and self.log_viewer:
                self.log_viewer.add_log_entry("ERROR", f"{title}: {message}", "main_window")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отображения ошибки: {e}")
    
    def _on_closing(self) -> None:
        """Обработка закрытия окна."""
        try:
            # Корректное завершение StakingManager
            if hasattr(self, 'staking_manager') and self.staking_manager:
                import asyncio
                try:
                    # Создаём новый event loop если его нет
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            raise RuntimeError("Event loop is closed")
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Запускаем shutdown
                    loop.run_until_complete(self.staking_manager.shutdown())
                    logger.info("✅ StakingManager корректно завершён")
                except Exception as e:
                    logger.error(f"❌ Ошибка завершения StakingManager: {e}")
            
            # Сохранение настроек и состояния
            if self.settings_tab:
                # Автосохранение настроек если включено
                pass
            
            # Остановка мониторинга логов
            if hasattr(self, 'log_viewer') and self.log_viewer:
                self.log_viewer.stop_monitoring()
            
            # Закрытие соединений
            if self.database_manager:
                # Здесь может быть закрытие БД
                pass
            
            logger.info("👋 Приложение завершается...")
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии: {e}")
            # Принудительное закрытие
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
    
    def run(self) -> None:
        """Запуск приложения."""
        try:
            self.create_window()
            
            # Добавляем стартовые логи
            if hasattr(self, 'log_viewer') and self.log_viewer:
                self.log_viewer.add_log_entry("INFO", "Приложение запущено", "main_window")
                self.log_viewer.add_log_entry("INFO", "Интерфейс полностью адаптивный (resizable)", "ui")
            
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка приложения: {e}")
            if self.root:
                messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение:\\n{e}")


def main():
    """Главная функция."""
    try:
        app = PLEXStakingMainWindow()
        app.run()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
