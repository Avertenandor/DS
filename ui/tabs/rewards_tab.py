"""
PLEX Dynamic Staking Manager - Rewards Tab
Вкладка для управления наградами участников стейкинга.

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

from ui.themes.dark_theme import get_theme
from ui.components.progress_bar import ProgressBar, ProgressState
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class RewardsTab(ctk.CTkFrame):
    """
    Вкладка управления наградами.
    
    Функциональность:
    - Просмотр рассчитанных наград
    - Настройка параметров наград
    - Экспорт списков для выплат
    - Предотвращение двойных выплат
    - История выплат
    """
    
    def __init__(self, parent, reward_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация RewardsTab.
        
        Args:
            parent: Родительский виджет
            reward_manager: Экземпляр RewardManager
            **kwargs: Дополнительные параметры
        """
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        
        # Применение стиля фрейма
        frame_style = self.theme.get_frame_style('primary')
        frame_style.update(kwargs)
        super().__init__(parent, **frame_style)
        
        # Ссылка на менеджер наград
        self.reward_manager = reward_manager
        
        # Данные наград
        self.current_rewards = []
        self.filtered_rewards = []
        self.calculation_running = False
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        
        logger.debug("🎁 RewardsTab инициализирована")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Заголовок
        self.title_label = self.theme.create_styled_label(
            self,
            "🎁 Управление наградами",
            'title'
        )
        
        # Панель настроек наград
        self.settings_frame = self.theme.create_styled_frame(self, 'card')
        
        self.settings_title = self.theme.create_styled_label(
            self.settings_frame,
            "⚙️ Настройки наград",
            'subtitle'
        )
        
        # Параметры расчета наград
        self.params_frame = self.theme.create_styled_frame(self.settings_frame, 'primary')
        
        # Тип награды
        self.reward_type_label = self.theme.create_styled_label(
            self.params_frame,
            "🏆 Тип награды:",
            'primary'
        )
        
        self.reward_type_var = ctk.StringVar(value="volume_based")
        self.reward_type_options = ["volume_based", "tier_based", "equal", "custom"]
        self.reward_type_menu = ctk.CTkOptionMenu(
            self.params_frame,
            values=["По объему", "По уровням", "Равные", "Кастом"],
            variable=self.reward_type_var,
            command=self._on_reward_type_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Общий пул наград
        self.total_pool_label = self.theme.create_styled_label(
            self.params_frame,
            "💰 Общий пул (PLEX):",
            'primary'
        )
        
        self.total_pool_entry = self.theme.create_styled_entry(
            self.params_frame,
            placeholder="10000",
            width=120
        )
        self.total_pool_entry.insert(0, "10000")
        
        # Множители для категорий
        self.multipliers_frame = self.theme.create_styled_frame(self.params_frame, 'secondary')
        
        self.multipliers_label = self.theme.create_styled_label(
            self.multipliers_frame,
            "🎯 Множители по категориям:",
            'subtitle'
        )
        
        # Множители
        self.multiplier_entries = {}
        multiplier_configs = [
            ("perfect", "⭐ Идеальные", "1.0"),
            ("missed_purchase", "⚠️ С пропусками", "0.8"),
            ("sold_token", "❌ Продавшие", "0.0"),
            ("transferred", "🔄 С переводами", "0.5")
        ]
        
        for key, label, default in multiplier_configs:
            frame = self.theme.create_styled_frame(self.multipliers_frame, 'primary')
            
            label_widget = self.theme.create_styled_label(frame, label, 'primary')
            
            entry = self.theme.create_styled_entry(
                frame,
                placeholder=default,
                width=80
            )
            entry.insert(0, default)
            
            self.multiplier_entries[key] = {
                'frame': frame,
                'label': label_widget,
                'entry': entry
            }
        
        # Кнопки управления
        self.control_frame = self.theme.create_styled_frame(self.settings_frame, 'primary')
        
        self.calculate_rewards_button = self.theme.create_styled_button(
            self.control_frame,
            "💎 Рассчитать награды",
            'plex',
            command=self._calculate_rewards,
            width=150
        )
        
        self.export_rewards_button = self.theme.create_styled_button(
            self.control_frame,
            "📋 Экспорт списка",
            'success',
            command=self._export_rewards,
            width=120,
            state='disabled'
        )
        
        self.check_duplicates_button = self.theme.create_styled_button(
            self.control_frame,
            "🔍 Проверка дублей",
            'warning',
            command=self._check_duplicates,
            width=130
        )
        
        # Прогресс-бар
        self.progress_bar = ProgressBar(
            self,
            **self.theme.get_progress_style()
        )
        
        # Панель результатов
        self.results_frame = self.theme.create_styled_frame(self, 'card')
        
        self.results_title = self.theme.create_styled_label(
            self.results_frame,
            "📊 Результаты расчета наград",
            'subtitle'
        )
        
        # Статистика наград
        self.stats_frame = self.theme.create_styled_frame(self.results_frame, 'primary')
        
        # Карточки статистики
        self.total_recipients_card = self._create_stat_card(
            self.stats_frame,
            "👥 Получателей",
            "0",
            'info'
        )
        
        self.allocated_rewards_card = self._create_stat_card(
            self.stats_frame,
            "💰 Распределено",
            "0 PLEX",
            'success'
        )
        
        self.remaining_pool_card = self._create_stat_card(
            self.stats_frame,
            "💎 Остаток пула",
            "0 PLEX",
            'warning'
        )
        
        self.avg_reward_card = self._create_stat_card(
            self.stats_frame,
            "📈 Средняя награда",
            "0 PLEX",
            'accent'
        )
        
        # Фильтры наград
        self.filter_frame = self.theme.create_styled_frame(self.results_frame, 'primary')
        
        self.filter_label = self.theme.create_styled_label(
            self.filter_frame,
            "🔍 Фильтры:",
            'primary'
        )
        
        # Поиск по адресу
        self.search_entry = self.theme.create_styled_entry(
            self.filter_frame,
            placeholder="Поиск по адресу...",
            width=200
        )
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        # Фильтр по минимальной награде
        self.min_reward_label = self.theme.create_styled_label(
            self.filter_frame,
            "Мин. награда:",
            'secondary'
        )
        
        self.min_reward_entry = self.theme.create_styled_entry(
            self.filter_frame,
            placeholder="0",
            width=80
        )
        self.min_reward_entry.bind('<KeyRelease>', self._on_filter_changed)
        
        # Сортировка
        self.sort_label = self.theme.create_styled_label(
            self.filter_frame,
            "Сортировка:",
            'secondary'
        )
        
        self.sort_var = ctk.StringVar(value="reward_desc")
        self.sort_menu = ctk.CTkOptionMenu(
            self.filter_frame,
            values=["По награде ↓", "По награде ↑", "По адресу", "По категории"],
            variable=self.sort_var,
            command=self._on_sort_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Таблица наград
        self.rewards_frame = self.theme.create_styled_frame(self.results_frame, 'primary')
        
        # Заголовки таблицы
        self.table_header = self.theme.create_styled_frame(self.rewards_frame, 'secondary')
        
        self.header_address = self.theme.create_styled_label(
            self.table_header,
            "Адрес",
            'primary'
        )
        
        self.header_category = self.theme.create_styled_label(
            self.table_header,
            "Категория",
            'primary'
        )
        
        self.header_volume = self.theme.create_styled_label(
            self.table_header,
            "Объем (USD)",
            'primary'
        )
        
        self.header_multiplier = self.theme.create_styled_label(
            self.table_header,
            "Множитель",
            'primary'
        )
        
        self.header_reward = self.theme.create_styled_label(
            self.table_header,
            "Награда (PLEX)",
            'primary'
        )
        
        self.header_status = self.theme.create_styled_label(
            self.table_header,
            "Статус",
            'primary'
        )
        
        # Прокручиваемая область для таблицы
        self.table_scrollable = ctk.CTkScrollableFrame(
            self.rewards_frame,
            **self.theme.get_frame_style('primary')
        )
        
        # История выплат
        self.history_frame = self.theme.create_styled_frame(self, 'card')
        
        self.history_title = self.theme.create_styled_label(
            self.history_frame,
            "📋 История выплат",
            'subtitle'
        )
        
        self.history_button = self.theme.create_styled_button(
            self.history_frame,
            "📄 Показать историю",
            'info',
            command=self._show_payment_history,
            width=150
        )
        
        # Список истории
        self.history_list = ctk.CTkScrollableFrame(
            self.history_frame,
            height=150,
            **self.theme.get_frame_style('secondary')
        )
    
    def _create_stat_card(self, parent, title: str, value: str, color_type: str) -> Dict[str, ctk.CTkLabel]:
        """
        Создание карточки статистики.
        
        Args:
            parent: Родительский виджет
            title: Заголовок карточки
            value: Значение
            color_type: Тип цвета
            
        Returns:
            Dict: Словарь с виджетами карточки
        """
        card_frame = self.theme.create_styled_frame(parent, 'card')
        
        title_label = self.theme.create_styled_label(
            card_frame,
            title,
            'secondary'
        )
        
        value_label = self.theme.create_styled_label(
            card_frame,
            value,
            'title'
        )
        
        # Применение цвета
        color = self.theme.get_status_color(color_type)
        value_label.configure(text_color=color)
        
        title_label.pack(pady=(10, 2))
        value_label.pack(pady=(2, 10))
        
        return {
            'frame': card_frame,
            'title': title_label,
            'value': value_label
        }
    
    def _setup_layout(self) -> None:
        """Настройка расположения виджетов."""
        # Заголовок
        self.title_label.pack(pady=(20, 10))
        
        # Панель настроек
        self.settings_frame.pack(fill='x', padx=20, pady=10)
        
        self.settings_title.pack(pady=(15, 10))
        
        # Параметры
        self.params_frame.pack(fill='x', padx=15, pady=5)
        
        # Тип награды
        reward_type_row = self.theme.create_styled_frame(self.params_frame, 'primary')
        reward_type_row.pack(fill='x', pady=5)
        
        self.reward_type_label.pack(side='left')
        self.reward_type_menu.pack(side='left', padx=(10, 20))
        
        self.total_pool_label.pack(side='left')
        self.total_pool_entry.pack(side='left', padx=(10, 0))
        
        # Множители
        self.multipliers_frame.pack(fill='x', pady=(10, 5))
        self.multipliers_label.pack(pady=(10, 5))
        
        for key, config in self.multiplier_entries.items():
            config['frame'].pack(fill='x', pady=2)
            config['label'].pack(side='left', anchor='w', fill='x', expand=True)
            config['entry'].pack(side='right', padx=(5, 10))
        
        # Кнопки управления
        self.control_frame.pack(fill='x', padx=15, pady=(10, 15))
        
        self.calculate_rewards_button.pack(side='left', padx=(0, 10))
        self.export_rewards_button.pack(side='left', padx=(0, 10))
        self.check_duplicates_button.pack(side='right')
        
        # Прогресс-бар
        self.progress_bar.pack(fill='x', padx=20, pady=10)
        
        # Панель результатов
        self.results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.results_title.pack(pady=(15, 10))
        
        # Статистика
        self.stats_frame.pack(fill='x', padx=15, pady=5)
        
        # Размещение карточек статистики в ряд
        self.total_recipients_card['frame'].pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.allocated_rewards_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
        self.remaining_pool_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
        self.avg_reward_card['frame'].pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        # Фильтры
        self.filter_frame.pack(fill='x', padx=15, pady=10)
        
        self.filter_label.pack(side='left', padx=(0, 10))
        self.search_entry.pack(side='left', padx=(0, 15))
        self.min_reward_label.pack(side='left', padx=(0, 5))
        self.min_reward_entry.pack(side='left', padx=(0, 15))
        self.sort_label.pack(side='left', padx=(0, 5))
        self.sort_menu.pack(side='left')
        
        # Таблица наград
        self.rewards_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))
          # Заголовок таблицы
        self.table_header.pack(fill='x', pady=(0, 5))
        self.header_address.pack(side='left', fill='x', expand=True)
        self.header_category.configure(width=100)
        self.header_category.pack(side='left')
        self.header_volume.configure(width=100)
        self.header_volume.pack(side='left')
        self.header_multiplier.configure(width=80)
        self.header_multiplier.pack(side='left')
        self.header_reward.configure(width=120)
        self.header_reward.pack(side='left')
        self.header_status.configure(width=80)
        self.header_status.pack(side='left')
        
        # Прокручиваемая таблица
        self.table_scrollable.pack(fill='both', expand=True, pady=(5, 0))
        
        # История выплат
        self.history_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.history_title.pack(pady=(15, 5))
        self.history_button.pack(pady=5)
        self.history_list.pack(fill='x', padx=15, pady=(0, 15))
    
    def _on_reward_type_changed(self, value: str) -> None:
        """Обработка изменения типа награды."""
        logger.debug(f"🎯 Изменен тип награды: {value}")
        # Здесь можно добавить логику изменения интерфейса в зависимости от типа
    
    def _on_search_changed(self, event=None) -> None:
        """Обработка изменения поискового запроса."""
        self._apply_filters()
    
    def _on_filter_changed(self, event=None) -> None:
        """Обработка изменения фильтров."""
        self._apply_filters()
    
    def _on_sort_changed(self, value: str) -> None:
        """Обработка изменения сортировки."""
        self._apply_filters()
    
    def _apply_filters(self) -> None:
        """Применение фильтров к наградам."""
        if not self.current_rewards:
            return
        
        try:
            search_text = self.search_entry.get().lower()
            min_reward_text = self.min_reward_entry.get()
            min_reward = float(min_reward_text) if min_reward_text else 0
            sort_type = self.sort_var.get()
            
            # Фильтрация
            filtered = []
            for reward in self.current_rewards:
                # Фильтр по поиску
                if search_text and search_text not in reward.get('address', '').lower():
                    continue
                
                # Фильтр по минимальной награде
                if reward.get('reward_amount', 0) < min_reward:
                    continue
                
                filtered.append(reward)
            
            # Сортировка
            sort_mapping = {
                "По награде ↓": lambda x: -x.get('reward_amount', 0),
                "По награде ↑": lambda x: x.get('reward_amount', 0),
                "По адресу": lambda x: x.get('address', ''),
                "По категории": lambda x: x.get('category', '')
            }
            
            if sort_type in sort_mapping:
                filtered.sort(key=sort_mapping[sort_type])
            
            self.filtered_rewards = filtered
            self._update_rewards_table()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения фильтров: {e}")
    
    def _calculate_rewards(self) -> None:
        """Расчет наград для участников."""
        if self.calculation_running:
            return
        
        try:
            # Валидация параметров
            total_pool = self._get_total_pool()
            if total_pool is None or total_pool <= 0:
                messagebox.showerror("Ошибка", "Некорректный размер пула наград")
                return
            
            multipliers = self._get_multipliers()
            if not multipliers:
                messagebox.showerror("Ошибка", "Некорректные множители")
                return
            
            # Подготовка UI
            self.calculation_running = True
            self.calculate_rewards_button.configure(state='disabled')
            self.export_rewards_button.configure(state='disabled')
            
            # Сброс прогресс-бара
            self.progress_bar.reset()
            self.progress_bar.set_range(0, 100)
            self.progress_bar.start()
            
            # Запуск расчета в отдельном потоке
            calc_thread = threading.Thread(
                target=self._run_calculation_thread,
                args=(total_pool, multipliers),
                daemon=True
            )
            calc_thread.start()
            
            logger.info(f"💎 Запущен расчет наград с пулом {total_pool} PLEX")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска расчета наград: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить расчет:\\n{e}")
            self._calculation_completed(success=False)
    
    def _run_calculation_thread(self, total_pool: float, multipliers: Dict[str, float]) -> None:
        """Выполнение расчета наград в отдельном потоке."""
        try:
            # Настройка прогресса
            def update_progress(value, message=""):
                if self.calculation_running:
                    self.after_idle(lambda: self.progress_bar.set_progress(value, message))
            
            # Этапы расчета
            update_progress(10, "Подготовка данных...")
            
            if not self.calculation_running:
                return
            
            # Здесь должен быть вызов реального расчета наград
            # if self.reward_manager:
            #     result = await self.reward_manager.calculate_rewards(
            #         total_pool=total_pool,
            #         multipliers=multipliers,
            #         reward_type=self.reward_type_var.get()
            #     )
            
            # Имитация для демонстрации
            import time
            import random
            
            for i in range(10, 100, 15):
                if not self.calculation_running:
                    return
                
                time.sleep(0.3)  # Имитация работы
                update_progress(i, f"Расчет наград... {i}%")
            
            # Создание демонстрационного результата
            demo_rewards = self._create_demo_rewards(total_pool, multipliers)
            
            update_progress(100, "Расчет завершен")
            
            # Обновление UI в главном потоке
            self.after_idle(lambda: self._calculation_completed(success=True, rewards=demo_rewards))
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения расчета наград: {e}")
            self.after_idle(lambda: self._calculation_completed(success=False, error=str(e)))
    
    def _create_demo_rewards(self, total_pool: float, multipliers: Dict[str, float]) -> List[Dict[str, Any]]:
        """Создание демонстрационных наград."""
        import random
        
        # Генерация тестовых участников
        rewards = []
        categories = ['perfect', 'missed_purchase', 'sold_token', 'transferred']
        
        for i in range(30):
            category = random.choice(categories)
            volume = random.uniform(100, 50000)
            base_reward = (volume / 1000) * 10  # Базовая формула
            final_reward = base_reward * multipliers.get(category, 1.0)
            
            reward = {
                'address': f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                'category': category,
                'volume_usd': Decimal(str(volume)),
                'multiplier': multipliers.get(category, 1.0),
                'reward_amount': Decimal(str(final_reward)),
                'status': 'pending',
                'calculation_time': datetime.now()
            }
            rewards.append(reward)
        
        # Нормализация к общему пулу
        total_calculated = sum(r['reward_amount'] for r in rewards)
        if total_calculated > 0:
            scaling_factor = Decimal(str(total_pool)) / total_calculated
            for reward in rewards:
                reward['reward_amount'] = reward['reward_amount'] * scaling_factor
        
        return rewards
    
    def _calculation_completed(self, success: bool, rewards: List = None, error: str = "") -> None:
        """Обработка завершения расчета наград."""
        try:
            self.calculation_running = False
            
            # Обновление состояния кнопок
            self.calculate_rewards_button.configure(state='normal')
            
            if success and rewards:
                # Успешное завершение
                self.progress_bar.complete()
                self.current_rewards = rewards
                self.export_rewards_button.configure(state='normal')
                
                # Обновление статистики
                self._update_statistics(rewards)
                
                # Обновление таблицы
                self.filtered_rewards = rewards
                self._update_rewards_table()
                
                messagebox.showinfo("Успех", f"Награды рассчитаны для {len(rewards)} участников!")
                
            else:
                # Ошибка
                self.progress_bar.error(error)
                error_msg = f"Ошибка расчета наград:\\n{error}" if error else "Неизвестная ошибка"
                messagebox.showerror("Ошибка", error_msg)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки завершения расчета: {e}")
    
    def _update_statistics(self, rewards: List[Dict[str, Any]]) -> None:
        """Обновление статистики наград."""
        try:
            # Общее количество получателей
            total_recipients = len(rewards)
            self.total_recipients_card['value'].configure(text=str(total_recipients))
            
            # Распределенные награды
            allocated = sum(r.get('reward_amount', 0) for r in rewards)
            self.allocated_rewards_card['value'].configure(text=f"{allocated:,.0f} PLEX")
            
            # Остаток пула
            total_pool = self._get_total_pool() or 0
            remaining = max(0, total_pool - float(allocated))
            self.remaining_pool_card['value'].configure(text=f"{remaining:,.0f} PLEX")
            
            # Средняя награда
            avg_reward = allocated / total_recipients if total_recipients > 0 else 0
            self.avg_reward_card['value'].configure(text=f"{avg_reward:,.0f} PLEX")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики наград: {e}")
    
    def _update_rewards_table(self) -> None:
        """Обновление таблицы наград."""
        try:
            # Очистка существующих строк
            for widget in self.table_scrollable.winfo_children():
                widget.destroy()
            
            # Добавление наград
            for i, reward in enumerate(self.filtered_rewards[:50]):  # Ограничение для производительности
                self._create_reward_row(reward, i)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления таблицы наград: {e}")
    
    def _create_reward_row(self, reward: Dict[str, Any], index: int) -> None:
        """Создание строки награды в таблице."""
        try:
            # Фрейм строки
            row_style = 'secondary' if index % 2 == 0 else 'primary'
            row_frame = self.theme.create_styled_frame(self.table_scrollable, row_style)
            row_frame.pack(fill='x', pady=1)
            
            # Адрес (сокращенный)
            address = reward.get('address', '')
            short_address = f"{address[:10]}...{address[-8:]}" if len(address) > 18 else address
            
            address_label = self.theme.create_styled_label(
                row_frame,
                short_address,
                'primary'
            )
            
            # Категория с цветом
            category = reward.get('category', 'unknown')
            category_colors = {
                'perfect': 'success',
                'missed_purchase': 'warning',
                'sold_token': 'error',
                'transferred': 'info'
            }
            category_color = category_colors.get(category, 'primary')
            
            category_text = {
                'perfect': '⭐',
                'missed_purchase': '⚠️',
                'sold_token': '❌',
                'transferred': '🔄'
            }.get(category, category)
            
            category_label = self.theme.create_styled_label(
                row_frame,
                category_text,
                'primary'
            )
            category_label.configure(text_color=self.theme.get_status_color(category_color))
            
            # Объем торговли
            volume = reward.get('volume_usd', Decimal('0'))
            volume_label = self.theme.create_styled_label(
                row_frame,
                f"${volume:,.0f}",
                'primary'
            )
            
            # Множитель
            multiplier = reward.get('multiplier', 1.0)
            multiplier_label = self.theme.create_styled_label(
                row_frame,
                f"{multiplier:.1f}x",
                'secondary'
            )
            
            # Награда
            reward_amount = reward.get('reward_amount', Decimal('0'))
            reward_label = self.theme.create_styled_label(
                row_frame,
                f"{reward_amount:,.0f}",
                'accent'
            )
            
            # Статус
            status = reward.get('status', 'pending')
            status_colors = {
                'pending': 'warning',
                'paid': 'success',
                'failed': 'error'
            }
            status_color = status_colors.get(status, 'primary')
            
            status_text = {
                'pending': '⏳',
                'paid': '✅',
                'failed': '❌'
            }.get(status, status)
            
            status_label = self.theme.create_styled_label(
                row_frame,
                status_text,
                'primary'
            )
            status_label.configure(text_color=self.theme.get_status_color(status_color))
              # Размещение элементов
            address_label.pack(side='left', fill='x', expand=True, padx=(10, 5))
            category_label.configure(width=100)
            category_label.pack(side='left', padx=5)
            volume_label.configure(width=100)
            volume_label.pack(side='left', padx=5)
            multiplier_label.configure(width=80)
            multiplier_label.pack(side='left', padx=5)
            reward_label.configure(width=120)
            reward_label.pack(side='left', padx=5)
            status_label.configure(width=80)
            status_label.pack(side='left', padx=(5, 10))
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания строки награды: {e}")
    
    def _get_total_pool(self) -> Optional[float]:
        """Получение общего пула наград."""
        try:
            value_str = self.total_pool_entry.get()
            if not value_str:
                return None
            
            return float(value_str)
            
        except ValueError:
            return None
    
    def _get_multipliers(self) -> Optional[Dict[str, float]]:
        """Получение множителей для категорий."""
        try:
            multipliers = {}
            
            for key, config in self.multiplier_entries.items():
                value_str = config['entry'].get()
                if not value_str:
                    return None
                
                multipliers[key] = float(value_str)
            
            return multipliers
            
        except ValueError:
            return None
    
    def _export_rewards(self) -> None:
        """Экспорт списка наград."""
        if not self.current_rewards:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        try:
            # Выбор файла для сохранения
            file_path = filedialog.asksaveasfilename(
                title="Экспорт списка наград",
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
                self._export_rewards_to_csv(file_path)
            elif file_path.endswith('.xlsx'):
                self._export_rewards_to_excel(file_path)
            elif file_path.endswith('.json'):
                self._export_rewards_to_json(file_path)
            else:
                self._export_rewards_to_csv(file_path)
            
            messagebox.showinfo("Успех", f"Список наград экспортирован в:\\n{file_path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта наград: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные:\\n{e}")
    
    def _export_rewards_to_csv(self, file_path: str) -> None:
        """Экспорт наград в CSV формат."""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'address', 'category', 'volume_usd', 'multiplier', 
                'reward_amount', 'status', 'calculation_time'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for reward in self.filtered_rewards:
                writer.writerow({
                    'address': reward.get('address', ''),
                    'category': reward.get('category', ''),
                    'volume_usd': float(reward.get('volume_usd', 0)),
                    'multiplier': reward.get('multiplier', 0),
                    'reward_amount': float(reward.get('reward_amount', 0)),
                    'status': reward.get('status', ''),
                    'calculation_time': reward.get('calculation_time', '').isoformat() if reward.get('calculation_time') else ''
                })
    
    def _export_rewards_to_excel(self, file_path: str) -> None:
        """Экспорт наград в Excel формат."""
        try:
            import pandas as pd
            
            # Подготовка данных
            data = []
            for reward in self.filtered_rewards:
                data.append({
                    'Адрес': reward.get('address', ''),
                    'Категория': reward.get('category', ''),
                    'Объем USD': float(reward.get('volume_usd', 0)),
                    'Множитель': reward.get('multiplier', 0),
                    'Награда PLEX': float(reward.get('reward_amount', 0)),
                    'Статус': reward.get('status', ''),
                    'Время расчета': reward.get('calculation_time', '')
                })
            
            # Создание DataFrame и сохранение
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
        except ImportError:
            # Fallback на CSV если pandas не установлен
            self._export_rewards_to_csv(file_path.replace('.xlsx', '.csv'))
    
    def _export_rewards_to_json(self, file_path: str) -> None:
        """Экспорт наград в JSON формат."""
        import json
        from decimal import Decimal
        
        # Функция для сериализации Decimal и datetime
        def default_serializer(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(
                {
                    'rewards': self.filtered_rewards,
                    'export_time': datetime.now().isoformat(),
                    'total_rewards': len(self.filtered_rewards)
                },
                jsonfile,
                indent=2,
                default=default_serializer,
                ensure_ascii=False
            )
    
    def _check_duplicates(self) -> None:
        """Проверка на дублирующие выплаты."""
        try:
            # Здесь должна быть логика проверки дублей через DuplicateProtection
            # Для демонстрации показываем информационное сообщение
            
            result = messagebox.askquestion(
                "Проверка дублей",
                "Запустить проверку на дублирующие выплаты?\\n\\n"
                "Это поможет избежать двойных выплат участникам."
            )
            
            if result == 'yes':
                # Имитация проверки
                import time
                import threading
                
                def check_thread():
                    time.sleep(2)  # Имитация проверки
                    self.after_idle(lambda: messagebox.showinfo(
                        "Результат проверки",
                        "✅ Дублирующие выплаты не обнаружены.\\n\\n"
                        "Все участники уникальны и готовы к выплате."
                    ))
                
                threading.Thread(target=check_thread, daemon=True).start()
                
                # Показать индикатор загрузки
                self.progress_bar.set_indeterminate(True)
                self.progress_bar.set_progress(50, "Проверка дублей...")
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки дублей: {e}")
            messagebox.showerror("Ошибка", f"Не удалось выполнить проверку:\\n{e}")
    
    def _show_payment_history(self) -> None:
        """Отображение истории выплат."""
        try:
            # Очистка списка истории
            for widget in self.history_list.winfo_children():
                widget.destroy()
            
            # Создание демонстрационной истории
            history_items = [
                {
                    'date': datetime.now() - timedelta(days=7),
                    'recipients': 45,
                    'total_amount': 12500,
                    'status': 'completed'
                },
                {
                    'date': datetime.now() - timedelta(days=14),
                    'recipients': 38,
                    'total_amount': 9800,
                    'status': 'completed'
                },
                {
                    'date': datetime.now() - timedelta(days=21),
                    'recipients': 52,
                    'total_amount': 15200,
                    'status': 'completed'
                }
            ]
            
            for i, item in enumerate(history_items):
                # Фрейм элемента истории
                item_frame = self.theme.create_styled_frame(self.history_list, 'primary')
                item_frame.pack(fill='x', pady=2, padx=5)
                
                # Дата
                date_str = item['date'].strftime('%Y-%m-%d %H:%M')
                date_label = self.theme.create_styled_label(
                    item_frame,
                    date_str,
                    'primary'
                )
                date_label.pack(side='left', anchor='w')
                
                # Информация о выплате
                info_text = f"👥 {item['recipients']} получателей • 💰 {item['total_amount']:,} PLEX"
                info_label = self.theme.create_styled_label(
                    item_frame,
                    info_text,
                    'secondary'
                )
                info_label.pack(side='left', padx=(20, 0), anchor='w')
                
                # Статус
                status_text = "✅ Завершено" if item['status'] == 'completed' else "⏳ В процессе"
                status_label = self.theme.create_styled_label(
                    item_frame,
                    status_text,
                    'accent'
                )
                status_label.pack(side='right', anchor='e')
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения истории: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить историю:\\n{e}")
    
    def set_reward_manager(self, reward_manager) -> None:
        """Установка менеджера наград."""
        self.reward_manager = reward_manager
        logger.debug("✅ RewardManager установлен для RewardsTab")


# Экспорт для удобного импорта
__all__ = ['RewardsTab']


if __name__ == "__main__":
    # Демонстрация вкладки
    def demo_rewards_tab():
        """Демонстрация RewardsTab."""
        try:
            print("🧪 Демонстрация RewardsTab...")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Rewards Tab Demo")
            root.geometry("1400x900")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание вкладки наград
            rewards_tab = RewardsTab(root)
            rewards_tab.pack(fill='both', expand=True)
            
            print("✅ RewardsTab запущена. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_rewards_tab()
    print("💡 Для демонстрации RewardsTab раскомментируй последнюю строку")
