"""
PLEX Dynamic Staking Manager - Progress Bar
Расширенный компонент прогресс-бара с анимацией и статистикой.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
import customtkinter as ctk

from ui.themes.dark_theme import get_theme
from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class ProgressState(Enum):
    """Состояния прогресс-бара."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ProgressBar(ctk.CTkFrame):
    """
    Production-ready компонент прогресс-бара с расширенным функционалом.
    
    Функциональность:
    - Анимированный прогресс с плавными переходами
    - Отображение времени выполнения и ETA
    - Поддержка пауз и отмены
    - Индикатор скорости выполнения
    - Детальная статистика
    - Множественные стили визуализации
    """
    
    def __init__(
        self,
        parent,
        title: str = "Прогресс",
        show_percentage: bool = True,
        show_eta: bool = True,
        show_speed: bool = True,
        animated: bool = True,
        style: str = "default",
        **kwargs
    ):
        """
        Инициализация ProgressBar.
        
        Args:
            parent: Родительский виджет
            title: Заголовок прогресс-бара
            show_percentage: Показывать процент выполнения
            show_eta: Показывать оценочное время завершения
            show_speed: Показывать скорость выполнения
            animated: Использовать анимацию
            style: Стиль оформления ('default', 'compact', 'detailed')
            **kwargs: Дополнительные параметры
        """
        self.theme = get_theme()
        
        # Применение стиля фрейма
        frame_style = self.theme.get_frame_style('card')
        frame_style.update(kwargs)
        super().__init__(parent, **frame_style)
        
        # Настройки
        self.title = title
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.show_speed = show_speed
        self.animated = animated
        self.style = style
        
        # Состояние прогресса
        self.state = ProgressState.IDLE
        self.current_value = 0.0
        self.max_value = 100.0
        self.min_value = 0.0
        self.target_value = 0.0
        
        # Статистика времени
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.total_paused_time = timedelta()
        self.last_update_time: Optional[datetime] = None
        
        # История прогресса для расчета скорости
        self.progress_history: List[tuple] = []  # (time, value)
        self.max_history_size = 10
        
        # Анимация
        self.animation_thread: Optional[threading.Thread] = None
        self.animation_running = False
        self.animation_speed = 0.02  # секунд между кадрами
        
        # Колбэки
        self.on_progress_changed: Optional[Callable[[float], None]] = None
        self.on_completed: Optional[Callable[[], None]] = None
        self.on_cancelled: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Создание интерфейса
        self._create_widgets()
        self._setup_layout()
        
        logger.debug(f"📊 ProgressBar '{title}' инициализирован")
    
    def _create_widgets(self) -> None:
        """Создание виджетов интерфейса."""
        # Заголовок
        self.title_label = self.theme.create_styled_label(
            self,
            self.title,
            'title' if self.style == 'detailed' else 'primary'
        )
        
        # Основной прогресс-бар
        self.progress_bar = self.theme.create_styled_progressbar(
            self,
            height=12 if self.style == 'detailed' else 8
        )
        
        # Панель информации
        self.info_frame = self.theme.create_styled_frame(self, 'primary')
        
        # Процент выполнения
        if self.show_percentage:
            self.percentage_label = self.theme.create_styled_label(
                self.info_frame,
                "0%",
                'accent'
            )
        
        # Статус
        self.status_label = self.theme.create_styled_label(
            self.info_frame,
            "Готов к запуску",
            'secondary'
        )
        
        # ETA
        if self.show_eta:
            self.eta_label = self.theme.create_styled_label(
                self.info_frame,
                "ETA: --:--",
                'muted'
            )
        
        # Скорость
        if self.show_speed:
            self.speed_label = self.theme.create_styled_label(
                self.info_frame,
                "Скорость: --",
                'muted'
            )
        
        # Время выполнения
        self.elapsed_label = self.theme.create_styled_label(
            self.info_frame,
            "Время: 00:00",
            'muted'
        )
        
        # Панель управления (только для detailed стиля)
        if self.style == 'detailed':
            self.control_frame = self.theme.create_styled_frame(self, 'primary')
            
            self.pause_button = self.theme.create_styled_button(
                self.control_frame,
                "⏸️ Пауза",
                'secondary',
                command=self._toggle_pause,
                width=80
            )
            
            self.cancel_button = self.theme.create_styled_button(
                self.control_frame,
                "❌ Отмена",
                'danger',
                command=self._cancel_progress,
                width=80
            )
            
            self.reset_button = self.theme.create_styled_button(
                self.control_frame,
                "🔄 Сброс",
                'secondary',
                command=self._reset_progress,
                width=80
            )
        
        # Детальная информация (только для detailed стиля)
        if self.style == 'detailed':
            self.details_frame = self.theme.create_styled_frame(self, 'secondary')
            
            self.details_text = self.theme.create_styled_textbox(
                self.details_frame,
                height=60,
                font=('Consolas', 9, 'normal')
            )
    
    def _setup_layout(self) -> None:
        """Настройка расположения виджетов."""
        if self.style == 'compact':
            self._setup_compact_layout()
        elif self.style == 'detailed':
            self._setup_detailed_layout()
        else:
            self._setup_default_layout()
    
    def _setup_default_layout(self) -> None:
        """Стандартная компоновка."""
        # Заголовок
        self.title_label.pack(pady=(10, 5))
        
        # Прогресс-бар
        self.progress_bar.pack(fill='x', padx=10, pady=5)
        
        # Информационная панель
        self.info_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        # Размещение информации
        left_info = self.theme.create_styled_frame(self.info_frame, 'primary')
        left_info.pack(side='left', fill='x', expand=True)
        
        right_info = self.theme.create_styled_frame(self.info_frame, 'primary')
        right_info.pack(side='right')
        
        # Левая часть
        if self.show_percentage:
            self.percentage_label.pack(side='left')
        
        self.status_label.pack(side='left', padx=(10, 0))
        
        # Правая часть
        self.elapsed_label.pack(side='right')
        
        if self.show_eta:
            self.eta_label.pack(side='right', padx=(0, 10))
        
        if self.show_speed:
            self.speed_label.pack(side='right', padx=(0, 10))
    
    def _setup_compact_layout(self) -> None:
        """Компактная компоновка."""
        # Все в одной строке
        main_info = self.theme.create_styled_frame(self, 'primary')
        main_info.pack(fill='x', padx=5, pady=5)
        
        # Заголовок слева
        self.title_label.pack(side='left')
        
        # Прогресс-бар в центре
        progress_frame = self.theme.create_styled_frame(main_info, 'primary')
        progress_frame.pack(side='left', fill='x', expand=True, padx=(10, 10))
        
        self.progress_bar.pack(fill='x')
        
        # Процент справа
        if self.show_percentage:
            self.percentage_label.pack(side='right')
    
    def _setup_detailed_layout(self) -> None:
        """Детальная компоновка."""
        # Заголовок
        self.title_label.pack(pady=(10, 5))
        
        # Прогресс-бар
        self.progress_bar.pack(fill='x', padx=10, pady=5)
        
        # Основная информация
        self.info_frame.pack(fill='x', padx=10, pady=5)
        
        # Первая строка информации
        info_row1 = self.theme.create_styled_frame(self.info_frame, 'primary')
        info_row1.pack(fill='x', pady=2)
        
        if self.show_percentage:
            self.percentage_label.pack(side='left')
        
        self.status_label.pack(side='left', padx=(10, 0))
        self.elapsed_label.pack(side='right')
        
        # Вторая строка информации
        if self.show_eta or self.show_speed:
            info_row2 = self.theme.create_styled_frame(self.info_frame, 'primary')
            info_row2.pack(fill='x', pady=2)
            
            if self.show_speed:
                self.speed_label.pack(side='left')
            
            if self.show_eta:
                self.eta_label.pack(side='right')
        
        # Панель управления
        self.control_frame.pack(fill='x', padx=10, pady=5)
        
        self.pause_button.pack(side='left', padx=(0, 5))
        self.cancel_button.pack(side='left', padx=(0, 5))
        self.reset_button.pack(side='right')
        
        # Детальная информация
        self.details_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        self.details_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def _update_display(self) -> None:
        """Обновление отображения прогресса."""
        try:
            # Обновление прогресс-бара
            progress_ratio = self.get_progress_ratio()
            self.progress_bar.set(progress_ratio)
            
            # Обновление процента
            if self.show_percentage:
                percentage = int(progress_ratio * 100)
                self.percentage_label.configure(text=f"{percentage}%")
            
            # Обновление статуса
            status_text = self._get_status_text()
            self.status_label.configure(text=status_text)
            
            # Обновление времени
            elapsed = self._get_elapsed_time()
            self.elapsed_label.configure(text=f"Время: {self._format_timedelta(elapsed)}")
            
            # Обновление ETA
            if self.show_eta:
                eta = self._calculate_eta()
                eta_text = f"ETA: {self._format_timedelta(eta)}" if eta else "ETA: --:--"
                self.eta_label.configure(text=eta_text)
            
            # Обновление скорости
            if self.show_speed:
                speed = self._calculate_speed()
                speed_text = f"Скорость: {speed:.1f}/с" if speed else "Скорость: --"
                self.speed_label.configure(text=speed_text)
            
            # Обновление детальной информации
            if self.style == 'detailed':
                self._update_details()
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления отображения прогресса: {e}")
    
    def _get_status_text(self) -> str:
        """Получение текста статуса."""
        status_texts = {
            ProgressState.IDLE: "Готов к запуску",
            ProgressState.RUNNING: "Выполняется...",
            ProgressState.PAUSED: "Приостановлено",
            ProgressState.COMPLETED: "Завершено",
            ProgressState.ERROR: "Ошибка",
            ProgressState.CANCELLED: "Отменено"
        }
        
        return status_texts.get(self.state, "Неизвестно")
    
    def _calculate_eta(self) -> Optional[timedelta]:
        """Расчет оценочного времени завершения."""
        try:
            if self.state != ProgressState.RUNNING:
                return None
            
            speed = self._calculate_speed()
            if not speed or speed <= 0:
                return None
            
            remaining = self.max_value - self.current_value
            eta_seconds = remaining / speed
            
            return timedelta(seconds=eta_seconds)
            
        except Exception:
            return None
    
    def _calculate_speed(self) -> Optional[float]:
        """Расчет скорости выполнения."""
        try:
            if len(self.progress_history) < 2:
                return None
            
            # Используем последние записи для расчета скорости
            recent_history = self.progress_history[-5:]  # Последние 5 записей
            
            if len(recent_history) < 2:
                return None
            
            time_diff = (recent_history[-1][0] - recent_history[0][0]).total_seconds()
            value_diff = recent_history[-1][1] - recent_history[0][1]
            
            if time_diff <= 0:
                return None
            
            return value_diff / time_diff
            
        except Exception:
            return None
    
    def _get_elapsed_time(self) -> timedelta:
        """Получение времени выполнения."""
        if not self.start_time:
            return timedelta()
        
        current_time = datetime.now()
        
        if self.state == ProgressState.PAUSED and self.pause_time:
            # Если на паузе, не учитываем время паузы
            elapsed = (self.pause_time - self.start_time) - self.total_paused_time
        else:
            # Общее время минус время пауз
            elapsed = (current_time - self.start_time) - self.total_paused_time
        
        return max(elapsed, timedelta())
    
    def _format_timedelta(self, td: timedelta) -> str:
        """Форматирование времени."""
        if not td:
            return "00:00"
        
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _update_details(self) -> None:
        """Обновление детальной информации."""
        try:
            if not hasattr(self, 'details_text'):
                return
            
            details = []
            details.append(f"Состояние: {self.state.value}")
            details.append(f"Прогресс: {self.current_value:.2f} / {self.max_value:.2f}")
            details.append(f"Соотношение: {self.get_progress_ratio():.2%}")
            
            if self.start_time:
                details.append(f"Время старта: {self.start_time.strftime('%H:%M:%S')}")
            
            elapsed = self._get_elapsed_time()
            details.append(f"Прошло времени: {self._format_timedelta(elapsed)}")
            
            if self.total_paused_time.total_seconds() > 0:
                details.append(f"Время пауз: {self._format_timedelta(self.total_paused_time)}")
            
            speed = self._calculate_speed()
            if speed:
                details.append(f"Скорость: {speed:.2f} единиц/сек")
            
            eta = self._calculate_eta()
            if eta:
                details.append(f"До завершения: {self._format_timedelta(eta)}")
            
            details.append(f"История: {len(self.progress_history)} записей")
            
            # Обновление текста
            self.details_text.delete('1.0', 'end')
            self.details_text.insert('1.0', '\n'.join(details))
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления деталей: {e}")
    
    def _animate_progress(self) -> None:
        """Анимация плавного перехода прогресса."""
        while self.animation_running:
            try:
                if abs(self.current_value - self.target_value) > 0.1:
                    # Плавное движение к целевому значению
                    diff = self.target_value - self.current_value
                    self.current_value += diff * 0.1  # 10% от разности за кадр
                    
                    # Обновление отображения в главном потоке
                    self.after_idle(self._update_display)
                else:
                    # Достигли целевого значения
                    self.current_value = self.target_value
                    self.after_idle(self._update_display)
                
                time.sleep(self.animation_speed)
                
            except Exception as e:
                logger.error(f"❌ Ошибка анимации прогресса: {e}")
                break
    
    def _start_animation(self) -> None:
        """Запуск анимации."""
        if not self.animated or self.animation_running:
            return
        
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self._animate_progress, daemon=True)
        self.animation_thread.start()
    
    def _stop_animation(self) -> None:
        """Остановка анимации."""
        self.animation_running = False
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1)
    
    def _toggle_pause(self) -> None:
        """Переключение паузы."""
        if self.state == ProgressState.RUNNING:
            self.pause()
        elif self.state == ProgressState.PAUSED:
            self.resume()
    
    def _cancel_progress(self) -> None:
        """Отмена прогресса."""
        self.cancel()
    
    def _reset_progress(self) -> None:
        """Сброс прогресса."""
        self.reset()
    
    # Публичные методы
    
    def start(self) -> None:
        """Запуск прогресса."""
        if self.state == ProgressState.RUNNING:
            return
        
        self.state = ProgressState.RUNNING
        
        if not self.start_time:
            self.start_time = datetime.now()
        
        self.last_update_time = datetime.now()
        
        if self.animated:
            self._start_animation()
        
        self._update_display()
        logger.debug(f"▶️ Прогресс '{self.title}' запущен")
    
    def pause(self) -> None:
        """Приостановка прогресса."""
        if self.state != ProgressState.RUNNING:
            return
        
        self.state = ProgressState.PAUSED
        self.pause_time = datetime.now()
        
        if self.style == 'detailed':
            self.pause_button.configure(text="▶️ Продолжить")
        
        self._update_display()
        logger.debug(f"⏸️ Прогресс '{self.title}' приостановлен")
    
    def resume(self) -> None:
        """Возобновление прогресса."""
        if self.state != ProgressState.PAUSED:
            return
        
        if self.pause_time:
            # Добавляем время паузы к общему времени пауз
            pause_duration = datetime.now() - self.pause_time
            self.total_paused_time += pause_duration
            self.pause_time = None
        
        self.state = ProgressState.RUNNING
        self.last_update_time = datetime.now()
        
        if self.style == 'detailed':
            self.pause_button.configure(text="⏸️ Пауза")
        
        self._update_display()
        logger.debug(f"▶️ Прогресс '{self.title}' возобновлен")
    
    def cancel(self) -> None:
        """Отмена прогресса."""
        self.state = ProgressState.CANCELLED
        self._stop_animation()
        self._update_display()
        
        if self.on_cancelled:
            self.on_cancelled()
        
        logger.debug(f"❌ Прогресс '{self.title}' отменен")
    
    def complete(self) -> None:
        """Завершение прогресса."""
        self.state = ProgressState.COMPLETED
        self.current_value = self.max_value
        self.target_value = self.max_value
        self._stop_animation()
        self._update_display()
        
        if self.on_completed:
            self.on_completed()
        
        logger.debug(f"✅ Прогресс '{self.title}' завершен")
    
    def error(self, message: str = "") -> None:
        """Установка состояния ошибки."""
        self.state = ProgressState.ERROR
        self._stop_animation()
        self._update_display()
        
        if self.on_error:
            self.on_error(message)
        
        logger.debug(f"❌ Ошибка в прогрессе '{self.title}': {message}")
    
    def reset(self) -> None:
        """Сброс прогресса."""
        self.state = ProgressState.IDLE
        self.current_value = self.min_value
        self.target_value = self.min_value
        self.start_time = None
        self.pause_time = None
        self.total_paused_time = timedelta()
        self.last_update_time = None
        self.progress_history.clear()
        
        self._stop_animation()
        
        if self.style == 'detailed':
            self.pause_button.configure(text="⏸️ Пауза")
        
        self._update_display()
        logger.debug(f"🔄 Прогресс '{self.title}' сброшен")
    
    def set_progress(self, value: float, message: str = "") -> None:
        """
        Установка значения прогресса.
        
        Args:
            value: Новое значение прогресса
            message: Дополнительное сообщение
        """
        # Ограничение значения
        value = max(self.min_value, min(value, self.max_value))
        
        # Обновление истории
        current_time = datetime.now()
        self.progress_history.append((current_time, value))
        
        # Ограничение размера истории
        if len(self.progress_history) > self.max_history_size:
            self.progress_history = self.progress_history[-self.max_history_size:]
        
        # Установка целевого значения
        if self.animated and self.state == ProgressState.RUNNING:
            self.target_value = value
            if not self.animation_running:
                self._start_animation()
        else:
            self.current_value = value
            self.target_value = value
        
        self.last_update_time = current_time
        
        # Обновление отображения
        if not self.animated:
            self._update_display()
        
        # Колбэк изменения прогресса
        if self.on_progress_changed:
            self.on_progress_changed(value)
        
        # Автоматическое завершение при достижении максимума
        if value >= self.max_value and self.state == ProgressState.RUNNING:
            self.complete()
    
    def increment(self, delta: float = 1.0, message: str = "") -> None:
        """
        Увеличение прогресса на заданное значение.
        
        Args:
            delta: Значение увеличения
            message: Дополнительное сообщение
        """
        new_value = self.current_value + delta
        self.set_progress(new_value, message)
    
    def get_progress_ratio(self) -> float:
        """
        Получение прогресса как отношения (0.0 - 1.0).
        
        Returns:
            float: Отношение прогресса
        """
        if self.max_value == self.min_value:
            return 1.0
        
        return (self.current_value - self.min_value) / (self.max_value - self.min_value)
    
    def set_range(self, min_value: float, max_value: float) -> None:
        """
        Установка диапазона прогресса.
        
        Args:
            min_value: Минимальное значение
            max_value: Максимальное значение
        """
        self.min_value = min_value
        self.max_value = max_value
        
        # Корректировка текущего значения
        self.current_value = max(min_value, min(self.current_value, max_value))
        self.target_value = max(min_value, min(self.target_value, max_value))
        
        self._update_display()
    
    def set_title(self, title: str) -> None:
        """
        Установка заголовка.
        
        Args:
            title: Новый заголовок
        """
        self.title = title
        self.title_label.configure(text=title)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики прогресса.
        
        Returns:
            Dict: Словарь со статистикой
        """
        elapsed = self._get_elapsed_time()
        speed = self._calculate_speed()
        eta = self._calculate_eta()
        
        return {
            'title': self.title,
            'state': self.state.value,
            'current_value': self.current_value,
            'max_value': self.max_value,
            'min_value': self.min_value,
            'progress_ratio': self.get_progress_ratio(),
            'percentage': int(self.get_progress_ratio() * 100),
            'elapsed_time': elapsed.total_seconds(),
            'paused_time': self.total_paused_time.total_seconds(),
            'speed': speed,
            'eta_seconds': eta.total_seconds() if eta else None,
            'history_size': len(self.progress_history),
            'is_animated': self.animated,
            'is_animation_running': self.animation_running
        }


# Экспорт для удобного импорта
__all__ = ['ProgressBar', 'ProgressState']


if __name__ == "__main__":
    # Демонстрация компонента
    def demo_progress_bar():
        """Демонстрация ProgressBar."""
        try:
            print("🧪 Демонстрация ProgressBar...")
            
            # Создание главного окна
            root = ctk.CTk()
            root.title("PLEX Progress Bar Demo")
            root.geometry("800x600")
            
            # Применение темы
            from ui.themes.dark_theme import apply_window_style
            apply_window_style(root)
            
            # Создание разных стилей прогресс-баров
            
            # Компактный
            compact_progress = ProgressBar(
                root,
                title="Компактный прогресс",
                style="compact",
                show_eta=False,
                show_speed=False
            )
            compact_progress.pack(fill='x', padx=20, pady=10)
            
            # Стандартный
            default_progress = ProgressBar(
                root,
                title="Стандартный прогресс",
                style="default",
                animated=True
            )
            default_progress.pack(fill='x', padx=20, pady=10)
            
            # Детальный
            detailed_progress = ProgressBar(
                root,
                title="Детальный прогресс",
                style="detailed",
                animated=True,
                show_percentage=True,
                show_eta=True,
                show_speed=True
            )
            detailed_progress.pack(fill='both', expand=True, padx=20, pady=10)
            
            # Симуляция прогресса
            def simulate_progress():
                import random
                
                # Запуск всех прогресс-баров
                compact_progress.start()
                default_progress.start()
                detailed_progress.start()
                
                def update_progress():
                    # Обновление с разной скоростью
                    compact_progress.increment(random.uniform(0.5, 2.0))
                    default_progress.increment(random.uniform(0.3, 1.5))
                    detailed_progress.increment(random.uniform(0.2, 1.0))
                    
                    # Продолжение если не завершено
                    if (compact_progress.state == ProgressState.RUNNING or
                        default_progress.state == ProgressState.RUNNING or
                        detailed_progress.state == ProgressState.RUNNING):
                        
                        root.after(100, update_progress)  # Обновление каждые 100мс
                
                # Запуск обновления
                root.after(500, update_progress)
            
            # Колбэки
            def on_completed():
                print("✅ Прогресс завершен!")
            
            def on_progress_changed(value):
                # print(f"📊 Прогресс изменен: {value}")
                pass
            
            # Установка колбэков
            detailed_progress.on_completed = on_completed
            detailed_progress.on_progress_changed = on_progress_changed
            
            # Кнопка запуска симуляции
            start_button = ctk.CTkButton(
                root,
                text="🚀 Запустить симуляцию",
                command=simulate_progress,
                font=('Segoe UI', 12, 'bold')
            )
            start_button.pack(pady=10)
            
            print("✅ Demo запущено. Закройте окно для завершения.")
            root.mainloop()
            
        except Exception as e:
            print(f"❌ Ошибка демонстрации: {e}")
    
    # Запуск демонстрации
    # demo_progress_bar()
    print("💡 Для демонстрации ProgressBar раскомментируй последнюю строку")
