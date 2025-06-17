"""
Модуль: Главное окно UI для PLEX Dynamic Staking Manager
Описание: Современный интерфейс для анализа и мониторинга участников
Автор: GitHub Copilot
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from datetime import datetime, timedelta
import asyncio
import threading
from typing import Dict, List, Optional
import json

from config.constants import UI_COLORS, TOKEN_NAME, TOKEN_SYMBOL
from config.settings import settings
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory
from core.participant_analyzer_v2 import ParticipantAnalyzer, ParticipantData
from db.models import DatabaseManager

logger = get_logger("PLEX_UI")

class PLEXStakingUI:
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализация UI"""
        # Настройка темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        
        # Создаем главное окно
        self.root = ctk.CTk()
        self.root.title(f"PLEX Dynamic Staking Manager v1.0.0")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Инициализация компонентов
        self.analyzer = ParticipantAnalyzer()
        self.db_manager = DatabaseManager()
        self.participants: Dict[str, ParticipantData] = {}
        self.analysis_running = False
        
        # Переменные для UI
        self.progress_var = tk.StringVar(value="Готов к анализу")
        self.status_var = tk.StringVar(value="Система инициализирована")
        
        self._setup_ui()
        self._setup_styles()
        
        logger.info("🎨 UI инициализирован")

    def _setup_ui(self):
        """Настройка интерфейса"""
        # Главный контейнер
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Заголовок
        self.header_frame = ctk.CTkFrame(self.main_frame)
        self.header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            self.header_frame,
            text=f"🚀 PLEX Dynamic Staking Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)
        
        # Информация о подключении
        self.connection_label = ctk.CTkLabel(
            self.header_frame,
            text="🔗 QuickNode BSC | 📊 SQLite DB",
            font=ctk.CTkFont(size=12)
        )
        self.connection_label.pack(side="right", padx=20, pady=15)
        
        # Создаем табы
        self.tab_view = ctk.CTkTabview(self.main_frame)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Вкладки
        self.tab_analysis = self.tab_view.add("📊 Анализ участников")
        self.tab_results = self.tab_view.add("👥 Результаты")
        self.tab_rewards = self.tab_view.add("🏆 Награды")
        self.tab_export = self.tab_view.add("📁 Экспорт")
        self.tab_settings = self.tab_view.add("⚙️ Настройки")
        
        self._setup_analysis_tab()
        self._setup_results_tab()
        self._setup_rewards_tab()
        self._setup_export_tab()
        self._setup_settings_tab()
        
        # Статус бар
        self.status_frame = ctk.CTkFrame(self.main_frame)
        self.status_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=15, pady=8)
        
        self.progress_label = ctk.CTkLabel(
            self.status_frame,
            textvariable=self.progress_var,
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.pack(side="right", padx=15, pady=8)

    def _setup_analysis_tab(self):
        """Настройка вкладки анализа"""
        # Параметры анализа
        params_frame = ctk.CTkFrame(self.tab_analysis)
        params_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            params_frame,
            text="📋 Параметры анализа",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Период анализа
        period_frame = ctk.CTkFrame(params_frame)
        period_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(period_frame, text="📅 Период анализа:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.period_var = tk.StringVar(value="last_30_days")
        period_menu = ctk.CTkOptionMenu(
            period_frame,
            variable=self.period_var,
            values=["last_7_days", "last_30_days", "last_90_days", "custom"]
        )
        period_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Блоки для анализа        ctk.CTkLabel(period_frame, text="📦 Начальный блок:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.start_block_entry = self.widget_factory.create_entry(
            period_frame
        )
        self.widget_factory.setup_placeholder(self.start_block_entry, "Авто")
        self.start_block_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(period_frame, text="📦 Конечный блок:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.end_block_entry = self.widget_factory.create_entry(
            period_frame
        )
        self.widget_factory.setup_placeholder(self.end_block_entry, "Последний")
        self.end_block_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        period_frame.columnconfigure(1, weight=1)
        
        # Кнопки управления
        controls_frame = ctk.CTkFrame(self.tab_analysis)
        controls_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.start_btn = ctk.CTkButton(
            controls_frame,
            text="🚀 Начать анализ",
            command=self._start_analysis,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.start_btn.pack(side="left", padx=20, pady=15)
        
        self.stop_btn = ctk.CTkButton(
            controls_frame,
            text="⏹️ Остановить",
            command=self._stop_analysis,
            state="disabled",
            fg_color="red",
            height=40
        )
        self.stop_btn.pack(side="left", padx=10, pady=15)
        
        # Прогресс анализа
        progress_frame = ctk.CTkFrame(self.tab_analysis)
        progress_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            progress_frame,
            text="📈 Прогресс анализа",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        
        self.progress_text = ctk.CTkTextbox(progress_frame, height=200)
        self.progress_text.pack(fill="both", expand=True, padx=20, pady=(0, 15))

    def _setup_results_tab(self):
        """Настройка вкладки результатов"""
        # Статистика
        stats_frame = ctk.CTkFrame(self.tab_results)
        stats_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            stats_frame,
            text="📊 Общая статистика",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Карточки статистики
        cards_frame = ctk.CTkFrame(stats_frame)
        cards_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.stats_cards = {}
        stats_data = [
            ("total", "👥 Всего участников", "0"),
            ("qualified", "🎯 Квалифицированных", "0"),
            ("volume", "💰 Общий объем", "$0"),
            ("categories", "📂 Категорий", "0")
        ]
        
        for i, (key, title, value) in enumerate(stats_data):
            card = ctk.CTkFrame(cards_frame)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="ew")
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12)).pack(pady=(10, 5))
            value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=18, weight="bold"))
            value_label.pack(pady=(0, 10))
            
            self.stats_cards[key] = value_label
            cards_frame.columnconfigure(i, weight=1)
        
        # Таблица участников
        table_frame = ctk.CTkFrame(self.tab_results)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            table_frame,
            text="👥 Список участников",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Создаем Treeview для таблицы
        self.create_participants_table(table_frame)

    def create_participants_table(self, parent):
        """Создание таблицы участников"""
        # Фрейм для таблицы и скроллбара
        table_container = ctk.CTkFrame(parent)
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Настраиваем стиль для Treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        # Конфигурируем цвета для темной темы
        style.configure("Treeview",
                       background="#2B2B2B",
                       foreground="#FFFFFF",
                       fieldbackground="#2B2B2B",
                       borderwidth=0,
                       font=('Segoe UI', 9))
        
        style.configure("Treeview.Heading",
                       background="#404040",
                       foreground="#FFFFFF",
                       borderwidth=1,
                       font=('Segoe UI', 9, 'bold'))
        
        # Создаем Treeview
        columns = ("address", "category", "swaps", "volume", "score", "tier", "qualified")
        self.participants_tree = ttk.Treeview(table_container, columns=columns, show="headings", height=15)
        
        # Настраиваем заголовки
        headers = {
            "address": "Адрес",
            "category": "Категория", 
            "swaps": "Swaps",
            "volume": "Объем USD",
            "score": "Score",
            "tier": "Tier",
            "qualified": "Статус"
        }
        
        for col, header in headers.items():
            self.participants_tree.heading(col, text=header)
            
        # Настраиваем ширину колонок
        column_widths = {
            "address": 200,
            "category": 120,
            "swaps": 80,
            "volume": 120,
            "score": 80,
            "tier": 100,
            "qualified": 80
        }
        
        for col, width in column_widths.items():
            self.participants_tree.column(col, width=width, minwidth=width//2)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.participants_tree.yview)
        self.participants_tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        self.participants_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _setup_rewards_tab(self):
        """Настройка вкладки наград"""
        rewards_label = ctk.CTkLabel(
            self.tab_rewards,
            text="🏆 Система наград (в разработке)",
            font=ctk.CTkFont(size=18)
        )
        rewards_label.pack(expand=True)

    def _setup_export_tab(self):
        """Настройка вкладки экспорта"""
        export_frame = ctk.CTkFrame(self.tab_export)
        export_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            export_frame,
            text="📁 Экспорт данных",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 20))
        
        # Кнопки экспорта
        export_json_btn = ctk.CTkButton(
            export_frame,
            text="📄 Экспорт в JSON",
            command=self._export_json,
            height=40
        )
        export_json_btn.pack(padx=20, pady=10, anchor="w")
        
        export_csv_btn = ctk.CTkButton(
            export_frame,
            text="📊 Экспорт в CSV",
            command=self._export_csv,
            height=40
        )
        export_csv_btn.pack(padx=20, pady=10, anchor="w")

    def _setup_settings_tab(self):
        """Настройка вкладки настроек"""
        settings_label = ctk.CTkLabel(
            self.tab_settings,
            text="⚙️ Настройки системы (в разработке)",
            font=ctk.CTkFont(size=18)
        )
        settings_label.pack(expand=True)

    def _setup_styles(self):
        """Настройка стилей"""
        pass  # Стили уже настроены в customtkinter

    def _start_analysis(self):
        """Запуск анализа участников"""
        if self.analysis_running:
            return
        
        self.analysis_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_text.delete("0.0", "end")
        
        # Запускаем анализ в отдельном потоке
        thread = threading.Thread(target=self._run_analysis)
        thread.daemon = True
        thread.start()

    def _run_analysis(self):
        """Выполнение анализа в отдельном потоке"""
        try:
            self._update_progress("Инициализация анализа...")
            
            # Определяем блоки для анализа
            latest_block = self.analyzer.web3_manager.get_latest_block_number()
            
            if self.period_var.get() == "last_7_days":
                start_block = latest_block - (7 * 24 * 60 * 60 // 3)  # ~7 дней назад
            elif self.period_var.get() == "last_30_days":
                start_block = latest_block - (30 * 24 * 60 * 60 // 3)  # ~30 дней назад
            elif self.period_var.get() == "last_90_days":
                start_block = latest_block - (90 * 24 * 60 * 60 // 3)  # ~90 дней назад
            else:
                start_block = int(self.start_block_entry.get()) if self.start_block_entry.get() else latest_block - 100000
            
            end_block = int(self.end_block_entry.get()) if self.end_block_entry.get() else latest_block
            
            self._update_progress(f"Анализ блоков {start_block:,} - {end_block:,}")
            
            # Запускаем анализ
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.participants = loop.run_until_complete(
                self.analyzer.analyze_participants(
                    start_block, 
                    end_block,
                    self._update_progress
                )
            )
            
            # Обновляем UI
            self.root.after(0, self._update_results_ui)
            self._update_progress("✅ Анализ завершен успешно!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            self._update_progress(f"❌ Ошибка: {e}")
        finally:
            self.analysis_running = False
            self.root.after(0, self._analysis_finished)

    def _update_progress(self, message: str):
        """Обновление прогресса анализа"""
        def update_ui():
            self.progress_text.insert("end", f"{datetime.now().strftime('%H:%M:%S')} | {message}\n")
            self.progress_text.see("end")
            self.progress_var.set(message)
        
        self.root.after(0, update_ui)

    def _analysis_finished(self):
        """Завершение анализа"""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set(f"Анализ завершен. Участников: {len(self.participants)}")

    def _stop_analysis(self):
        """Остановка анализа"""
        self.analysis_running = False
        self._analysis_finished()
        self._update_progress("⏹️ Анализ остановлен пользователем")

    def _update_results_ui(self):
        """Обновление UI результатов"""
        if not self.participants:
            return
        
        # Обновляем статистические карточки
        total = len(self.participants)
        qualified = sum(1 for p in self.participants.values() if p.is_qualified)
        total_volume = sum(p.total_volume_usd for p in self.participants.values())
        categories = len(set(p.category for p in self.participants.values()))
        
        self.stats_cards["total"].configure(text=str(total))
        self.stats_cards["qualified"].configure(text=str(qualified))
        self.stats_cards["volume"].configure(text=f"${total_volume:,.0f}")
        self.stats_cards["categories"].configure(text=str(categories))
        
        # Обновляем таблицу участников
        # Очищаем таблицу
        for item in self.participants_tree.get_children():
            self.participants_tree.delete(item)
        
        # Добавляем участников (топ 100)
        sorted_participants = sorted(
            self.participants.values(),
            key=lambda x: x.eligibility_score,
            reverse=True
        )[:100]
        
        for participant in sorted_participants:
            values = (
                participant.address[:10] + "...",
                participant.category,
                participant.total_swaps,
                f"${participant.total_volume_usd:,.0f}",
                f"{participant.eligibility_score:.3f}",
                participant.reward_tier,
                "✅" if participant.is_qualified else "❌"
            )
            self.participants_tree.insert("", "end", values=values)

    def _export_json(self):
        """Экспорт в JSON"""
        if not self.participants:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                summary = self.analyzer.export_participants_summary()
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")

    def _export_csv(self):
        """Экспорт в CSV"""
        messagebox.showinfo("Информация", "CSV экспорт будет реализован в следующей версии")

    def run(self):
        """Запуск приложения"""
        try:
            logger.info("🚀 Запуск UI приложения")
            self.root.mainloop()
        except Exception as e:
            logger.error(f"❌ Ошибка UI: {e}")
            messagebox.showerror("Критическая ошибка", f"Ошибка приложения: {e}")

def main():
    """Главная функция UI"""
    try:
        app = PLEXStakingUI()
        app.run()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка UI: {e}")

if __name__ == "__main__":
    main()
