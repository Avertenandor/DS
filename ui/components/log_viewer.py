"""
PLEX Dynamic Staking Manager - Fixed Log Viewer
Компонент для просмотра логов в реальном времени с фильтрацией и поиском.

Автор: PLEX Dynamic Staking Team
Версия: 1.1.0 (FIXED)
"""

import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ui.themes.dark_theme import get_theme
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class LogLevel(Enum):
    """Уровни логирования."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry:
    """Запись в логе."""
    
    def __init__(self, timestamp: str, level: str, message: str, module: str = ""):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.module = module
        self.full_text = f"[{timestamp}] {level} - {module}: {message}"


class LogViewer(ctk.CTkFrame):
    """
    Production-ready компонент для просмотра логов.
    
    Функциональность:
    - Отображение логов в реальном времени
    - Фильтрация по уровням логирования
    - Поиск по тексту
    - Экспорт логов
    - Автоматическая прокрутка
    - Подсветка синтаксиса
    - Полная поддержка resizable интерфейса
    """
    
    def __init__(
        self,
        parent,
        log_file_path: Optional[str] = None,
        auto_scroll: bool = True,
        max_lines: int = 1000,
        **kwargs
    ):
        """
        Инициализация LogViewer.
        
        Args:
            parent: Родительский виджет
            log_file_path: Путь к файлу логов
            auto_scroll: Автоматическая прокрутка
            max_lines: Максимальное количество строк
            **kwargs: Дополнительные параметры
        """
        self.theme = get_theme()
        
        # Применение стиля фрейма
        frame_style = self.theme.get_frame_style('secondary')
        frame_style.update(kwargs)
        super().__init__(parent, **frame_style)
        
        # Настройки
        self.log_file_path = log_file_path
        self.auto_scroll = auto_scroll
        self.max_lines = max_lines
        
        # Состояние
        self.log_entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_file_size = 0
        
        # Фильтры
        self.level_filter = set(LogLevel)  # Показывать все уровни по умолчанию
        self.search_text = ""
        self.module_filter = ""
        
        # Колбэки
        self.on_log_entry: Optional[Callable[[LogEntry], None]] = None
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        
        # Добавляем тестовые записи для проверки
        self._add_initial_logs()
        
        # Запуск мониторинга если указан файл
        if self.log_file_path and os.path.exists(self.log_file_path):
            self.start_monitoring()
        
        logger.debug("📋 LogViewer (FIXED) инициализирован")
    
    def _add_initial_logs(self) -> None:
        """Добавление начальных логов для проверки работы."""
        initial_logs = [
            ("INFO", "LogViewer инициализирован", "ui.log_viewer"),
            ("DEBUG", "Создание интерфейса логов", "ui.log_viewer"),
            ("INFO", "Готов к приему логов", "system"),
        ]
        
        for level, message, module in initial_logs:
            self.add_log_entry(level, message, module)
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Панель управления (верхняя)
        self.control_panel = self.theme.create_styled_frame(self, 'primary')
        
        # Кнопки управления
        self.btn_open_file = self.theme.create_styled_button(
            self.control_panel,
            "📂 Открыть файл",
            'secondary',
            command=self._open_log_file,
            width=120
        )
        
        self.btn_clear = self.theme.create_styled_button(
            self.control_panel,
            "🗑️ Очистить",
            'secondary',
            command=self._clear_logs,
            width=100
        )
        
        self.btn_export = self.theme.create_styled_button(
            self.control_panel,
            "💾 Экспорт",
            'secondary',
            command=self._export_logs,
            width=100
        )
        
        self.btn_refresh = self.theme.create_styled_button(
            self.control_panel,
            "🔄 Обновить",
            'primary',
            command=self._refresh_logs,
            width=100
        )
        
        # Переключатель автопрокрутки
        self.auto_scroll_var = ctk.BooleanVar(value=self.auto_scroll)
        self.switch_auto_scroll = ctk.CTkSwitch(
            self.control_panel,
            text="Автопрокрутка",
            variable=self.auto_scroll_var,
            command=self._toggle_auto_scroll,
            **self.theme.get_switch_style()
        )
        
        # Панель фильтров
        self.filter_panel = self.theme.create_styled_frame(self, 'primary')
        
        # Поиск
        self.search_label = self.theme.create_styled_label(
            self.filter_panel,
            "🔍 Поиск:",
            'secondary'
        )
          # Создаем экземпляр SafeWidgetFactory
        widget_factory = SafeWidgetFactory()
        
        self.search_entry = widget_factory.create_entry(
            self.filter_panel,
            width=200
        )
        widget_factory.setup_placeholder(self.search_entry, "Введите текст для поиска...")
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        # Фильтр по модулю
        self.module_label = self.theme.create_styled_label(
            self.filter_panel,
            "📦 Модуль:",
            'secondary'
        )
        
        self.module_entry = widget_factory.create_entry(
            self.filter_panel,
            width=150
        )
        widget_factory.setup_placeholder(self.module_entry, "Фильтр по модулю...")
        self.module_entry.bind('<KeyRelease>', self._on_module_filter_changed)
        
        # Фильтры по уровням
        self.level_frame = self.theme.create_styled_frame(self.filter_panel, 'primary')
        
        self.level_label = self.theme.create_styled_label(
            self.level_frame,
            "📊 Уровни:",
            'secondary'
        )
        
        # Чекбоксы для уровней
        self.level_vars = {}
        self.level_checkboxes = {}
        
        level_colors = {
            LogLevel.DEBUG: self.theme.colors['text_muted'],
            LogLevel.INFO: self.theme.colors['info'],
            LogLevel.WARNING: self.theme.colors['warning'],
            LogLevel.ERROR: self.theme.colors['error'],
            LogLevel.CRITICAL: self.theme.colors['btn_danger']
        }
        
        for level in LogLevel:
            var = ctk.BooleanVar(value=True)  # По умолчанию все включены
            self.level_vars[level] = var
            
            checkbox = ctk.CTkCheckBox(
                self.level_frame,
                text=level.value,
                variable=var,
                command=self._on_level_filter_changed,
                text_color=level_colors.get(level, self.theme.colors['text_primary']),
                font=('Segoe UI', 10, 'normal')
            )
            self.level_checkboxes[level] = checkbox
        
        # Основная область логов
        self.log_frame = self.theme.create_styled_frame(self, 'card')
        
        # Создание текстового поля для логов (ИСПРАВЛЕНО)
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame,
            font=('Consolas', 9, 'normal'),
            wrap='word',
            fg_color=self.theme.colors['input_bg'],
            text_color=self.theme.colors['text_primary'],
            corner_radius=5
        )
        
        # Скроллбар для текстового поля
        self.log_scrollbar = ctk.CTkScrollbar(
            self.log_frame,
            command=self.log_textbox._textbox.yview
        )
        self.log_textbox._textbox.configure(yscrollcommand=self.log_scrollbar.set)
        
        # Статус панель
        self.status_panel = self.theme.create_styled_frame(self, 'primary')
        
        self.status_label = self.theme.create_styled_label(
            self.status_panel,
            "📋 Готов к работе",
            'muted'
        )
        
        self.log_count_label = self.theme.create_styled_label(
            self.status_panel,
            "Записей: 0",
            'muted'
        )
        
        self.file_status_label = self.theme.create_styled_label(
            self.status_panel,
            "Файл: не выбран",
            'muted'
        )
    
    def _setup_layout(self) -> None:
        """Настройка расположения виджетов для полной поддержки resizable."""
        # Панель управления (фиксированная высота)
        self.control_panel.pack(fill='x', padx=5, pady=(5, 2))
        
        self.btn_open_file.pack(side='left', padx=(0, 5))
        self.btn_clear.pack(side='left', padx=(0, 5))
        self.btn_export.pack(side='left', padx=(0, 5))
        self.btn_refresh.pack(side='left', padx=(0, 10))
        self.switch_auto_scroll.pack(side='right')
        
        # Панель фильтров (фиксированная высота)
        self.filter_panel.pack(fill='x', padx=5, pady=2)
        
        # Первая строка фильтров
        filter_row1 = self.theme.create_styled_frame(self.filter_panel, 'primary')
        filter_row1.pack(fill='x', pady=(5, 2))
        
        self.search_label.pack(side='left', padx=(0, 5))
        self.search_entry.pack(side='left', padx=(0, 20))
        self.module_label.pack(side='left', padx=(0, 5))
        self.module_entry.pack(side='left')
        
        # Вторая строка фильтров (уровни)
        self.level_frame.pack(fill='x', pady=(2, 5))
        
        self.level_label.pack(side='left', padx=(0, 10))
        for checkbox in self.level_checkboxes.values():
            checkbox.pack(side='left', padx=(0, 10))
        
        # Основная область логов (РАСТЯГИВАЕТСЯ)
        self.log_frame.pack(fill='both', expand=True, padx=5, pady=2)
        
        # Размещение текстового поля и скроллбара
        self.log_scrollbar.pack(side='right', fill='y', padx=(0, 2))
        self.log_textbox.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Статус панель (фиксированная высота)
        self.status_panel.pack(fill='x', padx=5, pady=(2, 5))
        
        self.status_label.pack(side='left')
        self.log_count_label.pack(side='left', padx=(20, 0))
        self.file_status_label.pack(side='right')
    
    def _open_log_file(self) -> None:
        """Открытие файла логов."""
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите файл логов",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                self.set_log_file(file_path)
                self._update_status(f"📂 Открыт файл: {os.path.basename(file_path)}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка открытия файла логов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
    
    def _clear_logs(self) -> None:
        """Очистка логов."""
        try:
            self.log_entries.clear()
            self.filtered_entries.clear()
            self.log_textbox.delete('1.0', 'end')
            self._update_log_count()
            self._update_status("🗑️ Логи очищены")
            self.add_log_entry("INFO", "Логи очищены", "log_viewer")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки логов: {e}")
    
    def _export_logs(self) -> None:
        """Экспорт логов в файл."""
        try:
            if not self.filtered_entries:
                messagebox.showinfo("Информация", "Нет логов для экспорта")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="Сохранить логи",
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for entry in self.filtered_entries:
                        f.write(f"{entry.full_text}\n")
                
                self._update_status(f"💾 Экспортировано в: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Логи экспортированы в:\n{file_path}")
                self.add_log_entry("INFO", f"Логи экспортированы: {file_path}", "log_viewer")
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта логов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать логи:\n{e}")
    
    def _refresh_logs(self) -> None:
        """Обновление логов."""
        try:
            if self.log_file_path and os.path.exists(self.log_file_path):
                self._read_log_file()
                self._update_status("🔄 Логи обновлены")
                self.add_log_entry("INFO", "Логи обновлены", "log_viewer")
            else:
                self._update_status("⚠️ Файл логов не найден")
                self.add_log_entry("WARNING", "Файл логов не найден", "log_viewer")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления логов: {e}")
            self._update_status(f"❌ Ошибка обновления: {e}")
    
    def _toggle_auto_scroll(self) -> None:
        """Переключение автопрокрутки."""
        self.auto_scroll = self.auto_scroll_var.get()
        status = "включена" if self.auto_scroll else "отключена"
        self._update_status(f"📜 Автопрокрутка {status}")
        self.add_log_entry("INFO", f"Автопрокрутка {status}", "log_viewer")
    
    def _on_search_changed(self, event=None) -> None:
        """Обработка изменения поискового запроса."""
        self.search_text = self.search_entry.get().lower()
        self._apply_filters()
    
    def _on_module_filter_changed(self, event=None) -> None:
        """Обработка изменения фильтра по модулю."""
        self.module_filter = self.module_entry.get().lower()
        self._apply_filters()
    
    def _on_level_filter_changed(self) -> None:
        """Обработка изменения фильтра по уровням."""
        self.level_filter = {
            level for level, var in self.level_vars.items()
            if var.get()
        }
        self._apply_filters()
    
    def _apply_filters(self) -> None:
        """Применение всех фильтров."""
        try:
            self.filtered_entries = []
            
            for entry in self.log_entries:
                # Фильтр по уровню (если фильтр не пустой)
                if self.level_filter and not any(level.value == entry.level for level in self.level_filter):
                    continue
                
                # Фильтр по поиску
                if self.search_text and self.search_text not in entry.full_text.lower():
                    continue
                
                # Фильтр по модулю
                if self.module_filter and self.module_filter not in entry.module.lower():
                    continue
                
                self.filtered_entries.append(entry)
            
            self._update_display()
            self._update_log_count()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения фильтров: {e}")
            # Добавим простое отображение всех логов если фильтр сломался
            self.filtered_entries = self.log_entries.copy()
            self._update_display()
            self._update_log_count()
    
    def _update_display(self) -> None:
        """Обновление отображения логов."""
        try:
            # Очистка текстового поля
            self.log_textbox.delete('1.0', 'end')
            
            # Добавление отфильтрованных записей
            for entry in self.filtered_entries:
                self._insert_log_entry(entry)
            
            # Автопрокрутка
            if self.auto_scroll:
                self.log_textbox.see('end')
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления отображения: {e}")
    
    def _insert_log_entry(self, entry: LogEntry) -> None:
        """Вставка записи лога с цветовой подсветкой."""
        try:
            # Цвета для разных уровней
            level_colors = {
                'DEBUG': '#808080',    # Серый
                'INFO': '#00BFFF',     # Синий  
                'WARNING': '#FFA500',  # Оранжевый
                'ERROR': '#FF6B6B',    # Красный
                'CRITICAL': '#FF0000'  # Ярко-красный
            }
            
            color = level_colors.get(entry.level, '#FFFFFF')  # Белый по умолчанию
            
            # Вставка текста
            start_pos = self.log_textbox.index('end-1c')
            self.log_textbox.insert('end', f"{entry.full_text}\n")
            end_pos = self.log_textbox.index('end-1c')
            
            # Создание тега для цвета
            try:
                tag_name = f"level_{entry.level}_{id(entry)}"
                self.log_textbox.tag_configure(tag_name, foreground=color)
                self.log_textbox.tag_add(tag_name, start_pos, end_pos)
            except:
                # Если теги не поддерживаются, продолжаем без цветов
                pass
                
        except Exception as e:
            logger.error(f"❌ Ошибка вставки записи лога: {e}")
    
    def add_log_entry(self, level: str, message: str, module: str = "") -> None:
        """
        Добавление записи лога программно.
        
        Args:
            level: Уровень лога
            message: Сообщение
            module: Модуль
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = LogEntry(timestamp, level.upper(), message, module)
            
            self.log_entries.append(entry)
            
            # Ограничение количества записей
            if len(self.log_entries) > self.max_lines * 2:
                self.log_entries = self.log_entries[-self.max_lines:]
            
            # Применение фильтров
            self._apply_filters()
            
            # Вызов колбэка
            if self.on_log_entry:
                self.on_log_entry(entry)
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления записи лога: {e}")
    
    def _update_status(self, message: str) -> None:
        """Обновление статуса."""
        try:
            self.status_label.configure(text=message)
            # Автоматическое возвращение к стандартному сообщению через 5 секунд
            self.after(5000, lambda: self.status_label.configure(text="📋 Готов к работе"))
        except:
            pass
    
    def _update_log_count(self) -> None:
        """Обновление счетчика логов."""
        try:
            total = len(self.log_entries)
            filtered = len(self.filtered_entries)
            self.log_count_label.configure(text=f"Записей: {filtered}/{total}")
        except:
            pass
    
    def start_monitoring(self) -> None:
        """Запуск мониторинга файла логов."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_log_file,
            daemon=True
        )
        self.monitor_thread.start()
        logger.debug("🔍 Мониторинг логов запущен")
    
    def stop_monitoring(self) -> None:
        """Остановка мониторинга файла логов."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.debug("🛑 Мониторинг логов остановлен")
    
    def set_log_file(self, file_path: str) -> None:
        """Установка файла логов."""
        try:
            # Остановка текущего мониторинга
            self.stop_monitoring()
            
            # Установка нового файла
            self.log_file_path = file_path
            self.last_file_size = 0
            
            # Обновление статуса
            self.file_status_label.configure(text=f"Файл: {os.path.basename(file_path)}")
            
            # Чтение файла
            self._read_log_file()
            
            # Запуск мониторинга
            self.start_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки файла логов: {e}")
    
    def _read_log_file(self) -> None:
        """Чтение файла логов."""
        try:
            if not self.log_file_path or not os.path.exists(self.log_file_path):
                return
            
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Обработка только новых строк если мониторинг активен
            if self.is_monitoring and hasattr(self, '_last_line_count'):
                new_lines = lines[self._last_line_count:]
                self._last_line_count = len(lines)
            else:
                new_lines = lines
                self._last_line_count = len(lines)
            
            # Парсинг новых строк
            for line in new_lines:
                entry = self._parse_log_line(line)
                if entry:
                    self.log_entries.append(entry)
                    
                    # Вызов колбэка если установлен
                    if self.on_log_entry:
                        self.on_log_entry(entry)
            
            # Ограничение количества записей
            if len(self.log_entries) > self.max_lines * 2:
                self.log_entries = self.log_entries[-self.max_lines:]
            
            # Применение фильтров и обновление
            self._apply_filters()
            
        except Exception as e:
            logger.error(f"❌ Ошибка чтения файла логов: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Парсинг строки лога."""
        try:
            line = line.strip()
            if not line:
                return None
            
            # Попытка распарсить стандартный формат
            # [2024-01-01 12:00:00] INFO - module.name: Message
            if line.startswith('[') and ']' in line:
                parts = line.split(']', 1)
                if len(parts) == 2:
                    timestamp = parts[0][1:]  # Убираем [
                    rest = parts[1].strip()
                    
                    # Поиск уровня
                    level_part = rest.split(' - ', 1)
                    if len(level_part) == 2:
                        level = level_part[0].strip()
                        message_part = level_part[1]
                        
                        # Поиск модуля
                        if ':' in message_part:
                            module_message = message_part.split(':', 1)
                            module = module_message[0].strip()
                            message = module_message[1].strip()
                        else:
                            module = ""
                            message = message_part.strip()
                        
                        return LogEntry(timestamp, level, message, module)
            
            # Если не удалось распарсить, создаем простую запись
            return LogEntry(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                level='INFO',
                message=line,
                module='unknown'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга строки лога: {e}")
            return None
    
    def _monitor_log_file(self) -> None:
        """Мониторинг файла логов в отдельном потоке."""
        while self.is_monitoring and self.log_file_path:
            try:
                if os.path.exists(self.log_file_path):
                    current_size = os.path.getsize(self.log_file_path)
                    
                    # Если размер файла изменился
                    if current_size != self.last_file_size:
                        self.last_file_size = current_size
                        self._read_log_file()
                
                time.sleep(1)  # Проверка каждую секунду
                
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга файла логов: {e}")
                time.sleep(5)  # Более длительная пауза при ошибке
    
    def get_filtered_logs(self) -> List[LogEntry]:
        """Получение отфильтрованных логов."""
        return self.filtered_entries.copy()
    
    def set_max_lines(self, max_lines: int) -> None:
        """Установка максимального количества строк."""
        self.max_lines = max_lines
        
        # Обрезка если необходимо
        if len(self.log_entries) > max_lines * 2:
            self.log_entries = self.log_entries[-max_lines:]
            self._apply_filters()


# Экспорт для удобного импорта
__all__ = ['LogViewer', 'LogLevel', 'LogEntry']
