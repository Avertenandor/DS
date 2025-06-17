"""
PLEX Dynamic Staking Manager - History Tab
Вкладка для просмотра истории анализов и операций.

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


class HistoryTab(ctk.CTkFrame):
    """
    Вкладка истории операций.
    
    Функциональность:
    - Просмотр истории анализов
    - История выплат наград
    - Фильтрация по датам и типам операций
    - Экспорт истории
    - Детализация операций
    """
    
    def __init__(self, parent, history_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация HistoryTab.
        
        Args:
            parent: Родительский виджет
            history_manager: Экземпляр HistoryManager
            **kwargs: Дополнительные параметры
        """
        self.theme = get_theme()
        self.widget_factory = widget_factory or SafeWidgetFactory(self.theme)
        
        # Применение стиля фрейма
        frame_style = self.theme.get_frame_style('primary')
        frame_style.update(kwargs)
        super().__init__(parent, **frame_style)
        
        # Ссылка на менеджер истории
        self.history_manager = history_manager
        
        # Данные истории
        self.current_history = []
        self.filtered_history = []
        self.loading_history = False
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        
        # Загрузка истории при инициализации
        self._load_initial_history()
        
        logger.debug("📚 HistoryTab инициализирована")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Заголовок
        self.title_label = self.theme.create_styled_label(
            self,
            "📚 История операций",
            'title'
        )
        
        # Панель фильтров
        self.filters_frame = self.theme.create_styled_frame(self, 'card')
        
        self.filters_title = self.theme.create_styled_label(
            self.filters_frame,
            "🔍 Фильтры истории",
            'subtitle'
        )
        
        # Период
        self.period_frame = self.theme.create_styled_frame(self.filters_frame, 'primary')
        
        self.period_label = self.theme.create_styled_label(
            self.period_frame,
            "📅 Период:",
            'primary'
        )
        
        self.period_var = ctk.StringVar(value="30d")
        self.period_options = ["24h", "7d", "30d", "90d", "all", "custom"]
        self.period_menu = ctk.CTkOptionMenu(
            self.period_frame,
            values=["24 часа", "7 дней", "30 дней", "90 дней", "Всё время", "Кастом"],
            variable=self.period_var,
            command=self._on_period_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Кастомный период
        self.custom_period_frame = self.theme.create_styled_frame(self.period_frame, 'primary')
        
        self.start_date_label = self.theme.create_styled_label(
            self.custom_period_frame,
            "От:",
            'secondary'
        )
        
        self.start_date_entry = self.theme.create_styled_entry(
            self.custom_period_frame,
            placeholder="YYYY-MM-DD",
            width=120
        )
        
        self.end_date_label = self.theme.create_styled_label(
            self.custom_period_frame,
            "До:",
            'secondary'
        )
        
        self.end_date_entry = self.theme.create_styled_entry(
            self.custom_period_frame,
            placeholder="YYYY-MM-DD",
            width=120
        )
        
        # Тип операции
        self.operation_frame = self.theme.create_styled_frame(self.filters_frame, 'primary')
        
        self.operation_label = self.theme.create_styled_label(
            self.operation_frame,
            "🔧 Тип операции:",
            'primary'
        )
        
        self.operation_var = ctk.StringVar(value="all")
        self.operation_options = ["all", "analysis", "rewards", "export", "backup"]
        self.operation_menu = ctk.CTkOptionMenu(
            self.operation_frame,
            values=["Все", "Анализы", "Награды", "Экспорт", "Резервные копии"],
            variable=self.operation_var,
            command=self._on_filter_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Статус операции
        self.status_label = self.theme.create_styled_label(
            self.operation_frame,
            "📊 Статус:",
            'primary'
        )
        
        self.status_var = ctk.StringVar(value="all")
        self.status_menu = ctk.CTkOptionMenu(
            self.operation_frame,
            values=["Все", "Успешно", "Ошибка", "В процессе"],
            variable=self.status_var,
            command=self._on_filter_changed,
            **self.theme.get_button_style('secondary')
        )
        
        # Кнопки управления
        self.control_frame = self.theme.create_styled_frame(self.filters_frame, 'primary')
        
        self.refresh_button = self.theme.create_styled_button(
            self.control_frame,
            "🔄 Обновить",
            'info',
            command=self._refresh_history,
            width=100
        )
        
        self.export_history_button = self.theme.create_styled_button(
            self.control_frame,
            "💾 Экспорт",
            'secondary',
            command=self._export_history,
            width=100
        )
        
        self.clear_history_button = self.theme.create_styled_button(
            self.control_frame,
            "🗑️ Очистить",
            'danger',
            command=self._clear_history,
            width=100
        )
        
        # Прогресс-бар для загрузки
        self.progress_bar = ProgressBar(
            self,
            **self.theme.get_progress_style()
        )
        
        # Панель статистики
        self.stats_frame = self.theme.create_styled_frame(self, 'card')
        
        self.stats_title = self.theme.create_styled_label(
            self.stats_frame,
            "📊 Статистика операций",
            'subtitle'
        )
        
        # Карточки статистики
        self.stats_cards_frame = self.theme.create_styled_frame(self.stats_frame, 'primary')
        
        self.total_operations_card = self._create_stat_card(
            self.stats_cards_frame,
            "📋 Всего операций",
            "0",
            'info'
        )
        
        self.successful_operations_card = self._create_stat_card(
            self.stats_cards_frame,
            "✅ Успешных",
            "0",
            'success'
        )
        
        self.failed_operations_card = self._create_stat_card(
            self.stats_cards_frame,
            "❌ С ошибками",
            "0",
            'error'
        )
        
        self.recent_activity_card = self._create_stat_card(
            self.stats_cards_frame,
            "🕒 За 24ч",
            "0",
            'warning'
        )
        
        # Панель истории
        self.history_frame = self.theme.create_styled_frame(self, 'card')
        
        self.history_title = self.theme.create_styled_label(
            self.history_frame,
            "📜 История операций",
            'subtitle'
        )
        
        # Заголовки таблицы
        self.table_header = self.theme.create_styled_frame(self.history_frame, 'secondary')
        
        self.header_date = self.theme.create_styled_label(
            self.table_header,
            "Дата",
            'primary'
        )
        
        self.header_type = self.theme.create_styled_label(
            self.table_header,
            "Тип",
            'primary'
        )
        
        self.header_description = self.theme.create_styled_label(
            self.table_header,
            "Описание",
            'primary'
        )
        
        self.header_status = self.theme.create_styled_label(
            self.table_header,
            "Статус",
            'primary'
        )
        
        self.header_duration = self.theme.create_styled_label(
            self.table_header,
            "Время",
            'primary'
        )
        
        self.header_actions = self.theme.create_styled_label(
            self.table_header,
            "Действия",
            'primary'
        )
        
        # Прокручиваемая область для таблицы
        self.table_scrollable = ctk.CTkScrollableFrame(
            self.history_frame,
            **self.theme.get_frame_style('primary')
        )
        
        # Детали операции
        self.details_frame = self.theme.create_styled_frame(self, 'card')
        
        self.details_title = self.theme.create_styled_label(
            self.details_frame,
            "🔍 Детали операции",
            'subtitle'
        )
        
        self.details_text = ctk.CTkTextbox(
            self.details_frame,
            height=200,
            **self.theme.get_text_style()
        )
        
        # Скрываем детали по умолчанию
        self.details_frame.pack_forget()
        
        # Скрываем кастомный период по умолчанию
        self.custom_period_frame.pack_forget()
    
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
        
        # Панель фильтров
        self.filters_frame.pack(fill='x', padx=20, pady=10)
        
        self.filters_title.pack(pady=(15, 10))
        
        # Период
        self.period_frame.pack(fill='x', padx=15, pady=5)
        
        period_row = self.theme.create_styled_frame(self.period_frame, 'primary')
        period_row.pack(fill='x', pady=5)
        
        self.period_label.pack(side='left')
        self.period_menu.pack(side='left', padx=(10, 0))
        
        # Кастомный период
        self.custom_period_frame.pack(fill='x', pady=(5, 0))
        
        self.start_date_label.pack(side='left', padx=(0, 5))
        self.start_date_entry.pack(side='left', padx=(0, 20))
        self.end_date_label.pack(side='left', padx=(0, 5))
        self.end_date_entry.pack(side='left')
        
        # Тип операции
        self.operation_frame.pack(fill='x', padx=15, pady=5)
        
        operation_row = self.theme.create_styled_frame(self.operation_frame, 'primary')
        operation_row.pack(fill='x', pady=5)
        
        self.operation_label.pack(side='left')
        self.operation_menu.pack(side='left', padx=(10, 20))
        
        self.status_label.pack(side='left')
        self.status_menu.pack(side='left', padx=(10, 0))
        
        # Кнопки управления
        self.control_frame.pack(fill='x', padx=15, pady=(10, 15))
        
        self.refresh_button.pack(side='left', padx=(0, 10))
        self.export_history_button.pack(side='left', padx=(0, 10))
        self.clear_history_button.pack(side='right')
        
        # Прогресс-бар
        self.progress_bar.pack(fill='x', padx=20, pady=10)
        
        # Статистика
        self.stats_frame.pack(fill='x', padx=20, pady=10)
        
        self.stats_title.pack(pady=(15, 10))
        
        self.stats_cards_frame.pack(fill='x', padx=15, pady=5)
        
        # Размещение карточек статистики в ряд
        self.total_operations_card['frame'].pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.successful_operations_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
        self.failed_operations_card['frame'].pack(side='left', fill='x', expand=True, padx=5)
        self.recent_activity_card['frame'].pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        # История
        self.history_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.history_title.pack(pady=(15, 10))
        
        # Заголовок таблицы        self.table_header.pack(fill='x', padx=15, pady=(0, 5))
        
        self.header_date.configure(width=140)
        self.header_date.pack(side='left')
        self.header_type.configure(width=100)
        self.header_type.pack(side='left')
        self.header_description.pack(side='left', fill='x', expand=True)
        self.header_status.configure(width=80)
        self.header_status.pack(side='left')
        self.header_duration.configure(width=80)
        self.header_duration.pack(side='left')
        self.header_actions.configure(width=100)
        self.header_actions.pack(side='left')
        
        # Прокручиваемая таблица
        self.table_scrollable.pack(fill='both', expand=True, padx=15, pady=(5, 15))
        
        # Детали операции
        self.details_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.details_title.pack(pady=(15, 10))
        self.details_text.pack(fill='x', padx=15, pady=(0, 15))
    
    def _on_period_changed(self, value: str) -> None:
        """Обработка изменения периода."""
        if value == "Кастом":
            self.custom_period_frame.pack(fill='x', pady=(5, 0))
            # Установка значений по умолчанию
            now = datetime.now()
            end_date = now.strftime('%Y-%m-%d')
            start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
            
            self.start_date_entry.delete(0, 'end')
            self.start_date_entry.insert(0, start_date)
            self.end_date_entry.delete(0, 'end')
            self.end_date_entry.insert(0, end_date)
        else:
            self.custom_period_frame.pack_forget()
        
        self._apply_filters()
    
    def _on_filter_changed(self, value: str = None) -> None:
        """Обработка изменения фильтров."""
        self._apply_filters()
    
    def _apply_filters(self) -> None:
        """Применение фильтров к истории."""
        if not self.current_history:
            return
        
        try:
            # Получение параметров фильтрации
            period_type = self.period_var.get()
            operation_type = self.operation_var.get()
            status_filter = self.status_var.get()
            
            # Определение временного диапазона
            start_date, end_date = self._get_date_range(period_type)
            
            # Фильтрация
            filtered = []
            for item in self.current_history:
                item_date = item.get('timestamp')
                if not isinstance(item_date, datetime):
                    continue
                
                # Фильтр по дате
                if start_date and item_date < start_date:
                    continue
                if end_date and item_date > end_date:
                    continue
                
                # Фильтр по типу операции
                if operation_type != "all":
                    operation_mapping = {
                        "analysis": "analysis",
                        "rewards": "rewards",
                        "export": "export",
                        "backup": "backup"
                    }
                    if item.get('operation_type') != operation_mapping.get(operation_type):
                        continue
                
                # Фильтр по статусу
                if status_filter != "all":
                    status_mapping = {
                        "Успешно": "success",
                        "Ошибка": "error",
                        "В процессе": "in_progress"
                    }
                    if item.get('status') != status_mapping.get(status_filter):
                        continue
                
                filtered.append(item)
            
            self.filtered_history = filtered
            self._update_history_table()
            self._update_statistics()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения фильтров истории: {e}")
    
    def _get_date_range(self, period_type: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Получение диапазона дат для фильтрации."""
        try:
            now = datetime.now()
            
            if period_type == "Кастом":
                start_str = self.start_date_entry.get()
                end_str = self.end_date_entry.get()
                
                if start_str and end_str:
                    start_date = datetime.strptime(start_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1)
                    return start_date, end_date
                
                return None, None
            
            elif period_type == "24 часа":
                return now - timedelta(hours=24), now
            elif period_type == "7 дней":
                return now - timedelta(days=7), now
            elif period_type == "30 дней":
                return now - timedelta(days=30), now
            elif period_type == "90 дней":
                return now - timedelta(days=90), now
            else:  # "Всё время"
                return None, None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения диапазона дат: {e}")
            return None, None
    
    def _load_initial_history(self) -> None:
        """Загрузка начальной истории."""
        try:
            # Создание демонстрационной истории
            self.current_history = self._create_demo_history()
            self.filtered_history = self.current_history
            self._update_history_table()
            self._update_statistics()
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки истории: {e}")
    
    def _create_demo_history(self) -> List[Dict[str, Any]]:
        """Создание демонстрационной истории."""
        import random
        
        history = []
        operations = [
            ("analysis", "Анализ участников стейкинга"),
            ("rewards", "Расчет наград"),
            ("export", "Экспорт данных"),
            ("backup", "Создание резервной копии")
        ]
        
        statuses = ["success", "error", "in_progress"]
        
        for i in range(20):
            op_type, description = random.choice(operations)
            status = random.choice(statuses)
            
            # Более высокая вероятность успешных операций
            if random.random() < 0.8:
                status = "success"
            
            timestamp = datetime.now() - timedelta(
                days=random.randint(0, 90),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            duration = random.randint(5, 300)  # секунды
            
            history.append({
                'id': f"op_{i+1}",
                'timestamp': timestamp,
                'operation_type': op_type,
                'description': description,
                'status': status,
                'duration': duration,
                'details': {
                    'participants_count': random.randint(10, 100) if op_type in ['analysis', 'rewards'] else None,
                    'total_amount': random.randint(1000, 50000) if op_type == 'rewards' else None,
                    'file_size': f"{random.randint(1, 10)}MB" if op_type in ['export', 'backup'] else None,
                    'error_message': "Таймаут подключения к блокчейну" if status == "error" else None
                }
            })
        
        # Сортировка по времени (новые сверху)
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return history
    
    def _refresh_history(self) -> None:
        """Обновление истории."""
        if self.loading_history:
            return
        
        try:
            self.loading_history = True
            self.refresh_button.configure(state='disabled')
            
            # Показать прогресс
            self.progress_bar.reset()
            self.progress_bar.set_indeterminate(True)
            self.progress_bar.start()
            
            # Имитация загрузки в отдельном потоке
            def refresh_thread():
                import time
                time.sleep(2)  # Имитация загрузки
                
                # Обновление данных
                self.current_history = self._create_demo_history()
                
                # Обновление UI в главном потоке
                self.after_idle(self._refresh_completed)
            
            threading.Thread(target=refresh_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления истории: {e}")
            self._refresh_completed(success=False, error=str(e))
    
    def _refresh_completed(self, success: bool = True, error: str = "") -> None:
        """Завершение обновления истории."""
        try:
            self.loading_history = False
            self.refresh_button.configure(state='normal')
            self.progress_bar.complete()
            
            if success:
                self._apply_filters()
                messagebox.showinfo("Успех", "История успешно обновлена!")
            else:
                messagebox.showerror("Ошибка", f"Не удалось обновить историю:\\n{error}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка завершения обновления: {e}")
    
    def _update_statistics(self) -> None:
        """Обновление статистики."""
        try:
            # Общее количество операций
            total = len(self.filtered_history)
            self.total_operations_card['value'].configure(text=str(total))
            
            # Успешные операции
            successful = len([h for h in self.filtered_history if h.get('status') == 'success'])
            self.successful_operations_card['value'].configure(text=str(successful))
            
            # Операции с ошибками
            failed = len([h for h in self.filtered_history if h.get('status') == 'error'])
            self.failed_operations_card['value'].configure(text=str(failed))
            
            # Операции за 24 часа
            recent_threshold = datetime.now() - timedelta(hours=24)
            recent = len([
                h for h in self.filtered_history 
                if h.get('timestamp') and h['timestamp'] > recent_threshold
            ])
            self.recent_activity_card['value'].configure(text=str(recent))
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")
    
    def _update_history_table(self) -> None:
        """Обновление таблицы истории."""
        try:
            # Очистка существующих строк
            for widget in self.table_scrollable.winfo_children():
                widget.destroy()
            
            # Добавление операций
            for i, item in enumerate(self.filtered_history[:50]):  # Ограничение для производительности
                self._create_history_row(item, i)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления таблицы истории: {e}")
    
    def _create_history_row(self, item: Dict[str, Any], index: int) -> None:
        """Создание строки истории в таблице."""
        try:
            # Фрейм строки
            row_style = 'secondary' if index % 2 == 0 else 'primary'
            row_frame = self.theme.create_styled_frame(self.table_scrollable, row_style)
            row_frame.pack(fill='x', pady=1)
            
            # Дата
            timestamp = item.get('timestamp')
            if isinstance(timestamp, datetime):
                date_str = timestamp.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = "Неизвестно"
            
            date_label = self.theme.create_styled_label(
                row_frame,
                date_str,
                'primary'
            )
            
            # Тип операции с иконкой
            op_type = item.get('operation_type', 'unknown')
            type_icons = {
                'analysis': '📊',
                'rewards': '🎁',
                'export': '💾',
                'backup': '🔄'
            }
            type_icon = type_icons.get(op_type, '❓')
            
            type_label = self.theme.create_styled_label(
                row_frame,
                type_icon,
                'primary'
            )
            
            # Описание
            description = item.get('description', 'Нет описания')
            description_label = self.theme.create_styled_label(
                row_frame,
                description[:50] + "..." if len(description) > 50 else description,
                'primary'
            )
            
            # Статус с цветом
            status = item.get('status', 'unknown')
            status_colors = {
                'success': 'success',
                'error': 'error',
                'in_progress': 'warning'
            }
            status_color = status_colors.get(status, 'primary')
            
            status_icons = {
                'success': '✅',
                'error': '❌',
                'in_progress': '⏳'
            }
            status_icon = status_icons.get(status, '❓')
            
            status_label = self.theme.create_styled_label(
                row_frame,
                status_icon,
                'primary'
            )
            status_label.configure(text_color=self.theme.get_status_color(status_color))
            
            # Длительность
            duration = item.get('duration', 0)
            if duration < 60:
                duration_text = f"{duration}с"
            elif duration < 3600:
                duration_text = f"{duration//60}м"
            else:
                duration_text = f"{duration//3600}ч"
            
            duration_label = self.theme.create_styled_label(
                row_frame,
                duration_text,
                'secondary'
            )
            
            # Кнопка деталей
            details_button = self.theme.create_styled_button(
                row_frame,
                "👁️",
                'info',
                command=lambda i=item: self._show_operation_details(i),
                width=30,
                height=25
            )
              # Размещение элементов
            date_label.configure(width=140)
            date_label.pack(side='left', padx=(10, 5))
            type_label.configure(width=100)
            type_label.pack(side='left', padx=5)
            description_label.pack(side='left', fill='x', expand=True, padx=5, anchor='w')
            status_label.configure(width=80)
            status_label.pack(side='left', padx=5)
            duration_label.configure(width=80)
            duration_label.pack(side='left', padx=5)
            details_button.configure(width=100)
            details_button.pack(side='left', padx=(5, 10))
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания строки истории: {e}")
    
    def _show_operation_details(self, item: Dict[str, Any]) -> None:
        """Отображение деталей операции."""
        try:
            # Показываем панель деталей
            self.details_frame.pack(fill='x', padx=20, pady=(0, 20))
            
            # Формирование текста деталей
            details_text = []
            details_text.append(f"🆔 ID операции: {item.get('id', 'Неизвестно')}")
            details_text.append(f"📅 Время: {item.get('timestamp', 'Неизвестно')}")
            details_text.append(f"🔧 Тип: {item.get('operation_type', 'Неизвестно')}")
            details_text.append(f"📝 Описание: {item.get('description', 'Нет описания')}")
            details_text.append(f"📊 Статус: {item.get('status', 'Неизвестно')}")
            details_text.append(f"⏱️ Длительность: {item.get('duration', 0)} секунд")
            details_text.append("")
            
            # Дополнительные детали
            details = item.get('details', {})
            if details:
                details_text.append("🔍 Дополнительная информация:")
                
                if details.get('participants_count'):
                    details_text.append(f"  👥 Участников: {details['participants_count']}")
                
                if details.get('total_amount'):
                    details_text.append(f"  💰 Общая сумма: {details['total_amount']} PLEX")
                
                if details.get('file_size'):
                    details_text.append(f"  📁 Размер файла: {details['file_size']}")
                
                if details.get('error_message'):
                    details_text.append(f"  ❌ Ошибка: {details['error_message']}")
            
            # Обновление текста
            self.details_text.delete("1.0", "end")
            self.details_text.insert("1.0", "\\n".join(details_text))
            
        except Exception as e:
            logger.error(f"❌ Ошибка отображения деталей: {e}")
    
    def _export_history(self) -> None:
        """Экспорт истории операций."""
        if not self.filtered_history:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        try:
            # Выбор файла для сохранения
            file_path = filedialog.asksaveasfilename(
                title="Экспорт истории операций",
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
                self._export_history_to_csv(file_path)
            elif file_path.endswith('.xlsx'):
                self._export_history_to_excel(file_path)
            elif file_path.endswith('.json'):
                self._export_history_to_json(file_path)
            else:
                self._export_history_to_csv(file_path)
            
            messagebox.showinfo("Успех", f"История экспортирована в:\\n{file_path}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта истории: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные:\\n{e}")
    
    def _export_history_to_csv(self, file_path: str) -> None:
        """Экспорт истории в CSV формат."""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'timestamp', 'operation_type', 'description', 
                'status', 'duration', 'participants_count', 'total_amount'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in self.filtered_history:
                details = item.get('details', {})
                
                writer.writerow({
                    'id': item.get('id', ''),
                    'timestamp': item.get('timestamp', '').isoformat() if item.get('timestamp') else '',
                    'operation_type': item.get('operation_type', ''),
                    'description': item.get('description', ''),
                    'status': item.get('status', ''),
                    'duration': item.get('duration', 0),
                    'participants_count': details.get('participants_count', ''),
                    'total_amount': details.get('total_amount', '')
                })
    
    def _export_history_to_excel(self, file_path: str) -> None:
        """Экспорт истории в Excel формат."""
        try:
            import pandas as pd
            
            # Подготовка данных
            data = []
            for item in self.filtered_history:
                details = item.get('details', {})
                
                data.append({
                    'ID': item.get('id', ''),
                    'Дата': item.get('timestamp', ''),
                    'Тип операции': item.get('operation_type', ''),
                    'Описание': item.get('description', ''),
                    'Статус': item.get('status', ''),
                    'Длительность (сек)': item.get('duration', 0),
                    'Участников': details.get('participants_count', ''),
                    'Сумма': details.get('total_amount', '')
                })
            
            # Создание DataFrame и сохранение
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
        except ImportError:
            # Fallback на CSV если pandas не установлен
            self._export_history_to_csv(file_path.replace('.xlsx', '.csv'))
    
    def _export_history_to_json(self, file_path: str) -> None:
        """Экспорт истории в JSON формат."""
        import json
        
        # Функция для сериализации datetime
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(
                {
                    'history': self.filtered_history,
                    'export_time': datetime.now().isoformat(),
                    'total_operations': len(self.filtered_history)
                },
                jsonfile,
                indent=2,
                default=default_serializer,
                ensure_ascii=False
            )
    
    def _clear_history(self) -> None:
        """Очистка истории операций."""
        try:
            result = messagebox.askquestion(
                "Подтверждение",
                "Вы уверены, что хотите очистить всю историю операций?\\n\\n"
                "Это действие нельзя отменить!"
            )
            
            if result == 'yes':
                self.current_history = []
                self.filtered_history = []
                self._update_history_table()
                self._update_statistics()
                
                # Скрываем панель деталей
                self.details_frame.pack_forget()
                
                messagebox.showinfo("Успех", "История операций очищена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки истории: {e}")
            messagebox.showerror("Ошибка", f"Не удалось очистить историю:\\n{e}")
    
    def set_history_manager(self, history_manager) -> None:
        """Установка менеджера истории."""
        self.history_manager = history_manager
        logger.debug("✅ HistoryManager установлен для HistoryTab")


# Экспорт для удобного импорта
__all__ = ['HistoryTab']


if __name__ == "__main__":
    # Демонстрация вкладки
    def demo_history_tab():
        """Демонстрация HistoryTab."""
        try:
            print("🧪 Демонстрация HistoryTab...")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX History Tab Demo")
            root.geometry("1400x900")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание вкладки истории
            history_tab = HistoryTab(root)
            history_tab.pack(fill='both', expand=True)
            
            print("✅ HistoryTab запущена. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_history_tab()
    print("💡 Для демонстрации HistoryTab раскомментируй последнюю строку")
