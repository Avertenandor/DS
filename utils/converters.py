"""
Модуль: Конвертеры данных для PLEX Dynamic Staking Manager
Описание: Конвертация между Wei/Token, форматирование данных, утилиты для UI
Зависимости: decimal, datetime
Автор: GitHub Copilot
"""

from decimal import Decimal, ROUND_DOWN, ROUND_UP, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any
import json

from config.constants import TOKEN_DECIMALS, TOKEN_SYMBOL
from utils.logger import get_logger

logger = get_logger("Converters")


class TokenConverter:
    """Конвертер для работы с токенами PLEX"""
    
    @staticmethod
    def wei_to_token(wei_amount: Union[int, str], round_digits: int = 9) -> Decimal:
        """
        Конвертировать Wei в токены PLEX
        
        Args:
            wei_amount: Количество в Wei
            round_digits: Количество знаков после запятой для округления
            
        Returns:
            Decimal: Количество токенов
        """
        try:
            wei = Decimal(str(wei_amount))
            token_amount = wei / Decimal(10 ** TOKEN_DECIMALS)
            
            if round_digits is not None:
                token_amount = token_amount.quantize(
                    Decimal(10) ** -round_digits, 
                    rounding=ROUND_DOWN
                )
            
            return token_amount
            
        except Exception as e:
            logger.error(f"❌ Error converting Wei to token: {e}")
            return Decimal(0)
    
    @staticmethod
    def token_to_wei(token_amount: Union[str, float, Decimal]) -> int:
        """
        Конвертировать токены PLEX в Wei
        
        Args:
            token_amount: Количество токенов
            
        Returns:
            int: Количество в Wei
        """
        try:
            amount = Decimal(str(token_amount))
            wei = int(amount * Decimal(10 ** TOKEN_DECIMALS))
            return wei
            
        except Exception as e:
            logger.error(f"❌ Error converting token to Wei: {e}")
            return 0
    
    @staticmethod
    def format_token_amount(amount: Union[str, float, Decimal], 
                          include_symbol: bool = True,
                          precision: int = 4) -> str:
        """
        Форматировать количество токенов для отображения
        
        Args:
            amount: Количество токенов
            include_symbol: Включать символ токена
            precision: Точность отображения
            
        Returns:
            str: Отформатированная строка
        """
        try:
            decimal_amount = Decimal(str(amount))
            
            # Округляем для отображения
            rounded = decimal_amount.quantize(
                Decimal(10) ** -precision,
                rounding=ROUND_HALF_UP
            )
            
            # Форматируем с разделителями тысяч
            formatted = f"{rounded:,}"
            
            if include_symbol:
                formatted += f" {TOKEN_SYMBOL}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Error formatting token amount: {e}")
            return "0"
    
    @staticmethod
    def format_large_number(number: Union[int, float, Decimal], 
                          suffix_map: Optional[Dict] = None) -> str:
        """
        Форматировать большие числа с суффиксами (K, M, B)
        
        Args:
            number: Число для форматирования
            suffix_map: Карта суффиксов
            
        Returns:
            str: Отформатированное число
        """
        if suffix_map is None:
            suffix_map = {
                1_000: 'K',
                1_000_000: 'M', 
                1_000_000_000: 'B',
                1_000_000_000_000: 'T'
            }
        
        try:
            num = float(number)
            
            if num == 0:
                return "0"
            
            # Находим подходящий суффикс
            for threshold in sorted(suffix_map.keys(), reverse=True):
                if abs(num) >= threshold:
                    formatted_num = num / threshold
                    if formatted_num == int(formatted_num):
                        return f"{int(formatted_num)}{suffix_map[threshold]}"
                    else:
                        return f"{formatted_num:.1f}{suffix_map[threshold]}"
            
            # Если число меньше 1000, возвращаем как есть
            if num == int(num):
                return str(int(num))
            else:
                return f"{num:.2f}"
                
        except Exception as e:
            logger.error(f"❌ Error formatting large number: {e}")
            return str(number)


class PriceConverter:
    """Конвертер для работы с ценами и USD стоимостью"""
    
    @staticmethod
    def format_usd_amount(amount: Union[str, float, Decimal], 
                         include_symbol: bool = True,
                         precision: int = 2) -> str:
        """
        Форматировать USD сумму
        
        Args:
            amount: Сумма в USD
            include_symbol: Включать символ $
            precision: Количество знаков после запятой
            
        Returns:
            str: Отформатированная USD сумма
        """
        try:
            decimal_amount = Decimal(str(amount))
            
            # Округляем до нужной точности
            rounded = decimal_amount.quantize(
                Decimal(10) ** -precision,
                rounding=ROUND_HALF_UP
            )
            
            # Форматируем с разделителями тысяч
            formatted = f"{rounded:,}"
            
            if include_symbol:
                formatted = f"${formatted}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Error formatting USD amount: {e}")
            return "$0.00"
    
    @staticmethod
    def is_in_daily_range(usd_amount: Union[str, float, Decimal],
                         min_amount: float = 2.8,
                         max_amount: float = 3.2) -> bool:
        """
        Проверить, находится ли USD сумма в дневном диапазоне
        
        Args:
            usd_amount: Сумма в USD
            min_amount: Минимальная сумма
            max_amount: Максимальная сумма
            
        Returns:
            bool: True если в диапазоне
        """
        try:
            amount = Decimal(str(usd_amount))
            return Decimal(str(min_amount)) <= amount <= Decimal(str(max_amount))
        except Exception:
            return False


class TimeConverter:
    """Конвертер для работы со временем"""
    
    @staticmethod
    def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
        """
        Конвертировать Unix timestamp в datetime
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            datetime: Объект datetime
        """
        try:
            return datetime.fromtimestamp(int(timestamp))
        except Exception as e:
            logger.error(f"❌ Error converting timestamp: {e}")
            return datetime.now()
    
    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> int:
        """
        Конвертировать datetime в Unix timestamp
        
        Args:
            dt: Объект datetime
            
        Returns:
            int: Unix timestamp
        """
        try:
            return int(dt.timestamp())
        except Exception as e:
            logger.error(f"❌ Error converting datetime: {e}")
            return 0
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Форматировать datetime для отображения
        
        Args:
            dt: Объект datetime
            format_str: Строка формата
            
        Returns:
            str: Отформатированная дата/время
        """
        try:
            return dt.strftime(format_str)
        except Exception as e:
            logger.error(f"❌ Error formatting datetime: {e}")
            return "Unknown"
    
    @staticmethod
    def format_duration(seconds: Union[int, float]) -> str:
        """
        Форматировать продолжительность в читаемый вид
        
        Args:
            seconds: Количество секунд
            
        Returns:
            str: Отформатированная продолжительность
        """
        try:
            seconds = int(seconds)
            
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                minutes = seconds // 60
                seconds = seconds % 60
                return f"{minutes}m {seconds}s"
            elif seconds < 86400:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                return f"{hours}h {minutes}m"
            else:
                days = seconds // 86400
                hours = (seconds % 86400) // 3600
                return f"{days}d {hours}h"
                
        except Exception as e:
            logger.error(f"❌ Error formatting duration: {e}")
            return "Unknown"
    
    @staticmethod
    def get_period_dates(days_ago: int) -> tuple:
        """
        Получить даты начала и конца периода
        
        Args:
            days_ago: Количество дней назад
            
        Returns:
            tuple: (start_datetime, end_datetime)
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_ago)
            return start_date, end_date
        except Exception as e:
            logger.error(f"❌ Error calculating period dates: {e}")
            return datetime.now(), datetime.now()


class AddressConverter:
    """Конвертер для работы с адресами"""
    
    @staticmethod
    def format_address(address: str, 
                      start_chars: int = 6, 
                      end_chars: int = 4) -> str:
        """
        Форматировать адрес для отображения (сокращенный вид)
        
        Args:
            address: Полный адрес
            start_chars: Количество символов в начале
            end_chars: Количество символов в конце
            
        Returns:
            str: Сокращенный адрес
        """
        try:
            if len(address) < start_chars + end_chars + 2:
                return address
            
            return f"{address[:start_chars]}...{address[-end_chars:]}"
            
        except Exception as e:
            logger.error(f"❌ Error formatting address: {e}")
            return address
    
    @staticmethod
    def get_address_label(address: str, known_addresses: Optional[Dict] = None) -> str:
        """
        Получить читаемое имя для известного адреса
        
        Args:
            address: Адрес
            known_addresses: Словарь известных адресов
            
        Returns:
            str: Имя адреса или сокращенный адрес
        """
        if known_addresses and address.lower() in known_addresses:
            return known_addresses[address.lower()]
        
        return AddressConverter.format_address(address)


class DataConverter:
    """Общие конвертеры данных"""
    
    @staticmethod
    def percentage_to_string(value: Union[float, Decimal], precision: int = 2) -> str:
        """
        Конвертировать число в процентную строку
        
        Args:
            value: Значение (0.1 = 10%)
            precision: Точность
            
        Returns:
            str: Процентная строка
        """
        try:
            percentage = float(value) * 100
            return f"{percentage:.{precision}f}%"
        except Exception:
            return "0%"
    
    @staticmethod
    def dict_to_json(data: Dict, indent: int = 2) -> str:
        """
        Конвертировать словарь в JSON строку
        
        Args:
            data: Данные для конвертации
            indent: Отступы для форматирования
            
        Returns:
            str: JSON строка
        """
        try:
            return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error converting to JSON: {e}")
            return "{}"
    
    @staticmethod
    def bytes_to_hex(data: bytes) -> str:
        """
        Конвертировать bytes в hex строку
        
        Args:
            data: Данные в bytes
            
        Returns:
            str: Hex строка
        """
        try:
            return data.hex() if data else ""
        except Exception as e:
            logger.error(f"❌ Error converting bytes to hex: {e}")
            return ""
    
    @staticmethod
    def hex_to_int(hex_str: str) -> int:
        """
        Конвертировать hex строку в int
        
        Args:
            hex_str: Hex строка
            
        Returns:
            int: Число
        """
        try:
            # Убираем 0x если есть
            if hex_str.startswith('0x'):
                hex_str = hex_str[2:]
            return int(hex_str, 16)
        except Exception as e:
            logger.error(f"❌ Error converting hex to int: {e}")
            return 0


class UIConverter:
    """Конвертеры для UI элементов"""
    
    @staticmethod
    def format_table_row(data: Dict, max_width: Dict[str, int] = None) -> Dict:
        """
        Форматировать строку таблицы для отображения
        
        Args:
            data: Данные строки
            max_width: Максимальная ширина колонок
            
        Returns:
            Dict: Отформатированные данные
        """
        formatted = {}
        
        for key, value in data.items():
            if max_width and key in max_width:
                width = max_width[key]
                if isinstance(value, str) and len(value) > width:
                    formatted[key] = value[:width-3] + "..."
                else:
                    formatted[key] = str(value)
            else:
                formatted[key] = str(value)
        
        return formatted
    
    @staticmethod
    def status_to_emoji(status: str) -> str:
        """
        Конвертировать статус в emoji
        
        Args:
            status: Статус
            
        Returns:
            str: Emoji
        """
        status_map = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'pending': '⏳',
            'perfect': '🌟',
            'missed_purchase': '⚠️',
            'sold_token': '❌',
            'transferred': '📤',
            'processing': '🔄',
            'completed': '✅',
            'failed': '❌'
        }
        
        return status_map.get(status.lower(), '❓')
    
    @staticmethod
    def category_to_color(category: str) -> str:
        """
        Конвертировать категорию в цвет для UI
        
        Args:
            category: Категория участника
            
        Returns:
            str: Hex цвет
        """
        color_map = {
            'perfect': '#10B981',        # Зеленый
            'missed_purchase': '#F59E0B', # Желтый
            'sold_token': '#EF4444',     # Красный
            'transferred': '#3B82F6'     # Синий
        }
        
        return color_map.get(category.lower(), '#6B7280')  # Серый по умолчанию


# Вспомогательные функции для удобства

def format_plex_amount(amount: Union[str, float, Decimal], precision: int = 4) -> str:
    """Быстрое форматирование PLEX количества"""
    return TokenConverter.format_token_amount(amount, precision=precision)


def format_usd(amount: Union[str, float, Decimal]) -> str:
    """Быстрое форматирование USD суммы"""
    return PriceConverter.format_usd_amount(amount)


def short_address(address: str) -> str:
    """Быстрое сокращение адреса"""
    return AddressConverter.format_address(address)


def time_ago(timestamp: Union[int, datetime]) -> str:
    """Показать время в формате 'N минут назад'"""
    if isinstance(timestamp, int):
        dt = TimeConverter.timestamp_to_datetime(timestamp)
    else:
        dt = timestamp
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} дней назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} часов назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} минут назад"
    else:
        return "Только что"


def format_number(number: Union[int, float, Decimal], decimals: int = 2) -> str:
    """
    Форматирование числа с разделителями тысяч
    
    Args:
        number: Число для форматирования
        decimals: Количество знаков после запятой
        
    Returns:
        str: Отформатированная строка
    """
    try:
        if isinstance(number, Decimal):
            num = float(number)
        else:
            num = number
        
        return f"{num:,.{decimals}f}"
    except Exception as e:
        logger.error(f"❌ Error formatting number: {e}")
        return str(number)


# Функции-обертки для удобства импорта
def wei_to_token(wei_amount: Union[int, str], round_digits: int = 9) -> Decimal:
    """Конвертировать Wei в токены PLEX"""
    return TokenConverter.wei_to_token(wei_amount, round_digits)

def token_to_wei(token_amount: Union[Decimal, float, str]) -> int:
    """Конвертировать токены PLEX в Wei"""
    return TokenConverter.token_to_wei(token_amount)

def format_token_amount(amount: Union[Decimal, float, str], round_digits: int = 4) -> str:
    """Форматировать количество токенов"""
    return TokenConverter.format_token_amount(amount, round_digits)

def format_number(number: Union[int, float, Decimal, str], decimal_places: int = 2) -> str:
    """Форматировать число с разделителями тысяч"""
    try:
        if isinstance(number, Decimal):
            num = float(number)
        elif isinstance(number, str):
            num = float(number)
        else:
            num = number
        
        return f"{num:,.{decimal_places}f}"
    except Exception as e:
        logger.error(f"❌ Error formatting number: {e}")
        return str(number)

def calculate_percentage(part: Union[Decimal, float], total: Union[Decimal, float]) -> Decimal:
    """Рассчитать процент"""
    return TokenConverter.calculate_percentage(part, total)


if __name__ == "__main__":
    # Тестирование конвертеров
    
    # Тест токенов
    wei_amount = 123456789000000000  # 123.456789 PLEX
    token_amount = TokenConverter.wei_to_token(wei_amount)
    formatted = TokenConverter.format_token_amount(token_amount)
    print(f"✅ Token conversion: {wei_amount} Wei -> {token_amount} -> {formatted}")
    
    # Тест USD
    usd_formatted = PriceConverter.format_usd_amount(1234.56)
    print(f"✅ USD format: {usd_formatted}")
    
    # Тест времени
    now = datetime.now()
    timestamp = TimeConverter.datetime_to_timestamp(now)
    back_to_dt = TimeConverter.timestamp_to_datetime(timestamp)
    print(f"✅ Time conversion: {now} -> {timestamp} -> {back_to_dt}")
    
    # Тест адресов
    long_address = "0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1"
    short = AddressConverter.format_address(long_address)
    print(f"✅ Address format: {long_address} -> {short}")
    
    # Тест больших чисел
    large_number = 1234567
    formatted_large = TokenConverter.format_large_number(large_number)
    print(f"✅ Large number: {large_number} -> {formatted_large}")
    
    print("✅ Все конвертеры протестированы")
