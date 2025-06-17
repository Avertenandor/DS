"""
PLEX Dynamic Staking Manager - Duplicate Payment Protection Dialog
Защита от двойных выплат с помощью интуитивного UI.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import customtkinter as ctk
from typing import List, Dict, Any, Optional, Callable
from decimal import Decimal
from datetime import datetime, timedelta
import threading
import time

from utils.logger import get_logger
from utils.widget_factory import SafeWidgetFactory

logger = get_logger(__name__)


class DuplicateWarningDialog:
    """
    Диалог предупреждения о возможных дубликатах выплат.
    
    Функции:
    - Интуитивный интерфейс для проверки дубликатов
    - Детальная информация о найденных совпадениях
    - Возможность исключения/подтверждения каждого адреса
    - Экспорт отчета о дубликатах
    - Автоматическое сохранение решений
    """
    
    def __init__(self, parent_window, duplicates_data: List[Dict[str, Any]], 
                 callback: Optional[Callable] = None, widget_factory=None):
        """
        Инициализация диалога.
        
        Args:
            parent_window: Родительское окно
            duplicates_data: Данные о дубликатах
            callback: Функция обратного вызова с результатом
        """
        self.parent = parent_window
        self.duplicates_data = duplicates_data
        self.callback = callback
        
        # Состояние диалога
        self.user_decisions = {}  # address -> {'action': 'exclude'/'include', 'reason': '...'}
        self.result = None
        
        # Создание диалогового окна
        self.dialog = None
        self.create_dialog()
        
        logger.info(f"⚠️ Создан диалог предупреждения о {len(duplicates_data)} дубликатах")
    
    def create_dialog(self):
        """Создание UI диалога."""
        try:
            # Создание модального окна
            self.dialog = ctk.CTkToplevel(self.parent)
            self.dialog.title("⚠️ Обнаружены возможные дубликаты выплат")
            self.dialog.geometry("800x600")
            self.dialog.resizable(True, True)
            
            # Центрирование окна
            self.center_dialog()
            
            # Блокировка взаимодействия с родительским окном
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Настройка темы
            self.setup_theme()
            
            # Создание интерфейса
            self.create_header()
            self.create_duplicates_list()
            self.create_action_buttons()
            
            # Обработка закрытия окна
            self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания диалога: {e}")
            raise
    
    def setup_theme(self):
        """Настройка темы диалога."""
        try:
            # Цветовая схема для предупреждения
            self.colors = {
                'warning_bg': '#2b1810',
                'warning_accent': '#ff6b35',
                'safe_bg': '#1a2b1a',
                'safe_accent': '#4caf50',
                'danger_bg': '#2b1a1a',
                'danger_accent': '#f44336',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0b0'
            }
            
            # Применение темы к диалогу
            self.dialog.configure(fg_color=self.colors['warning_bg'])
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки темы: {e}")
    
    def create_header(self):
        """Создание заголовка диалога."""
        try:
            # Основной контейнер заголовка
            header_frame = ctk.CTkFrame(
                self.dialog,
                fg_color=self.colors['warning_accent'],
                corner_radius=10
            )
            header_frame.pack(fill="x", padx=20, pady=(20, 10))
            
            # Иконка предупреждения и заголовок
            title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
            title_frame.pack(fill="x", padx=20, pady=15)
            
            warning_icon = ctk.CTkLabel(
                title_frame,
                text="⚠️",
                font=ctk.CTkFont(size=32),
                text_color=self.colors['text_primary']
            )
            warning_icon.pack(side="left", padx=(0, 15))
            
            title_text = ctk.CTkLabel(
                title_frame,
                text="Обнаружены возможные дубликаты выплат",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.colors['text_primary']
            )
            title_text.pack(side="left")
            
            # Описание проблемы
            description_label = ctk.CTkLabel(
                header_frame,
                text=(
                    f"Найдено {len(self.duplicates_data)} адресов с возможными дублированными выплатами.\\n"
                    "Проверьте каждый случай и примите решение о включении в выплату."
                ),
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text_primary'],
                wraplength=700
            )
            description_label.pack(padx=20, pady=(0, 15))
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания заголовка: {e}")
    
    def create_duplicates_list(self):
        """Создание списка дубликатов."""
        try:
            # Контейнер для списка
            list_frame = ctk.CTkFrame(self.dialog)
            list_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Заголовок списка
            list_header = ctk.CTkLabel(
                list_frame,
                text="Найденные дубликаты:",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            list_header.pack(fill="x", padx=15, pady=(15, 5))
            
            # Прокручиваемый контейнер
            scrollable_frame = ctk.CTkScrollableFrame(
                list_frame,
                height=350
            )
            scrollable_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            
            # Создание элементов списка
            for i, duplicate_info in enumerate(self.duplicates_data):
                self.create_duplicate_item(scrollable_frame, duplicate_info, i)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания списка дубликатов: {e}")
    
    def create_duplicate_item(self, parent, duplicate_info: Dict[str, Any], index: int):
        """Создание элемента списка дубликатов."""
        try:
            address = duplicate_info.get('address', 'Unknown')
            amount = duplicate_info.get('amount', Decimal('0'))
            risk_level = duplicate_info.get('risk_level', 'medium')
            last_payment = duplicate_info.get('last_payment_date')
            reasons = duplicate_info.get('reasons', [])
            
            # Определение цвета на основе уровня риска
            risk_colors = {
                'high': self.colors['danger_accent'],
                'medium': self.colors['warning_accent'],
                'low': '#ffeb3b'
            }
            risk_color = risk_colors.get(risk_level, self.colors['warning_accent'])
            
            # Контейнер элемента
            item_frame = ctk.CTkFrame(
                parent,
                fg_color=risk_color,
                corner_radius=8
            )
            item_frame.pack(fill="x", pady=5)
            
            # Основная информация
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(fill="x", padx=15, pady=10)
            
            # Адрес и сумма
            address_label = ctk.CTkLabel(
                info_frame,
                text=f"📍 {address[:10]}...{address[-10:]}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            )
            address_label.pack(fill="x")
            
            amount_label = ctk.CTkLabel(
                info_frame,
                text=f"💰 Сумма: {amount:,.2f} PLEX",
                font=ctk.CTkFont(size=11),
                anchor="w"
            )
            amount_label.pack(fill="x")
            
            # Информация о последней выплате
            if last_payment:
                last_payment_str = last_payment.strftime("%d.%m.%Y %H:%M") if isinstance(last_payment, datetime) else str(last_payment)
                payment_label = ctk.CTkLabel(
                    info_frame,
                    text=f"⏰ Последняя выплата: {last_payment_str}",
                    font=ctk.CTkFont(size=10),
                    text_color=self.colors['text_secondary'],
                    anchor="w"
                )
                payment_label.pack(fill="x")
            
            # Причины дублирования
            if reasons:
                reasons_text = " • ".join(reasons[:3])  # Первые 3 причины
                if len(reasons) > 3:
                    reasons_text += f" (+{len(reasons)-3} еще)"
                
                reasons_label = ctk.CTkLabel(
                    info_frame,
                    text=f"⚠️ Причины: {reasons_text}",
                    font=ctk.CTkFont(size=10),
                    text_color=self.colors['text_secondary'],
                    anchor="w",
                    wraplength=400
                )
                reasons_label.pack(fill="x", pady=(5, 0))
            
            # Кнопки действий
            actions_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            actions_frame.pack(fill="x", padx=15, pady=(0, 10))
              # Кнопка исключения
            exclude_btn = ctk.CTkButton(
                actions_frame,
                text="❌ Исключить",
                width=100,
                height=30,
                fg_color=self.colors['danger_accent'],
                command=lambda addr=address: self.exclude_address(addr, index)
            )
            exclude_btn.pack(side="left", padx=(0, 10))
              # Кнопка включения
            include_btn = ctk.CTkButton(
                actions_frame,
                text="✅ Включить",
                width=100,
                height=30,
                fg_color=self.colors['safe_accent'],
                command=lambda addr=address: self.include_address(addr, index)
            )
            include_btn.pack(side="left", padx=(0, 10))
              # Кнопка деталей
            details_btn = ctk.CTkButton(
                actions_frame,
                text="📋 Детали",
                width=80,
                height=30,
                fg_color="#607d8b",
                command=lambda addr=address: self.show_details(addr, duplicate_info)
            )
            details_btn.pack(side="left")
            
            # Статус решения
            status_label = ctk.CTkLabel(
                actions_frame,
                text="⏳ Ожидает решения",
                font=ctk.CTkFont(size=10),
                text_color=self.colors['text_secondary']
            )
            status_label.pack(side="right")
            
            # Сохранение ссылок для обновления
            setattr(status_label, 'address', address)
            setattr(item_frame, 'status_label', status_label)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания элемента дубликата: {e}")
    
    def create_action_buttons(self):
        """Создание кнопок действий."""
        try:
            # Контейнер кнопок
            buttons_frame = ctk.CTkFrame(self.dialog)
            buttons_frame.pack(fill="x", padx=20, pady=(10, 20))
            
            # Левая группа кнопок
            left_buttons = ctk.CTkFrame(buttons_frame, fg_color="transparent")
            left_buttons.pack(side="left", padx=15, pady=15)
              # Кнопка исключения всех
            exclude_all_btn = ctk.CTkButton(
                left_buttons,
                text="❌ Исключить все",
                width=120,
                height=35,
                fg_color=self.colors['danger_accent'],
                command=self.exclude_all
            )
            exclude_all_btn.pack(side="left", padx=(0, 10))
              # Кнопка включения всех
            include_all_btn = ctk.CTkButton(
                left_buttons,
                text="✅ Включить все",
                width=120,
                height=35,
                fg_color=self.colors['safe_accent'],
                command=self.include_all
            )
            include_all_btn.pack(side="left", padx=(0, 10))
            
            # Правая группа кнопок
            right_buttons = ctk.CTkFrame(buttons_frame, fg_color="transparent")
            right_buttons.pack(side="right", padx=15, pady=15)
              # Кнопка отмены
            cancel_btn = ctk.CTkButton(
                right_buttons,
                text="↩️ Отмена",
                width=100,
                height=35,
                fg_color="#757575",
                command=self.on_cancel
            )
            cancel_btn.pack(side="left", padx=(0, 10))
              # Кнопка применения
            apply_btn = ctk.CTkButton(
                right_buttons,
                text="✅ Применить",
                width=120,
                height=35,
                fg_color="#2196f3",
                command=self.on_apply
            )
            apply_btn.pack(side="left")
            
            # Статистика решений
            self.stats_label = ctk.CTkLabel(
                buttons_frame,
                text=self.get_stats_text(),
                font=ctk.CTkFont(size=10),
                text_color=self.colors['text_secondary']
            )
            self.stats_label.pack(pady=5)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания кнопок действий: {e}")
    
    def exclude_address(self, address: str, index: int):
        """Исключить адрес из выплаты."""
        try:
            self.user_decisions[address] = {
                'action': 'exclude',
                'reason': 'Исключен пользователем',
                'timestamp': datetime.now()
            }
            
            self.update_item_status(address, "❌ Исключен")
            self.update_stats()
            
            logger.debug(f"👤 Адрес {address[:10]}... исключен пользователем")
            
        except Exception as e:
            logger.error(f"❌ Ошибка исключения адреса: {e}")
    
    def include_address(self, address: str, index: int):
        """Включить адрес в выплату."""
        try:
            self.user_decisions[address] = {
                'action': 'include',
                'reason': 'Подтвержден пользователем',
                'timestamp': datetime.now()
            }
            
            self.update_item_status(address, "✅ Включен")
            self.update_stats()
            
            logger.debug(f"👤 Адрес {address[:10]}... включен пользователем")
            
        except Exception as e:
            logger.error(f"❌ Ошибка включения адреса: {e}")
    
    def show_details(self, address: str, duplicate_info: Dict[str, Any]):
        """Показать детальную информацию о дубликате."""
        try:
            # Создание окна деталей
            details_window = ctk.CTkToplevel(self.dialog)
            details_window.title(f"Детали дубликата: {address[:10]}...")
            details_window.geometry("500x400")
            details_window.transient(self.dialog)
            
            # Содержимое окна деталей
            details_frame = ctk.CTkScrollableFrame(details_window)
            details_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Заголовок
            title_label = ctk.CTkLabel(
                details_frame,
                text=f"Детальная информация о дубликате",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            title_label.pack(anchor="w", pady=(0, 20))
            
            # Информация об адресе
            info_items = [
                ("📍 Адрес:", address),
                ("💰 Сумма:", f"{duplicate_info.get('amount', 0):,.2f} PLEX"),
                ("⚠️ Уровень риска:", duplicate_info.get('risk_level', 'medium').upper()),
                ("⏰ Последняя выплата:", str(duplicate_info.get('last_payment_date', 'Неизвестно'))),
                ("🔍 Найдено совпадений:", str(duplicate_info.get('matches_count', 0))),
            ]
            
            for label, value in info_items:
                item_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
                item_frame.pack(fill="x", pady=2)
                
                label_widget = ctk.CTkLabel(item_frame, text=label, width=150, anchor="w")
                label_widget.pack(side="left")
                
                value_widget = ctk.CTkLabel(item_frame, text=value, anchor="w")
                value_widget.pack(side="left", padx=(10, 0))
            
            # Причины дублирования
            reasons = duplicate_info.get('reasons', [])
            if reasons:
                reasons_label = ctk.CTkLabel(
                    details_frame,
                    text="⚠️ Причины дублирования:",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w"
                )
                reasons_label.pack(anchor="w", pady=(20, 5))
                
                for reason in reasons:
                    reason_label = ctk.CTkLabel(
                        details_frame,
                        text=f"  • {reason}",
                        anchor="w"
                    )
                    reason_label.pack(anchor="w", pady=1)
            
            # Кнопка закрытия
            close_btn = ctk.CTkButton(
                details_window,
                text="Закрыть",
                command=details_window.destroy
            )
            close_btn.pack(pady=20)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа деталей: {e}")
    
    def exclude_all(self):
        """Исключить все адреса."""
        try:
            for duplicate_info in self.duplicates_data:
                address = duplicate_info.get('address')
                if address:
                    self.user_decisions[address] = {
                        'action': 'exclude',
                        'reason': 'Исключен массовой операцией',
                        'timestamp': datetime.now()
                    }
                    self.update_item_status(address, "❌ Исключен")
            
            self.update_stats()
            logger.info("👥 Все дубликаты исключены пользователем")
            
        except Exception as e:
            logger.error(f"❌ Ошибка массового исключения: {e}")
    
    def include_all(self):
        """Включить все адреса."""
        try:
            for duplicate_info in self.duplicates_data:
                address = duplicate_info.get('address')
                if address:
                    self.user_decisions[address] = {
                        'action': 'include',
                        'reason': 'Включен массовой операцией',
                        'timestamp': datetime.now()
                    }
                    self.update_item_status(address, "✅ Включен")
            
            self.update_stats()
            logger.info("👥 Все дубликаты включены пользователем")
            
        except Exception as e:
            logger.error(f"❌ Ошибка массового включения: {e}")
    
    def update_item_status(self, address: str, status_text: str):
        """Обновление статуса элемента списка."""
        try:
            # Поиск и обновление метки статуса
            for widget in self.dialog.winfo_children():
                self._find_and_update_status_label(widget, address, status_text)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса: {e}")
    
    def _find_and_update_status_label(self, widget, address: str, status_text: str):
        """Рекурсивный поиск и обновление метки статуса."""
        try:
            if hasattr(widget, 'status_label'):
                status_label = widget.status_label
                if hasattr(status_label, 'address') and status_label.address == address:
                    status_label.configure(text=status_text)
                    return
            
            # Рекурсивный поиск в дочерних виджетах
            for child in widget.winfo_children():
                self._find_and_update_status_label(child, address, status_text)
                
        except Exception:
            pass  # Игнорируем ошибки поиска
    
    def update_stats(self):
        """Обновление статистики решений."""
        try:
            if hasattr(self, 'stats_label'):
                self.stats_label.configure(text=self.get_stats_text())
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")
    
    def get_stats_text(self) -> str:
        """Получить текст статистики."""
        try:
            total = len(self.duplicates_data)
            decided = len(self.user_decisions)
            excluded = len([d for d in self.user_decisions.values() if d['action'] == 'exclude'])
            included = len([d for d in self.user_decisions.values() if d['action'] == 'include'])
            pending = total - decided
            
            return f"Всего: {total} | Решено: {decided} | Исключено: {excluded} | Включено: {included} | Ожидает: {pending}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return "Статистика недоступна"
    
    def on_apply(self):
        """Применение решений."""
        try:
            # Проверка, что все решения приняты
            total_decisions = len(self.user_decisions)
            total_duplicates = len(self.duplicates_data)
            
            if total_decisions < total_duplicates:
                # Предупреждение о нерешенных дубликатах
                pending_count = total_duplicates - total_decisions
                
                confirm_dialog = ctk.CTkToplevel(self.dialog)
                confirm_dialog.title("⚠️ Не все решения приняты")
                confirm_dialog.geometry("400x200")
                confirm_dialog.transient(self.dialog)
                confirm_dialog.grab_set()
                
                warning_label = ctk.CTkLabel(
                    confirm_dialog,
                    text=f"Остается {pending_count} нерешенных дубликатов.\\nПродолжить с текущими решениями?",
                    font=ctk.CTkFont(size=12),
                    wraplength=350
                )
                warning_label.pack(pady=30)
                
                buttons_frame = ctk.CTkFrame(confirm_dialog, fg_color="transparent")
                buttons_frame.pack(pady=20)
                
                yes_btn = ctk.CTkButton(
                    buttons_frame,
                    text="Да, продолжить",
                    command=lambda: [confirm_dialog.destroy(), self._finalize_decisions()]
                )
                yes_btn.pack(side="left", padx=10)
                
                no_btn = ctk.CTkButton(
                    buttons_frame,
                    text="Нет, вернуться",
                    command=confirm_dialog.destroy
                )
                no_btn.pack(side="left", padx=10)
                
                return
            
            # Применение решений
            self._finalize_decisions()
            
        except Exception as e:
            logger.error(f"❌ Ошибка применения решений: {e}")
    
    def _finalize_decisions(self):
        """Финализация и применение решений."""
        try:
            # Подготовка результата
            self.result = {
                'user_decisions': self.user_decisions,
                'excluded_addresses': [
                    addr for addr, decision in self.user_decisions.items()
                    if decision['action'] == 'exclude'
                ],
                'included_addresses': [
                    addr for addr, decision in self.user_decisions.items()
                    if decision['action'] == 'include'
                ],
                'total_duplicates': len(self.duplicates_data),
                'total_decisions': len(self.user_decisions),
                'timestamp': datetime.now()
            }
            
            # Логирование результата
            excluded_count = len(self.result['excluded_addresses'])
            included_count = len(self.result['included_addresses'])
            
            logger.info(f"✅ Решения по дубликатам приняты: исключено {excluded_count}, включено {included_count}")
            
            # Вызов callback
            if self.callback:
                threading.Thread(
                    target=self.callback,
                    args=(self.result,),
                    daemon=True
                ).start()
            
            # Закрытие диалога
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"❌ Ошибка финализации решений: {e}")
    
    def on_cancel(self):
        """Отмена диалога."""
        try:
            logger.info("↩️ Диалог дубликатов отменен пользователем")
            
            # Результат отмены
            self.result = {
                'cancelled': True,
                'timestamp': datetime.now()
            }
            
            # Вызов callback с отменой
            if self.callback:
                threading.Thread(
                    target=self.callback,
                    args=(self.result,),
                    daemon=True
                ).start()
            
            self.dialog.destroy()
            
        except Exception as e:
            logger.error(f"❌ Ошибка отмены диалога: {e}")
            if self.dialog:
                self.dialog.destroy()
    
    def center_dialog(self):
        """Центрирование диалога относительно родительского окна."""
        try:
            # Обновление геометрии для получения актуальных размеров
            self.dialog.update_idletasks()
            
            # Получение размеров окон
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            dialog_width = self.dialog.winfo_width()
            dialog_height = self.dialog.winfo_height()
            
            # Расчет центральной позиции
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
            
            # Применение позиции
            self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка центрирования диалога: {e}")


def show_duplicate_warning(parent_window, duplicates_data: List[Dict[str, Any]], 
                          callback: Optional[Callable] = None) -> DuplicateWarningDialog:
    """
    Показать диалог предупреждения о дубликатах.
    
    Args:
        parent_window: Родительское окно
        duplicates_data: Данные о дубликатах
        callback: Функция обратного вызова
        
    Returns:
        DuplicateWarningDialog: Экземпляр диалога
    """
    try:
        dialog = DuplicateWarningDialog(parent_window, duplicates_data, callback)
        return dialog
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания диалога предупреждения: {e}")
        raise


# Экспорт для удобного импорта
__all__ = ['DuplicateWarningDialog', 'show_duplicate_warning']


if __name__ == "__main__":
    print("⚠️ Демонстрация DuplicateWarningDialog...")
    print("💡 Этот модуль требует CustomTkinter и родительское окно")
    print("🛡️ Защита от двойных выплат с интуитивным UI")
