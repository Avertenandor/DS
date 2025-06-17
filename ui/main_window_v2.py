"""
Модуль: Главное окно с вкладками PLEX Dynamic Staking Manager
Описание: Современный UI с темной темой ChatGPT и вкладочным интерфейсом
Автор: GitHub Copilot
"""

import tkinter as tk
from typing import Dict, List, Optional, Callable
import threading
import queue
from datetime import datetime

try:
    import customtkinter as ctk
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False

from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory
from config.constants import *

logger = get_logger("PLEX_UI")

# ChatGPT Dark Theme Colors
UI_COLORS = {
    'bg_primary': '#212121',      # Основной фон
    'bg_secondary': '#2A2A2A',    # Второстепенный фон  
    'bg_tertiary': '#333333',     # Третичный фон
    'accent': '#10A37F',          # Зеленый акцент
    'accent_hover': '#0E8F6F',    # Зеленый при наведении
    'text_primary': '#ECECEC',    # Основной текст
    'text_secondary': '#A0A0A0',  # Второстепенный текст
    'error': '#EF4444',           # Красный для ошибок
    'warning': '#F59E0B',         # Желтый для предупреждений
    'success': '#10B981',         # Зеленый для успеха
    'border': '#404040'           # Цвет границ
}

class PLEXStakingUI:
    """Главное окно PLEX Dynamic Staking Manager"""
    
    def __init__(self):
        """Инициализация UI"""
        if not UI_AVAILABLE:
            raise ImportError("CustomTkinter не установлен. Выполните: pip install customtkinter")
        
        self.logger = logger
        self.log_queue = queue.Queue()
        self.progress_callback = None
        
        # Настройка темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        # Создание основного окна
        self.root = ctk.CTk()
        self.root.title("PLEX Dynamic Staking Manager v1.0.0")
        self.root.geometry("1400x900")
        self.root.configure(fg_color=UI_COLORS['bg_primary'])
        
        # Центрирование окна
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")
        
        # Данные
        self.current_analysis_results = None
        self.connection_status = False
        
        self.logger.info("🎨 Инициализация UI интерфейса...")
        self._create_ui()
        self.logger.info("✅ UI интерфейс создан")

    def _create_ui(self):
        """Создание интерфейса"""
        
        # Заголовок
        self._create_header()
        
        # Основной контейнер с вкладками
        self._create_main_container()
        
        # Статус бар
        self._create_status_bar()
        
        # Живые логи
        self._create_log_viewer()

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
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y", padx=20)
        
        # Главный заголовок
        title_label = ctk.CTkLabel(
            title_frame,
            text="🚀 PLEX Dynamic Staking Manager",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(anchor="w", pady=(10, 0))
        
        # Подзаголовок
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Production-ready система анализа динамического стейкинга",
            font=ctk.CTkFont(size=12),
            text_color=UI_COLORS['text_secondary']
        )
        subtitle_label.pack(anchor="w")
        
        # Статус подключения
        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.pack(side="right", fill="y", padx=20)
        
        self.connection_label = ctk.CTkLabel(
            status_frame,
            text="🔴 Не подключен",
            font=ctk.CTkFont(size=14),
            text_color=UI_COLORS['error']
        )
        self.connection_label.pack(pady=(20, 0))
        
        # Кнопка подключения
        self.connect_btn = ctk.CTkButton(
            status_frame,
            text="Подключиться",
            command=self._test_connection,
            fg_color=UI_COLORS['accent'],
            hover_color=UI_COLORS['accent_hover'],
            width=120,
            height=32
        )
        self.connect_btn.pack(pady=(5, 0))

    def _create_main_container(self):
        """Создание основного контейнера с вкладками"""
        # Контейнер для вкладок
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=UI_COLORS['bg_primary']
        )
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        
        # Создание табов
        self.tabview = ctk.CTkTabview(
            self.main_frame,
            fg_color=UI_COLORS['bg_secondary'],
            segmented_button_fg_color=UI_COLORS['bg_tertiary'],
            segmented_button_selected_color=UI_COLORS['accent'],
            segmented_button_selected_hover_color=UI_COLORS['accent_hover'],
            text_color=UI_COLORS['text_primary']
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Создание вкладок
        self.tabview.add("📊 Анализ")
        self.tabview.add("🏆 Награды") 
        self.tabview.add("🤝 Амнистии")
        self.tabview.add("📈 История")
        self.tabview.add("⚙️ Настройки")
        
        # Наполнение вкладок
        self._create_analysis_tab()
        self._create_rewards_tab()
        self._create_amnesty_tab()
        self._create_history_tab()
        self._create_settings_tab()

    def _create_analysis_tab(self):
        """Вкладка анализа участников"""
        tab = self.tabview.tab("📊 Анализ")
        
        # Левая панель - настройки
        left_frame = ctk.CTkFrame(tab, width=350, fg_color=UI_COLORS['bg_secondary'])
        left_frame.pack(side="left", fill="y", padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)
        
        # Заголовок настроек
        settings_label = ctk.CTkLabel(
            left_frame,
            text="🔧 Настройки анализа",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        settings_label.pack(pady=(20, 10), padx=20)
        
        # Период анализа
        period_label = ctk.CTkLabel(
            left_frame,
            text="Период анализа (дни):",
            font=ctk.CTkFont(size=12),
            text_color=UI_COLORS['text_secondary']
        )
        period_label.pack(pady=(10, 5), padx=20, anchor="w")
        
        self.period_entry = self.widget_factory.create_entry(
    left_frame,
    width=200,
    height=32
)
self.widget_factory.setup_placeholder(period_entry, "30")
        self.period_entry.pack(pady=(0, 10), padx=20)
        self.period_entry.insert(0, "30")
        
        # Фильтры
        filter_label = ctk.CTkLabel(
            left_frame,
            text="Фильтры:",
            font=ctk.CTkFont(size=12),
            text_color=UI_COLORS['text_secondary']
        )
        filter_label.pack(pady=(10, 5), padx=20, anchor="w")
        
        self.min_balance_var = ctk.StringVar(value="100")
        min_balance_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        min_balance_frame.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(
            min_balance_frame,
            text="Мин. баланс PLEX:",
            text_color=UI_COLORS['text_secondary']
        ).pack(side="left")
        
        ctk.CTkEntry(
            min_balance_frame,
            textvariable=self.min_balance_var,
            width=80,
            height=24
        ).pack(side="right")
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        buttons_frame.pack(pady=20, padx=20, fill="x")
        
        self.analyze_btn = ctk.CTkButton(
            buttons_frame,
            text="🚀 Запустить анализ",
            command=self._start_analysis,
            fg_color=UI_COLORS['accent'],
            hover_color=UI_COLORS['accent_hover'],
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analyze_btn.pack(fill="x", pady=(0, 10))
        
        self.export_btn = ctk.CTkButton(
            buttons_frame,
            text="📁 Экспорт результатов",
            command=self._export_analysis,
            fg_color=UI_COLORS['bg_tertiary'],
            hover_color="#404040",
            height=32,
            state="disabled"
        )
        self.export_btn.pack(fill="x")
        
        # Правая панель - результаты
        right_frame = ctk.CTkFrame(tab, fg_color=UI_COLORS['bg_secondary'])
        right_frame.pack(side="right", fill="both", expand=True, pady=0)
        
        # Заголовок результатов
        results_label = ctk.CTkLabel(
            right_frame,
            text="📊 Результаты анализа",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        results_label.pack(pady=(20, 10), padx=20)
        
        # Статистика
        self.stats_frame = ctk.CTkFrame(right_frame, fg_color=UI_COLORS['bg_tertiary'])
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Создаем статистические плитки
        stats_grid = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stats_grid.pack(fill="x", padx=10, pady=10)
        
        # Первая строка статистики
        row1 = ctk.CTkFrame(stats_grid, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 5))
        
        self.total_participants_label = self._create_stat_tile(row1, "Всего участников", "0", "👥")
        self.total_participants_label.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.perfect_participants_label = self._create_stat_tile(row1, "Perfect", "0", "✨")
        self.perfect_participants_label.pack(side="left", fill="x", expand=True, padx=5)
        
        self.eligible_participants_label = self._create_stat_tile(row1, "Квалифицированы", "0", "🎯")
        self.eligible_participants_label.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Прогресс бар
        self.progress_frame = ctk.CTkFrame(right_frame, fg_color=UI_COLORS['bg_tertiary'])
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Готов к анализу",
            text_color=UI_COLORS['text_secondary']
        )
        self.progress_label.pack(pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=400,
            height=10,
            progress_color=UI_COLORS['accent']
        )
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        # Таблица результатов (заглушка)
        self.results_text = ctk.CTkTextbox(
            right_frame,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=UI_COLORS['bg_primary'],
            text_color=UI_COLORS['text_primary']
        )
        self.results_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Начальное сообщение
        self.results_text.insert("1.0", "Запустите анализ для просмотра результатов...\n\n")
        self.results_text.insert("end", "Доступные операции:\n")
        self.results_text.insert("end", "• Анализ участников динамического стейкинга\n")
        self.results_text.insert("end", "• Категоризация по группам (Perfect, Missed, Sold, Transferred)\n")
        self.results_text.insert("end", "• Расчет eligibility и наград\n")
        self.results_text.insert("end", "• Экспорт результатов в Excel/CSV\n")

    def _create_rewards_tab(self):
        """Вкладка управления наградами"""
        tab = self.tabview.tab("🏆 Награды")
        
        # Заголовок
        title_label = ctk.CTkLabel(
            tab,
            text="🏆 Управление наградами",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(pady=20)
        
        # Временная заглушка
        placeholder_label = ctk.CTkLabel(
            tab,
            text="🚧 Модуль наград будет реализован в следующей версии",
            font=ctk.CTkFont(size=16),
            text_color=UI_COLORS['text_secondary']
        )
        placeholder_label.pack(pady=50)

    def _create_amnesty_tab(self):
        """Вкладка управления амнистиями"""
        tab = self.tabview.tab("🤝 Амнистии")
        
        # Заголовок
        title_label = ctk.CTkLabel(
            tab,
            text="🤝 Управление амнистиями",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(pady=20)
        
        # Временная заглушка
        placeholder_label = ctk.CTkLabel(
            tab,
            text="🚧 Модуль амнистий будет реализован в следующей версии",
            font=ctk.CTkFont(size=16),
            text_color=UI_COLORS['text_secondary']
        )
        placeholder_label.pack(pady=50)

    def _create_history_tab(self):
        """Вкладка истории операций"""
        tab = self.tabview.tab("📈 История")
        
        # Заголовок
        title_label = ctk.CTkLabel(
            tab,
            text="📈 История операций",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(pady=20)
        
        # Временная заглушка
        placeholder_label = ctk.CTkLabel(
            tab,
            text="🚧 Модуль истории будет реализован в следующей версии",
            font=ctk.CTkFont(size=16),
            text_color=UI_COLORS['text_secondary']
        )
        placeholder_label.pack(pady=50)

    def _create_settings_tab(self):
        """Вкладка настроек"""
        tab = self.tabview.tab("⚙️ Настройки")
        
        # Заголовок
        title_label = ctk.CTkLabel(
            tab,
            text="⚙️ Настройки системы",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=UI_COLORS['text_primary']
        )
        title_label.pack(pady=20)
        
        # Временная заглушка
        placeholder_label = ctk.CTkLabel(
            tab,
            text="🚧 Модуль настроек будет реализован в следующей версии",
            font=ctk.CTkFont(size=16),
            text_color=UI_COLORS['text_secondary']
        )
        placeholder_label.pack(pady=50)

    def _create_status_bar(self):
        """Создание статус бара"""
        self.status_frame = ctk.CTkFrame(
            self.root,
            height=30,
            fg_color=UI_COLORS['bg_tertiary'],
            corner_radius=0
        )
        self.status_frame.pack(fill="x", side="bottom", padx=0, pady=0)
        self.status_frame.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=10),
            text_color=UI_COLORS['text_secondary']
        )
        self.status_label.pack(side="left", padx=10, pady=5)
        
        # Время
        self.time_label = ctk.CTkLabel(
            self.status_frame,
            text=datetime.now().strftime("%H:%M:%S"),
            font=ctk.CTkFont(size=10),
            text_color=UI_COLORS['text_secondary']
        )
        self.time_label.pack(side="right", padx=10, pady=5)
        
        # Обновление времени
        self._update_time()

    def _create_log_viewer(self):
        """Создание просмотрщика логов"""
        # Фрейм логов (свернутый по умолчанию)
        self.log_frame = ctk.CTkFrame(
            self.root,
            height=0,  # Начально свернут
            fg_color=UI_COLORS['bg_secondary']
        )
        self.log_frame.pack(fill="x", side="bottom", padx=10, pady=(0, 10))
        
        # Кнопка показать/скрыть логи
        self.toggle_logs_btn = ctk.CTkButton(
            self.status_frame,
            text="📄 Показать логи",
            command=self._toggle_logs,
            width=100,
            height=20,
            fg_color="transparent",
            text_color=UI_COLORS['text_secondary']
        )
        self.toggle_logs_btn.pack(side="right", padx=(0, 10), pady=5)
        
        self.logs_visible = False

    def _create_stat_tile(self, parent, title: str, value: str, icon: str):
        """Создание плитки статистики"""
        tile = ctk.CTkFrame(parent, fg_color=UI_COLORS['bg_primary'])
        
        # Иконка
        icon_label = ctk.CTkLabel(
            tile,
            text=icon,
            font=ctk.CTkFont(size=20)
        )
        icon_label.pack(pady=(10, 0))
        
        # Значение
        value_label = ctk.CTkLabel(
            tile,
            text=value,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=UI_COLORS['accent']
        )
        value_label.pack()
        
        # Заголовок
        title_label = ctk.CTkLabel(
            tile,
            text=title,
            font=ctk.CTkFont(size=10),
            text_color=UI_COLORS['text_secondary']
        )
        title_label.pack(pady=(0, 10))
        
        return tile

    def _test_connection(self):
        """Тестирование подключения"""
        self.connect_btn.configure(state="disabled", text="Подключение...")
        
        def test():
            try:
                # Здесь будет реальная проверка подключения
                import time
                time.sleep(2)  # Имитация подключения
                
                self.root.after(0, lambda: self._connection_success())
            except Exception as e:
                self.root.after(0, lambda: self._connection_failed(str(e)))
        
        threading.Thread(target=test, daemon=True).start()

    def _connection_success(self):
        """Успешное подключение"""
        self.connection_status = True
        self.connection_label.configure(
            text="🟢 Подключен к BSC",
            text_color=UI_COLORS['success']
        )
        self.connect_btn.configure(
            state="normal",
            text="Переподключить",
            fg_color=UI_COLORS['success']
        )
        self._update_status("Подключение к блокчейну установлено")

    def _connection_failed(self, error: str):
        """Ошибка подключения"""
        self.connection_status = False
        self.connection_label.configure(
            text="🔴 Ошибка подключения",
            text_color=UI_COLORS['error']
        )
        self.connect_btn.configure(
            state="normal",
            text="Повторить",
            fg_color=UI_COLORS['error']
        )
        self._update_status(f"Ошибка подключения: {error}")

    def _start_analysis(self):
        """Запуск анализа участников"""
        if not self.connection_status:
            self._show_error("Сначала установите подключение к блокчейну")
            return
        
        # Получаем параметры
        try:
            days = int(self.period_entry.get() or "30")
        except ValueError:
            self._show_error("Неверный формат периода анализа")
            return
        
        # Запускаем анализ в отдельном потоке
        self.analyze_btn.configure(state="disabled", text="Анализ запущен...")
        self.progress_bar.set(0)
        self._update_status("Запуск анализа участников...")
        
        def analyze():
            try:
                # Здесь будет реальный анализ
                for i in range(101):
                    progress = i / 100
                    self.root.after(0, lambda p=progress: self._update_progress(p, f"Анализ: {i}%"))
                    import time
                    time.sleep(0.05)  # Имитация работы
                
                # Имитация результатов
                results = {
                    'total_participants': 150,
                    'perfect': 45,
                    'eligible': 120,
                    'categories': {
                        'perfect': 45,
                        'missed_purchase': 60,
                        'transferred': 30,
                        'sold_token': 15
                    }
                }
                
                self.root.after(0, lambda: self._analysis_complete(results))
                
            except Exception as e:
                self.root.after(0, lambda: self._analysis_failed(str(e)))
        
        threading.Thread(target=analyze, daemon=True).start()

    def _update_progress(self, progress: float, message: str):
        """Обновление прогресса"""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=message)
        self._update_status(message)

    def _analysis_complete(self, results: Dict):
        """Завершение анализа"""
        self.current_analysis_results = results
        self.analyze_btn.configure(state="normal", text="🚀 Запустить анализ")
        self.export_btn.configure(state="normal")
        
        # Обновляем статистику
        self._update_stats(results)
        
        # Обновляем результаты
        self._display_results(results)
        
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="Анализ завершен успешно!")
        self._update_status("Анализ участников завершен")

    def _analysis_failed(self, error: str):
        """Ошибка анализа"""
        self.analyze_btn.configure(state="normal", text="🚀 Запустить анализ")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Ошибка анализа")
        self._update_status(f"Ошибка анализа: {error}")
        self._show_error(f"Ошибка анализа: {error}")

    def _update_stats(self, results: Dict):
        """Обновление статистики"""
        # Обновляем значения в плитках статистики
        total = results.get('total_participants', 0)
        perfect = results.get('perfect', 0)
        eligible = results.get('eligible', 0)
        
        # Здесь нужно обновить label'ы в плитках
        # В реальной реализации нужно сохранить ссылки на label'ы значений

    def _display_results(self, results: Dict):
        """Отображение результатов анализа"""
        self.results_text.delete("1.0", "end")
        
        # Заголовок
        self.results_text.insert("end", "📊 РЕЗУЛЬТАТЫ АНАЛИЗА УЧАСТНИКОВ\n")
        self.results_text.insert("end", "=" * 50 + "\n\n")
        
        # Общая статистика
        self.results_text.insert("end", f"👥 Всего участников: {results.get('total_participants', 0)}\n")
        self.results_text.insert("end", f"✨ Perfect участников: {results.get('perfect', 0)}\n")
        self.results_text.insert("end", f"🎯 Квалифицированных: {results.get('eligible', 0)}\n\n")
        
        # Категории
        categories = results.get('categories', {})
        if categories:
            self.results_text.insert("end", "📊 РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:\n")
            self.results_text.insert("end", "-" * 30 + "\n")
            
            for category, count in categories.items():
                emoji = {
                    'perfect': '✨',
                    'missed_purchase': '⏰',
                    'transferred': '🔄',
                    'sold_token': '❌'
                }.get(category, '📋')
                
                percentage = (count / results.get('total_participants', 1)) * 100
                self.results_text.insert("end", f"{emoji} {category.replace('_', ' ').title()}: {count} ({percentage:.1f}%)\n")
        
        self.results_text.insert("end", "\n" + "=" * 50 + "\n")
        self.results_text.insert("end", f"⏰ Анализ завершен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def _export_analysis(self):
        """Экспорт результатов анализа"""
        if not self.current_analysis_results:
            self._show_error("Нет данных для экспорта")
            return
        
        # Здесь будет реальный экспорт
        self._show_info("Экспорт результатов будет реализован в следующей версии")

    def _toggle_logs(self):
        """Показать/скрыть логи"""
        if self.logs_visible:
            self.log_frame.configure(height=0)
            self.toggle_logs_btn.configure(text="📄 Показать логи")
            self.logs_visible = False
        else:
            self.log_frame.configure(height=200)
            self.toggle_logs_btn.configure(text="📄 Скрыть логи")
            self.logs_visible = True
            
            # Создаем текстовое поле для логов если его нет
            if not hasattr(self, 'log_text'):
                self.log_text = ctk.CTkTextbox(
                    self.log_frame,
                    font=ctk.CTkFont(family="Courier", size=9),
                    fg_color=UI_COLORS['bg_primary'],
                    text_color=UI_COLORS['text_secondary']
                )
                self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
                self.log_text.insert("1.0", "Система логирования готова...\n")

    def _update_time(self):
        """Обновление времени в статус баре"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.root.after(1000, self._update_time)

    def _update_status(self, message: str):
        """Обновление статуса"""
        self.status_label.configure(text=message)
        self.logger.info(f"UI Status: {message}")

    def _show_error(self, message: str):
        """Показать ошибку"""
        self._update_status(f"Ошибка: {message}")
        # В реальной реализации можно добавить popup
        self.logger.error(f"UI Error: {message}")

    def _show_info(self, message: str):
        """Показать информацию"""
        self._update_status(message)
        # В реальной реализации можно добавить popup
        self.logger.info(f"UI Info: {message}")

    def run(self):
        """Запуск интерфейса"""
        try:
            self.logger.info("🚀 Запуск UI интерфейса")
            
            # Проверяем подключение при старте
            self.root.after(1000, self._test_connection)
            
            # Запускаем главный цикл
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска UI: {e}")
            raise
        finally:
            self.logger.info("🔄 UI интерфейс завершен")


if __name__ == "__main__":
    if UI_AVAILABLE:
        app = PLEXStakingUI()
        app.run()
    else:
        print("❌ CustomTkinter не установлен. Выполните: pip install customtkinter")
