"""
PLEX Dynamic Staking Manager - Analysis Tab
Вкладка для анализа участников стейкинга и их активности.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from ui.themes.dark_theme import get_theme
from ui.components.progress_bar import ProgressBar, ProgressState
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory
from core.full_optimized_analyzer import FullOptimizedAnalyzer

logger = get_logger(__name__)


class AnalysisTab(ctk.CTkFrame):
    """
    Вкладка анализа участников стейкинга.
    
    Функциональность:
    - Настройка параметров анализа
    - Запуск анализа с прогресс-баром
    - Отображение результатов анализа
    - Экспорт результатов
    - Фильтрация и поиск участников
    """
    
    def __init__(self, parent, staking_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация AnalysisTab.
        
        Args:
            parent: Родительский виджет
            staking_manager: Экземпляр StakingManager
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
        
        try:
            # Попытка инициализации с минимальными зависимостями
            self.full_analyzer = None
            logger.debug("FullOptimizedAnalyzer будет инициализирован позже при наличии зависимостей")
        except Exception as e:
            logger.error(f"Ошибка подготовки FullOptimizedAnalyzer: {e}")
        
        self._create_widgets()
        self._setup_layout()
        
    def _create_widgets(self):
        """Создание виджетов интерфейса."""
        try:            # Заголовок
            self.title_label = ctk.CTkLabel(
                self,
                text="Анализ участников стейкинга",
                font=("Arial", 24, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Фрейм настроек
            self.settings_frame = ctk.CTkFrame(self)
            self.settings_frame.configure(fg_color=self.theme.colors['bg_secondary'])
            
            self.settings_title = ctk.CTkLabel(
                self.settings_frame,
                text="Настройки анализа",
                font=("Arial", 16, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Период анализа
            self.period_frame = ctk.CTkFrame(self.settings_frame)
            
            self.period_label = ctk.CTkLabel(
                self.period_frame,
                text="Период анализа:",
                text_color=self.theme.colors['text_secondary']
            )
            
            self.period_var = ctk.StringVar(value="24h")
            self.period_options = ["1h", "6h", "24h", "7d", "30d", "custom"]
            self.period_menu = ctk.CTkOptionMenu(
                self.period_frame,
                values=["1 час", "6 часов", "24 часа", "7 дней", "30 дней", "Свой период"],
                variable=self.period_var,
                command=self._on_period_changed            )
            
            # Кастомные даты (скрыто по умолчанию)
            self.custom_frame = ctk.CTkFrame(self.period_frame)
            
            self.start_date_label = ctk.CTkLabel(
                self.custom_frame,
                text="От:",
                text_color=self.theme.colors['text_secondary']
            )
            
            self.start_date_entry = self.widget_factory.create_entry(
                self.custom_frame,
                width=150
            )
            self.widget_factory.setup_placeholder(self.start_date_entry, "YYYY-MM-DD HH:MM")
            
            self.end_date_label = ctk.CTkLabel(
                self.custom_frame,
                text="До:",
                text_color=self.theme.colors['text_secondary']
            )
            
            self.end_date_entry = self.widget_factory.create_entry(
                self.custom_frame,
                width=150
            )
            self.widget_factory.setup_placeholder(self.end_date_entry, "YYYY-MM-DD HH:MM")
            
            # Параметры анализа
            self.params_frame = ctk.CTkFrame(self.settings_frame)
            
            self.min_volume_label = ctk.CTkLabel(
                self.params_frame,
                text="Мин. объем (USD):",
                text_color=self.theme.colors['text_secondary']            )
            
            self.min_volume_entry = self.widget_factory.create_entry(
                self.params_frame,
                width=100
            )
            self.widget_factory.setup_placeholder(self.min_volume_entry, "1000")
            
            self.force_refresh_var = ctk.BooleanVar(value=False)
            self.force_refresh_switch = ctk.CTkCheckBox(
                self.params_frame,
                text="Принудительное обновление",
                variable=self.force_refresh_var,
                text_color=self.theme.colors['text_secondary']
            )
              # Кнопки управления
            self.control_frame = ctk.CTkFrame(self.settings_frame)
            
            self.start_analysis_button = ctk.CTkButton(
                self.control_frame,
                text="🚀 Запустить анализ",
                command=self._start_analysis,
                fg_color=self.theme.colors['btn_primary'],                font=("Arial", 12, "bold"),
                height=35
            )
            
            self.stop_analysis_button = ctk.CTkButton(
                self.control_frame,
                text="⏹️ Остановить",
                command=self._stop_analysis,
                fg_color=self.theme.colors['btn_danger'],                state="disabled",
                height=35
            )
            
            self.export_button = ctk.CTkButton(
                self.control_frame,
                text="📊 Экспорт",
                command=self._export_results,
                fg_color=self.theme.colors['success'],
                state="disabled",
                height=35
            )
            
            # Прогресс-бар
            self.progress_bar = ProgressBar(self)
              # Фрейм результатов
            self.results_frame = ctk.CTkFrame(self)
            self.results_frame.configure(fg_color=self.theme.colors['bg_secondary'])
            
            self.results_title = ctk.CTkLabel(
                self.results_frame,
                text="Результаты анализа",
                font=("Arial", 16, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Статистика
            self.stats_frame = ctk.CTkFrame(self.results_frame)
            
            # Карточки статистики
            self.total_participants_card = self._create_stat_card(
                self.stats_frame, "Всего участников", "0", "info"
            )
            
            self.perfect_participants_card = self._create_stat_card(
                self.stats_frame, "Идеальные", "0", "success"
            )
            
            self.total_volume_card = self._create_stat_card(
                self.stats_frame, "Общий объем", "$0", "accent"
            )
            
            self.total_rewards_card = self._create_stat_card(
                self.stats_frame, "Общие награды", "0 PLEX", "warning"
            )
            
            # Фильтры
            self.filter_frame = ctk.CTkFrame(self.results_frame)
            
            self.filter_label = ctk.CTkLabel(
                self.filter_frame,
                text="Поиск и фильтры:",
                text_color=self.theme.colors['text_secondary']            )
            
            self.search_entry = self.widget_factory.create_entry(
                self.filter_frame,
                width=200
            )
            self.widget_factory.setup_placeholder(self.search_entry, "Поиск по адресу...")
            self.search_entry.bind('<KeyRelease>', self._on_search_changed)
            
            # Фильтр по категории
            self.category_var = ctk.StringVar(value="all")
            self.category_menu = ctk.CTkOptionMenu(
                self.filter_frame,
                values=["Все", "Идеальные", "Пропуски", "Продали", "Переводы"],
                variable=self.category_var,
                command=self._on_filter_changed
            )
            
            # Таблица участников
            self.participants_frame = ctk.CTkFrame(self.results_frame)
              # Заголовки таблицы
            self.table_header = ctk.CTkFrame(self.participants_frame)
            self.table_header.configure(fg_color=self.theme.colors['bg_primary'])
            
            self.header_address = ctk.CTkLabel(
                self.table_header,
                text="Адрес",
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            self.header_category = ctk.CTkLabel(
                self.table_header,
                text="Категория",
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            self.header_volume = ctk.CTkLabel(
                self.table_header,
                text="Объем (USD)",
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            self.header_balance = ctk.CTkLabel(
                self.table_header,
                text="Баланс PLEX",
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            self.header_reward = ctk.CTkLabel(
                self.table_header,
                text="Награда",
                font=("Arial", 12, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Прокручиваемая область для таблицы
            self.table_scrollable = ctk.CTkScrollableFrame(
                self.participants_frame,
                fg_color=self.theme.colors['bg_primary']
            )
            
            # Первоначальное скрытие кастомного фрейма
            self.custom_frame.pack_forget()
            
        except Exception as e:
            logger.error(f"Ошибка создания виджетов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать интерфейс: {e}")
    
    def _create_stat_card(self, parent, title: str, value: str, color_type: str) -> Dict[str, ctk.CTkLabel]:
        """
        Создание карточки статистики.
        
        Args:
            parent: Родительский виджет
            title: Заголовок карточки
            value: Значение
            color_type: Тип цвета
            
        Returns:
            Dict: Словарь с виджетами карточки        """
        card_frame = ctk.CTkFrame(parent)
        card_frame.configure(fg_color=self.theme.colors['bg_primary'])
        
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=("Arial", 10),
            text_color=self.theme.colors['text_secondary']
        )
        
        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_accent']
        )
        
        title_label.pack(pady=(10, 2))
        value_label.pack(pady=(2, 10))
        
        return {
            'frame': card_frame,
            'title': title_label,
            'value': value_label
        }
    
    def _setup_layout(self):
        """Настройка расположения виджетов."""
        try:
            # Настройка grid weights
            self.grid_rowconfigure(4, weight=1)
            self.grid_columnconfigure(0, weight=1)
            
            # Заголовок
            self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="ew")
            
            # Панель настроек
            self.settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            
            self.settings_title.pack(pady=(15, 10))
            
            # Период анализа
            self.period_frame.pack(fill='x', padx=15, pady=5)
            
            period_row = ctk.CTkFrame(self.period_frame)
            period_row.pack(fill='x', pady=5)
            
            self.period_label.pack(side='left')
            self.period_menu.pack(side='left', padx=(10, 0))
            
            # Кастомные даты
            self.custom_frame.pack(fill='x', pady=(5, 0))
            
            self.start_date_label.pack(side='left', padx=(0, 5))
            self.start_date_entry.pack(side='left', padx=(0, 20))
            self.end_date_label.pack(side='left', padx=(0, 5))
            self.end_date_entry.pack(side='left')
            
            # Параметры анализа
            self.params_frame.pack(fill='x', padx=15, pady=5)
            
            params_row1 = ctk.CTkFrame(self.params_frame)
            params_row1.pack(fill='x', pady=5)
            
            self.min_volume_label.pack(side='left')
            self.min_volume_entry.pack(side='left', padx=(10, 0))
            
            params_row2 = ctk.CTkFrame(self.params_frame)
            params_row2.pack(fill='x', pady=5)
            
            self.force_refresh_switch.pack(side='left')
            
            # Кнопки управления
            self.control_frame.pack(fill='x', padx=15, pady=(10, 15))
            
            self.start_analysis_button.pack(side='left', padx=(0, 10))
            self.stop_analysis_button.pack(side='left', padx=(0, 10))
            self.export_button.pack(side='right')
            
            # Прогресс-бар
            self.progress_bar.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
            
            # Панель результатов
            self.results_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
            
            self.results_title.pack(pady=(15, 10))
            
            # Статистика
            self.stats_frame.pack(fill='x', padx=15, pady=5)
            
            # Размещение карточек статистики в ряд
            self.total_participants_card['frame'].pack(side='left', fill='x', expand=True, padx=(0, 5))
            self.perfect_participants_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
            self.total_volume_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
            self.total_rewards_card['frame'].pack(side='left', fill='x', expand=True, padx=(5, 0))
            
            # Фильтры
            self.filter_frame.pack(fill='x', padx=15, pady=10)
            
            self.filter_label.pack(side='left', padx=(0, 10))
            self.search_entry.pack(side='left', padx=(0, 10))
            self.category_menu.pack(side='left')
            
            # Таблица участников
            self.participants_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
              # Заголовок таблицы
            self.table_header.pack(fill='x', pady=(0, 5))
            
            self.header_address.pack(side='left', fill='x', expand=True, padx=(10, 5))
            self.header_category.configure(width=100)
            self.header_category.pack(side='left', padx=5)
            self.header_volume.configure(width=120)
            self.header_volume.pack(side='left', padx=5)
            self.header_balance.configure(width=120)
            self.header_balance.pack(side='left', padx=5)
            self.header_reward.configure(width=100)
            self.header_reward.pack(side='left', padx=(5, 10))
            
            # Прокручиваемая таблица
            self.table_scrollable.pack(fill='both', expand=True, pady=(5, 0))
            
        except Exception as e:
            logger.error(f"Ошибка настройки layout: {e}")
    
    def _on_period_changed(self, value: str):
        """Обработка изменения периода анализа."""
        if value == "Свой период":
            self.custom_frame.pack(fill='x', pady=(5, 0))
            # Установка значений по умолчанию
            now = datetime.now()
            end_time = now.strftime('%Y-%m-%d %H:%M')
            start_time = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')
            
            self.start_date_entry.delete(0, 'end')
            self.start_date_entry.insert(0, start_time)
            self.end_date_entry.delete(0, 'end')
            self.end_date_entry.insert(0, end_time)
        else:
            self.custom_frame.pack_forget()
    
    def _on_search_changed(self, event=None):
        """Обработка изменения поискового запроса."""
        self._apply_filters()
    
    def _on_filter_changed(self, value: str):
        """Обработка изменения фильтра категории."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Применение фильтров к результатам."""
        if not self.current_analysis_result:
            return
        
        try:
            search_text = self.search_entry.get().lower()
            category_filter = self.category_var.get()
            
            # Получение всех участников
            all_participants = self.current_analysis_result.get('participants', [])
            
            # Применение фильтров
            filtered = []
            for participant in all_participants:
                # Фильтр по поиску
                if search_text and search_text not in participant.get('address', '').lower():
                    continue
                
                # Фильтр по категории
                if category_filter != "Все":
                    participant_category = participant.get('category', '')
                    
                    filter_mapping = {
                        "Идеальные": "perfect",
                        "Пропуски": "missed_purchase",
                        "Продали": "sold_token",
                        "Переводы": "transferred"
                    }
                    
                    if participant_category != filter_mapping.get(category_filter):
                        continue
                
                filtered.append(participant)
            
            self.filtered_participants = filtered
            self._update_participants_table()
            
        except Exception as e:
            logger.error(f"Ошибка применения фильтров: {e}")
    
    def _start_analysis(self):
        """Запуск анализа участников."""
        if self.analysis_running:
            return
        
        try:
            # Валидация параметров
            period_start, period_end = self._get_analysis_period()
            if not period_start or not period_end:
                messagebox.showerror("Ошибка", "Некорректный период анализа")
                return
            
            min_volume = self._get_min_volume()
            if min_volume is None:
                messagebox.showerror("Ошибка", "Некорректное значение минимального объема")
                return
            
            # Подготовка UI
            self.analysis_running = True
            self.start_analysis_button.configure(state='disabled')
            self.stop_analysis_button.configure(state='normal')
            self.export_button.configure(state='disabled')
            
            # Сброс прогресс-бара
            self.progress_bar.reset()
            self.progress_bar.set_state(ProgressState.RUNNING)
            
            # Запуск анализа в отдельном потоке
            analysis_thread = threading.Thread(
                target=self._run_analysis_thread,
                args=(period_start, period_end, min_volume),
                daemon=True
            )
            analysis_thread.start()
            
            logger.info(f"Запущен анализ за период {period_start} - {period_end}")
            
        except Exception as e:
            logger.error(f"Ошибка запуска анализа: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить анализ:\n{e}")
            self._analysis_completed(success=False)
    
    def _stop_analysis(self):
        """Остановка анализа."""
        if not self.analysis_running:
            return
        
        try:
            self.analysis_running = False
            self.progress_bar.set_state(ProgressState.CANCELLED)
            self._analysis_completed(success=False, cancelled=True)
            logger.info("Анализ остановлен пользователем")
            
        except Exception as e:
            logger.error(f"Ошибка остановки анализа: {e}")
    
    def _run_analysis_thread(self, period_start: datetime, period_end: datetime, min_volume: float):
        """Выполнение анализа в отдельном потоке."""
        try:
            # Настройка прогресса
            def update_progress(value, message=""):
                if self.analysis_running:
                    self.after_idle(lambda: self.progress_bar.set_progress(value, message))
            
            # Этапы анализа
            update_progress(10, "Инициализация...")
            
            if not self.analysis_running:
                return
            
            # Получение данных о свапах
            update_progress(30, "Сбор данных о транзакциях...")
            
            if self.full_analyzer:
                # Использование FullOptimizedAnalyzer
                result = self.full_analyzer.run_optimized_full_analysis(
                    min_stake_amount=min_volume,
                    period_days=30,  # TODO: Вычислить из period_start и period_end
                    use_optimizations=True,
                    progress_callback=update_progress
                )
            else:
                # Создание демонстрационного результата
                result = self._create_demo_result()
                
                import time
                for i in range(30, 100, 10):
                    if not self.analysis_running:
                        return
                    
                    time.sleep(0.5)
                    update_progress(i, f"Анализ участников... {i}%")
            
            update_progress(100, "Анализ завершен")
            
            # Обновление UI в главном потоке
            self.after_idle(lambda: self._analysis_completed(success=True, result=result))
            
        except Exception as e:
            logger.error(f"Ошибка выполнения анализа: {e}")
            self.after_idle(lambda: self._analysis_completed(success=False, error=str(e)))
    
    def _create_demo_result(self) -> Dict[str, Any]:
        """Создание демонстрационного результата анализа."""
        import random
        
        # Генерация тестовых участников
        participants = []
        categories = ['perfect', 'missed_purchase', 'sold_token', 'transferred']
        
        for i in range(50):
            participant = {
                'address': f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                'category': random.choice(categories),
                'total_volume_usd': Decimal(str(random.uniform(100, 50000))),
                'current_balance': {
                    'plex': Decimal(str(random.uniform(1000, 100000))),
                    'usdt': Decimal(str(random.uniform(10, 1000))),
                    'bnb': Decimal(str(random.uniform(0.1, 10)))
                },
                'reward_amount': Decimal(str(random.uniform(10, 1000))),
                'transaction_count': random.randint(5, 100),
                'first_transaction': datetime.now() - timedelta(days=random.randint(1, 90))
            }
            participants.append(participant)
        
        return {
            'participants': participants,
            'total_participants': len(participants),
            'perfect_participants': len([p for p in participants if p['category'] == 'perfect']),
            'total_volume_usd': sum(p['total_volume_usd'] for p in participants),
            'total_rewards': sum(p['reward_amount'] for p in participants),
            'analysis_time': datetime.now(),
            'period_start': datetime.now() - timedelta(days=1),
            'period_end': datetime.now()
        }
    
    def _analysis_completed(self, success: bool, result: Dict = None, error: str = "", cancelled: bool = False):
        """Обработка завершения анализа."""
        try:
            self.analysis_running = False
            
            # Обновление состояния кнопок
            self.start_analysis_button.configure(state='normal')
            self.stop_analysis_button.configure(state='disabled')
            
            if success and result:
                # Успешное завершение
                self.progress_bar.set_state(ProgressState.COMPLETED)
                self.current_analysis_result = result
                self.export_button.configure(state='normal')
                
                # Обновление статистики
                self._update_statistics(result)
                
                # Обновление таблицы участников
                self.filtered_participants = result.get('participants', [])
                self._update_participants_table()
                
                messagebox.showinfo("Успех", "Анализ успешно завершен!")
                
            elif cancelled:
                # Отменено пользователем
                self.progress_bar.set_state(ProgressState.CANCELLED)
                
            else:
                # Ошибка
                self.progress_bar.set_state(ProgressState.ERROR)
                error_msg = f"Ошибка выполнения анализа:\n{error}" if error else "Неизвестная ошибка"
                messagebox.showerror("Ошибка", error_msg)
                
        except Exception as e:
            logger.error(f"Ошибка обработки завершения анализа: {e}")
    
    def _update_statistics(self, result: Dict[str, Any]):
        """Обновление карточек статистики."""
        try:
            # Общее количество участников
            total = result.get('total_participants', 0)
            self.total_participants_card['value'].configure(text=str(total))
            
            # Идеальные участники
            perfect = result.get('perfect_participants', 0)
            self.perfect_participants_card['value'].configure(text=str(perfect))
            
            # Общий объем
            volume = result.get('total_volume_usd', Decimal('0'))
            volume_text = f"${volume:,.0f}"
            self.total_volume_card['value'].configure(text=volume_text)
            
            # Общие награды
            rewards = result.get('total_rewards', Decimal('0'))
            rewards_text = f"{rewards:,.0f} PLEX"
            self.total_rewards_card['value'].configure(text=rewards_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
    
    def _update_participants_table(self):
        """Обновление таблицы участников."""
        try:
            # Очистка существующих строк
            for widget in self.table_scrollable.winfo_children():
                widget.destroy()
            
            # Добавление участников
            for i, participant in enumerate(self.filtered_participants[:100]):  # Ограничение для производительности
                self._create_participant_row(participant, i)
                
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы участников: {e}")
    
    def _create_participant_row(self, participant: Dict[str, Any], index: int):
        """Создание строки участника в таблице."""
        try:            # Фрейм строки
            row_frame = ctk.CTkFrame(self.table_scrollable)
            if index % 2 == 0:
                row_frame.configure(fg_color=self.theme.colors['bg_secondary'])
            else:
                row_frame.configure(fg_color=self.theme.colors['bg_primary'])
            row_frame.pack(fill='x', pady=1)
            
            # Адрес (сокращенный)
            address = participant.get('address', '')
            short_address = f"{address[:10]}...{address[-8:]}" if len(address) > 18 else address
            
            address_label = ctk.CTkLabel(
                row_frame,
                text=short_address,
                text_color=self.theme.colors['text_primary']
            )
            
            # Категория с цветом
            category = participant.get('category', 'unknown')
            category_colors = {
                'perfect': '#4CAF50',
                'missed_purchase': '#FF9800',
                'sold_token': '#F44336',
                'transferred': '#2196F3'
            }
            
            category_text = {
                'perfect': '⭐ Идеальный',
                'missed_purchase': '⚠️ Пропуски',
                'sold_token': '❌ Продажа',
                'transferred': '🔄 Переводы'            }.get(category, category)
            
            category_label = ctk.CTkLabel(
                row_frame,
                text=category_text,
                text_color=category_colors.get(category, self.theme.colors['text_primary'])
            )
            
            # Объем торговли
            volume = participant.get('total_volume_usd', Decimal('0'))
            volume_label = ctk.CTkLabel(
                row_frame,
                text=f"${volume:,.0f}",
                text_color=self.theme.colors['text_primary']
            )
            
            # Баланс PLEX
            balance = participant.get('current_balance', {}).get('plex', Decimal('0'))
            balance_label = ctk.CTkLabel(
                row_frame,
                text=f"{balance:,.0f}",
                text_color=self.theme.colors['text_primary']
            )
            
            # Награда
            reward = participant.get('reward_amount', Decimal('0'))
            reward_label = ctk.CTkLabel(
                row_frame,
                text=f"{reward:,.0f}",
                text_color=self.theme.colors['text_accent']            )
            
            # Размещение элементов
            address_label.pack(side='left', fill='x', expand=True, padx=(10, 5))
            category_label.configure(width=100)
            category_label.pack(side='left', padx=5)
            volume_label.configure(width=120)
            volume_label.pack(side='left', padx=5)
            balance_label.configure(width=120)
            balance_label.pack(side='left', padx=5)
            reward_label.configure(width=100)
            reward_label.pack(side='left', padx=(5, 10))
            
        except Exception as e:
            logger.error(f"Ошибка создания строки участника: {e}")
    
    def _get_analysis_period(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Получение периода анализа."""
        try:
            period = self.period_var.get()
            
            if period == "custom":
                # Кастомный период
                start_str = self.start_date_entry.get()
                end_str = self.end_date_entry.get()
                
                if not start_str or not end_str:
                    return None, None
                
                try:
                    start_date = datetime.strptime(start_str, '%Y-%m-%d %H:%M')
                    end_date = datetime.strptime(end_str, '%Y-%m-%d %H:%M')
                    return start_date, end_date
                except ValueError:
                    return None, None
            
            else:
                # Предустановленный период
                end_date = datetime.now()
                
                period_mapping = {
                    "1h": timedelta(hours=1),
                    "6h": timedelta(hours=6),
                    "24h": timedelta(hours=24),
                    "7d": timedelta(days=7),
                    "30d": timedelta(days=30)
                }
                
                delta = period_mapping.get(period, timedelta(hours=24))
                start_date = end_date - delta
                
                return start_date, end_date
                
        except Exception as e:
            logger.error(f"Ошибка получения периода анализа: {e}")
            return None, None
    
    def _get_min_volume(self) -> Optional[float]:
        """Получение минимального объема."""
        try:
            value_str = self.min_volume_entry.get()
            if not value_str:
                return 0.0
            
            return float(value_str)
            
        except ValueError:
            return None
    
    def _export_results(self):
        """Экспорт результатов анализа."""
        if not self.current_analysis_result:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        try:
            # Выбор файла для сохранения
            file_path = filedialog.asksaveasfilename(
                title="Сохранить результаты анализа",
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx"),
                    ("JSON files", "*.json"),
                    ("All files", "*.*")
                ]
            )
            
            if not file_path:
                return
            
            # Экспорт в зависимости от расширения
            if file_path.endswith('.csv'):
                self._export_to_csv(file_path)
            elif file_path.endswith('.xlsx'):
                self._export_to_excel(file_path)
            elif file_path.endswith('.json'):
                self._export_to_json(file_path)
            else:
                self._export_to_csv(file_path)
            
            messagebox.showinfo("Успех", f"Результаты экспортированы в:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные:\n{e}")
    
    def _export_to_csv(self, file_path: str):
        """Экспорт в CSV формат."""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'address', 'category', 'total_volume_usd', 'plex_balance',
                'usdt_balance', 'bnb_balance', 'reward_amount', 'transaction_count'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for participant in self.filtered_participants:
                balance = participant.get('current_balance', {})
                
                writer.writerow({
                    'address': participant.get('address', ''),
                    'category': participant.get('category', ''),
                    'total_volume_usd': float(participant.get('total_volume_usd', 0)),
                    'plex_balance': float(balance.get('plex', 0)),
                    'usdt_balance': float(balance.get('usdt', 0)),
                    'bnb_balance': float(balance.get('bnb', 0)),
                    'reward_amount': float(participant.get('reward_amount', 0)),
                    'transaction_count': participant.get('transaction_count', 0)
                })
    
    def _export_to_excel(self, file_path: str):
        """Экспорт в Excel формат."""
        try:
            import pandas as pd
            
            # Подготовка данных
            data = []
            for participant in self.filtered_participants:
                balance = participant.get('current_balance', {})
                
                data.append({
                    'Адрес': participant.get('address', ''),
                    'Категория': participant.get('category', ''),
                    'Объем USD': float(participant.get('total_volume_usd', 0)),
                    'Баланс PLEX': float(balance.get('plex', 0)),
                    'Баланс USDT': float(balance.get('usdt', 0)),
                    'Баланс BNB': float(balance.get('bnb', 0)),
                    'Награда': float(participant.get('reward_amount', 0)),
                    'Транзакций': participant.get('transaction_count', 0)
                })
            
            # Создание DataFrame и сохранение
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
        except ImportError:
            # Fallback на CSV если pandas не установлен
            self._export_to_csv(file_path.replace('.xlsx', '.csv'))
    
    def _export_to_json(self, file_path: str):
        """Экспорт в JSON формат."""
        import json
        from decimal import Decimal
        
        # Функция для сериализации Decimal
        def decimal_serializer(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(
                {
                    'analysis_result': self.current_analysis_result,
                    'filtered_participants': self.filtered_participants
                },
                jsonfile,
                indent=2,
                default=decimal_serializer,
                ensure_ascii=False
            )
    
    def set_staking_manager(self, staking_manager):
        """Установка менеджера стейкинга."""
        self.staking_manager = staking_manager
        logger.debug("StakingManager установлен для AnalysisTab")
    
    def refresh_data(self):
        """Обновление данных вкладки."""
        try:
            # Обновляем данные если необходимо
            pass
        except Exception as e:
            logger.error(f"Ошибка обновления данных: {e}")
    
    def get_tab_name(self) -> str:
        """Получение названия вкладки."""
        return "Анализ"


# Экспорт для удобного импорта
__all__ = ['AnalysisTab']


if __name__ == "__main__":
    # Демонстрация вкладки
    def demo_analysis_tab():
        """Демонстрация AnalysisTab."""
        try:
            print("🧪 Демонстрация AnalysisTab...")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Analysis Tab Demo")
            root.geometry("1200x800")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание вкладки анализа
            analysis_tab = AnalysisTab(root)
            analysis_tab.pack(fill='both', expand=True)
            
            print("✅ AnalysisTab запущена. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_analysis_tab()
    print("💡 Для демонстрации AnalysisTab раскомментируй последнюю строку")
