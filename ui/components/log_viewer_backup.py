"""
PLEX Dynamic Staking Manager - Log Viewer
Компонент для просмотра логов в реальном времени с фильтрацией и поиском.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
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
        
        # Запуск мониторинга если указан файл
        if self.log_file_path and os.path.exists(self.log_file_path):
            self.start_monitoring()
        
        logger.debug("📋 LogViewer инициализирован")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Панель управления
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
        
        self.search_entry = self.theme.create_styled_entry(
            self.filter_panel,
            "Введите текст для поиска...",
            width=200
        )
        self.search_entry.bind('<KeyRelease>', self._on_search_changed)
        
        # Фильтр по модулю
        self.module_label = self.theme.create_styled_label(
            self.filter_panel,
            "📦 Модуль:",
            'secondary'
        )
        
        self.module_entry = self.theme.create_styled_entry(
            self.filter_panel,
            "Фильтр по модулю...",
            width=150
        )
        self.module_entry.bind('<KeyRelease>', self._on_module_filter_changed)
        
        # Фильтры по уровням
        self.level_frame = self.theme.create_styled_frame(self.filter_panel, 'primary')
        
        self.level_label = self.theme.create_styled_label(
            self.level_frame,
            "📊 Уровни:",
            'secondary'
        )
        
        # Чекбоксы для уровней логирования
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
            var = ctk.BooleanVar(value=True)
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
        
        # Текстовое поле для логов
        self.log_textbox = self.theme.create_styled_textbox(
            self.log_frame,
            font=('Consolas', 9, 'normal'),
            wrap='word'
        )
        
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
        """Настройка расположения виджетов."""
        # Панель управления
        self.control_panel.pack(fill='x', padx=10, pady=(10, 5))
        
        self.btn_open_file.pack(side='left', padx=(0, 5))
        self.btn_clear.pack(side='left', padx=(0, 5))
        self.btn_export.pack(side='left', padx=(0, 5))
        self.btn_refresh.pack(side='left', padx=(0, 10))
        self.switch_auto_scroll.pack(side='right')
        
        # Панель фильтров
        self.filter_panel.pack(fill='x', padx=10, pady=5)
        
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
        
        # Основная область логов
        self.log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.log_textbox.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Статус панель
        self.status_panel.pack(fill='x', padx=10, pady=(5, 10))
        
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
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта логов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать логи:\n{e}")
    
    def _refresh_logs(self) -> None:
        """Обновление логов."""
        try:
            if self.log_file_path and os.path.exists(self.log_file_path):
                self._read_log_file()
                self._update_status("🔄 Логи обновлены")
            else:
                self._update_status("⚠️ Файл логов не найден")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления логов: {e}")
            self._update_status(f"❌ Ошибка обновления: {e}")
    
    def _toggle_auto_scroll(self) -> None:
        """Переключение автопрокрутки."""
        self.auto_scroll = self.auto_scroll_var.get()
        status = "включена" if self.auto_scroll else "отключена"
        self._update_status(f"📜 Автопрокрутка {status}")
    
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
            for entry in self.filtered_entries[-self.max_lines:]:
                self._insert_log_entry(entry)
            
            # Автопрокрутка
            if self.auto_scroll:
                self.log_textbox.see('end')
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления отображения: {e}")
    
    def _insert_log_entry(self, entry: LogEntry) -> None:
        """
        Вставка записи лога с подсветкой.
        
        Args:
            entry: Запись лога
        """
        try:
            # Определение цвета по уровню
            level_colors = {
                'DEBUG': self.theme.colors['text_muted'],
                'INFO': self.theme.colors['info'],
                'WARNING': self.theme.colors['warning'],
                'ERROR': self.theme.colors['error'],
                'CRITICAL': self.theme.colors['btn_danger']
            }
            
            color = level_colors.get(entry.level, self.theme.colors['text_primary'])
            
            # Вставка текста
            start_pos = self.log_textbox.index('end')
            self.log_textbox.insert('end', f"{entry.full_text}\n")
            end_pos = self.log_textbox.index('end')
            
            # Создание тега для цвета (если поддерживается)
            try:
                tag_name = f"level_{entry.level}"
                self.log_textbox.tag_configure(tag_name, foreground=color)
                self.log_textbox.tag_add(tag_name, start_pos, end_pos)
            except:
                pass  # Если теги не поддерживаются
                
        except Exception as e:
            logger.error(f"❌ Ошибка вставки записи лога: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """
        Парсинг строки лога.
        
        Args:
            line: Строка лога
            
        Returns:
            LogEntry или None если не удалось распарсить
        """
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
    
    def _update_status(self, message: str) -> None:
        """
        Обновление статуса.
        
        Args:
            message: Сообщение статуса
        """
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
            
            if total == filtered:
                text = f"Записей: {total}"
            else:
                text = f"Записей: {filtered}/{total}"
                
            self.log_count_label.configure(text=text)
        except:
            pass
    
    def _update_file_status(self) -> None:
        """Обновление статуса файла."""
        try:
            if self.log_file_path:
                filename = os.path.basename(self.log_file_path)
                status = "мониторинг" if self.is_monitoring else "загружен"
                text = f"Файл: {filename} ({status})"
            else:
                text = "Файл: не выбран"
                
            self.file_status_label.configure(text=text)
        except:
            pass
    
    # Публичные методы
    
    def set_log_file(self, file_path: str) -> None:
        """
        Установка файла логов.
        
        Args:
            file_path: Путь к файлу логов
        """
        try:
            # Остановка предыдущего мониторинга
            self.stop_monitoring()
            
            self.log_file_path = file_path
            self.last_file_size = 0
            self._last_line_count = 0
            
            # Очистка предыдущих логов
            self.log_entries.clear()
            
            # Чтение файла
            self._read_log_file()
            
            # Обновление статуса
            self._update_file_status()
            
            # Запуск мониторинга
            self.start_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки файла логов: {e}")
    
    def start_monitoring(self) -> None:
        """Запуск мониторинга файла логов."""
        if not self.log_file_path or self.is_monitoring:
            return
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_log_file,
                daemon=True
            )
            self.monitor_thread.start()
            
            self._update_file_status()
            logger.debug("📊 Мониторинг логов запущен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            self.is_monitoring = False
    
    def stop_monitoring(self) -> None:
        """Остановка мониторинга файла логов."""
        if not self.is_monitoring:
            return
        
        try:
            self.is_monitoring = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2)
            
            self._update_file_status()
            logger.debug("🛑 Мониторинг логов остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
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
            entry = LogEntry(timestamp, level, message, module)
            
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
    
    def get_filtered_logs(self) -> List[LogEntry]:
        """
        Получение отфильтрованных логов.
        
        Returns:
            List[LogEntry]: Список отфильтрованных записей
        """
        return self.filtered_entries.copy()
    
    def set_max_lines(self, max_lines: int) -> None:
        """
        Установка максимального количества строк.
        
        Args:
            max_lines: Максимальное количество строк
        """
        self.max_lines = max_lines
        
        # Обрезка если необходимо
        if len(self.log_entries) > max_lines * 2:
            self.log_entries = self.log_entries[-max_lines:]
            self._apply_filters()


# Экспорт для удобного импорта
__all__ = ['LogViewer', 'LogLevel', 'LogEntry']


if __name__ == "__main__":
    # Демонстрация компонента
    def demo_log_viewer():
        """Демонстрация LogViewer."""
        try:
            import tempfile
            import os
            
            print("🧪 Демонстрация LogViewer...")
            
            # Создание тестового файла логов
            with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
                test_log_file = f.name
                f.write("[2024-01-01 10:00:00] INFO - blockchain.node_client: Подключение к QuickNode успешно\n")
                f.write("[2024-01-01 10:00:01] DEBUG - swap_analyzer: Анализ swap событий начат\n")
                f.write("[2024-01-01 10:00:02] WARNING - gas_manager: Высокая цена газа: 15 gwei\n")
                f.write("[2024-01-01 10:00:03] ERROR - balance_checker: Не удалось получить баланс для 0x123...\n")
                f.write("[2024-01-01 10:00:04] INFO - reward_manager: Рассчитаны награды для 150 участников\n")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Log Viewer Demo")
            root.geometry("1000x700")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание LogViewer
            log_viewer = LogViewer(root, log_file_path=test_log_file, auto_scroll=True)
            log_viewer.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Колбэк для новых записей
            def on_new_log(entry):
                print(f"📋 Новая запись: {entry.level} - {entry.message}")
            
            log_viewer.on_log_entry = on_new_log
            
            # Функция для добавления тестовых логов
            def add_test_log():
                import random
                levels = ['INFO', 'DEBUG', 'WARNING', 'ERROR']
                modules = ['staking_manager', 'reward_calculator', 'ui.main_window']
                messages = [
                    "Операция выполнена успешно",
                    "Проверка данных завершена",
                    "Обнаружена аномалия в данных",
                    "Соединение с API восстановлено"
                ]
                
                level = random.choice(levels)
                module = random.choice(modules)
                message = random.choice(messages)
                
                log_viewer.add_log_entry(level, message, module)
                
                # Запланировать следующее добавление
                root.after(2000, add_test_log)
            
            # Запуск добавления тестовых логов
            root.after(1000, add_test_log)
            
            print("✅ LogViewer запущен. Закройте окно для завершения.")
            
            try:
                root.mainloop()
            finally:
                # Удаление тестового файла
                try:
                    os.unlink(test_log_file)
                except:
                    pass
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_log_viewer()
    print("💡 Для демонстрации LogViewer раскомментируй последнюю строку")
