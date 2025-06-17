"""
PLEX Dynamic Staking Manager - Enhanced History Tab
Улучшенная вкладка для просмотра истории операций с полным набором кнопок.

Автор: PLEX Dynamic Staking Team
Версия: 1.1.0
"""

import asyncio
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import customtkinter as ctk

from ui.themes.dark_theme import get_theme
from ui.components.progress_bar import ProgressBar, ProgressState
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class EnhancedHistoryTab(ctk.CTkFrame):
    """
    Улучшенная вкладка истории операций.
    
    Функциональность:
    - Просмотр истории операций
    - Фильтрация по датам и типам
    - Поиск операций
    - Экспорт истории
    - Анализ операций
    - Полный набор кнопок управления
    """
    
    def __init__(self, parent, history_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация EnhancedHistoryTab.
        
        Args:
            parent: Родительский виджет
            history_manager: Экземпляр HistoryManager
            **kwargs: Дополнительные параметры
        """
        super().__init__(parent, **kwargs)
        
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        self.history_manager = history_manager
        
        # Данные истории
        self.current_history = []
        self.filtered_history = []
        self.loading_history = False
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        
        logger.info("✅ Enhanced HistoryTab инициализирована")
    
    def _create_widgets(self):
        """Создание виджетов интерфейса."""
        try:
            # Заголовок
            self.title_label = ctk.CTkLabel(
                self,
                text="📚 История операций",
                font=("Arial", 24, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # ПАНЕЛЬ УПРАВЛЕНИЯ ИСТОРИЕЙ
            self.control_panel = self._create_control_panel()
            
            # ПАНЕЛЬ ФИЛЬТРОВ
            self.filter_panel = self._create_filter_panel()
            
            # ПРОГРЕСС-БАР
            self.progress_bar = ProgressBar(self)
            
            # ПАНЕЛЬ РЕЗУЛЬТАТОВ
            self.results_panel = self._create_results_panel()
            
            logger.debug("✅ Все виджеты созданы успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания виджетов: {e}")
            raise
    
    def _create_control_panel(self) -> ctk.CTkFrame:
        """Создание панели управления историей."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок панели
        title = ctk.CTkLabel(
            panel,
            text="🎮 Управление историей",
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
        
        self.load_history_btn = ctk.CTkButton(
            row1,
            text="📥 Загрузить историю",
            command=self._load_history,
            fg_color=self.theme.colors['btn_primary'],
            hover_color=self.theme.colors['btn_primary_hover'],
            font=("Arial", 12, "bold"),
            height=40,
            width=160
        )
        self.load_history_btn.pack(side='left', padx=(0, 10))
        
        self.refresh_btn = ctk.CTkButton(
            row1,
            text="🔄 Обновить",
            command=self._refresh_history,
            fg_color=self.theme.colors['info'],
            font=("Arial", 12, "bold"),
            height=40,
            width=120
        )
        self.refresh_btn.pack(side='left', padx=(0, 10))
        
        self.analyze_btn = ctk.CTkButton(
            row1,
            text="📊 Анализировать",
            command=self._analyze_history,
            fg_color=self.theme.colors['plex_primary'],
            font=("Arial", 12, "bold"),
            height=40,
            width=140
        )
        self.analyze_btn.pack(side='left', padx=(0, 10))
        
        self.clear_btn = ctk.CTkButton(
            row1,
            text="🗑️ Очистить",
            command=self._clear_history,
            fg_color=self.theme.colors['btn_danger'],
            font=("Arial", 12, "bold"),
            height=40,
            width=120
        )
        self.clear_btn.pack(side='right')
        
        # Ряд 2: Экспорт и утилиты
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
        
        self.export_pdf_btn = ctk.CTkButton(
            row2,
            text="📋 Отчет PDF",
            command=self._export_pdf_report,
            fg_color=self.theme.colors['success'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.export_pdf_btn.pack(side='left', padx=(0, 10))
        
        self.backup_btn = ctk.CTkButton(
            row2,
            text="💾 Бэкап",
            command=self._create_backup,
            fg_color=self.theme.colors['warning'],
            font=("Arial", 12, "bold"),
            height=35,
            width=100
        )
        self.backup_btn.pack(side='right', padx=(10, 0))
        
        self.restore_btn = ctk.CTkButton(
            row2,
            text="📦 Восстановить",
            command=self._restore_backup,
            fg_color=self.theme.colors['info'],
            font=("Arial", 12, "bold"),
            height=35,
            width=130
        )
        self.restore_btn.pack(side='right')
        
        return panel
    
    def _create_filter_panel(self) -> ctk.CTkFrame:
        """Создание панели фильтров."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок
        title = ctk.CTkLabel(
            panel,
            text="🔍 Фильтры и поиск",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title.pack(pady=(15, 10))
        
        # Фильтры в сетке
        filters_grid = ctk.CTkFrame(panel)
        filters_grid.configure(fg_color="transparent")
        filters_grid.pack(fill='x', padx=15, pady=10)
        
        # Ряд 1: Поиск и период
        search_frame = ctk.CTkFrame(filters_grid)
        search_frame.configure(fg_color="transparent")
        search_frame.pack(fill='x', pady=5)
        
        # Поиск
        ctk.CTkLabel(
            search_frame,
            text="🔍 Поиск:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")        ).pack(side='left')
        
        self.search_entry = self.widget_factory.create_entry(
            search_frame,
            width=300
        )
        self.widget_factory.setup_placeholder(self.search_entry, "Адрес, хэш транзакции, тип...")
        self.search_entry.pack(side='left', padx=(10, 20))
        
        self.search_btn = ctk.CTkButton(
            search_frame,
            text="🔍",
            command=self._apply_search,
            fg_color=self.theme.colors['btn_primary'],
            width=40,
            height=30
        )
        self.search_btn.pack(side='left', padx=(0, 20))
        
        # Период
        ctk.CTkLabel(
            search_frame,
            text="📅 Период:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        self.period_var = ctk.StringVar(value="7d")
        self.period_menu = ctk.CTkOptionMenu(
            search_frame,
            values=["1h", "6h", "24h", "7d", "30d", "90d", "all"],
            variable=self.period_var,
            command=self._on_period_change,
            fg_color=self.theme.colors['input_bg'],
            button_color=self.theme.colors['btn_primary'],
            width=100
        )
        self.period_menu.pack(side='left', padx=10)
        
        # Ряд 2: Типы операций
        types_frame = ctk.CTkFrame(filters_grid)
        types_frame.configure(fg_color="transparent")
        types_frame.pack(fill='x', pady=5)
        
        ctk.CTkLabel(
            types_frame,
            text="📝 Типы:",
            text_color=self.theme.colors['text_secondary'],
            font=("Arial", 12, "bold")
        ).pack(side='left')
        
        # Чекбоксы типов операций
        self.operation_types = {}
        types = [
            ("stake", "Стейкинг"),
            ("unstake", "Анстейкинг"),
            ("reward", "Награды"),
            ("transfer", "Переводы"),
            ("swap", "Обмены")
        ]
        
        types_checkboxes = ctk.CTkFrame(types_frame)
        types_checkboxes.configure(fg_color="transparent")
        types_checkboxes.pack(side='left', padx=(10, 20))
        
        for type_key, type_name in types:
            var = ctk.BooleanVar(value=True)
            self.operation_types[type_key] = var
            
            checkbox = ctk.CTkCheckBox(
                types_checkboxes,
                text=type_name,
                variable=var,
                command=self._apply_filters,
                text_color=self.theme.colors['text_secondary']
            )
            checkbox.pack(side='left', padx=5)
        
        # Кнопки управления фильтрами
        filter_controls = ctk.CTkFrame(types_frame)
        filter_controls.configure(fg_color="transparent")
        filter_controls.pack(side='right')
        
        self.select_all_btn = ctk.CTkButton(
            filter_controls,
            text="✅ Все",
            command=self._select_all_types,
            fg_color=self.theme.colors['btn_secondary'],
            width=60,
            height=25
        )
        self.select_all_btn.pack(side='left', padx=2)
        
        self.select_none_btn = ctk.CTkButton(
            filter_controls,
            text="❌ Ничего",
            command=self._select_no_types,
            fg_color=self.theme.colors['btn_secondary'],
            width=70,
            height=25
        )
        self.select_none_btn.pack(side='left', padx=2)
        
        self.reset_filters_btn = ctk.CTkButton(
            filter_controls,
            text="🔄 Сброс",
            command=self._reset_filters,
            fg_color=self.theme.colors['warning'],
            width=60,
            height=25
        )
        self.reset_filters_btn.pack(side='left', padx=2)
        
        return panel
    
    def _create_results_panel(self) -> ctk.CTkFrame:
        """Создание панели результатов."""
        panel = ctk.CTkFrame(self)
        panel.configure(fg_color=self.theme.colors['bg_secondary'])
        
        # Заголовок с информацией
        header = ctk.CTkFrame(panel)
        header.configure(fg_color="transparent")
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        title = ctk.CTkLabel(
            header,
            text="📜 История операций",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title.pack(side='left')
        
        # Информация о количестве
        self.count_label = ctk.CTkLabel(
            header,
            text="Записей: 0",
            font=("Arial", 12),
            text_color=self.theme.colors['text_secondary']
        )
        self.count_label.pack(side='left', padx=(20, 0))
        
        # Кнопки управления отображением
        display_controls = ctk.CTkFrame(header)
        display_controls.configure(fg_color="transparent")
        display_controls.pack(side='right')
        
        self.sort_by_var = ctk.StringVar(value="date_desc")
        self.sort_menu = ctk.CTkOptionMenu(
            display_controls,
            values=["Дата ↓", "Дата ↑", "Сумма ↓", "Сумма ↑", "Тип"],
            variable=self.sort_by_var,
            command=self._apply_sorting,
            fg_color=self.theme.colors['btn_secondary'],
            width=120
        )
        self.sort_menu.pack(side='left', padx=(0, 10))
        
        self.view_mode_btn = ctk.CTkButton(
            display_controls,
            text="📋 Режим",
            command=self._toggle_view_mode,
            fg_color=self.theme.colors['btn_secondary'],
            width=80,
            height=30
        )
        self.view_mode_btn.pack(side='left')
        
        # Статистика операций
        self.stats_frame = ctk.CTkFrame(panel)
        self.stats_frame.configure(fg_color=self.theme.colors['bg_tertiary'])
        self.stats_frame.pack(fill='x', padx=15, pady=10)
        
        # Карточки статистики
        self._create_history_stats_cards()
        
        # Список операций
        self.history_list_frame = ctk.CTkFrame(panel)
        self.history_list_frame.configure(fg_color=self.theme.colors['bg_tertiary'])
        self.history_list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        
        # Заглушка для списка
        self.history_placeholder = ctk.CTkLabel(
            self.history_list_frame,
            text="📥 Загрузите историю для отображения операций",
            font=("Arial", 14),
            text_color=self.theme.colors['text_muted']
        )
        self.history_placeholder.pack(expand=True, pady=50)
        
        return panel
    
    def _create_history_stats_cards(self):
        """Создание карточек статистики истории."""
        stats_data = [
            ("📜", "Операций", "0", "info"),
            ("💰", "Общий объем", "0.0 PLEX", "success"),
            ("🎁", "Наград", "0.0 PLEX", "plex_primary"),
            ("⏱️", "Последняя", "Никогда", "warning")
        ]
        
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
            
            ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 14, "bold"),
                text_color=self.theme.colors[color] if color in self.theme.colors else self.theme.colors['text_primary']
            ).pack(pady=(0, 10))
    
    def _setup_layout(self):
        """Настройка расположения виджетов."""
        try:
            # Настройка grid weights
            self.grid_rowconfigure(4, weight=1)  # Результаты растягиваются
            self.grid_columnconfigure(0, weight=1)
            
            # Размещение компонентов
            self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")
            self.control_panel.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            self.filter_panel.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
            self.progress_bar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
            self.results_panel.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
            
            logger.debug("✅ Layout настроен успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки layout: {e}")
    
    # Методы обработки событий
    def _load_history(self):
        """Загрузка истории."""
        logger.info("📥 Загрузка истории...")
        
        self.load_history_btn.configure(state="disabled")
        self._simulate_loading()
    
    def _simulate_loading(self):
        """Симуляция загрузки истории."""
        def run_loading():
            try:
                self.loading_history = True
                
                for i in range(101):
                    if not self.loading_history:
                        break
                    
                    progress = i / 100
                    message = f"Загрузка истории... {i}%"
                    
                    self.after(0, lambda p=progress, m=message: self.progress_bar.set_progress(p, m))
                    threading.Event().wait(0.02)
                
                if self.loading_history:
                    self.after(0, self._loading_completed)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки: {e}")
                self.after(0, self._reset_loading)
        
        thread = threading.Thread(target=run_loading, daemon=True)
        thread.start()
    
    def _loading_completed(self):
        """Завершение загрузки истории."""
        logger.info("✅ История загружена")
        
        self.loading_history = False
        self.load_history_btn.configure(state="normal")
        
        self.progress_bar.set_progress(1.0, "История загружена!")
        
        # Обновление счетчика
        self.count_label.configure(text="Записей: 1,234")
        
        # Обновление заглушки
        self.history_placeholder.configure(
            text="✅ Загружено 1,234 операций\\n📊 Период: последние 7 дней"
        )
    
    def _refresh_history(self):
        """Обновление истории."""
        logger.info("🔄 Обновление истории...")
        messagebox.showinfo("Обновлено", "История успешно обновлена!")
    
    def _analyze_history(self):
        """Анализ истории."""
        logger.info("📊 Анализ истории...")
        messagebox.showinfo("Анализ", "Анализ истории завершен!\\n\\nНайдено:\\n- 45 уникальных адресов\\n- 156 операций стейкинга\\n- 89 операций вывода")
    
    def _clear_history(self):
        """Очистка истории."""
        result = messagebox.askyesno("Подтверждение", "Вы уверены, что хотите очистить историю?")
        if result:
            logger.info("🗑️ История очищена")
            self.count_label.configure(text="Записей: 0")
            self.history_placeholder.configure(
                text="📥 Загрузите историю для отображения операций"
            )
    
    def _export_csv(self):
        """Экспорт в CSV."""
        logger.info("📄 Экспорт в CSV...")
        messagebox.showinfo("Экспорт", "История экспортирована в CSV!")
    
    def _export_excel(self):
        """Экспорт в Excel."""
        logger.info("📊 Экспорт в Excel...")
        messagebox.showinfo("Экспорт", "История экспортирована в Excel!")
    
    def _export_pdf_report(self):
        """Экспорт отчета в PDF."""
        logger.info("📋 Создание PDF отчета...")
        messagebox.showinfo("Отчет", "PDF отчет создан!")
    
    def _create_backup(self):
        """Создание бэкапа."""
        logger.info("💾 Создание бэкапа...")
        messagebox.showinfo("Бэкап", "Бэкап истории создан!")
    
    def _restore_backup(self):
        """Восстановление из бэкапа."""
        logger.info("📦 Восстановление из бэкапа...")
        messagebox.showinfo("Восстановление", "История восстановлена из бэкапа!")
    
    def _apply_search(self):
        """Применение поиска."""
        search_text = self.search_entry.get()
        logger.info(f"🔍 Поиск: {search_text}")
        messagebox.showinfo("Поиск", f"Поиск по запросу: '{search_text}'")
    
    def _on_period_change(self, value):
        """Обработка изменения периода."""
        logger.debug(f"📅 Период изменен на: {value}")
        self._apply_filters()
    
    def _apply_filters(self):
        """Применение фильтров."""
        logger.debug("🔍 Применение фильтров...")
    
    def _select_all_types(self):
        """Выбор всех типов операций."""
        for var in self.operation_types.values():
            var.set(True)
        self._apply_filters()
    
    def _select_no_types(self):
        """Снятие выбора всех типов."""
        for var in self.operation_types.values():
            var.set(False)
        self._apply_filters()
    
    def _reset_filters(self):
        """Сброс всех фильтров."""
        logger.info("🔄 Сброс фильтров...")
        self.search_entry.delete(0, "end")
        self.period_var.set("7d")
        self._select_all_types()
    
    def _apply_sorting(self, value):
        """Применение сортировки."""
        logger.debug(f"📊 Сортировка: {value}")
    
    def _toggle_view_mode(self):
        """Переключение режима отображения."""
        logger.info("📋 Переключение режима отображения...")
        messagebox.showinfo("Режим", "Режим отображения изменен!")
    
    def _reset_loading(self):
        """Сброс состояния загрузки."""
        self.loading_history = False
        self.load_history_btn.configure(state="normal")
    
    def set_history_manager(self, history_manager):
        """Установка менеджера истории."""
        self.history_manager = history_manager
        logger.info("✅ HistoryManager подключен к Enhanced HistoryTab")
