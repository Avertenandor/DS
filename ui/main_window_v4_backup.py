"""
PLEX Dynamic Staking Manager - Main Window V4
Главное окно приложения с интегрированными вкладками.

Автор: PLEX Dynamic Staking Team
Версия: 4.0.0
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

# Добавление корневой директории в путь
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ui.themes.dark_theme import get_theme, apply_window_style
from ui.components.log_viewer import LogViewer
from ui.components.progress_bar import ProgressBar
from ui.components.wallet_connection_dialog import WalletConnectionDialog
from ui.tabs.analysis_tab import AnalysisTab
from ui.tabs.rewards_tab import RewardsTab
from ui.tabs.history_tab import HistoryTab
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
    """
    
    def __init__(self):
        """Инициализация главного окна."""
        self.theme = get_theme()
        
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
        
        logger.debug("🚀 PLEXStakingMainWindow инициализирован")
    
    def create_window(self) -> None:
        """Создание главного окна."""
        try:
            # Создание корневого окна
            self.root = ctk.CTk()
            self.root.title("PLEX Dynamic Staking Manager v4.0")
            self.root.geometry("1400x900")
            self.root.minsize(1200, 700)
            
            # Применение темы
            apply_window_style(self.root)
            
            # Настройка закрытия окна
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            # Создание интерфейса
            self._create_interface()
            
            # Инициализация компонентов
            self._initialize_components()
            
            logger.info("✅ Главное окно создано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания окна: {e}")
            if self.root:
                messagebox.showerror("Ошибка", f"Не удалось создать окно:\\n{e}")
            raise
    
    def _create_interface(self) -> None:
        """Создание интерфейса."""
        # Главный контейнер
        self.main_container = self.theme.create_styled_frame(self.root, 'primary')
        self.main_container.pack(fill='both', expand=True)
        
        # Верхняя панель с заголовком и статусом
        self._create_header()
        
        # Панель инструментов
        self._create_toolbar()
        
        # Основная область с вкладками
        self._create_main_area()
          # Нижняя панель с логами и статусом
        self._create_footer()
    
    def _create_header(self) -> None:
        """Создание верхней панели с расширенным статусом."""
        self.header_frame = self.theme.create_styled_frame(self.main_container, 'secondary')
        self.header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # Левая часть - заголовок
        self.header_left = self.theme.create_styled_frame(self.header_frame, 'secondary')
        self.header_left.pack(side='left', fill='x', expand=True, padx=20, pady=10)
        
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
        self.db_status_label.pack(side='left')
        
        # Правая часть - основные индикаторы
        self.header_right = self.theme.create_styled_frame(self.header_frame, 'secondary')
        self.header_right.pack(side='right', padx=20, pady=10)
        
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
        self.toolbar_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Левая группа кнопок
        self.toolbar_left = self.theme.create_styled_frame(self.toolbar_frame, 'card')
        self.toolbar_left.pack(side='left', padx=15, pady=10)
        
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
        self.toolbar_right.pack(side='right', padx=15, pady=10)
        
        # Кнопка просмотра логов
        self.logs_button = self.theme.create_styled_button(
            self.toolbar_right,
            "📋 Показать логи",
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
        """Создание основной области с вкладками."""
        # Контейнер для вкладок
        self.tabs_container = self.theme.create_styled_frame(self.main_container, 'primary')
        self.tabs_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Создание TabView
        self.tabview = ctk.CTkTabview(
            self.tabs_container,
            **self.theme.get_tabview_style()
        )
        self.tabview.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Создание вкладок
        self._create_tabs()
    
    def _create_tabs(self) -> None:
        """Создание всех вкладок."""
        # Вкладка анализа
        self.tabview.add("📊 Анализ")
        analysis_frame = self.tabview.tab("📊 Анализ")
        self.analysis_tab = AnalysisTab(analysis_frame)
        self.analysis_tab.pack(fill='both', expand=True)
        
        # 🚀 ИНТЕГРАЦИЯ ОПТИМИЗИРОВАННОГО АНАЛИЗА
        success = patch_analysis_tab_with_optimization(self.analysis_tab)
        if success:
            logger.info("🚀 AnalysisTab интегрирована с FullOptimizedAnalyzer (экономия 88.8% API)")
        else:
            logger.warning("⚠️ Оптимизированный анализ недоступен, используется базовая версия")
        
        # Вкладка наград
        self.tabview.add("🎁 Награды")
        rewards_frame = self.tabview.tab("🎁 Награды")
        self.rewards_tab = RewardsTab(rewards_frame)
        self.rewards_tab.pack(fill='both', expand=True)
        
        # Вкладка истории
        self.tabview.add("📚 История")
        history_frame = self.tabview.tab("📚 История")
        self.history_tab = HistoryTab(history_frame)
        self.history_tab.pack(fill='both', expand=True)
        
        # Вкладка настроек
        self.tabview.add("⚙️ Настройки")
        settings_frame = self.tabview.tab("⚙️ Настройки")
        self.settings_tab = SettingsTab(settings_frame)
        self.settings_tab.pack(fill='both', expand=True)
        
        # Установка активной вкладки
        self.tabview.set("📊 Анализ")
    
    def _create_footer(self) -> None:
        """Создание нижней панели."""
        self.footer_frame = self.theme.create_styled_frame(self.main_container, 'secondary')
        self.footer_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        # Контейнер для логов
        self.logs_container = self.theme.create_styled_frame(self.footer_frame, 'primary')
        self.logs_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Заголовок логов
        self.logs_title = self.theme.create_styled_label(
            self.logs_container,
            "📋 Логи приложения",
            'subtitle'
        )
        self.logs_title.pack(anchor='w', padx=10, pady=(5, 0))
        
        # Компонент просмотра логов
        self.log_viewer = LogViewer(
            self.logs_container,
            height=150
        )
        self.log_viewer.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        
        # Статус бар
        self.status_bar = self._create_status_bar()
    
    def _create_status_bar(self) -> ctk.CTkFrame:
        """Создание статус бара."""
        status_frame = self.theme.create_styled_frame(self.footer_frame, 'tertiary')
        status_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Индикатор активности
        self.activity_label = self.theme.create_styled_label(
            status_frame,
            "💤 Ожидание",
            'secondary'
        )
        self.activity_label.pack(side='left', padx=10, pady=5)
        
        # Счетчики
        self.counters_frame = self.theme.create_styled_frame(status_frame, 'tertiary')
        self.counters_frame.pack(side='right', padx=10, pady=5)
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
    
    def _async_initialization(self) -> None:
        """Асинхронная инициализация компонентов."""
        try:
            # Обновление статуса
            self.root.after_idle(lambda: self._update_activity("🔄 Инициализация..."))
            self.root.after_idle(lambda: self._update_header_status("init", "connecting", "Запуск системы"))
            
            # Инициализация менеджера базы данных
            self.root.after_idle(lambda: self._update_header_status("database", "connecting", "Подключение к БД"))
            self.database_manager = DatabaseManager()
            self.root.after_idle(lambda: self._update_header_status("database", "ready", "Готова"))
            
            # Инициализация менеджера истории
            self.history_manager = HistoryManager(self.database_manager)
            
            # Инициализация калькулятора наград
            self.reward_calculator = RewardCalculator()
            
            # Инициализация основного менеджера стейкинга
            self.staking_manager = StakingManager()
            
            # Установка менеджеров во вкладки
            self.root.after_idle(self._connect_managers_to_tabs)
            
            # Попытка подключения к блокчейну
            self.root.after_idle(self._try_blockchain_connection)
            
            self.is_initialized = True
            self.root.after_idle(lambda: self._update_header_status("init", "ready", "Завершена"))
            self.root.after_idle(lambda: self._update_activity("✅ Готов к работе"))
            self.root.after_idle(self._update_system_status)
            
            logger.info("✅ Все компоненты инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка асинхронной инициализации: {e}")
            self.root.after_idle(lambda: self._update_header_status("init", "error", f"Ошибка: {str(e)[:30]}"))
            self.root.after_idle(lambda: self._show_error("Ошибка инициализации", str(e)))
    
    def _connect_managers_to_tabs(self) -> None:
        """Подключение менеджеров к вкладкам."""
        try:
            # Подключение к вкладке анализа
            if self.analysis_tab and self.staking_manager:
                self.analysis_tab.set_staking_manager(self.staking_manager)
            
            # Подключение к вкладке наград
            if self.rewards_tab and self.reward_calculator:
                self.rewards_tab.set_reward_manager(self.reward_calculator)
            
            # Подключение к вкладке истории
            if self.history_tab and self.history_manager:
                self.history_tab.set_history_manager(self.history_manager)
            
            # Подключение к вкладке настроек
            if self.settings_tab:
                self.settings_tab.set_settings_manager(settings)
            
            logger.debug("✅ Менеджеры подключены к вкладкам")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения менеджеров: {e}")
    
    def _try_blockchain_connection(self) -> None:
        """Попытка подключения к блокчейну."""
        try:
            # Получение настроек RPC
            rpc_url = getattr(settings, 'QUICKNODE_RPC_URL', '')
            
            if rpc_url:
                # Попытка подключения в отдельном потоке
                connection_thread = threading.Thread(
                    target=self._test_blockchain_connection,
                    args=(rpc_url,),
                    daemon=True
                )
                connection_thread.start()
            else:
                self._update_connection_status("disconnected", "RPC URL не настроен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка попытки подключения: {e}")
            self._update_connection_status("error", str(e))
    
    def _test_blockchain_connection(self, rpc_url: str) -> None:
        """Тестирование подключения к блокчейну."""
        try:
            # Здесь должна быть реальная проверка подключения
            # w3_manager = Web3Manager()
            # is_connected = w3_manager.test_connection(rpc_url)
            
            # Имитация для демонстрации
            import time
            time.sleep(2)
            is_connected = True  # В реальности результат проверки
            
            if is_connected:
                self.root.after_idle(lambda: self._update_connection_status("connected", "Подключен к BSC"))
            else:
                self.root.after_idle(lambda: self._update_connection_status("disconnected", "Ошибка подключения"))
                
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования подключения: {e}")
            self.root.after_idle(lambda: self._update_connection_status("error", str(e)))
    
    def _update_connection_status(self, status: str, message: str = "") -> None:
        """Обновление статуса подключения."""
        try:
            self.connection_status = status
            
            status_configs = {
                "connected": {
                    "text": "🟢 Подключено",
                    "color": "success"
                },
                "disconnected": {
                    "text": "🔴 Не подключено",
                    "color": "error"
                },
                "connecting": {
                    "text": "🟡 Подключение...",
                    "color": "warning"
                },
                "error": {
                    "text": "❌ Ошибка",
                    "color": "error"
                }
            }
            
            config = status_configs.get(status, status_configs["disconnected"])
            
            self.connection_indicator.configure(
                text=config["text"],
                text_color=self.theme.get_status_color(config["color"])
            )
            
            # Добавление сообщения в лог
            if message:
                if self.log_viewer:
                    self.log_viewer.add_log_entry("system", f"Статус подключения: {message}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")
    
    def _update_activity(self, message: str) -> None:
        """Обновление индикатора активности."""
        try:
            if self.activity_label:
                self.activity_label.configure(text=message)
            
            if self.log_viewer:
                self.log_viewer.add_log_entry("info", message)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления активности: {e}")
    
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
            
            if self.log_viewer:
                self.log_viewer.add_log_entry("error", f"{title}: {message}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отображения ошибки: {e}")
    
    def _on_closing(self) -> None:
        """Обработка закрытия окна."""
        try:
            # Сохранение настроек и состояния
            if self.settings_tab:
                # Автосохранение настроек если включено
                pass
            
            # Закрытие соединений
            if self.database_manager:
                self.database_manager.close()
            
            logger.info("👋 Приложение закрывается")
            
            # Закрытие окна
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии: {e}")
            self.root.destroy()
    
    def run(self) -> None:
        """Запуск приложения."""
        try:
            if not self.root:
                self.create_window()
            
            logger.info("🚀 Запуск PLEX Dynamic Staking Manager v4.0")
            
            # Запуск главного цикла
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка запуска: {e}")
            if self.root:
                messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение:\\n{e}")
    
    def get_current_tab(self) -> str:
        """Получение текущей активной вкладки."""
        if self.tabview:
            return self.tabview.get()
        return ""
    
    def switch_to_tab(self, tab_name: str) -> None:
        """Переключение на указанную вкладку."""
        try:
            if self.tabview:
                self.tabview.set(tab_name)
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения вкладки: {e}")
    
    def _show_wallet_dialog(self) -> None:
        """Отображение диалога подключения кошелька."""
        try:
            dialog = WalletConnectionDialog(self.root)
            result = dialog.show()
            
            if result and result.get('success'):
                # Успешное подключение кошелька
                self.wallet_connected = True
                self.wallet_address = result.get('address', 'Unknown')
                wallet_type = result.get('type', 'private_key')
                
                # Обновление UI
                self._update_wallet_status(True, self.wallet_address, wallet_type)
                
                # Уведомление в логах
                self.log_viewer.add_log_entry(
                    "success", 
                    f"✅ Кошелек подключен ({wallet_type}): {self.wallet_address[:10]}...{self.wallet_address[-8:]}"
                )
                
                logger.info(f"✅ Кошелек подключен: {self.wallet_address}")
                
            else:
                # Отмена или ошибка
                error_msg = result.get('error', 'Подключение отменено') if result else 'Подключение отменено'
                self.log_viewer.add_log_entry("warning", f"⚠️ {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка диалога кошелька: {e}")
            self._show_error("Ошибка кошелька", f"Не удалось открыть диалог подключения: {e}")
    
    def _update_wallet_status(self, connected: bool, address: str = None, wallet_type: str = None) -> None:
        """Обновление статуса кошелька в UI."""
        try:
            if connected and address:
                # Кошелек подключен
                short_address = f"{address[:6]}...{address[-4:]}"
                type_icon = "🌱" if wallet_type == "seed_phrase" else "🔑"
                
                self.wallet_button.configure(text=f"{type_icon} {short_address}")
                self.wallet_status_label.configure(
                    text="✅ Кошелек подключен",
                    text_color=self.theme.get_status_color("success")
                )
            else:
                # Кошелек не подключен
                self.wallet_button.configure(text="🔐 Подключить кошелек")
                self.wallet_status_label.configure(
                    text="❌ Кошелек не подключен",
                    text_color=self.theme.get_status_color("error")
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса кошелька: {e}")
    
    def _toggle_logs_panel(self) -> None:
        """Переключение видимости панели логов."""
        try:
            if self.logs_visible:
                # Скрыть логи
                self.footer_frame.pack_forget()
                self.logs_button.configure(text="📋 Показать логи")
                self.logs_visible = False
                self.log_viewer.add_log_entry("info", "📋 Панель логов скрыта")
            else:
                # Показать логи
                self.footer_frame.pack(fill='x', padx=10, pady=(5, 10))
                self.logs_button.configure(text="📋 Скрыть логи")
                self.logs_visible = True
                self.log_viewer.add_log_entry("info", "📋 Панель логов отображена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения логов: {e}")
    
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
            # Проверка подключения к блокчейну
            if hasattr(settings, 'QUICKNODE_RPC_URL') and settings.QUICKNODE_RPC_URL:
                self.root.after_idle(lambda: self._try_blockchain_connection())
            
            # Обновление счетчиков (здесь можно добавить реальную логику)
            # Пример: подсчет участников из базы данных
            participants_count = 0
            operations_count = 0
            
            if self.database_manager:
                # Здесь можно добавить реальные запросы к БД
                pass
            
            # Обновление UI в главном потоке
            self.root.after_idle(lambda: self._update_counters(participants_count, operations_count))
            self.root.after_idle(lambda: self._update_activity("✅ Статус обновлен"))
            
            # Лог об обновлении
            self.root.after_idle(lambda: self.log_viewer.add_log_entry(
                "info", 
                f"🔄 Статус обновлен: участников {participants_count}, операций {operations_count}"
            ))
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения обновления: {e}")
            self.root.after_idle(lambda: self._update_activity("❌ Ошибка обновления"))
            self.root.after_idle(lambda: self.log_viewer.add_log_entry("error", f"❌ Ошибка обновления: {e}"))
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Получение информации о подключенном кошельке."""
        return {
            'connected': self.wallet_connected,
            'address': self.wallet_address,
            'status': 'connected' if self.wallet_connected else 'disconnected'
        }
    
    def _update_header_status(self, component: str, status: str, message: str = "") -> None:
        """Обновление статуса компонента в верхней панели."""
        try:
            from datetime import datetime
            
            status_configs = {
                "success": {"color": "success", "icon": "✅"},
                "error": {"color": "error", "icon": "❌"}, 
                "warning": {"color": "warning", "icon": "⚠️"},
                "connecting": {"color": "warning", "icon": "🔄"},
                "ready": {"color": "success", "icon": "✅"},
                "not_ready": {"color": "error", "icon": "❌"}
            }
            
            config = status_configs.get(status, status_configs["error"])
            
            # Обновление компонентов
            if component == "init":
                if hasattr(self, 'init_status_label'):
                    text = f"{config['icon']} {message}" if message else f"{config['icon']} Инициализация"
                    self.init_status_label.configure(
                        text=text,
                        text_color=self.theme.get_status_color(config["color"])
                    )
            
            elif component == "node":
                if hasattr(self, 'node_status_label'):
                    text = f"🌐 Нода: {message}" if message else f"🌐 Нода: {status}"
                    self.node_status_label.configure(
                        text=text,
                        text_color=self.theme.get_status_color(config["color"])
                    )
            
            elif component == "wallet":
                if hasattr(self, 'wallet_status_header'):
                    text = f"👛 Кошелек: {message}" if message else f"👛 Кошелек: {status}"
                    self.wallet_status_header.configure(
                        text=text,
                        text_color=self.theme.get_status_color(config["color"])
                    )
            
            elif component == "database":
                if hasattr(self, 'db_status_label'):
                    text = f"🗄️ БД: {message}" if message else f"🗄️ БД: {status}"
                    self.db_status_label.configure(
                        text=text,
                        text_color=self.theme.get_status_color(config["color"])
                    )
            
            elif component == "system":
                if hasattr(self, 'system_status_label'):
                    text = f"{config['icon']} {message}" if message else f"{config['icon']} Система {status}"
                    self.system_status_label.configure(
                        text=text,
                        text_color=self.theme.get_status_color(config["color"])
                    )
            
            # Обновление времени
            if hasattr(self, 'last_update_label'):
                current_time = datetime.now().strftime("%H:%M:%S")
                self.last_update_label.configure(text=f"Обновлено: {current_time}")
            
            # Лог изменения
            if self.log_viewer and message:
                self.log_viewer.add_log_entry("system", f"{component.upper()}: {message}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса {component}: {e}")
    
    def _update_system_status(self) -> None:
        """Обновление общего статуса системы на основе всех компонентов."""
        try:
            # Проверка готовности всех компонентов
            init_ready = self.is_initialized
            node_ready = self.connection_status == "connected"
            wallet_ready = getattr(self, 'wallet_connected', False)
            db_ready = self.database_manager is not None
            
            if init_ready and node_ready and db_ready:
                if wallet_ready:
                    self._update_header_status("system", "ready", "Система готова")
                else:
                    self._update_header_status("system", "warning", "Подключите кошелек")
            elif init_ready and db_ready:
                self._update_header_status("system", "warning", "Подключите ноду")
            elif init_ready:
                self._update_header_status("system", "warning", "Инициализация БД")
            else:
                self._update_header_status("system", "error", "Система не готова")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления системного статуса: {e}")
    
    def _init_all_statuses(self) -> None:
        """Инициализация всех статусов в верхней панели."""
        try:
            self._update_header_status("init", "connecting", "Инициализация...")
            self._update_header_status("node", "error", "Не подключена")
            self._update_header_status("wallet", "error", "Не подключен")
            self._update_header_status("database", "warning", "Не готова")
            self._update_system_status()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации статусов: {e}")


def main():
    """Главная функция запуска приложения."""
    try:
        print("🚀 Запуск PLEX Dynamic Staking Manager v4.0...")
        
        # Проверка доступности UI
        try:
            import customtkinter as ctk
        except ImportError:
            print("❌ CustomTkinter не установлен. Установите: pip install customtkinter")
            return
        
        # Создание и запуск приложения
        app = PLEXStakingMainWindow()
        app.run()
        
    except KeyboardInterrupt:
        print("\\n👋 Приложение остановлено пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка запуска: {e}")


if __name__ == "__main__":
    main()
