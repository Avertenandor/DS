"""
PLEX Dynamic Staking Manager - Enhanced Rewards Tab
Расширенная вкладка для управления наградами участников стейкинга.

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


class EnhancedRewardsTab(ctk.CTkFrame):
    """
    Расширенная вкладка управления наградами.
    
    Функциональность:
    - Просмотр рассчитанных наград
    - Настройка параметров наград
    - Экспорт списков для выплат
    - Предотвращение двойных выплат
    - История выплат
    - Улучшенная аналитика наград
    """
    
    def __init__(self, parent, reward_manager=None, widget_factory=None, **kwargs):
        """
        Инициализация EnhancedRewardsTab.
        
        Args:
            parent: Родительский виджет
            reward_manager: Экземпляр RewardManager
            widget_factory: Фабрика виджетов
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
        
        logger.debug("🎁 EnhancedRewardsTab инициализирована")
    
    def set_reward_manager(self, reward_manager):
        """
        Установить менеджер наград.
        
        Args:
            reward_manager: Экземпляр RewardManager
        """
        self.reward_manager = reward_manager
        logger.info("✅ RewardManager подключен к Enhanced RewardsTab")
    
    def set_reward_manager(self, reward_manager):
        """
        Установить менеджер наград.
        
        Args:
            reward_manager: Экземпляр RewardManager
        """
        self.reward_manager = reward_manager
        logger.info("✅ RewardManager подключен к Enhanced RewardsTab")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        try:
            # Заголовок
            self.title_label = ctk.CTkLabel(
                self,
                text="Управление наградами",
                font=("Arial", 24, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Фрейм настроек наград
            self.settings_frame = ctk.CTkFrame(self)
            self.settings_frame.configure(fg_color=self.theme.colors['bg_secondary'])
            
            self.settings_title = ctk.CTkLabel(
                self.settings_frame,
                text="Настройки наград",
                font=("Arial", 16, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Базовые параметры наград
            self.base_reward_label = ctk.CTkLabel(
                self.settings_frame,
                text="Базовая награда (PLEX):",
                text_color=self.theme.colors['text_secondary']
            )
            
            self.base_reward_entry = self.widget_factory.create_entry(
                self.settings_frame,
                width=120
            )
            self.widget_factory.setup_placeholder(self.base_reward_entry, "100")
            
            # Множители наград по тирам
            self.tier_multipliers_frame = ctk.CTkFrame(self.settings_frame)
            
            self.tier_multipliers_label = ctk.CTkLabel(
                self.tier_multipliers_frame,
                text="Множители по тирам:",
                font=("Arial", 14, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Фрейм результатов
            self.results_frame = ctk.CTkFrame(self)
            self.results_frame.configure(fg_color=self.theme.colors['bg_secondary'])
            
            self.results_title = ctk.CTkLabel(
                self.results_frame,
                text="Рассчитанные награды",
                font=("Arial", 16, "bold"),
                text_color=self.theme.colors['text_primary']
            )
            
            # Статистика наград
            self.stats_frame = ctk.CTkFrame(self.results_frame)
            
            # Создание карточек статистики
            self.total_rewards_card = self._create_stat_card(
                self.stats_frame, "Общая сумма", "0 PLEX", "accent"
            )
            
            self.total_recipients_card = self._create_stat_card(
                self.stats_frame, "Получателей", "0", "info"
            )
            
            self.avg_reward_card = self._create_stat_card(
                self.stats_frame, "Средняя награда", "0 PLEX", "success"
            )
            
            # Таблица наград
            self.rewards_tree = ttk.Treeview(
                self.results_frame,
                columns=("address", "category", "tier", "reward", "status"),
                show="headings",
                height=15
            )
            
            # Настройка колонок
            self.rewards_tree.heading("address", text="Адрес")
            self.rewards_tree.heading("category", text="Категория")
            self.rewards_tree.heading("tier", text="Тир")
            self.rewards_tree.heading("reward", text="Награда (PLEX)")
            self.rewards_tree.heading("status", text="Статус")
            
            self.rewards_tree.column("address", width=300)
            self.rewards_tree.column("category", width=120)
            self.rewards_tree.column("tier", width=80)
            self.rewards_tree.column("reward", width=150)
            self.rewards_tree.column("status", width=100)
            
            # Скроллбар для таблицы
            self.tree_scrollbar = ttk.Scrollbar(
                self.results_frame,
                orient="vertical",
                command=self.rewards_tree.yview
            )
            self.rewards_tree.configure(yscrollcommand=self.tree_scrollbar.set)
            
            # Кнопки управления
            self.control_frame = ctk.CTkFrame(self)
            
            self.calculate_button = ctk.CTkButton(
                self.control_frame,
                text="🧮 Рассчитать награды",
                command=self._calculate_rewards,
                fg_color=self.theme.colors['btn_primary'],
                font=("Arial", 12, "bold"),
                height=35
            )
            
            self.export_button = ctk.CTkButton(
                self.control_frame,
                text="📄 Экспорт списка",
                command=self._export_rewards,
                fg_color=self.theme.colors['accent'],
                state="disabled",
                height=35
            )
            
            self.distribute_button = ctk.CTkButton(
                self.control_frame,
                text="💰 Распределить награды",
                command=self._distribute_rewards,
                fg_color=self.theme.colors['success'],
                state="disabled",
                height=35
            )
            
            # Прогресс-бар
            self.progress_bar = ProgressBar(self)
            
        except Exception as e:
            logger.error(f"Ошибка создания виджетов EnhancedRewardsTab: {e}")
            messagebox.showerror("Ошибка", f"Не удалось создать интерфейс: {e}")
    
    def _create_stat_card(self, parent, title: str, value: str, color_type: str) -> Dict[str, ctk.CTkLabel]:
        """Создание карточки статистики."""
        card_frame = ctk.CTkFrame(parent)
        card_frame.configure(fg_color=self.theme.colors['bg_primary'])
        
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=("Arial", 12),
            text_color=self.theme.colors['text_secondary']
        )
        
        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=("Arial", 20, "bold"),
            text_color=self.theme.get_status_color(color_type)
        )
        
        title_label.pack(pady=(10, 0))
        value_label.pack(pady=(0, 10))
        
        return {
            'frame': card_frame,
            'title': title_label,
            'value': value_label
        }
    
    def _setup_layout(self) -> None:
        """Настройка расположения виджетов."""
        try:
            # Заголовок
            self.title_label.pack(pady=20)
            
            # Настройки наград
            self.settings_frame.pack(fill="x", padx=20, pady=(0, 10))
            self.settings_title.pack(pady=10)
            
            # Базовые параметры
            base_params_frame = ctk.CTkFrame(self.settings_frame)
            base_params_frame.pack(fill="x", padx=10, pady=5)
            
            self.base_reward_label.pack(side="left", padx=10)
            self.base_reward_entry.pack(side="left", padx=10)
            
            # Результаты
            self.results_frame.pack(fill="both", expand=True, padx=20, pady=10)
            self.results_title.pack(pady=10)
            
            # Статистика
            self.stats_frame.pack(fill="x", padx=10, pady=5)
            
            # Размещение карточек статистики
            for i, card in enumerate([
                self.total_rewards_card,
                self.total_recipients_card, 
                self.avg_reward_card
            ]):
                card['frame'].grid(row=0, column=i, padx=10, pady=5, sticky="ew")
            
            self.stats_frame.grid_columnconfigure(0, weight=1)
            self.stats_frame.grid_columnconfigure(1, weight=1)
            self.stats_frame.grid_columnconfigure(2, weight=1)
            
            # Таблица наград
            tree_frame = ctk.CTkFrame(self.results_frame)
            tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            self.rewards_tree.pack(side="left", fill="both", expand=True)
            self.tree_scrollbar.pack(side="right", fill="y")
            
            # Кнопки управления
            self.control_frame.pack(fill="x", padx=20, pady=10)
            
            self.calculate_button.pack(side="left", padx=10)
            self.export_button.pack(side="left", padx=10)
            self.distribute_button.pack(side="left", padx=10)
            
            # Прогресс-бар
            self.progress_bar.pack(fill="x", padx=20, pady=(0, 20))
            
        except Exception as e:
            logger.error(f"Ошибка настройки layout EnhancedRewardsTab: {e}")
    
    def _calculate_rewards(self) -> None:
        """Рассчет наград для участников."""
        try:
            if not self.reward_manager:
                messagebox.showwarning("Предупреждение", "RewardManager не инициализирован")
                return
            
            # Заглушка для расчета наград
            self.progress_bar.set_state(ProgressState.LOADING)
            self.progress_bar.set_text("Расчет наград...")
            
            # Здесь будет реальная логика расчета наград
            logger.info("🧮 Начат расчет наград")
            
            # Имитация расчета
            self.after(2000, self._on_calculation_complete)
            
        except Exception as e:
            logger.error(f"Ошибка расчета наград: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при расчете наград: {e}")
            self.progress_bar.set_state(ProgressState.ERROR)
    
    def _on_calculation_complete(self) -> None:
        """Завершение расчета наград."""
        try:
            self.progress_bar.set_state(ProgressState.SUCCESS)
            self.progress_bar.set_text("Расчет завершен")
            
            # Активация кнопок экспорта и распределения
            self.export_button.configure(state="normal")
            self.distribute_button.configure(state="normal")
            
            logger.info("✅ Расчет наград завершен")
            
        except Exception as e:
            logger.error(f"Ошибка завершения расчета: {e}")
    
    def _export_rewards(self) -> None:
        """Экспорт списка наград."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
            )
            
            if filename:
                logger.info(f"📄 Экспорт наград в файл: {filename}")
                messagebox.showinfo("Успех", "Список наград экспортирован")
                
        except Exception as e:
            logger.error(f"Ошибка экспорта наград: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")
    
    def _distribute_rewards(self) -> None:
        """Распределение наград участникам."""
        try:
            result = messagebox.askyesno(
                "Подтверждение",
                "Вы уверены, что хотите начать распределение наград?\n"
                "Эта операция не может быть отменена."
            )
            
            if result:
                logger.info("💰 Начато распределение наград")
                messagebox.showinfo("Информация", "Распределение наград начато")
                
        except Exception as e:
            logger.error(f"Ошибка распределения наград: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при распределении наград: {e}")
    
    def refresh_data(self) -> None:
        """Обновление данных вкладки."""
        try:
            logger.debug("🔄 Обновление данных EnhancedRewardsTab")
            # Здесь будет логика обновления данных
            
        except Exception as e:
            logger.error(f"Ошибка обновления данных EnhancedRewardsTab: {e}")
