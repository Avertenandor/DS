"""
Модуль: Главное окно PLEX Dynamic Staking Manager (Версия 3)
Описание: Полностью интегрированный UI с новыми модулями анализа
Автор: GitHub Copilot
"""

import tkinter as tk
from typing import Dict, List, Optional, Callable
import threading
import queue
import json
from datetime import datetime, timedelta
from decimal import Decimal

try:
    import customtkinter as ctk
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False

from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory
from config.constants import *
from config.settings import settings
from blockchain.node_client import Web3Manager
from core.participant_analyzer_v2 import ParticipantAnalyzer
from core.reward_manager import RewardManager
from core.category_analyzer import CategoryAnalyzer
from core.eligibility import EligibilityEngine
from core.amnesty_manager import AmnestyManager

logger = get_logger("PLEX_UI_V3")

# Темная тема UI
UI_COLORS = {
    'bg_primary': '#212121',
    'bg_secondary': '#2A2A2A',
    'bg_tertiary': '#333333',
    'accent': '#10A37F',
    'accent_hover': '#0E8F6F',
    'text_primary': '#ECECEC',
    'text_secondary': '#A0A0A0',
    'error': '#EF4444',
    'warning': '#F59E0B',
    'success': '#10B981',
    'border': '#404040'
}

class PLEXStakingUI_V3:
    """Главное окно PLEX Dynamic Staking Manager V3"""
    
    def __init__(self):
        """Инициализация UI"""
        if not UI_AVAILABLE:
            raise ImportError("CustomTkinter не установлен")
        
        self.logger = logger
        self.log_queue = queue.Queue()
        
        # Инициализация компонентов системы
        self.web3_manager = Web3Manager()
        self.participant_analyzer = ParticipantAnalyzer()
        self.reward_manager = RewardManager()
        self.category_analyzer = CategoryAnalyzer()
        self.eligibility_calculator = EligibilityEngine()
        self.amnesty_manager = AmnestyManager()
        
        # Состояние приложения
        self.current_analysis_results = None
        self.connection_status = False
        self.analysis_running = False
        
        # Настройка темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        # Создание основного окна
        self.root = ctk.CTk()
        self.root.title("PLEX Dynamic Staking Manager v3.0.0")
        self.root.geometry("1600x1000")
        self.root.configure(fg_color=UI_COLORS['bg_primary'])
        
        # Центрирование окна
        self._center_window()
        
        self.logger.info("🎨 Инициализация UI V3...")
        self._create_ui()
        self.logger.info("✅ UI V3 создан")

    def _center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (1000 // 2)
        self.root.geometry(f"1600x1000+{x}+{y}")

    def _create_ui(self):
        """Создание интерфейса"""
        # Заголовок
        self._create_header()
        
        # Основной контейнер с вкладками
        self._create_main_container()
        
        # Статус бар
        self._create_status_bar()

    def _create_header(self):
        """Создание заголовка"""
        header_frame = ctk.CTkFrame(
            self.root,
            height=80,
            fg_color=UI_COLORS['bg_secondary'],
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        # Логотип и заголовок
        title_label = ctk.CTkLabel(
            header_frame,
            text="🚀 PLEX Dynamic Staking Manager",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(side="left", padx=20, pady=20)
        
        # Статус подключения
        self.connection_label = ctk.CTkLabel(
            header_frame,
            text="🔴 Отключен",
            font=ctk.CTkFont(size=14),
            text_color=UI_COLORS['error']
        )
        self.connection_label.pack(side="right", padx=20, pady=20)
        
        # Кнопка подключения
        self.connect_button = ctk.CTkButton(
            header_frame,
            text="Подключиться",
            command=self._connect_to_blockchain,
            width=120,
            height=32,
            fg_color=UI_COLORS['accent'],
            hover_color=UI_COLORS['accent_hover']
        )
        self.connect_button.pack(side="right", padx=(0, 10), pady=20)

    def _create_main_container(self):
        """Создание основного контейнера с вкладками"""
        # Notebook для вкладок
        self.notebook = ctk.CTkTabview(
            self.root,
            fg_color=UI_COLORS['bg_secondary'],
            segmented_button_fg_color=UI_COLORS['bg_tertiary'],
            segmented_button_selected_color=UI_COLORS['accent'],
            text_color=UI_COLORS['text_primary']
        )
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # Создание вкладок
        self._create_analysis_tab()
        self._create_participants_tab()
        self._create_rewards_tab()
        self._create_categories_tab()
        self._create_eligibility_tab()
        self._create_amnesty_tab()
        self._create_logs_tab()

    def _create_analysis_tab(self):
        """Вкладка анализа"""
        tab = self.notebook.add("📊 Анализ")
        
        # Левая панель - настройки анализа
        left_frame = ctk.CTkFrame(tab, width=400, fg_color=UI_COLORS['bg_tertiary'])
        left_frame.pack(side="left", fill="y", padx=(10, 5), pady=10)
        left_frame.pack_propagate(False)
        
        # Заголовок
        ctk.CTkLabel(
            left_frame,
            text="⚙️ Настройки анализа",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=(20, 10))
        
        # Период анализа
        period_frame = ctk.CTkFrame(left_frame, fg_color=UI_COLORS['bg_secondary'])
        period_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            period_frame,
            text="Период анализа:",
            font=ctk.CTkFont(size=14),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=(10, 5))
        
        self.period_var = tk.StringVar(value="1_day")
        periods = [
            ("Последний час", "1_hour"),
            ("Последний день", "1_day"),
            ("Последняя неделя", "1_week"),
            ("Последний месяц", "1_month"),
            ("Пользовательский", "custom")
        ]
        
        for text, value in periods:
            ctk.CTkRadioButton(
                period_frame,
                text=text,
                variable=self.period_var,
                value=value,
                text_color=UI_COLORS['text_primary']
            ).pack(anchor="w", padx=10, pady=2)
        
        # Кнопка запуска анализа
        self.analyze_button = ctk.CTkButton(
            left_frame,
            text="🔍 Начать анализ",
            command=self._start_analysis,
            width=200,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=UI_COLORS['accent'],
            hover_color=UI_COLORS['accent_hover']
        )
        self.analyze_button.pack(pady=20)
        
        # Прогресс-бар
        self.progress_bar = ctk.CTkProgressBar(
            left_frame,
            width=300,
            height=20,
            fg_color=UI_COLORS['bg_secondary'],
            progress_color=UI_COLORS['accent']
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            left_frame,
            text="Готов к анализу",
            font=ctk.CTkFont(size=12),
            text_color=UI_COLORS['text_secondary']
        )
        self.progress_label.pack(pady=5)
        
        # Правая панель - результаты
        right_frame = ctk.CTkFrame(tab, fg_color=UI_COLORS['bg_tertiary'])
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        ctk.CTkLabel(
            right_frame,
            text="📈 Результаты анализа",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=(20, 10))
        
        # Текстовое поле для результатов
        self.results_text = ctk.CTkTextbox(
            right_frame,
            width=600,
            height=400,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary'],
            wrap="word"
        )
        self.results_text.pack(fill="both", expand=True, padx=20, pady=20)

    def _create_participants_tab(self):
        """Вкладка участников"""
        tab = self.notebook.add("👥 Участники")
        
        # Фильтры
        filter_frame = ctk.CTkFrame(tab, height=100, fg_color=UI_COLORS['bg_tertiary'])
        filter_frame.pack(fill="x", padx=10, pady=10)
        filter_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            filter_frame,
            text="🔍 Фильтры участников",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(side="left", padx=20, pady=20)
        
        # Фильтр по категории
        self.category_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["Все", "Whale", "Active_Trader", "Regular_User", "Holder", "Newcomer"],
            command=self._filter_participants
        )
        self.category_filter.pack(side="left", padx=10, pady=20)
        
        # Таблица участников
        self.participants_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.participants_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_rewards_tab(self):
        """Вкладка наград"""
        tab = self.notebook.add("🏆 Награды")
        
        # Панель управления наградами
        control_frame = ctk.CTkFrame(tab, height=120, fg_color=UI_COLORS['bg_tertiary'])
        control_frame.pack(fill="x", padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            control_frame,
            text="🎯 Управление наградами",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=10)
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            buttons_frame,
            text="💰 Рассчитать награды",
            command=self._calculate_rewards,
            width=150,
            fg_color=UI_COLORS['accent'],
            hover_color=UI_COLORS['accent_hover']
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="📊 Экспорт наград",
            command=self._export_rewards,
            width=150,
            fg_color=UI_COLORS['warning']
        ).pack(side="left", padx=5)
        
        # Результаты наград
        self.rewards_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.rewards_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_categories_tab(self):
        """Вкладка категорий"""
        tab = self.notebook.add("📂 Категории")
        
        # Статистика по категориям
        stats_frame = ctk.CTkFrame(tab, height=150, fg_color=UI_COLORS['bg_tertiary'])
        stats_frame.pack(fill="x", padx=10, pady=10)
        stats_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            stats_frame,
            text="📊 Статистика категорий",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=10)
        
        # Детали категорий
        self.categories_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.categories_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_eligibility_tab(self):
        """Вкладка права на получение наград"""
        tab = self.notebook.add("✅ Eligibility")
        
        # Критерии eligibility
        criteria_frame = ctk.CTkFrame(tab, height=200, fg_color=UI_COLORS['bg_tertiary'])
        criteria_frame.pack(fill="x", padx=10, pady=10)
        criteria_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            criteria_frame,
            text="📋 Критерии Eligibility",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=10)
        
        # Список квалифицированных
        self.eligibility_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.eligibility_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_amnesty_tab(self):
        """Вкладка амнистий"""
        tab = self.notebook.add("🕊️ Амнистии")
        
        # Управление амнистиями
        control_frame = ctk.CTkFrame(tab, height=100, fg_color=UI_COLORS['bg_tertiary'])
        control_frame.pack(fill="x", padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        ctk.CTkLabel(
            control_frame,
            text="🕊️ Управление амнистиями",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        ).pack(pady=20)
        
        # Результаты амнистий
        self.amnesty_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.amnesty_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_logs_tab(self):
        """Вкладка логов"""
        tab = self.notebook.add("📝 Логи")
        
        # Живые логи
        self.logs_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=UI_COLORS['bg_secondary'],
            text_color=UI_COLORS['text_primary']
        )
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=10)

    def _create_status_bar(self):
        """Создание статус-бара"""
        status_frame = ctk.CTkFrame(
            self.root,
            height=30,
            fg_color=UI_COLORS['bg_secondary'],
            corner_radius=0
        )
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=12),
            text_color=UI_COLORS['text_secondary']
        )
        self.status_label.pack(side="left", padx=10, pady=5)

    def _connect_to_blockchain(self):
        """Подключение к блокчейну"""
        def connect():
            try:
                self.update_status("Подключение к QuickNode BSC...")
                self.web3_manager.connect()
                
                # Проверка подключения
                if self.web3_manager.is_connected():
                    self.connection_status = True
                    self.root.after(0, lambda: self._update_connection_status(True))
                    self.root.after(0, lambda: self.update_status("Подключен к BSC"))
                    self.logger.info("✅ Подключение к блокчейну установлено")
                else:
                    raise Exception("Не удалось подключиться")
                    
            except Exception as e:
                self.root.after(0, lambda: self._update_connection_status(False))
                self.root.after(0, lambda: self.update_status(f"Ошибка подключения: {e}"))
                self.logger.error(f"❌ Ошибка подключения: {e}")
        
        threading.Thread(target=connect, daemon=True).start()

    def _update_connection_status(self, connected: bool):
        """Обновление статуса подключения"""
        if connected:
            self.connection_label.configure(
                text="🟢 Подключен",
                text_color=UI_COLORS['success']
            )
            self.connect_button.configure(text="Отключиться")
        else:
            self.connection_label.configure(
                text="🔴 Отключен",
                text_color=UI_COLORS['error']
            )
            self.connect_button.configure(text="Подключиться")

    def _start_analysis(self):
        """Запуск анализа"""
        if self.analysis_running:
            return
            
        if not self.connection_status:
            self.update_status("❌ Необходимо подключение к блокчейну")
            return
        
        def analyze():
            try:
                self.analysis_running = True
                self.root.after(0, lambda: self.analyze_button.configure(state="disabled"))
                
                # Определяем диапазон блоков
                period = self.period_var.get()
                current_block = self.web3_manager.get_latest_block_number()
                
                if period == "1_hour":
                    blocks_back = 1200  # ~1 час
                elif period == "1_day":
                    blocks_back = 28800  # ~1 день
                elif period == "1_week":
                    blocks_back = 201600  # ~1 неделя
                elif period == "1_month":
                    blocks_back = 864000  # ~1 месяц
                else:
                    blocks_back = 28800  # По умолчанию 1 день
                
                start_block = current_block - blocks_back
                
                self.root.after(0, lambda: self.update_status(f"Анализ блоков {start_block:,} - {current_block:,}"))
                
                # Запуск анализа
                def progress_callback(message):
                    self.root.after(0, lambda: self.update_progress(message))
                
                results = self.participant_analyzer.analyze_participants(
                    start_block, current_block, progress_callback
                )
                
                self.current_analysis_results = results
                
                # Обновляем UI с результатами
                self.root.after(0, lambda: self._display_analysis_results(results))
                self.root.after(0, lambda: self.update_status("✅ Анализ завершен"))
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка анализа: {e}")
                self.root.after(0, lambda: self.update_status(f"❌ Ошибка: {e}"))
            finally:
                self.analysis_running = False
                self.root.after(0, lambda: self.analyze_button.configure(state="normal"))
                self.root.after(0, lambda: self.progress_bar.set(0))
        
        threading.Thread(target=analyze, daemon=True).start()

    def _display_analysis_results(self, results: Dict):
        """Отображение результатов анализа"""
        if not results:
            self.results_text.delete("1.0", "end")
            self.results_text.insert("1.0", "Нет данных для отображения")
            return
        
        # Сводка
        summary = self.participant_analyzer.export_participants_summary()
        
        output = []
        output.append("🔍 РЕЗУЛЬТАТЫ АНАЛИЗА УЧАСТНИКОВ")
        output.append("=" * 50)
        output.append(f"📊 Всего участников: {summary.get('total_participants', 0)}")
        output.append(f"⏰ Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        # Статистика по категориям
        output.append("📂 КАТЕГОРИИ:")
        categories = summary.get('categories', {})
        for category, count in sorted(categories.items()):
            percentage = (count / summary['total_participants'] * 100) if summary['total_participants'] > 0 else 0
            output.append(f"   {category}: {count} ({percentage:.1f}%)")
        
        output.append("")
        
        # Статистика по тирам наград
        output.append("🏆 ТИРЫ НАГРАД:")
        tiers = summary.get('reward_tiers', {})
        for tier, count in sorted(tiers.items()):
            percentage = (count / summary['total_participants'] * 100) if summary['total_participants'] > 0 else 0
            output.append(f"   {tier}: {count} ({percentage:.1f}%)")
        
        output.append("")
        
        # Топ участники
        output.append("🔝 ТОП ПО ОБЪЕМУ:")
        for i, p in enumerate(summary.get('top_by_volume', [])[:5]):
            output.append(f"   {i+1}. {p['address'][:10]}... - ${p['volume_usd']} ({p['category']})")
        
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", "\n".join(output))
        
        # Обновляем другие вкладки
        self._update_participants_tab(results)
        self._update_categories_tab(summary)

    def _update_participants_tab(self, results: Dict):
        """Обновление вкладки участников"""
        output = []
        output.append("👥 СПИСОК УЧАСТНИКОВ")
        output.append("=" * 80)
        output.append(f"{'Адрес':<20} {'Категория':<15} {'Свапы':<8} {'Объем USD':<12} {'Тир':<10} {'Score':<8}")
        output.append("-" * 80)
        
        # Сортируем по eligibility score
        sorted_participants = sorted(
            results.values(),
            key=lambda x: x.eligibility_score,
            reverse=True
        )
        
        for p in sorted_participants:
            output.append(
                f"{p.address[:20]:<20} "
                f"{p.category:<15} "
                f"{p.total_swaps:<8} "
                f"{str(p.total_volume_usd)[:12]:<12} "
                f"{p.reward_tier:<10} "
                f"{p.eligibility_score:.3f}"
            )
        
        self.participants_text.delete("1.0", "end")
        self.participants_text.insert("1.0", "\n".join(output))

    def _update_categories_tab(self, summary: Dict):
        """Обновление вкладки категорий"""
        output = []
        output.append("📂 ДЕТАЛЬНАЯ СТАТИСТИКА КАТЕГОРИЙ")
        output.append("=" * 50)
        
        categories = summary.get('categories', {})
        total = summary.get('total_participants', 0)
        
        for category, count in sorted(categories.items()):
            percentage = (count / total * 100) if total > 0 else 0
            output.append(f"\n🏷️ {category}:")
            output.append(f"   Участников: {count}")
            output.append(f"   Процент: {percentage:.1f}%")
            output.append(f"   Описание: {self._get_category_description(category)}")
        
        self.categories_text.delete("1.0", "end")
        self.categories_text.insert("1.0", "\n".join(output))

    def _get_category_description(self, category: str) -> str:
        """Получение описания категории"""
        descriptions = {
            "Whale": "Крупные игроки с высоким объемом торгов",
            "Active_Trader": "Активные трейдеры с частыми операциями",
            "Regular_User": "Обычные пользователи с регулярной активностью",
            "Holder": "Долгосрочные держатели токенов",
            "Newcomer": "Новые участники",
            "Inactive": "Неактивные пользователи"
        }
        return descriptions.get(category, "Неизвестная категория")

    def _filter_participants(self, category: str):
        """Фильтрация участников по категории"""
        if not self.current_analysis_results:
            return
        
        if category == "Все":
            filtered = self.current_analysis_results
        else:
            filtered = {
                addr: data for addr, data in self.current_analysis_results.items()
                if data.category == category
            }
        
        self._update_participants_tab(filtered)

    def _calculate_rewards(self):
        """Расчет наград"""
        if not self.current_analysis_results:
            self.update_status("❌ Сначала выполните анализ участников")
            return
        
        def calculate():
            try:
                qualified = self.participant_analyzer.get_participants_for_rewards()
                rewards = self.reward_manager.calculate_rewards(qualified)
                
                output = []
                output.append("🏆 РАСЧЕТ НАГРАД")
                output.append("=" * 50)
                output.append(f"Квалифицированных участников: {len(qualified)}")
                output.append(f"Общая сумма наград: {sum(rewards.values()):,.2f} PLEX")
                output.append("")
                
                for addr, amount in sorted(rewards.items(), key=lambda x: x[1], reverse=True):
                    if addr in self.current_analysis_results:
                        participant = self.current_analysis_results[addr]
                        output.append(
                            f"{addr[:20]:<20} "
                            f"{participant.reward_tier:<10} "
                            f"{amount:>10.2f} PLEX"
                        )
                
                self.root.after(0, lambda: self._display_rewards(output))
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка расчета наград: {e}")
                self.root.after(0, lambda: self.update_status(f"❌ Ошибка: {e}"))
        
        threading.Thread(target=calculate, daemon=True).start()

    def _display_rewards(self, output: List[str]):
        """Отображение наград"""
        self.rewards_text.delete("1.0", "end")
        self.rewards_text.insert("1.0", "\n".join(output))

    def _export_rewards(self):
        """Экспорт наград"""
        self.update_status("💾 Экспорт наград в разработке...")

    def update_status(self, message: str):
        """Обновление статуса"""
        self.status_label.configure(text=message)
        self.logger.info(f"Status: {message}")

    def update_progress(self, message: str):
        """Обновление прогресса"""
        self.progress_label.configure(text=message)
        # Можно добавить парсинг процента и обновление progress_bar

    def run(self):
        """Запуск приложения"""
        try:
            self.logger.info("🚀 Запуск PLEX Dynamic Staking Manager UI V3")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("👋 Завершение работы по запросу пользователя")
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка UI: {e}")
        finally:
            self.close()

    def close(self):
        """Закрытие приложения"""
        try:
            if hasattr(self.web3_manager, 'close'):
                self.web3_manager.close()
            if hasattr(self.participant_analyzer, 'close'):
                self.participant_analyzer.close()
            self.logger.info("🔐 Приложение закрыто")
        except Exception as e:
            self.logger.error(f"❌ Ошибка закрытия: {e}")


def main():
    """Главная функция для запуска UI"""
    if not UI_AVAILABLE:
        print("❌ CustomTkinter не установлен. Выполните: pip install customtkinter")
        return
    
    try:
        app = PLEXStakingUI_V3()
        app.run()
    except Exception as e:
        print(f"❌ Ошибка запуска UI: {e}")


if __name__ == "__main__":
    main()
