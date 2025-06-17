"""
PLEX Dynamic Staking Manager - Participants Table
Компонент для отображения таблицы участников стейкинга.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, Menu
from typing import Dict, List, Optional, Any, Callable
import customtkinter as ctk
from decimal import Decimal
from datetime import datetime

from ui.themes.dark_theme import get_theme
from utils.logger import get_logger
from utils.converters import format_number

logger = get_logger(__name__)


class ParticipantsTable(ctk.CTkFrame):
    """
    Таблица участников стейкинга с возможностью сортировки, 
    фильтрации и выполнения действий.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Инициализация таблицы участников.
        
        Args:
            parent: Родительский виджет
            **kwargs: Дополнительные параметры
        """
        super().__init__(parent, **kwargs)
        
        self.theme = get_theme()
        self.participants_data = []
        self.filtered_data = []
        self.selected_participant = None
        
        # Колбэки для действий
        self.on_participant_select: Optional[Callable] = None
        self.on_participant_details: Optional[Callable] = None
        self.on_amnesty_request: Optional[Callable] = None
        self.on_reward_send: Optional[Callable] = None
        
        # Настройки сортировки
        self.sort_column = None
        self.sort_reverse = False
        
        # Создание интерфейса
        self._create_interface()
        
        logger.debug("✅ ParticipantsTable инициализирована")
    
    def _create_interface(self):
        """Создание интерфейса таблицы."""
        # Заголовок с кнопками действий
        self._create_header()
        
        # Панель фильтров
        self._create_filters()
        
        # Основная таблица
        self._create_table()
        
        # Статус бар
        self._create_status_bar()
    
    def _create_header(self):
        """Создание заголовка с кнопками действий."""
        header_frame = ctk.CTkFrame(self)
        header_frame.configure(fg_color="transparent")
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # Заголовок
        title_label = ctk.CTkLabel(
            header_frame,
            text="👥 Участники стейкинга",
            font=("Arial", 16, "bold"),
            text_color=self.theme.colors['text_primary']
        )
        title_label.pack(side='left')
        
        # Кнопки действий
        actions_frame = ctk.CTkFrame(header_frame)
        actions_frame.configure(fg_color="transparent")
        actions_frame.pack(side='right')
        
        # Кнопка "Детали"
        self.details_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Детали",
            command=self._show_participant_details,
            fg_color=self.theme.colors['btn_secondary'],
            width=100,
            height=30,
            state="disabled"
        )
        self.details_btn.pack(side='left', padx=(0, 5))
        
        # Кнопка "Амнистия"
        self.amnesty_btn = ctk.CTkButton(
            actions_frame,
            text="🤝 Амнистия",
            command=self._request_amnesty,
            fg_color=self.theme.colors['warning'],
            width=100,
            height=30,
            state="disabled"
        )
        self.amnesty_btn.pack(side='left', padx=(0, 5))
        
        # Кнопка "Награда"
        self.reward_btn = ctk.CTkButton(
            actions_frame,
            text="🎁 Награда",
            command=self._send_reward,
            fg_color=self.theme.colors['success'],
            width=100,
            height=30,
            state="disabled"
        )
        self.reward_btn.pack(side='left')
    
    def _create_filters(self):
        """Создание панели фильтров."""
        filters_frame = ctk.CTkFrame(self)
        filters_frame.configure(fg_color=self.theme.colors['bg_secondary'])
        filters_frame.pack(fill='x', padx=10, pady=5)
        
        # Поиск по адресу
        search_label = ctk.CTkLabel(
            filters_frame,
            text="🔍 Поиск:",
            text_color=self.theme.colors['text_secondary']
        )
        search_label.pack(side='left', padx=(10, 5), pady=10)
        
        self.search_entry = ctk.CTkEntry(
            filters_frame,
            placeholder_text="Введите адрес или часть адреса...",
            width=300,
            height=30
        )
        self.search_entry.pack(side='left', padx=(0, 10), pady=10)
        self.search_entry.bind('<KeyRelease>', self._on_search_change)
        
        # Фильтр по категории
        category_label = ctk.CTkLabel(
            filters_frame,
            text="📂 Категория:",
            text_color=self.theme.colors['text_secondary']
        )
        category_label.pack(side='left', padx=(10, 5), pady=10)
        
        self.category_filter = ctk.CTkOptionMenu(
            filters_frame,
            values=["Все", "Идеальные", "Пропуски", "Продажи", "Переводы"],
            command=self._on_filter_change,
            width=150,
            height=30
        )
        self.category_filter.pack(side='left', padx=(0, 10), pady=10)
        
        # Кнопка сброса фильтров
        reset_btn = ctk.CTkButton(
            filters_frame,
            text="🔄 Сброс",
            command=self._reset_filters,
            fg_color=self.theme.colors['btn_secondary'],
            width=80,
            height=30
        )
        reset_btn.pack(side='right', padx=10, pady=10)
    
    def _create_table(self):
        """Создание основной таблицы."""
        table_frame = ctk.CTkFrame(self)
        table_frame.configure(fg_color=self.theme.colors['bg_tertiary'])
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Создание Treeview для таблицы
        columns = ('address', 'balance', 'category', 'status', 'contribution', 'last_activity')
        
        self.tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show='headings',
            height=15
        )
        
        # Настройка заголовков колонок
        headers = {
            'address': '📍 Адрес',
            'balance': '💰 Баланс',
            'category': '📂 Категория', 
            'status': '🔄 Статус',
            'contribution': '📊 Вклад',
            'last_activity': '⏰ Активность'
        }
        
        for col in columns:
            self.tree.heading(
                col, 
                text=headers[col],
                command=lambda c=col: self._sort_by_column(c)
            )
            
        # Настройка ширины колонок
        column_widths = {
            'address': 200,
            'balance': 120,
            'category': 100,
            'status': 100,
            'contribution': 100,
            'last_activity': 150
        }
        
        for col in columns:
            self.tree.column(col, width=column_widths[col], anchor='center')
        
        # Scrollbar для таблицы
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Упаковка элементов
        self.tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side='right', fill='y', pady=10, padx=(0, 10))
        
        # Привязка событий
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        
        # Контекстное меню
        self._create_context_menu()
        
        # Заглушка если нет данных
        self.no_data_label = ctk.CTkLabel(
            table_frame,
            text="📋 Нет данных для отображения\\n\\nЗапустите анализ участников для загрузки данных",
            font=("Arial", 14),
            text_color=self.theme.colors['text_muted'],
            justify='center'
        )
    
    def _create_context_menu(self):
        """Создание контекстного меню для таблицы."""
        self.context_menu = Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="📋 Показать детали", command=self._show_participant_details)
        self.context_menu.add_command(label="📋 Копировать адрес", command=self._copy_address)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🤝 Запросить амнистию", command=self._request_amnesty)
        self.context_menu.add_command(label="🎁 Отправить награду", command=self._send_reward)
        
        self.tree.bind("<Button-3>", self._show_context_menu)  # Правая кнопка мыши
    
    def _create_status_bar(self):
        """Создание статус бара."""
        status_frame = ctk.CTkFrame(self)
        status_frame.configure(fg_color=self.theme.colors['bg_secondary'])
        status_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="📊 Участников: 0 | Отфильтровано: 0 | Выбрано: нет",
            text_color=self.theme.colors['text_secondary']
        )
        self.status_label.pack(side='left', padx=10, pady=5)
        
        # Кнопка экспорта
        export_btn = ctk.CTkButton(
            status_frame,
            text="📄 Экспорт",
            command=self._export_data,
            fg_color=self.theme.colors['btn_secondary'],
            width=100,
            height=25
        )
        export_btn.pack(side='right', padx=10, pady=5)
    
    def update_participants(self, participants_data: List[Dict[str, Any]]):
        """
        Обновление данных участников.
        
        Args:
            participants_data: Список данных участников
        """
        try:
            self.participants_data = participants_data
            self.filtered_data = participants_data.copy()
            
            # Очистка таблицы
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            if not participants_data:
                # Показать заглушку
                self.no_data_label.place(relx=0.5, rely=0.5, anchor='center')
            else:
                # Скрыть заглушку
                self.no_data_label.place_forget()
                
                # Заполнение таблицы
                for participant in participants_data:
                    self._add_participant_to_tree(participant)
            
            self._update_status_bar()
            
            logger.info(f"📊 Таблица участников обновлена: {len(participants_data)} записей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления таблицы участников: {e}")
            messagebox.showerror("Ошибка", f"Не удалось обновить таблицу:\\n{e}")
    
    def _add_participant_to_tree(self, participant: Dict[str, Any]):
        """Добавление участника в таблицу."""
        try:
            # Подготовка данных для отображения
            address = participant.get('address', 'N/A')
            balance = format_number(participant.get('balance', 0), 2) + ' PLEX'
            category = participant.get('category', 'Неизвестно')
            status = participant.get('status', 'Неизвестно')
            
            # Расчет вклада в процентах
            contribution = participant.get('contribution_percent', 0)
            contribution_str = f"{contribution:.1f}%"
            
            # Последняя активность
            last_activity = participant.get('last_activity', 'Неизвестно')
            if isinstance(last_activity, datetime):
                last_activity = last_activity.strftime('%Y-%m-%d %H:%M')
            
            # Сокращение адреса для отображения
            short_address = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
            
            # Вставка в таблицу
            item_id = self.tree.insert('', 'end', values=(
                short_address,
                balance,
                category,
                status,
                contribution_str,
                last_activity
            ))
            
            # Сохранение полных данных участника
            self.tree.item(item_id, tags=[address])
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления участника {participant.get('address', 'N/A')}: {e}")
    
    def _on_tree_select(self, event):
        """Обработка выбора участника в таблице."""
        try:
            selection = self.tree.selection()
            if selection:
                item_id = selection[0]
                tags = self.tree.item(item_id, 'tags')
                if tags:
                    address = tags[0]
                    
                    # Поиск полных данных участника
                    self.selected_participant = None
                    for participant in self.filtered_data:
                        if participant.get('address') == address:
                            self.selected_participant = participant
                            break
                    
                    # Активация кнопок
                    self.details_btn.configure(state="normal")
                    
                    # Условная активация кнопок амнистии и наград
                    if self.selected_participant:
                        category = self.selected_participant.get('category', '')
                        if 'пропуск' in category.lower() or 'перевод' in category.lower():
                            self.amnesty_btn.configure(state="normal")
                        else:
                            self.amnesty_btn.configure(state="disabled")
                            
                        if category.lower() == 'идеальные':
                            self.reward_btn.configure(state="normal")
                        else:
                            self.reward_btn.configure(state="disabled")
                    
                    # Вызов колбэка
                    if self.on_participant_select:
                        self.on_participant_select(self.selected_participant)
                        
                    self._update_status_bar()
            else:
                # Деактивация кнопок при снятии выбора
                self._deactivate_buttons()
                self.selected_participant = None
                self._update_status_bar()
                
        except Exception as e:
            logger.error(f"❌ Ошибка выбора участника: {e}")
    
    def _on_tree_double_click(self, event):
        """Обработка двойного клика - показ деталей."""
        self._show_participant_details()
    
    def _show_context_menu(self, event):
        """Показ контекстного меню."""
        try:
            # Выбираем элемент под курсором
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"❌ Ошибка показа контекстного меню: {e}")
    
    def _deactivate_buttons(self):
        """Деактивация всех кнопок действий."""
        self.details_btn.configure(state="disabled")
        self.amnesty_btn.configure(state="disabled")
        self.reward_btn.configure(state="disabled")
    
    def _show_participant_details(self):
        """Показ деталей участника."""
        if self.selected_participant and self.on_participant_details:
            self.on_participant_details(self.selected_participant)
        else:
            messagebox.showinfo("Детали", "Выберите участника для просмотра деталей")
    
    def _request_amnesty(self):
        """Запрос амнистии для участника."""
        if self.selected_participant and self.on_amnesty_request:
            self.on_amnesty_request(self.selected_participant)
        else:
            messagebox.showinfo("Амнистия", "Выберите участника для запроса амнистии")
    
    def _send_reward(self):
        """Отправка награды участнику."""
        if self.selected_participant and self.on_reward_send:
            self.on_reward_send(self.selected_participant)
        else:
            messagebox.showinfo("Награда", "Выберите участника для отправки награды")
    
    def _copy_address(self):
        """Копирование адреса в буфер обмена."""
        if self.selected_participant:
            address = self.selected_participant.get('address', '')
            self.clipboard_clear()
            self.clipboard_append(address)
            messagebox.showinfo("Скопировано", f"Адрес скопирован в буфер обмена:\\n{address}")
    
    def _on_search_change(self, event):
        """Обработка изменения поискового запроса."""
        self._apply_filters()
    
    def _on_filter_change(self, value):
        """Обработка изменения фильтра категории."""
        self._apply_filters()
    
    def _apply_filters(self):
        """Применение фильтров к данным."""
        try:
            search_text = self.search_entry.get().lower()
            category_filter = self.category_filter.get()
            
            # Фильтрация данных
            self.filtered_data = []
            for participant in self.participants_data:
                # Фильтр по поисковому запросу
                address = participant.get('address', '').lower()
                if search_text and search_text not in address:
                    continue
                
                # Фильтр по категории
                if category_filter != "Все":
                    category = participant.get('category', '')
                    if category_filter.lower() not in category.lower():
                        continue
                
                self.filtered_data.append(participant)
            
            # Обновление таблицы
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            for participant in self.filtered_data:
                self._add_participant_to_tree(participant)
                
            self._update_status_bar()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения фильтров: {e}")
    
    def _reset_filters(self):
        """Сброс всех фильтров."""
        self.search_entry.delete(0, 'end')
        self.category_filter.set("Все")
        self._apply_filters()
    
    def _sort_by_column(self, column):
        """Сортировка по колонке."""
        try:
            # Переключение направления сортировки
            if self.sort_column == column:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_column = column
                self.sort_reverse = False
            
            # Сортировка данных
            if column == 'address':
                self.filtered_data.sort(key=lambda x: x.get('address', ''), reverse=self.sort_reverse)
            elif column == 'balance':
                self.filtered_data.sort(key=lambda x: float(x.get('balance', 0)), reverse=self.sort_reverse)
            elif column == 'category':
                self.filtered_data.sort(key=lambda x: x.get('category', ''), reverse=self.sort_reverse)
            elif column == 'contribution':
                self.filtered_data.sort(key=lambda x: float(x.get('contribution_percent', 0)), reverse=self.sort_reverse)
            
            # Обновление таблицы
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            for participant in self.filtered_data:
                self._add_participant_to_tree(participant)
                
            logger.debug(f"📊 Таблица отсортирована по {column}, обратно: {self.sort_reverse}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сортировки по {column}: {e}")
    
    def _update_status_bar(self):
        """Обновление статус бара."""
        total_count = len(self.participants_data)
        filtered_count = len(self.filtered_data)
        selected_text = f"выбран {self.selected_participant.get('address', 'N/A')[:10]}..." if self.selected_participant else "нет"
        
        status_text = f"📊 Участников: {total_count} | Отфильтровано: {filtered_count} | Выбрано: {selected_text}"
        self.status_label.configure(text=status_text)
    
    def _export_data(self):
        """Экспорт данных в файл."""
        try:
            from tkinter import filedialog
            import json
            
            if not self.filtered_data:
                messagebox.showwarning("Экспорт", "Нет данных для экспорта")
                return
            
            # Выбор файла для сохранения
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Сохранить данные участников"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.filtered_data, f, indent=2, ensure_ascii=False, default=str)
                
                messagebox.showinfo("Экспорт", f"Данные успешно экспортированы в:\\n{filename}")
                logger.info(f"📄 Данные участников экспортированы в {filename}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта данных: {e}")
            messagebox.showerror("Ошибка экспорта", f"Не удалось экспортировать данные:\\n{e}")
    
    def set_callbacks(self, on_select=None, on_details=None, on_amnesty=None, on_reward=None):
        """
        Установка колбэков для действий с участниками.
        
        Args:
            on_select: Колбэк при выборе участника
            on_details: Колбэк для показа деталей
            on_amnesty: Колбэк для запроса амнистии
            on_reward: Колбэк для отправки награды
        """
        self.on_participant_select = on_select
        self.on_participant_details = on_details
        self.on_amnesty_request = on_amnesty
        self.on_reward_send = on_reward
        
        logger.debug("✅ Колбэки для ParticipantsTable установлены")
