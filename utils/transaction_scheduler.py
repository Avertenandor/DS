"""
PLEX Dynamic Staking Manager - Transaction Scheduler
Интеллектуальное планирование транзакций с оптимизацией интервалов.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from decimal import Decimal
import threading
from queue import PriorityQueue, Empty
from collections import defaultdict, deque
import random

from utils.logger import get_logger
from utils.retry import blockchain_retry

logger = get_logger(__name__)


@dataclass
class ScheduledTransaction:
    """Запланированная транзакция."""
    tx_id: str
    scheduled_time: datetime
    transaction_func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1 = высокий, 5 = низкий
    max_retries: int = 3
    retry_count: int = 0
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Сравнение для PriorityQueue (сначала время, потом приоритет)."""
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority < other.priority


@dataclass
class SchedulerStats:
    """Статистика планировщика."""
    total_scheduled: int = 0
    total_executed: int = 0
    total_failed: int = 0
    total_retried: int = 0
    average_delay: float = 0.0
    current_queue_size: int = 0
    last_execution_time: Optional[datetime] = None


class TransactionScheduler:
    """
    Планировщик транзакций с интеллектуальными интервалами.
    
    Функции:
    - Автоматическое распределение транзакций во времени
    - Адаптивные интервалы на основе загрузки сети
    - Retry логика с экспоненциальной задержкой
    - Приоритизация транзакций
    - Защита от спама и перегрузки
    - Мониторинг производительности
    """
    
    def __init__(self, web3_manager, base_interval: float = 1.0, 
                 max_interval: float = 30.0, network_monitor_interval: float = 10.0):
        """
        Инициализация планировщика.
        
        Args:
            web3_manager: Менеджер Web3 подключений
            base_interval: Базовый интервал между транзакциями (сек)
            max_interval: Максимальный интервал (сек)
            network_monitor_interval: Интервал мониторинга сети (сек)
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3_http
        
        # Настройки интервалов
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.current_interval = base_interval
        self.network_monitor_interval = network_monitor_interval
        
        # Очередь транзакций (приоритетная)
        self.transaction_queue = PriorityQueue()
        
        # Статистика и мониторинг
        self.stats = SchedulerStats()
        self.recent_execution_times = deque(maxlen=100)
        self.network_congestion_level = 0.0  # 0.0 - свободно, 1.0 - перегружено
        
        # Контроль потоков
        self.running = False
        self.scheduler_thread = None
        self.monitor_thread = None
        
        # Защита от перегрузки
        self.max_pending_transactions = 1000
        self.rate_limit_window = 60  # секунд
        self.max_transactions_per_window = 100
        self.transaction_timestamps = deque(maxlen=self.max_transactions_per_window)
        
        logger.info(f"⏰ TransactionScheduler инициализирован (интервал: {base_interval}s)")
    
    def start(self):
        """Запуск планировщика."""
        if self.running:
            logger.warning("⚠️ TransactionScheduler уже запущен")
            return
        
        self.running = True
        
        # Запуск потока планировщика
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
        
        # Запуск потока мониторинга сети
        self.monitor_thread = threading.Thread(
            target=self._network_monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info("🚀 TransactionScheduler запущен")
    
    def stop(self):
        """Остановка планировщика."""
        if not self.running:
            return
        
        logger.info("⏹️ Остановка TransactionScheduler...")
        self.running = False
        
        # Ожидание завершения потоков
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("✅ TransactionScheduler остановлен")
    
    def schedule_transaction(self, transaction_func: Callable, 
                           delay_seconds: Optional[float] = None,
                           priority: int = 3,
                           max_retries: int = 3,
                           callback: Optional[Callable] = None,
                           *args, **kwargs) -> str:
        """
        Запланировать выполнение транзакции.
        
        Args:
            transaction_func: Функция для выполнения транзакции
            delay_seconds: Задержка в секундах (None = автоматическая)
            priority: Приоритет (1-5, где 1 = высший)
            max_retries: Максимальное количество повторов
            callback: Функция обратного вызова
            *args, **kwargs: Аргументы для transaction_func
            
        Returns:
            str: ID транзакции
        """
        try:
            # Проверка лимитов
            if self.transaction_queue.qsize() >= self.max_pending_transactions:
                raise Exception(f"Превышен лимит ожидающих транзакций: {self.max_pending_transactions}")
            
            # Проверка rate limit
            if not self._check_rate_limit():
                raise Exception(f"Превышен лимит транзакций: {self.max_transactions_per_window}/{self.rate_limit_window}s")
            
            # Расчет времени выполнения
            if delay_seconds is None:
                delay_seconds = self._calculate_optimal_delay()
            
            scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)
            
            # Создание транзакции
            tx_id = f"tx_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            
            scheduled_tx = ScheduledTransaction(
                tx_id=tx_id,
                scheduled_time=scheduled_time,
                transaction_func=transaction_func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries,
                callback=callback,
                metadata={
                    'created_at': datetime.now(),
                    'delay_seconds': delay_seconds,
                    'congestion_level': self.network_congestion_level
                }
            )
            
            # Добавление в очередь
            self.transaction_queue.put(scheduled_tx)
            self.stats.total_scheduled += 1
            
            logger.debug(f"📅 Транзакция запланирована: {tx_id} (задержка: {delay_seconds:.1f}s)")
            
            return tx_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования транзакции: {e}")
            raise
    
    def schedule_bulk_transactions(self, transactions: List[Dict], 
                                 base_delay: float = 0.0,
                                 interval_between: Optional[float] = None) -> List[str]:
        """
        Запланировать множество транзакций с равномерным распределением.
        
        Args:
            transactions: Список словарей с параметрами транзакций
            base_delay: Базовая задержка перед первой транзакцией
            interval_between: Интервал между транзакциями (None = автоматический)
            
        Returns:
            List[str]: Список ID транзакций
        """
        if interval_between is None:
            interval_between = self.current_interval
        
        tx_ids = []
        
        for i, tx_params in enumerate(transactions):
            try:
                delay = base_delay + (i * interval_between)
                
                tx_id = self.schedule_transaction(
                    delay_seconds=delay,
                    **tx_params
                )
                tx_ids.append(tx_id)
                
            except Exception as e:
                logger.error(f"❌ Ошибка планирования транзакции {i}: {e}")
                tx_ids.append(None)
        
        successful = len([tx for tx in tx_ids if tx])
        logger.info(f"📦 Запланировано {successful}/{len(transactions)} транзакций")
        
        return tx_ids
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Получить статус очереди."""
        self.stats.current_queue_size = self.transaction_queue.qsize()
        
        return {
            'queue_size': self.stats.current_queue_size,
            'current_interval': self.current_interval,
            'network_congestion': self.network_congestion_level,
            'recent_avg_delay': (
                sum(self.recent_execution_times) / len(self.recent_execution_times)
                if self.recent_execution_times else 0.0
            ),
            'rate_limit_usage': len(self.transaction_timestamps),
            'is_running': self.running
        }
    
    def get_statistics(self) -> SchedulerStats:
        """Получить полную статистику."""
        self.stats.current_queue_size = self.transaction_queue.qsize()
        if self.recent_execution_times:
            self.stats.average_delay = sum(self.recent_execution_times) / len(self.recent_execution_times)
        
        return self.stats
    
    def _scheduler_loop(self):
        """Основной цикл планировщика."""
        logger.info("🔄 Запущен цикл планировщика транзакций")
        
        while self.running:
            try:
                # Получение следующей транзакции
                try:
                    scheduled_tx = self.transaction_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Проверка времени выполнения
                now = datetime.now()
                if scheduled_tx.scheduled_time > now:
                    # Рано для выполнения, возвращаем в очередь
                    self.transaction_queue.put(scheduled_tx)
                    time.sleep(0.1)
                    continue
                
                # Выполнение транзакции
                self._execute_scheduled_transaction(scheduled_tx)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле планировщика: {e}")
                time.sleep(1)
        
        logger.info("⏹️ Цикл планировщика завершен")
    
    def _execute_scheduled_transaction(self, scheduled_tx: ScheduledTransaction):
        """Выполнение запланированной транзакции."""
        start_time = time.time()
        
        try:
            logger.debug(f"🚀 Выполнение транзакции: {scheduled_tx.tx_id}")
            
            # Выполнение функции транзакции
            result = scheduled_tx.transaction_func(*scheduled_tx.args, **scheduled_tx.kwargs)
            
            execution_time = time.time() - start_time
            self.recent_execution_times.append(execution_time)
            
            # Обновление статистики
            self.stats.total_executed += 1
            self.stats.last_execution_time = datetime.now()
            
            # Обновление timestamp для rate limiting
            self.transaction_timestamps.append(time.time())
            
            # Вызов callback
            if scheduled_tx.callback:
                try:
                    scheduled_tx.callback(scheduled_tx, result, True)
                except Exception as e:
                    logger.error(f"❌ Ошибка callback для {scheduled_tx.tx_id}: {e}")
            
            logger.debug(f"✅ Транзакция {scheduled_tx.tx_id} выполнена за {execution_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения транзакции {scheduled_tx.tx_id}: {e}")
            
            # Обработка повторов
            if scheduled_tx.retry_count < scheduled_tx.max_retries:
                scheduled_tx.retry_count += 1
                
                # Экспоненциальная задержка для retry
                retry_delay = min(
                    self.base_interval * (2 ** scheduled_tx.retry_count),
                    self.max_interval
                )
                
                scheduled_tx.scheduled_time = datetime.now() + timedelta(seconds=retry_delay)
                
                # Возврат в очередь для повтора
                self.transaction_queue.put(scheduled_tx)
                self.stats.total_retried += 1
                
                logger.info(f"🔄 Транзакция {scheduled_tx.tx_id} будет повторена через {retry_delay:.1f}s (попытка {scheduled_tx.retry_count}/{scheduled_tx.max_retries})")
            else:
                # Максимум повторов достигнут
                self.stats.total_failed += 1
                
                # Вызов callback с ошибкой
                if scheduled_tx.callback:
                    try:
                        scheduled_tx.callback(scheduled_tx, None, False, str(e))
                    except Exception as cb_error:
                        logger.error(f"❌ Ошибка callback для неудачной транзакции {scheduled_tx.tx_id}: {cb_error}")
                
                logger.error(f"💀 Транзакция {scheduled_tx.tx_id} окончательно провалена после {scheduled_tx.max_retries} попыток")
    
    def _network_monitor_loop(self):
        """Цикл мониторинга сети для адаптации интервалов."""
        logger.info("📊 Запущен мониторинг сети")
        
        while self.running:
            try:
                # Мониторинг загрузки сети
                self._update_network_congestion()
                
                # Адаптация интервалов
                self._adapt_intervals()
                
                time.sleep(self.network_monitor_interval)
                
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга сети: {e}")
                time.sleep(self.network_monitor_interval)
        
        logger.info("📊 Мониторинг сети завершен")
    
    def _update_network_congestion(self):
        """Обновление уровня загрузки сети."""
        try:
            # Получение текущего gas price
            current_gas_price = self.w3.eth.gas_price
            
            # Получение количества pending транзакций
            pending_count = len(self.w3.eth.get_block('pending').transactions)
            
            # Простая эвристика для определения загрузки
            # В реальности можно использовать более сложные алгоритмы
            
            # Нормализация gas price (базовая цена 20 Gwei)
            base_gas_price = 20 * 10**9  # 20 Gwei
            gas_factor = min(current_gas_price / base_gas_price, 10.0) / 10.0
            
            # Нормализация pending транзакций
            pending_factor = min(pending_count / 1000, 1.0)
            
            # Комбинированный показатель загрузки
            self.network_congestion_level = (gas_factor * 0.7 + pending_factor * 0.3)
            
            logger.debug(f"📊 Загрузка сети: {self.network_congestion_level:.2f} (gas: {current_gas_price/10**9:.1f} Gwei, pending: {pending_count})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления загрузки сети: {e}")
            # При ошибке используем средний уровень
            self.network_congestion_level = 0.5
    
    def _adapt_intervals(self):
        """Адаптация интервалов на основе загрузки сети."""
        try:
            # Расчет адаптивного интервала
            congestion_multiplier = 1.0 + (self.network_congestion_level * 2.0)
            
            new_interval = min(
                self.base_interval * congestion_multiplier,
                self.max_interval
            )
            
            # Плавное изменение интервала
            if abs(new_interval - self.current_interval) > 0.1:
                self.current_interval = (self.current_interval * 0.8 + new_interval * 0.2)
                
                logger.debug(f"⚙️ Адаптация интервала: {self.current_interval:.2f}s (загрузка: {self.network_congestion_level:.2f})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка адаптации интервалов: {e}")
    
    def _calculate_optimal_delay(self) -> float:
        """Расчет оптимальной задержки для новой транзакции."""
        # Базовая задержка с учетом загрузки сети
        base_delay = self.current_interval
        
        # Добавление случайного джиттера (±20%)
        jitter = random.uniform(-0.2, 0.2) * base_delay
        
        # Учет размера очереди
        queue_factor = min(self.transaction_queue.qsize() / 100, 1.0)
        queue_delay = queue_factor * self.current_interval
        
        total_delay = max(base_delay + jitter + queue_delay, 0.1)
        
        return min(total_delay, self.max_interval)
    
    def _check_rate_limit(self) -> bool:
        """Проверка rate limit."""
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        # Удаление старых timestamp'ов
        while self.transaction_timestamps and self.transaction_timestamps[0] < window_start:
            self.transaction_timestamps.popleft()
        
        # Проверка лимита
        return len(self.transaction_timestamps) < self.max_transactions_per_window


# Экспорт для удобного импорта
__all__ = ['TransactionScheduler', 'ScheduledTransaction', 'SchedulerStats']


if __name__ == "__main__":
    print("⏰ Демонстрация TransactionScheduler...")
    print("💡 Этот модуль требует Web3Manager для инициализации")
    print("🎯 Интеллектуальное планирование транзакций с адаптивными интервалами")
