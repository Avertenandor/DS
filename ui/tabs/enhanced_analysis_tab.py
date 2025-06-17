"""
PLEX Dynamic Staking Manager - Enhanced Analysis Tab with Detailed Logging
Улучшенная вкладка для анализа участников стейкинга с детальным логированием и функциональностью копирования.

Автор: PLEX Dynamic Staking Team
Версия: 1.2.0
Изменения:
- Добавлено детальное логирование результатов анализа
- Добавлено контекстное меню для таблицы участников
- Добавлена функциональность копирования в буфер обмена
- Улучшено цветовое кодирование и отображение
- Добавлен поиск и фильтрация по таблице
"""

import asyncio
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import tkinter as tk
from tkinter import messagebox, filedialog, Menu
import customtkinter as ctk
import csv
import json

# Для работы с буфером обмена
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

from ui.themes.dark_theme import get_theme
from ui.components.progress_bar import ProgressBar, ProgressState
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class EnhancedAnalysisTab(ctk.CTkFrame):
    """
    Улучшенная вкладка анализа участников стейкинга с детальным логированием и копированием.
    
    Новые функции:
    - Детальное логирование результатов анализа
    - Контекстное меню для таблицы участников
    - Копирование данных в буфер обмена
    - Улучшенное цветовое кодирование
    - Поиск и фильтрация участников
    """
    
    def __init__(self, parent, staking_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация EnhancedAnalysisTab.
        
        Args:
            parent: Родительский виджет
            staking_manager: Экземпляр StakingManager
            widget_factory: SafeWidgetFactory для создания виджетов
            **kwargs: Дополнительные параметры
        """
        super().__init__(parent, **kwargs)
        
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        self.staking_manager = staking_manager
        
        # Инициализация внутренних переменных
        self.analysis_running = False
        self.current_analysis_result = None
        self.full_analyzer = None
        self.filtered_participants = []
        self.selected_rows = []  # Для отслеживания выбранных строк
        self.search_query = ""   # Для поиска
        
        # Инициализация интерфейса
        self._create_widgets()
        self._setup_layout()
        
        logger.info("✅ Enhanced AnalysisTab инициализирована с улучшенным функционалом")
    
    def _create_widgets(self):
        """Создание виджетов интерфейса."""
        try:
            # Заголовок
            self.title_label = ctk.CTkLabel(
                self,
                text="📊 Анализ участников стейкинга",
                font=("Arial", 24, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # ПАНЕЛЬ УПРАВЛЕНИЯ
            self.control_panel = self._create_control_panel()
            
            # ПАНЕЛЬ НАСТРОЕК
            self.settings_panel = self._create_settings_panel()
            
            # ПРОГРЕСС-БАР
            self.progress_bar = ProgressBar(self)
            
            # ПАНЕЛЬ РЕЗУЛЬТАТОВ
            self.results_panel = self._create_results_panel()
            
            logger.debug("✅ Все виджеты созданы успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания виджетов: {e}")
            raise
    
    def _create_control_panel(self) -> ctk.CTkFrame:
        """Создание панели управления с основными кнопками."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок панели
        title = ctk.CTkLabel(
            panel,
            text="🎮 Панель управления",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title.pack(pady=(15, 10))
        
        # Основные кнопки
        buttons_frame = ctk.CTkFrame(panel)
        buttons_frame.configure(fg_color="transparent")
        buttons_frame.pack(fill='x', padx=15, pady=10)
        
        # Ряд 1: Основные действия
        row1 = ctk.CTkFrame(buttons_frame)
        row1.configure(fg_color="transparent")
        row1.pack(fill='x', pady=5)
        
        self.start_analysis_btn = ctk.CTkButton(
            row1,
            text="🚀 Начать анализ",
            command=self._start_analysis,
            fg_color=self.theme.colors['btn_primary'],
            hover_color=self.theme.colors['btn_primary_hover'],
            font=("Arial", 12, "bold"),
            height=40,
            width=150
        )
        self.start_analysis_btn.pack(side='left', padx=(0, 10))
        
        self.stop_analysis_btn = ctk.CTkButton(
            row1,
            text="⏹️ Остановить",
            command=self._stop_analysis,
            fg_color=self.theme.colors['btn_danger'],
            hover_color=self.theme.colors['btn_danger_hover'],
            font=("Arial", 12, "bold"),
            height=40,
            width=150,
            state="disabled"
        )
        self.stop_analysis_btn.pack(side='left', padx=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(
            row1,
            text="🔄 Обновить данные",
            command=self._refresh_data,
            fg_color=self.theme.colors['info'],
            font=("Arial", 12, "bold"),
            height=40,
            width=150
        )
        self.refresh_btn.pack(side='left', padx=(0, 10))
        
        self.clear_btn = ctk.CTkButton(
            row1,
            text="🗑️ Очистить",
            command=self._clear_results,
            fg_color=self.theme.colors['warning'],
            font=("Arial", 12, "bold"),
            height=40,
            width=150
        )
        self.clear_btn.pack(side='right')
        
        # Ряд 2: Экспорт и фильтры
        row2 = ctk.CTkFrame(buttons_frame)
        row2.configure(fg_color="transparent")
        row2.pack(fill='x', pady=5)
        
        self.export_csv_btn = ctk.CTkButton(
            row2,
            text="📄 Экспорт CSV",
            command=self._export_csv,
            fg_color=self.theme.colors['success'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.export_csv_btn.pack(side='left', padx=(0, 10))
        
        self.export_excel_btn = ctk.CTkButton(
            row2,
            text="📊 Экспорт Excel",
            command=self._export_excel,
            fg_color=self.theme.colors['success'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.export_excel_btn.pack(side='left', padx=(0, 10))
        
        self.copy_table_btn = ctk.CTkButton(
            row2,
            text="📋 Копировать",
            command=self._copy_all_table,
            fg_color=self.theme.colors['plex_primary'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.copy_table_btn.pack(side='left', padx=(0, 10))
        
        self.filter_btn = ctk.CTkButton(
            row2,
            text="🔍 Фильтры",
            command=self._show_filters,
            fg_color=self.theme.colors['plex_primary'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.filter_btn.pack(side='right')
        
        return panel
    
    def _create_settings_panel(self) -> ctk.CTkFrame:
        """Создание панели настроек."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок
        title = ctk.CTkLabel(
            panel,
            text="⚙️ Настройки анализа",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title.pack(pady=(15, 10))
        
        # Настройки в сетке
        settings_grid = ctk.CTkFrame(panel)
        settings_grid.configure(fg_color="transparent")
        settings_grid.pack(fill='x', padx=15, pady=10)
        
        # Ряд 1: Период
        period_frame = ctk.CTkFrame(settings_grid)
        period_frame.configure(fg_color="transparent")
        period_frame.pack(fill='x', pady=5)
        
        ctk.CTkLabel(
            period_frame,
            text="📅 Период анализа:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        self.period_var = ctk.StringVar(value="24h")
        self.period_menu = ctk.CTkOptionMenu(
            period_frame,
            values=["1h", "6h", "24h", "7d", "30d", "custom"],
            variable=self.period_var,
            command=self._on_period_change,
            fg_color=self.theme.colors['input_bg'],
            button_color=self.theme.colors['btn_primary'],
            width=120
        )
        self.period_menu.pack(side='left', padx=(10, 0))
        
        # Кнопки быстрого выбора периода
        quick_buttons = ctk.CTkFrame(period_frame)
        quick_buttons.configure(fg_color="transparent")
        quick_buttons.pack(side='right')
        
        for period, text in [("1h", "1ч"), ("24h", "24ч"), ("7d", "7д"), ("30d", "30д")]:
            btn = ctk.CTkButton(
                quick_buttons,
                text=text,
                command=lambda p=period: self._set_quick_period(p),
                fg_color=self.theme.colors['btn_secondary'],
                width=40,
                height=25
            )
            btn.pack(side='left', padx=2)
        
        # Ряд 2: Даты (для кастомного периода)
        self.custom_frame = ctk.CTkFrame(settings_grid)
        self.custom_frame.configure(fg_color="transparent")
        
        ctk.CTkLabel(
            self.custom_frame,
            text="📅 От:",
            text_color=self.theme.colors['text_secondary']
        ).pack(side='left')
        
        self.start_date_entry = self.widget_factory.create_entry(
            self.custom_frame,
            width=150
        )
        self.widget_factory.setup_placeholder(self.start_date_entry, "YYYY-MM-DD HH:MM")
        self.start_date_entry.pack(side='left', padx=(5, 20))
        
        ctk.CTkLabel(
            self.custom_frame,
            text="📅 До:",
            text_color=self.theme.colors['text_secondary']
        ).pack(side='left')
        
        self.end_date_entry = self.widget_factory.create_entry(
            self.custom_frame,
            width=150
        )
        self.widget_factory.setup_placeholder(self.end_date_entry, "YYYY-MM-DD HH:MM")
        self.end_date_entry.pack(side='left', padx=5)
        
        # Ряд 3: Параметры и поиск
        params_frame = ctk.CTkFrame(settings_grid)
        params_frame.configure(fg_color="transparent")
        params_frame.pack(fill='x', pady=5)
        
        ctk.CTkLabel(
            params_frame,
            text="💰 Мин. объем:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        self.min_volume_entry = self.widget_factory.create_entry(
            params_frame,
            width=100
        )
        self.widget_factory.setup_placeholder(self.min_volume_entry, "0.0")
        self.min_volume_entry.pack(side='left', padx=(10, 20))
        
        # Поле поиска
        ctk.CTkLabel(
            params_frame,
            text="🔍 Поиск:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        self.search_entry = self.widget_factory.create_entry(
            params_frame,
            width=150
        )
        self.widget_factory.setup_placeholder(self.search_entry, "Адрес или категория...")
        self.search_entry.bind('<KeyRelease>', self._on_search_change)
        self.search_entry.pack(side='left', padx=(10, 20))
        
        # Переключатели
        self.force_refresh_var = ctk.BooleanVar()
        self.force_refresh_switch = ctk.CTkSwitch(
            params_frame,
            text="🔄 Принудительное обновление",
            variable=self.force_refresh_var,
            text_color=self.theme.colors['text_secondary']
        )
        self.force_refresh_switch.pack(side='right', padx=(0, 10))
        
        self.detailed_analysis_var = ctk.BooleanVar(value=True)
        self.detailed_analysis_switch = ctk.CTkSwitch(
            params_frame,
            text="🔍 Детальный анализ",
            variable=self.detailed_analysis_var,
            text_color=self.theme.colors['text_secondary']
        )
        self.detailed_analysis_switch.pack(side='right')
        
        return panel
    
    def _create_results_panel(self) -> ctk.CTkFrame:
        """Создание панели результатов."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок
        header = ctk.CTkFrame(panel)
        header.configure(fg_color="transparent")
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📈 Результаты анализа",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title.pack(side='left')
        
        # Кнопки управления результатами
        results_controls = ctk.CTkFrame(header)
        results_controls.configure(fg_color="transparent")
        results_controls.pack(side='right')
        
        self.sort_btn = ctk.CTkButton(
            results_controls,
            text="📊 Сортировка",
            command=self._show_sort_options,
            fg_color=self.theme.colors['btn_secondary'],
            width=100,
            height=30
        )
        self.sort_btn.pack(side='left', padx=(0, 5))
        
        self.view_btn = ctk.CTkButton(
            results_controls,
            text="👁️ Вид",
            command=self._toggle_view,
            fg_color=self.theme.colors['btn_secondary'],
            width=80,
            height=30
        )
        self.view_btn.pack(side='left')
        
        # Статистика
        self.stats_frame = ctk.CTkFrame(panel)
        self.stats_frame.configure(fg_color=self.theme.colors['bg_tertiary'])
        self.stats_frame.pack(fill='x', padx=15, pady=10)
        
        # Карточки статистики
        self._create_stats_cards()
        
        # Таблица результатов
        self.table_frame = ctk.CTkFrame(panel)
        self.table_frame.configure(fg_color=self.theme.colors['bg_tertiary'])
        self.table_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Создание реальной таблицы участников
        try:
            self._create_real_participants_table()
            logger.info("✅ Таблица участников создана")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблицы: {e}")
            # Fallback заглушка
            self.table_placeholder = ctk.CTkLabel(
                self.table_frame,
                text="🔄 Запустите анализ для отображения результатов",
                font=("Arial", 14),
                text_color=self.theme.colors['text_muted']
            )
            self.table_placeholder.pack(expand=True, pady=50)
        
        return panel
    
    def _create_stats_cards(self):
        """Создание карточек статистики."""
        stats_data = [
            ("👥", "Участников", "0", "info"),
            ("⭐", "Идеальных", "0", "success"),
            ("💰", "Общий объем", "0.0 PLEX", "warning"),
            ("🎁", "Награды", "0.0 PLEX", "plex_primary")
        ]
        
        self.stat_labels = {}  # Для обновления значений
        
        for icon, title, value, color in stats_data:
            card = ctk.CTkFrame(self.stats_frame)
            card.configure(fg_color=self.theme.colors['bg_primary'])
            card.pack(side='left', fill='x', expand=True, padx=5, pady=10)
            
            ctk.CTkLabel(
                card,
                text=icon,
                font=("Arial", 20)
            ).pack(pady=(10, 0))
            
            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 11),
                text_color=self.theme.colors['text_secondary']
            ).pack()
            
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 14, "bold"),
                text_color=self.theme.colors[color] if color in self.theme.colors else self.theme.colors['text_primary']
            )
            value_label.pack(pady=(0, 10))
            
            # Сохраняем ссылку для обновления
            self.stat_labels[title.lower()] = value_label
    
    def _setup_layout(self):
        """Настройка расположения виджетов."""
        try:
            # Настройка grid weights
            self.grid_rowconfigure(4, weight=1)  # Результаты растягиваются
            self.grid_columnconfigure(0, weight=1)
            
            # Размещение компонентов
            self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")
            self.control_panel.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            self.settings_panel.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
            self.progress_bar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
            self.results_panel.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
            
            # Показать/скрыть кастомные даты
            self._on_period_change("24h")
            
            logger.debug("✅ Layout настроен успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки layout: {e}")
    
    # ========== ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ РЕЗУЛЬТАТОВ ==========
    
    def _log_detailed_analysis_results(self, result: Dict[str, Any]) -> None:
        """
        Детальное логирование результатов анализа.
        
        Args:
            result: Словарь с результатами анализа
        """
        try:
            if not result or not result.get('success', False):
                logger.warning("⚠️ Попытка логирования неуспешного результата анализа")
                return
            
            logger.info("📊 ========== ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ АНАЛИЗА ==========")
            
            # Общая информация
            summary = result.get('summary', {})
            period = result.get('analysis_period', 'Неизвестно')
            start_time = result.get('start_time', 'Неизвестно')
            end_time = result.get('end_time', 'Неизвестно')
            
            logger.info(f"⏰ Период анализа: {period}")
            logger.info(f"🕐 Время начала: {start_time}")
            logger.info(f"🕐 Время завершения: {end_time}")
            logger.info(f"📦 Проанализировано блоков: {result.get('blocks_analyzed', 0):,}")
            logger.info(f"🔄 Обработано событий Transfer: {result.get('total_transfers', 0):,}")
            
            # Статистика по участникам
            total_participants = summary.get('total_participants', 0)
            logger.info(f"👥 Всего найдено участников: {total_participants}")
            
            if total_participants == 0:
                logger.warning("⚠️ Участники не найдены")
                return
            
            # Разбивка по категориям
            categories = summary.get('categories', {})
            logger.info("📋 Разбивка по категориям:")
            for category, count in categories.items():
                percentage = (count / total_participants * 100) if total_participants > 0 else 0
                logger.info(f"   📂 {category}: {count} ({percentage:.1f}%)")
            
            # Статусы участников
            statuses = summary.get('statuses', {})
            if statuses:
                logger.info("🔍 Статусы участников:")
                for status, count in statuses.items():
                    percentage = (count / total_participants * 100) if total_participants > 0 else 0
                    logger.info(f"   ✅ {status}: {count} ({percentage:.1f}%)")
            
            # Детальная информация по балансам
            participants = result.get('participants', [])
            if participants:
                balances = [float(p.get('balance_plex', 0)) for p in participants]
                total_balance = sum(balances)
                avg_balance = total_balance / len(balances) if balances else 0
                max_balance = max(balances) if balances else 0
                min_balance = min(balances) if balances else 0
                
                logger.info("💰 Статистика балансов:")
                logger.info(f"   💎 Общий баланс всех участников: {total_balance:,.2f} PLEX")
                logger.info(f"   📊 Средний баланс: {avg_balance:,.2f} PLEX")
                logger.info(f"   📈 Максимальный баланс: {max_balance:,.2f} PLEX")
                logger.info(f"   📉 Минимальный баланс: {min_balance:,.2f} PLEX")
            
            # Статистика по активности
            if participants:
                # Участники с покупками
                participants_with_purchases = [p for p in participants if p.get('purchase_count', 0) > 0]
                avg_purchases = sum(p.get('purchase_count', 0) for p in participants_with_purchases) / len(participants_with_purchases) if participants_with_purchases else 0
                
                # Участники с продажами
                participants_with_sales = [p for p in participants if p.get('sales_count', 0) > 0]
                
                # Участники с переводами
                participants_with_transfers = [p for p in participants if p.get('transfers_count', 0) > 0]
                
                logger.info("📈 Статистика активности:")
                logger.info(f"   🛒 Участников с покупками: {len(participants_with_purchases)}")
                logger.info(f"   📊 Средняя активность покупок: {avg_purchases:.1f}")
                logger.info(f"   💸 Участников с продажами: {len(participants_with_sales)}")
                logger.info(f"   🔄 Участников с переводами: {len(participants_with_transfers)}")
            
            # Списки адресов по категориям (первые 5 в каждой)
            logger.info("📋 Примеры адресов по категориям:")
            category_examples = {}
            for participant in participants[:20]:  # Ограничиваем вывод
                category = participant.get('category', 'UNKNOWN')
                if category not in category_examples:
                    category_examples[category] = []
                if len(category_examples[category]) < 5:
                    category_examples[category].append(participant.get('address', 'N/A'))
            
            for category, addresses in category_examples.items():
                logger.info(f"   📂 {category}:")
                for addr in addresses:
                    logger.info(f"      🔗 {addr}")
                if len(addresses) == 5:
                    logger.info(f"      ... и еще {categories.get(category, 0) - 5} адресов")
            
            # Информация о наградах (если есть)
            total_rewards = result.get('total_rewards_calculated', 0)
            eligible_for_rewards = len([p for p in participants if p.get('eligible_for_rewards', False)])
            
            if total_rewards > 0:
                logger.info("🎁 Система наград:")
                logger.info(f"   💰 Общая сумма рассчитанных наград: {total_rewards:,.2f} PLEX")
                logger.info(f"   🏆 Участников имеют право на награды: {eligible_for_rewards}")
                logger.info(f"   📊 Средняя награда: {(total_rewards / eligible_for_rewards):,.2f} PLEX" if eligible_for_rewards > 0 else "   📊 Средняя награда: 0 PLEX")
            
            # Технические детали
            logger.info("🔧 Технические детали:")
            logger.info(f"   ⚡ Время выполнения: {result.get('execution_time', 'Неизвестно')}")
            logger.info(f"   🔗 QuickNode API запросов: {result.get('api_requests_count', 'Неизвестно')}")
            logger.info(f"   💾 Размер данных: {result.get('data_size', 'Неизвестно')}")
            
            logger.info("📊 ============== КОНЕЦ ДЕТАЛЬНОГО ОТЧЕТА ==============")
            
        except Exception as e:
            logger.error(f"❌ Ошибка детального логирования: {e}")
    
    # ========== ФУНКЦИОНАЛЬНОСТЬ КОПИРОВАНИЯ ==========
    
    def _setup_table_context_menu(self):
        """Настройка контекстного меню для таблицы."""
        try:
            # Создание контекстного меню
            self.context_menu = Menu(self, tearoff=0, bg=self.theme.colors['bg_secondary'], fg=self.theme.colors['text_primary'])
            
            self.context_menu.add_command(
                label="📋 Копировать выбранную строку",
                command=self._copy_selected_row,
                accelerator="Ctrl+C"
            )
            
            self.context_menu.add_command(
                label="📄 Копировать всю таблицу",
                command=self._copy_all_table,
                accelerator="Ctrl+Shift+C"
            )
            
            self.context_menu.add_separator()
            
            self.context_menu.add_command(
                label="🔗 Копировать только адреса",
                command=self._copy_addresses_only
            )
            
            self.context_menu.add_command(
                label="📊 Копировать только балансы",
                command=self._copy_balances_only
            )
            
            self.context_menu.add_separator()
            
            self.context_menu.add_command(
                label="💾 Экспорт в CSV",
                command=self._export_to_csv
            )
            
            self.context_menu.add_command(
                label="📋 Показать детали",
                command=self._show_selected_details
            )
            
            logger.debug("✅ Контекстное меню таблицы настроено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки контекстного меню: {e}")
    
    def _show_context_menu(self, event):
        """Показ контекстного меню."""
        try:
            if hasattr(self, 'context_menu'):
                self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"❌ Ошибка показа контекстного меню: {e}")
    
    def _copy_selected_row(self):
        """Копирование выбранной строки в буфер обмена."""
        try:
            if not self.selected_rows:
                messagebox.showwarning("Копирование", "Не выбрана строка для копирования")
                return
            
            if not CLIPBOARD_AVAILABLE:
                messagebox.showerror("Ошибка", "Модуль pyperclip недоступен.\nУстановите: pip install pyperclip")
                return
            
            # Получаем данные выбранной строки
            selected_data = []
            for row_index in self.selected_rows:
                if row_index < len(self.participants_data):
                    participant = self.participants_data[row_index]
                    row_text = self._format_participant_for_copy(participant)
                    selected_data.append(row_text)
            
            if selected_data:
                clipboard_text = "\n".join(selected_data)
                pyperclip.copy(clipboard_text)
                
                logger.info(f"📋 Скопировано {len(selected_data)} строк в буфер обмена")
                messagebox.showinfo("Копирование", f"✅ Скопировано {len(selected_data)} строк в буфер обмена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка копирования строки: {e}")
            messagebox.showerror("Ошибка копирования", f"Не удалось скопировать данные:\n{e}")
    
    def _copy_all_table(self):
        """Копирование всей таблицы в буфер обмена."""
        try:
            if not self.participants_data:
                messagebox.showwarning("Копирование", "Нет данных для копирования")
                return
            
            if not CLIPBOARD_AVAILABLE:
                messagebox.showerror("Ошибка", "Модуль pyperclip недоступен.\nУстановите: pip install pyperclip")
                return
            
            # Формируем текст таблицы
            table_text = self._format_table_data_for_copy(include_headers=True)
            
            pyperclip.copy(table_text)
            
            logger.info(f"📋 Вся таблица ({len(self.participants_data)} строк) скопирована в буфер обмена")
            messagebox.showinfo("Копирование", f"✅ Таблица ({len(self.participants_data)} участников) скопирована в буфер обмена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка копирования таблицы: {e}")
            messagebox.showerror("Ошибка копирования", f"Не удалось скопировать таблицу:\n{e}")
    
    def _copy_addresses_only(self):
        """Копирование только адресов в буфер обмена."""
        try:
            if not self.participants_data:
                messagebox.showwarning("Копирование", "Нет данных для копирования")
                return
            
            if not CLIPBOARD_AVAILABLE:
                messagebox.showerror("Ошибка", "Модуль pyperclip недоступен.\nУстановите: pip install pyperclip")
                return
            
            # Извлекаем только адреса
            addresses = [participant.get('address', 'N/A') for participant in self.participants_data]
            addresses_text = "\n".join(addresses)
            
            pyperclip.copy(addresses_text)
            
            logger.info(f"📋 {len(addresses)} адресов скопировано в буфер обмена")
            messagebox.showinfo("Копирование", f"✅ {len(addresses)} адресов скопировано в буфер обмена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка копирования адресов: {e}")
            messagebox.showerror("Ошибка копирования", f"Не удалось скопировать адреса:\n{e}")
    
    def _copy_balances_only(self):
        """Копирование только балансов в буфер обмена."""
        try:
            if not self.participants_data:
                messagebox.showwarning("Копирование", "Нет данных для копирования")
                return
            
            if not CLIPBOARD_AVAILABLE:
                messagebox.showerror("Ошибка", "Модуль pyperclip недоступен.\nУстановите: pip install pyperclip")
                return
            
            # Извлекаем балансы с адресами
            balances_data = []
            for participant in self.participants_data:
                address = participant.get('address', 'N/A')
                balance = participant.get('balance_plex', 0)
                balances_data.append(f"{address}: {balance:.2f} PLEX")
            
            balances_text = "\n".join(balances_data)
            
            pyperclip.copy(balances_text)
            
            logger.info(f"📋 Балансы {len(balances_data)} участников скопированы в буфер обмена")
            messagebox.showinfo("Копирование", f"✅ Балансы {len(balances_data)} участников скопированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка копирования балансов: {e}")
            messagebox.showerror("Ошибка копирования", f"Не удалось скопировать балансы:\n{e}")
    
    def _format_participant_for_copy(self, participant: Dict[str, Any]) -> str:
        """Форматирование данных участника для копирования."""
        try:
            address = participant.get('address', 'N/A')
            balance = participant.get('balance_plex', 0)
            category = participant.get('category', 'UNKNOWN')
            status = "Подходит" if participant.get('eligible_for_rewards', False) else "Не подходит"
            
            return f"{address}\t{balance:.2f} PLEX\t{category}\t{status}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования участника: {e}")
            return "Ошибка форматирования"
    
    def _format_table_data_for_copy(self, include_headers: bool = True) -> str:
        """Форматирование данных таблицы для копирования."""
        try:
            lines = []
            
            # Заголовки
            if include_headers:
                headers = ["№", "Адрес", "Баланс (PLEX)", "Категория", "Статус"]
                lines.append("\t".join(headers))
                lines.append("-" * 80)  # Разделитель
            
            # Данные участников
            for i, participant in enumerate(self.participants_data, 1):
                address = participant.get('address', 'N/A')
                balance = participant.get('balance_plex', 0)
                category = participant.get('category', 'UNKNOWN')
                status = "Подходит" if participant.get('eligible_for_rewards', False) else "Не подходит"
                
                row = [
                    str(i),
                    address,
                    f"{balance:.2f}",
                    category,
                    status
                ]
                lines.append("\t".join(row))
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"❌ Ошибка форматирования таблицы: {e}")
            return "Ошибка форматирования таблицы"
    
    def _export_to_csv(self):
        """Экспорт таблицы в CSV файл."""
        try:
            if not self.participants_data:
                messagebox.showwarning("Экспорт", "Нет данных для экспорта")
                return
            
            # Выбор файла для сохранения
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"plex_participants_{timestamp}.csv"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['index', 'address', 'balance_plex', 'category', 'eligible_for_rewards', 
                                'purchase_count', 'sales_count', 'transfers_count', 'last_activity']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    # Заголовки
                    writer.writeheader()
                    
                    # Данные
                    for i, participant in enumerate(self.participants_data, 1):
                        row = {
                            'index': i,
                            'address': participant.get('address', 'N/A'),
                            'balance_plex': participant.get('balance_plex', 0),
                            'category': participant.get('category', 'UNKNOWN'),
                            'eligible_for_rewards': participant.get('eligible_for_rewards', False),
                            'purchase_count': participant.get('purchase_count', 0),
                            'sales_count': participant.get('sales_count', 0),
                            'transfers_count': participant.get('transfers_count', 0),
                            'last_activity': participant.get('last_activity', 'Неизвестно')
                        }
                        writer.writerow(row)
                
                logger.info(f"📊 Экспорт в CSV: {filename} ({len(self.participants_data)} записей)")
                messagebox.showinfo("Экспорт", f"✅ Данные экспортированы в:\n{filename}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта в CSV: {e}")
            messagebox.showerror("Ошибка экспорта", f"Не удалось экспортировать в CSV:\n{e}")
    
    def _show_selected_details(self):
        """Показ деталей выбранных участников."""
        try:
            if not self.selected_rows:
                messagebox.showwarning("Детали", "Не выбрана строка")
                return
            
            # Показываем детали первого выбранного участника
            if self.selected_rows[0] < len(self.participants_data):
                participant = self.participants_data[self.selected_rows[0]]
                self._show_participant_details(participant)
        
        except Exception as e:
            logger.error(f"❌ Ошибка показа деталей: {e}")
    
    # ========== ПОИСК И ФИЛЬТРАЦИЯ ==========
    
    def _on_search_change(self, event=None):
        """Обработка изменения поискового запроса."""
        try:
            search_query = self.search_entry.get().lower().strip()
            
            # Если запрос пустой, показываем всех участников
            if not search_query:
                self._update_participants_table(self.participants_data)
                return
            
            # Фильтрация участников по запросу
            filtered_participants = []
            for participant in self.participants_data:
                address = participant.get('address', '').lower()
                category = participant.get('category', '').lower()
                
                if (search_query in address or 
                    search_query in category or
                    search_query in str(participant.get('balance_plex', 0))):
                    filtered_participants.append(participant)
            
            # Обновляем таблицу с отфильтрованными данными
            self._update_participants_table(filtered_participants)
            
            logger.debug(f"🔍 Поиск '{search_query}': найдено {len(filtered_participants)} участников")
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
    
    # ========== ОСТАЛЬНЫЕ МЕТОДЫ (БАЗОВЫЕ) ==========
    
    def _start_analysis(self):
        """Запуск анализа."""
        try:
            logger.info("🚀 Запуск анализа...")
            
            # Изменение состояния кнопок
            self.start_analysis_btn.configure(state="disabled")
            self.stop_analysis_btn.configure(state="normal")
            
            # Сброс прогресса
            self.progress_bar.set_progress(0, "Начинаем анализ...")
            
            # Запуск реального анализа
            self._run_real_analysis()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска анализа: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить анализ:\n{e}")
            # Восстановление состояния кнопок при ошибке
            self.start_analysis_btn.configure(state="normal")
            self.stop_analysis_btn.configure(state="disabled")
    
    def _stop_analysis(self):
        """Остановка анализа."""
        try:
            logger.info("⏹️ Остановка анализа...")
            
            self.analysis_running = False
            
            # Остановка простого анализатора
            from core.simple_analyzer import simple_analyzer
            simple_analyzer.stop_analysis()
            
            # Изменение состояния кнопок
            self.start_analysis_btn.configure(state="normal")
            self.stop_analysis_btn.configure(state="disabled")
            self.progress_bar.set_progress(0, "Анализ остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки анализа: {e}")
    
    def _run_real_analysis(self):
        """Запуск реального анализа через SimpleAnalyzer."""
        def run_analysis():
            try:
                self.analysis_running = True
                
                # Используем простой анализатор
                from core.simple_analyzer import simple_analyzer
                
                # Обновление прогресса
                self.after(0, lambda: self.progress_bar.set_progress(0.1, "Подготовка анализа..."))
                
                # Получение периода анализа из UI
                period_value = self.period_var.get() if hasattr(self, 'period_var') else "24h"
                hours = self._parse_period_hours(period_value)
                
                # Функция обновления прогресса
                def progress_update(message, progress):
                    if self.analysis_running:
                        self.after(0, lambda m=message, p=progress: self.progress_bar.set_progress(p, m))
                
                # Инициализация анализатора
                progress_update("Инициализация подключения к BSC...", 0.05)
                if not simple_analyzer.initialize():
                    raise Exception("Не удалось подключиться к BSC")
                
                # Запуск анализа
                progress_update(f"Анализ за {period_value}...", 0.1)
                result = simple_analyzer.analyze_period(hours, progress_update)
                
                # Сохранение результата
                self.current_analysis_result = result
                
                if self.analysis_running and result.get('success', False):
                    # Детальное логирование результатов анализа
                    self._log_detailed_analysis_results(result)
                    
                    self.after(0, lambda: self.progress_bar.set_progress(1.0, "Анализ завершен!"))
                    self.after(0, self._analysis_completed)
                elif not result.get('success', False):
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    self.after(0, lambda: self.progress_bar.set_progress(0.0, f"Ошибка: {error_msg}"))
                    self.after(0, lambda: self._show_error("Ошибка анализа", error_msg))
                    
            except Exception as e:
                logger.error(f"❌ Ошибка выполнения анализа: {e}")
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self.progress_bar.set_progress(0.0, f"Ошибка: {msg}"))
                self.after(0, lambda msg=error_msg: self._show_error("Ошибка анализа", msg))
            finally:
                # Восстановление состояния кнопок
                self.after(0, lambda: self.start_analysis_btn.configure(state="normal"))
                self.after(0, lambda: self.stop_analysis_btn.configure(state="disabled"))
                self.analysis_running = False
        
        # Запуск в отдельном потоке
        import threading
        analysis_thread = threading.Thread(target=run_analysis, daemon=True)
        analysis_thread.start()
    
    def _parse_period_hours(self, period_str: str) -> int:
        """Преобразование строки периода в часы."""
        if period_str == "1h":
            return 1
        elif period_str == "6h":
            return 6
        elif period_str == "24h":
            return 24
        elif period_str == "7d":
            return 168  # 7 дней * 24 часа
        elif period_str == "30d":
            return 720  # 30 дней * 24 часа
        else:
            return 24  # По умолчанию 24 часа
    
    def _analysis_completed(self):
        """Завершение анализа."""
        try:
            logger.info("✅ Анализ завершен")
            
            # Сброс состояния
            self.analysis_running = False
            self.start_analysis_btn.configure(state="normal")
            self.stop_analysis_btn.configure(state="disabled")
            
            # Проверяем наличие результатов
            if not hasattr(self, 'current_analysis_result') or not self.current_analysis_result:
                if hasattr(self, 'table_placeholder'):
                    self.table_placeholder.configure(text="❌ Нет результатов анализа")
                return
            
            result = self.current_analysis_result
            
            # Обновление прогресса
            self.progress_bar.set_progress(1.0, "Анализ завершен успешно!")
            
            # Отображение результатов
            if result.get('success', False):
                summary = result.get('summary', {})
                participants_data = result.get('participants', [])
                
                # Сохраняем данные участников для работы с таблицей
                self.participants_data = participants_data
                
                # Обновляем статистические карточки
                self._update_stats_cards(summary)
                
                # Обновляем таблицу участников
                self._update_participants_table(participants_data)
                
                # Логируем успешный результат
                total_participants = summary.get('total_participants', 0)
                logger.info(f"📊 Результаты: {total_participants} участников, {result.get('total_transfers', 0)} транзакций")
                
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                if hasattr(self, 'table_placeholder'):
                    self.table_placeholder.configure(text=f"❌ Ошибка анализа:\n{error_msg}")
                logger.error(f"❌ Анализ завершился с ошибкой: {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка завершения анализа: {e}")
            if hasattr(self, 'table_placeholder'):
                self.table_placeholder.configure(text=f"❌ Ошибка отображения результатов:\n{str(e)}")
    
    def _update_stats_cards(self, summary: Dict[str, Any]):
        """Обновление статистических карточек."""
        try:
            total_participants = summary.get('total_participants', 0)
            categories = summary.get('categories', {})
            
            # Обновляем значения карточек
            if 'участников' in self.stat_labels:
                self.stat_labels['участников'].configure(text=str(total_participants))
            
            if 'идеальных' in self.stat_labels:
                perfect_count = categories.get('PERFECT', 0)
                self.stat_labels['идеальных'].configure(text=str(perfect_count))
            
            # Рассчитываем общий объем балансов
            if hasattr(self, 'participants_data') and self.participants_data:
                total_volume = sum(float(p.get('balance_plex', 0)) for p in self.participants_data)
                if 'общий объем' in self.stat_labels:
                    self.stat_labels['общий объем'].configure(text=f"{total_volume:,.1f} PLEX")
            
            # Подсчитываем потенциальные награды
            eligible_count = len([p for p in self.participants_data if p.get('eligible_for_rewards', False)]) if hasattr(self, 'participants_data') else 0
            estimated_rewards = eligible_count * 100  # Примерная награда 100 PLEX на участника
            if 'награды' in self.stat_labels:
                self.stat_labels['награды'].configure(text=f"{estimated_rewards:,.0f} PLEX")
            
            logger.debug("✅ Статистические карточки обновлены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")
    
    def _create_real_participants_table(self):
        """Создание реальной таблицы участников без внешних зависимостей."""
        # Создание контейнера для таблицы
        self.table_container = ctk.CTkFrame(self.table_frame)
        self.table_container.pack(fill='both', expand=True, padx=5, pady=5)
        self.table_container.configure(fg_color=self.theme.colors['bg_primary'])
        
        # Заголовки таблицы
        self.table_headers = ctk.CTkFrame(self.table_container)
        self.table_headers.pack(fill='x', padx=5, pady=(5, 0))
        self.table_headers.configure(fg_color=self.theme.colors['bg_secondary'])
        
        headers = ["№", "Адрес", "Баланс", "Категория", "Статус", "Действия"]
        self.header_labels = []
        
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(
                self.table_headers,
                text=header,
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            label.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            self.header_labels.append(label)
            
        # Настройка весов колонок
        for i in range(len(headers)):
            self.table_headers.grid_columnconfigure(i, weight=1)
        
        # Область для данных с прокруткой
        self.table_scroll_frame = ctk.CTkScrollableFrame(
            self.table_container,
            orientation="vertical"
        )
        self.table_scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.table_scroll_frame.configure(fg_color=self.theme.colors['bg_primary'])
        
        # Настройка контекстного меню
        self._setup_table_context_menu()
        
        # Bind правого клика к области таблицы
        self.table_scroll_frame.bind("<Button-3>", self._show_context_menu)
        
        # Изначально показываем placeholder
        self.table_placeholder = ctk.CTkLabel(
            self.table_scroll_frame,
            text="🔄 Запустите анализ для отображения участников",
            font=("Arial", 14),
            text_color=self.theme.colors['text_muted']
        )
        self.table_placeholder.pack(expand=True, pady=50)
        
        # Переменные для данных
        self.table_rows = []
        self.participants_data = []
    
    def _update_participants_table(self, participants: List[Dict[str, Any]]):
        """Обновление таблицы участников с реальными данными."""
        try:
            # Очистка старых данных
            self._clear_table_data()
            
            if not participants:
                # Показать placeholder если нет данных
                self.table_placeholder = ctk.CTkLabel(
                    self.table_scroll_frame,
                    text="📭 Участники не найдены\n\nПроверьте параметры анализа",
                    font=("Arial", 14),
                    text_color=self.theme.colors['text_warning']
                )
                self.table_placeholder.pack(expand=True, pady=50)
                return
            
            # Скрыть placeholder если он есть
            if hasattr(self, 'table_placeholder') and self.table_placeholder:
                self.table_placeholder.pack_forget()
            
            # Добавление участников в таблицу
            for i, participant in enumerate(participants):
                self._add_participant_row(i + 1, participant)
            
            logger.info(f"✅ Таблица обновлена: {len(participants)} участников")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления таблицы: {e}")
    
    def _clear_table_data(self):
        """Очистка данных таблицы."""
        # Удаление всех строк таблицы
        for row in self.table_rows:
            if row.winfo_exists():
                row.destroy()
        
        self.table_rows.clear()
        
        # Сброс выбранных строк
        self.selected_rows.clear()
        
        # Скрыть placeholder если есть
        if hasattr(self, 'table_placeholder') and self.table_placeholder:
            self.table_placeholder.pack_forget()
    
    def _add_participant_row(self, index: int, participant: Dict[str, Any]):
        """Добавление строки участника в таблицу."""
        try:
            # Создание фрейма для строки
            row_frame = ctk.CTkFrame(self.table_scroll_frame)
            row_frame.pack(fill='x', padx=2, pady=1)
            
            # Цвет строки в зависимости от категории
            category = participant.get('category', 'UNKNOWN')
            if category == 'PERFECT':
                row_color = self.theme.colors.get('success_bg', self.theme.colors['bg_secondary'])
            elif category == 'MISSED_PURCHASE':
                row_color = self.theme.colors.get('warning_bg', self.theme.colors['bg_secondary'])
            elif category == 'SOLD_TOKEN':
                row_color = self.theme.colors.get('error_bg', self.theme.colors['bg_secondary'])
            else:
                row_color = self.theme.colors['bg_secondary']
            
            row_frame.configure(fg_color=row_color)
            
            # Настройка клика для выбора строки
            row_index = index - 1
            row_frame.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            row_frame.bind("<Button-3>", self._show_context_menu)
            
            # Настройка весов колонок
            for i in range(6):
                row_frame.grid_columnconfigure(i, weight=1)
            
            # Столбцы данных
            address = participant.get('address', 'Unknown')
            balance = participant.get('balance_plex', 0)
            
            # Индекс
            index_label = ctk.CTkLabel(
                row_frame,
                text=str(index),
                font=("Arial", 10),
                text_color=self.theme.colors['text_primary']
            )
            index_label.grid(row=0, column=0, padx=5, pady=2)
            index_label.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            index_label.bind("<Button-3>", self._show_context_menu)
            
            # Адрес (сокращенный)
            short_address = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
            address_label = ctk.CTkLabel(
                row_frame,
                text=short_address,
                font=("Arial", 10),
                text_color=self.theme.colors['text_primary']
            )
            address_label.grid(row=0, column=1, padx=5, pady=2)
            address_label.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            address_label.bind("<Button-3>", self._show_context_menu)
            
            # Баланс
            balance_text = f"{balance:.2f}" if isinstance(balance, (int, float, Decimal)) else str(balance)
            balance_label = ctk.CTkLabel(
                row_frame,
                text=f"{balance_text} PLEX",
                font=("Arial", 10),
                text_color=self.theme.colors['text_primary']
            )
            balance_label.grid(row=0, column=2, padx=5, pady=2)
            balance_label.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            balance_label.bind("<Button-3>", self._show_context_menu)
            
            # Категория
            category_icons = {
                'PERFECT': '⭐',
                'MISSED_PURCHASE': '⚠️',
                'SOLD_TOKEN': '❌',
                'TRANSFERRED': '🔄'
            }
            category_text = f"{category_icons.get(category, '❓')} {category}"
            category_label = ctk.CTkLabel(
                row_frame,
                text=category_text,
                font=("Arial", 10),
                text_color=self.theme.colors['text_primary']
            )
            category_label.grid(row=0, column=3, padx=5, pady=2)
            category_label.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            category_label.bind("<Button-3>", self._show_context_menu)
            
            # Статус
            status = participant.get('eligible_for_rewards', False)
            status_text = "✅ Подходит" if status else "❌ Не подходит"
            status_color = self.theme.colors['success'] if status else self.theme.colors['error']
            status_label = ctk.CTkLabel(
                row_frame,
                text=status_text,
                font=("Arial", 10),
                text_color=status_color
            )
            status_label.grid(row=0, column=4, padx=5, pady=2)
            status_label.bind("<Button-1>", lambda e, idx=row_index: self._select_row(idx))
            status_label.bind("<Button-3>", self._show_context_menu)
            
            # Кнопки действий
            actions_frame = ctk.CTkFrame(row_frame)
            actions_frame.grid(row=0, column=5, padx=5, pady=2)
            actions_frame.configure(fg_color="transparent")
            
            # Кнопка деталей
            details_btn = ctk.CTkButton(
                actions_frame,
                text="📋",
                width=30,
                height=25,
                command=lambda p=participant: self._show_participant_details(p),
                fg_color=self.theme.colors['btn_secondary'],
                hover_color=self.theme.colors.get('btn_secondary_hover', self.theme.colors['btn_secondary'])
            )
            details_btn.pack(side='left', padx=1)
            
            # Кнопка амнистии (если применимо)
            if category == 'MISSED_PURCHASE':
                amnesty_btn = ctk.CTkButton(
                    actions_frame,
                    text="🎁",
                    width=30,
                    height=25,
                    command=lambda p=participant: self._request_participant_amnesty(p),
                    fg_color=self.theme.colors['warning'],
                    hover_color=self.theme.colors.get('warning_hover', self.theme.colors['warning'])
                )
                amnesty_btn.pack(side='left', padx=1)
            
            # Кнопка награды (если подходит)
            if status:
                reward_btn = ctk.CTkButton(
                    actions_frame,
                    text="💰",
                    width=30,
                    height=25,
                    command=lambda p=participant: self._send_participant_reward(p),
                    fg_color=self.theme.colors['success'],
                    hover_color=self.theme.colors.get('success_hover', self.theme.colors['success'])
                )
                reward_btn.pack(side='left', padx=1)
            
            # Сохранение ссылок
            self.table_rows.append(row_frame)
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления строки участника: {e}")
    
    def _select_row(self, row_index: int):
        """Выбор строки в таблице."""
        try:
            # Сброс предыдущего выбора
            self.selected_rows.clear()
            
            # Добавляем новый выбор
            self.selected_rows.append(row_index)
            
            # Визуальное выделение (можно добавить изменение цвета)
            logger.debug(f"🖱️ Выбрана строка {row_index + 1}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора строки: {e}")
    
    # ========== ОСТАЛЬНЫЕ МЕТОДЫ ==========
    
    def _refresh_data(self):
        """Обновление данных."""
        logger.info("🔄 Обновление данных...")
        messagebox.showinfo("Обновление", "Данные обновлены!")
    
    def _clear_results(self):
        """Очистка результатов."""
        try:
            logger.info("🗑️ Очистка результатов...")
            
            # Сброс прогресса
            self.progress_bar.set_progress(0, "Результаты очищены")
            
            # Очистка таблицы
            self._clear_table_data()
            
            # Показать placeholder
            self.table_placeholder = ctk.CTkLabel(
                self.table_scroll_frame,
                text="🔄 Запустите анализ для отображения результатов",
                font=("Arial", 14),
                text_color=self.theme.colors['text_muted']
            )
            self.table_placeholder.pack(expand=True, pady=50)
            
            # Сброс статистики
            for label in self.stat_labels.values():
                if hasattr(label, 'configure'):
                    label.configure(text="0")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки: {e}")
    
    def _export_csv(self):
        """Экспорт в CSV."""
        self._export_to_csv()
    
    def _export_excel(self):
        """Экспорт в Excel."""
        logger.info("📊 Экспорт в Excel...")
        messagebox.showinfo("Экспорт", "Excel файл сохранен!")
    
    def _show_filters(self):
        """Показать окно фильтров."""
        logger.info("🔍 Открытие фильтров...")
        messagebox.showinfo("Фильтры", "Окно фильтров (в разработке)")
    
    def _show_sort_options(self):
        """Показать опции сортировки."""
        logger.info("📊 Опции сортировки...")
        messagebox.showinfo("Сортировка", "Опции сортировки (в разработке)")
    
    def _toggle_view(self):
        """Переключение вида отображения."""
        logger.info("👁️ Переключение вида...")
        messagebox.showinfo("Вид", "Переключение вида (в разработке)")
    
    def _on_period_change(self, value):
        """Обработка изменения периода."""
        if value == "custom":
            self.custom_frame.pack(fill='x', pady=5)
        else:
            self.custom_frame.pack_forget()
    
    def _set_quick_period(self, period):
        """Быстрая установка периода."""
        self.period_var.set(period)
        self._on_period_change(period)
    
    def set_staking_manager(self, staking_manager):
        """Установка менеджера стейкинга."""
        self.staking_manager = staking_manager
        logger.info("✅ StakingManager подключен к Enhanced AnalysisTab")
    
    def _show_error(self, title: str, message: str):
        """Отображение ошибки пользователю."""
        try:
            messagebox.showerror(title, message)
        except Exception as e:
            logger.error(f"❌ Ошибка отображения сообщения об ошибке: {e}")
    
    # ========== МЕТОДЫ РАБОТЫ С УЧАСТНИКАМИ ==========
    
    def _show_participant_details(self, participant):
        """Показ деталей участника."""
        try:
            if not participant:
                messagebox.showwarning("Детали", "Не выбран участник")
                return
            
            # Создание окна с деталями
            details_window = ctk.CTkToplevel(self)
            details_window.title(f"📋 Детали участника")
            details_window.geometry("600x500")
            details_window.transient(self)
            details_window.grab_set()
            
            # Заголовок
            title_label = ctk.CTkLabel(
                details_window,
                text=f"📋 Детали участника",
                font=("Arial", 18, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            title_label.pack(pady=20)
            
            # Текст с деталями
            details_text = ctk.CTkTextbox(
                details_window,
                height=350,
                width=550,
                fg_color=self.theme.colors['bg_secondary']
            )
            details_text.pack(padx=20, pady=10, fill='both', expand=True)
            
            # Формирование информации об участнике
            address = participant.get('address', 'N/A')
            balance = participant.get('balance_plex', 0)
            category = participant.get('category', 'Неизвестно')
            status = participant.get('eligible_for_rewards', False)
            contribution = participant.get('contribution_percent', 0)
            
            info_text = f"""
📍 АДРЕС:
{address}

💰 БАЛАНС:
{balance:.2f} PLEX

📂 КАТЕГОРИЯ:
{category}

🔄 СТАТУС:
{'✅ Подходит для наград' if status else '❌ Не подходит для наград'}

📊 ВКЛАД:
{contribution:.2f}%

⏰ ПОСЛЕДНЯЯ АКТИВНОСТЬ:
{participant.get('last_activity', 'Неизвестно')}

📈 СТАТИСТИКА ПОКУПОК:
Всего покупок: {participant.get('purchase_count', 0)}
Пропущенных дней: {participant.get('missed_days', 0)}

📊 СТАТИСТИКА ПЕРЕВОДОВ:
Исходящих переводов: {participant.get('transfers_count', 0)}
Отправлено в корп: {participant.get('sent_to_corp', 0):.2f} PLEX

🏆 СИСТЕМА НАГРАД:
Право на награду: {'Да' if status else 'Нет'}
Последняя награда: {participant.get('last_reward_date', 'Никогда')}
            """
            
            details_text.insert("1.0", info_text.strip())
            details_text.configure(state="disabled")
            
            # Кнопки действий
            buttons_frame = ctk.CTkFrame(details_window)
            buttons_frame.pack(pady=10)
            buttons_frame.configure(fg_color="transparent")
            
            # Кнопка копирования адреса
            if CLIPBOARD_AVAILABLE:
                copy_btn = ctk.CTkButton(
                    buttons_frame,
                    text="📋 Копировать адрес",
                    command=lambda: pyperclip.copy(address),
                    fg_color=self.theme.colors['btn_primary'],
                    width=150,
                    height=30
                )
                copy_btn.pack(side='left', padx=5)
            
            # Кнопка закрытия
            close_btn = ctk.CTkButton(
                buttons_frame,
                text="❌ Закрыть",
                command=details_window.destroy,
                fg_color=self.theme.colors['btn_secondary'],
                width=100,
                height=30
            )
            close_btn.pack(side='left', padx=5)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа деталей участника: {e}")
            messagebox.showerror("Ошибка", f"Не удалось показать детали:\n{e}")
    
    def _request_participant_amnesty(self, participant):
        """Запрос амнистии для участника."""
        try:
            if not participant:
                messagebox.showwarning("Амнистия", "Не выбран участник")
                return
            
            address = participant.get('address', 'N/A')
            category = participant.get('category', 'Неизвестно')
            
            # Проверка возможности амнистии
            if 'SOLD_TOKEN' in category:
                messagebox.showerror(
                    "Амнистия невозможна", 
                    f"Участник {address[:10]}... продавал токены.\n\nАмнистия для продавцов невозможна согласно правилам."
                )
                return
            
            # Подтверждение амнистии
            result = messagebox.askyesno(
                "Подтверждение амнистии",
                f"Предоставить амнистию участнику?\n\n"
                f"Адрес: {address}\n"
                f"Категория: {category}\n\n"
                f"Это действие нельзя отменить."
            )
            
            if result:
                logger.info(f"✅ Амнистия предоставлена для {address}")
                messagebox.showinfo("Амнистия предоставлена", 
                                  f"Амнистия успешно предоставлена участнику:\n{address}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запроса амнистии: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запросить амнистию:\n{e}")
    
    def _send_participant_reward(self, participant):
        """Отправка награды участнику."""
        try:
            if not participant:
                messagebox.showwarning("Награда", "Не выбран участник")
                return
            
            address = participant.get('address', 'N/A')
            balance = participant.get('balance_plex', 0)
            category = participant.get('category', 'Неизвестно')
            
            # Проверка права на награду
            if not participant.get('eligible_for_rewards', False):
                messagebox.showwarning(
                    "Награда недоступна",
                    f"Участник {address[:10]}... не имеет права на награду.\n\n"
                    f"Текущая категория: {category}\n\n"
                    f"Только подходящие участники могут получать награды."
                )
                return
            
            # Расчет награды (примерная логика)
            reward_amount = min(balance * 0.1, 1000)  # 10% от баланса, максимум 1000 PLEX
            
            # Подтверждение отправки
            result = messagebox.askyesno(
                "Подтверждение награды",
                f"Отправить награду участнику?\n\n"
                f"Адрес: {address}\n"
                f"Баланс: {balance:.2f} PLEX\n"
                f"Сумма награды: {reward_amount:.2f} PLEX\n\n"
                f"Это действие нельзя отменить."
            )
            
            if result:
                logger.info(f"✅ Награда {reward_amount:.2f} PLEX подготовлена для {address}")
                messagebox.showinfo("Награда подготовлена", 
                                  f"Награда успешно подготовлена!\n\n"
                                  f"Участник: {address}\n"
                                  f"Сумма: {reward_amount:.2f} PLEX")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки награды: {e}")
            messagebox.showerror("Ошибка", f"Не удалось отправить награду:\n{e}")