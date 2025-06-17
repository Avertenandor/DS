"""
Модуль: Retry декораторы для блокчейн операций
Описание: Умные retry стратегии с экспоненциальным backoff для различных типов ошибок
Зависимости: tenacity, functools, time
Автор: GitHub Copilot
"""

import functools
import time
import random
from typing import Callable, Type, Union, List, Optional
from tenacity import (
    retry, stop_after_attempt, wait_exponential, 
    retry_if_exception_type, wait_fixed, wait_random_exponential
)

from utils.logger import get_logger
from config.settings import settings

logger = get_logger("Retry")


class BlockchainRetryError(Exception):
    """Базовый класс для ошибок retry"""
    pass


class RateLimitError(BlockchainRetryError):
    """Ошибка превышения лимита запросов"""
    pass


class PayloadTooLargeError(BlockchainRetryError):
    """Ошибка слишком большого payload"""
    pass


class ConnectionError(BlockchainRetryError):
    """Ошибка подключения к ноде"""
    pass


class TemporaryNodeError(BlockchainRetryError):
    """Временная ошибка ноды"""
    pass


def extract_error_type(exception: Exception) -> str:
    """Определить тип ошибки по сообщению"""
    error_msg = str(exception).lower()
    
    if "rate limit" in error_msg or "too many requests" in error_msg or "429" in error_msg:
        return "rate_limit"
    elif "payload too large" in error_msg or "request entity too large" in error_msg:
        return "payload_too_large"
    elif "connection" in error_msg or "timeout" in error_msg or "network" in error_msg:
        return "connection"
    elif "internal server error" in error_msg or "502" in error_msg or "503" in error_msg:
        return "temporary_node"
    else:
        return "unknown"


def log_retry_attempt(retry_state):
    """Логирование попыток retry"""
    attempt = retry_state.attempt_number
    if hasattr(retry_state, 'outcome') and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        error_type = extract_error_type(exception)
        logger.warning(f"🔄 Retry attempt {attempt} failed: {error_type} - {exception}")
    else:
        logger.debug(f"🔄 Retry attempt {attempt}")


def blockchain_retry(
    max_attempts: int = None,
    base_delay: float = None,
    max_delay: float = 60.0,
    jitter: bool = True,
    rate_limit_delay: float = 2.0
):
    """
    Умный retry декоратор для блокчейн операций
    
    Args:
        max_attempts: Максимальное количество попыток (по умолчанию из настроек)
        base_delay: Базовая задержка в секундах (по умолчанию из настроек)
        max_delay: Максимальная задержка в секундах
        jitter: Добавлять случайную задержку для распределения нагрузки
        rate_limit_delay: Дополнительная задержка для rate limit ошибок
    """
    if max_attempts is None:
        max_attempts = settings.retry_attempts
    if base_delay is None:
        base_delay = settings.retry_delay_base
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Логируем попытку
                    if attempt > 1:
                        logger.debug(f"🔄 Retry attempt {attempt}/{max_attempts} for {func.__name__}")
                    
                    # Выполняем функцию
                    result = func(*args, **kwargs)
                    
                    # Успех - логируем если были retry
                    if attempt > 1:
                        logger.info(f"✅ {func.__name__} succeeded on attempt {attempt}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    error_type = extract_error_type(e)
                    
                    # Проверяем, стоит ли повторять
                    if not should_retry(e, attempt, max_attempts):
                        logger.error(f"❌ {func.__name__} failed permanently: {e}")
                        raise e
                    
                    # Рассчитываем задержку
                    delay = calculate_retry_delay(
                        attempt, base_delay, max_delay, error_type, 
                        rate_limit_delay, jitter
                    )
                    
                    logger.warning(
                        f"⏳ {func.__name__} attempt {attempt} failed ({error_type}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    
                    # Ждем перед следующей попыткой
                    time.sleep(delay)
            
            # Все попытки исчерпаны
            logger.error(f"❌ {func.__name__} failed after {max_attempts} attempts")
            raise last_exception
            
        return wrapper
    return decorator


def should_retry(exception: Exception, attempt: int, max_attempts: int) -> bool:
    """Определить, стоит ли повторять операцию"""
    
    # Не повторяем на последней попытке
    if attempt >= max_attempts:
        return False
    
    error_msg = str(exception).lower()
    
    # Никогда не повторяем для постоянных ошибок
    permanent_errors = [
        "invalid address",
        "invalid transaction",
        "insufficient funds",
        "nonce too low",
        "authentication failed",
        "unauthorized",
        "forbidden",
        "bad request"
    ]
    
    for permanent_error in permanent_errors:
        if permanent_error in error_msg:
            return False
    
    # Всегда повторяем для временных ошибок
    temporary_errors = [
        "rate limit",
        "too many requests",
        "payload too large",
        "connection",
        "timeout",
        "internal server error",
        "bad gateway",
        "service unavailable",
        "gateway timeout"
    ]
    
    for temporary_error in temporary_errors:
        if temporary_error in error_msg:
            return True
    
    # По умолчанию не повторяем неизвестные ошибки
    return False


def calculate_retry_delay(
    attempt: int, 
    base_delay: float, 
    max_delay: float, 
    error_type: str,
    rate_limit_delay: float,
    jitter: bool
) -> float:
    """Рассчитать задержку для retry"""
    
    # Базовая экспоненциальная задержка
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    
    # Дополнительная задержка для rate limit
    if error_type == "rate_limit":
        delay += rate_limit_delay
    
    # Дополнительная задержка для payload too large
    elif error_type == "payload_too_large":
        delay += 1.0  # Даем серверу время восстановиться
    
    # Добавляем jitter для распределения нагрузки
    if jitter:
        jitter_amount = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_amount, jitter_amount)
    
    return max(0.1, delay)  # Минимум 0.1 секунды


# Специализированные декораторы для разных типов операций

def api_call_retry(max_attempts: int = 5):
    """Retry для API вызовов с умеренными настройками"""
    return blockchain_retry(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=30.0,
        rate_limit_delay=2.0
    )


def critical_operation_retry(max_attempts: int = 10):
    """Retry для критических операций с агрессивными настройками"""
    return blockchain_retry(
        max_attempts=max_attempts,
        base_delay=0.5,
        max_delay=60.0,
        rate_limit_delay=5.0
    )


def lightweight_retry(max_attempts: int = 3):
    """Retry для легких операций с быстрым восстановлением"""
    return blockchain_retry(
        max_attempts=max_attempts,
        base_delay=0.2,
        max_delay=5.0,
        rate_limit_delay=1.0
    )


def gas_transaction_retry(max_attempts: int = 7):
    """Специальный retry для газовых транзакций"""
    return blockchain_retry(
        max_attempts=max_attempts,
        base_delay=2.0,
        max_delay=120.0,
        rate_limit_delay=10.0
    )


# Tenacity декораторы для совместимости

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((ConnectionError, TemporaryNodeError)),
    after=log_retry_attempt
)
def tenacity_api_call(func: Callable) -> Callable:
    """Tenacity декоратор для API вызовов"""
    return func


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2) + wait_random_exponential(multiplier=1, max=10),
    retry=retry_if_exception_type(RateLimitError),
    after=log_retry_attempt
)
def tenacity_rate_limit_retry(func: Callable) -> Callable:
    """Tenacity декоратор для rate limit ошибок"""
    return func


class RetryCounter:
    """Счетчик retry попыток для мониторинга"""
    
    def __init__(self):
        self.counters = {}
        self.reset_time = time.time()
    
    def increment(self, operation: str, error_type: str):
        """Увеличить счетчик для операции и типа ошибки"""
        key = f"{operation}:{error_type}"
        self.counters[key] = self.counters.get(key, 0) + 1
    
    def get_stats(self) -> dict:
        """Получить статистику retry попыток"""
        total_retries = sum(self.counters.values())
        uptime_hours = (time.time() - self.reset_time) / 3600
        
        return {
            "total_retries": total_retries,
            "retries_per_hour": total_retries / uptime_hours if uptime_hours > 0 else 0,
            "by_operation": self.counters,
            "uptime_hours": uptime_hours
        }
    
    def reset(self):
        """Сбросить счетчики"""
        self.counters.clear()
        self.reset_time = time.time()


# Глобальный счетчик retry
retry_counter = RetryCounter()


def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Универсальный декоратор retry с настраиваемыми параметрами
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками
        backoff: Коэффициент увеличения задержки
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"❌ {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"⚠️ {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator


if __name__ == "__main__":
    # Тестирование retry декораторов
    
    @api_call_retry()
    def test_api_call(should_fail: bool = False):
        """Тестовая функция API вызова"""
        if should_fail:
            raise Exception("rate limit exceeded")
        return "success"
    
    @critical_operation_retry()
    def test_critical_operation(should_fail: bool = False):
        """Тестовая критическая операция"""
        if should_fail:
            raise Exception("connection timeout")
        return "critical success"
    
    # Тестируем успешный вызов
    result = test_api_call(False)
    print(f"✅ API call result: {result}")
    
    # Тестируем неуспешный вызов
    try:
        result = test_api_call(True)
    except Exception as e:
        print(f"❌ API call failed after retries: {e}")
    
    # Статистика retry
    stats = retry_counter.get_stats()
    print(f"📊 Retry stats: {stats}")
