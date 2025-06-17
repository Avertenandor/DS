"""
Модуль: Система кэширования для оптимизации API запросов
Описание: Кэширование блоков, балансов и результатов с TTL для экономии 90% запросов
Зависимости: threading, time, collections
Автор: GitHub Copilot
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from collections import OrderedDict, defaultdict
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.logger import get_logger
from config.constants import TOKEN_DECIMALS

logger = get_logger("CacheManager")


@dataclass
class CacheEntry:
    """Запись в кэше с TTL"""
    value: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    last_access: float = 0


class BlockNumberCache:
    """Кэш номера блока с TTL для экономии 90% запросов поиска текущего блока"""
    
    def __init__(self, ttl_seconds: int = 60):
        self._cache = None
        self._timestamp = 0
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        
        logger.info(f"🔄 BlockNumberCache инициализирован с TTL {ttl_seconds}s")
        
    def get_block_number(self, w3) -> int:
        """Получить номер блока с кэшированием"""
        now = time.time()
        
        with self._lock:
            # Проверяем актуальность кэша
            if self._cache and (now - self._timestamp) < self.ttl:
                self.hits += 1
                logger.debug(f"📦 Cache HIT: block {self._cache}")
                return self._cache
            
            # Кэш устарел или отсутствует - получаем новый
            self.misses += 1
            self._cache = w3.eth.block_number
            self._timestamp = now
            
            logger.debug(f"🔄 Cache MISS: fetched block {self._cache}")
            return self._cache
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика использования кэша"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total,
            'credits_saved': self.hits * 20  # 20 кредитов за запрос
        }


class SmartCache:
    """Интеллектуальный кэш с предзагрузкой и анализом популярности"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.cache: Dict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        
        # Статистика
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Анализ популярности
        self.access_patterns = defaultdict(int)
        self.popular_keys = []
        
        logger.info(f"🧠 SmartCache инициализирован: max_size={max_size}, default_ttl={default_ttl}s")
        
    def get(self, key: str, fetch_func: Callable = None, ttl: int = None, 
            **fetch_kwargs) -> Optional[Any]:
        """Получить значение из кэша или вычислить"""
        now = time.time()
        
        with self._lock:
            # Проверяем наличие в кэше
            if key in self.cache:
                entry = self.cache[key]
                
                # Проверяем TTL
                if now - entry.timestamp < entry.ttl:
                    # Обновляем статистику доступа
                    entry.access_count += 1
                    entry.last_access = now
                    self.access_patterns[key] += 1
                    self.hits += 1
                    
                    # Перемещаем в конец (LRU)
                    self.cache.move_to_end(key)
                    
                    logger.debug(f"📦 Cache HIT: {key}")
                    return entry.value
                else:
                    # Запись устарела
                    del self.cache[key]
                    logger.debug(f"⏰ Cache EXPIRED: {key}")
            
            # Кэш промах - нужно получить значение
            self.misses += 1
            
            if fetch_func is None:
                logger.debug(f"❌ Cache MISS: {key} (no fetch function)")
                return None
            
            # Получаем новое значение
            try:
                value = fetch_func(**fetch_kwargs)
                
                # Сохраняем в кэш
                self.set(key, value, ttl or self.default_ttl)
                
                logger.debug(f"🔄 Cache MISS: {key} (fetched and cached)")
                return value
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения значения для {key}: {e}")
                return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Сохранить значение в кэш"""
        now = time.time()
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Проверяем размер кэша
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Создаем новую запись
            entry = CacheEntry(
                value=value,
                timestamp=now,
                ttl=ttl,
                access_count=1,
                last_access=now
            )
            
            self.cache[key] = entry
            self.access_patterns[key] += 1
            
    def _evict_lru(self):
        """Удалить наименее используемые записи"""
        if not self.cache:
            return
            
        # Удаляем самую старую запись (LRU)
        oldest_key = next(iter(self.cache))
        del self.cache[oldest_key]
        self.evictions += 1
        
        logger.debug(f"🗑️ Evicted LRU entry: {oldest_key}")
    
    def preload_popular(self, fetch_func: Callable, popular_keys: List[str], 
                       **fetch_kwargs):
        """Предзагрузка популярных ключей в фоновом режиме"""
        def _preload():
            for key in popular_keys[:50]:  # Ограничиваем 50 записями
                if key not in self.cache:
                    try:
                        value = fetch_func(key=key, **fetch_kwargs)
                        self.set(key, value)
                        time.sleep(0.1)  # Небольшая задержка между запросами
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка предзагрузки {key}: {e}")
        
        threading.Thread(target=_preload, daemon=True).start()
        logger.info(f"🚀 Запущена предзагрузка {len(popular_keys)} популярных ключей")
    
    def update_popular_keys(self):
        """Обновить список популярных ключей на основе статистики"""
        # Сортируем по количеству обращений
        sorted_keys = sorted(
            self.access_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        self.popular_keys = [key for key, count in sorted_keys[:100]]
        logger.debug(f"📊 Обновлен список популярных ключей: {len(self.popular_keys)}")
    
    def cleanup_expired(self):
        """Очистка устаревших записей"""
        now = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self.cache.items():
                if now - entry.timestamp >= entry.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        if expired_keys:
            logger.info(f"🧹 Очищено {len(expired_keys)} устаревших записей")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика кэша"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': f"{hit_rate:.1f}%",
            'popular_keys_count': len(self.popular_keys),
            'credits_saved': self.hits * 20  # Примерная экономия
        }


class MulticallCache:
    """Специализированный кэш для Multicall запросов балансов"""
    
    def __init__(self, ttl_seconds: int = 120):
        self.cache: Dict[str, Dict[str, Decimal]] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        
        # Статистика
        self.batch_hits = 0
        self.batch_misses = 0
        self.individual_hits = 0
        
        logger.info(f"💰 MulticallCache инициализирован с TTL {ttl_seconds}s")
    
    def get_batch_balances(self, token_address: str, addresses: List[str], 
                          block: int, fetch_func: Callable) -> Dict[str, Decimal]:
        """Получить балансы для списка адресов с кэшированием"""
        cache_key = f"{token_address}:{block}"
        now = time.time()
        
        with self._lock:
            # Проверяем кэш для этого блока
            if (cache_key in self.cache and 
                cache_key in self.timestamps and
                now - self.timestamps[cache_key] < self.ttl):
                
                cached_balances = self.cache[cache_key]
                
                # Проверяем, есть ли все нужные адреса в кэше
                missing_addresses = [addr for addr in addresses if addr not in cached_balances]
                
                if not missing_addresses:
                    # Все адреса в кэше
                    self.batch_hits += 1
                    result = {addr: cached_balances[addr] for addr in addresses}
                    logger.debug(f"📦 Batch cache HIT: {len(addresses)} адресов")
                    return result
                
                # Частичное попадание - запрашиваем только недостающие
                if len(missing_addresses) < len(addresses):
                    logger.debug(f"📦 Partial cache HIT: {len(addresses) - len(missing_addresses)}/{len(addresses)}")
                    
                    # Получаем недостающие балансы
                    new_balances = fetch_func(token_address, missing_addresses, block)
                    
                    # Обновляем кэш
                    cached_balances.update(new_balances)
                    self.timestamps[cache_key] = now
                    
                    # Возвращаем полный результат
                    result = {addr: cached_balances[addr] for addr in addresses}
                    return result
            
            # Полный промах - получаем все балансы
            self.batch_misses += 1
            
            balances = fetch_func(token_address, addresses, block)
            
            # Сохраняем в кэш
            self.cache[cache_key] = balances.copy()
            self.timestamps[cache_key] = now
            
            logger.debug(f"🔄 Batch cache MISS: получено {len(balances)} балансов")
            return balances
    
    def get_balance(self, token_address: str, address: str, block: int) -> Optional[Decimal]:
        """Получить баланс одного адреса из кэша"""
        cache_key = f"{token_address}:{block}"
        now = time.time()
        
        with self._lock:
            if (cache_key in self.cache and 
                cache_key in self.timestamps and
                now - self.timestamps[cache_key] < self.ttl):
                
                if address in self.cache[cache_key]:
                    self.individual_hits += 1
                    return self.cache[cache_key][address]
        
        return None
    
    def cleanup_old_entries(self, keep_latest_n: int = 100):
        """Очистка старых записей, оставляя только последние N блоков"""
        with self._lock:
            if len(self.cache) <= keep_latest_n:
                return
            
            # Сортируем по времени и оставляем только последние
            sorted_keys = sorted(
                self.timestamps.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            keys_to_keep = [key for key, _ in sorted_keys[:keep_latest_n]]
            keys_to_remove = [key for key in self.cache.keys() if key not in keys_to_keep]
            
            for key in keys_to_remove:
                del self.cache[key]
                del self.timestamps[key]
            
            logger.info(f"🧹 Очищено {len(keys_to_remove)} старых записей кэша балансов")
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика кэша балансов"""
        total_batches = self.batch_hits + self.batch_misses
        batch_hit_rate = (self.batch_hits / total_batches * 100) if total_batches > 0 else 0
        
        return {
            'cached_blocks': len(self.cache),
            'batch_hits': self.batch_hits,
            'batch_misses': self.batch_misses,
            'batch_hit_rate': f"{batch_hit_rate:.1f}%",
            'individual_hits': self.individual_hits,
            'estimated_credits_saved': (self.batch_hits * 1000 + self.individual_hits * 20)
        }


# Глобальные экземпляры кэшей
block_cache = BlockNumberCache(ttl_seconds=60)
smart_cache = SmartCache(max_size=50000, default_ttl=300)
multicall_cache = MulticallCache(ttl_seconds=120)


def get_cache_manager_stats() -> Dict[str, Any]:
    """Общая статистика всех кэшей"""
    return {
        'block_cache': block_cache.get_stats(),
        'smart_cache': smart_cache.get_stats(),
        'multicall_cache': multicall_cache.get_stats(),
        'timestamp': datetime.now().isoformat()
    }


def cleanup_all_caches():
    """Очистка всех кэшей"""
    smart_cache.cleanup_expired()
    multicall_cache.cleanup_old_entries()
    logger.info("🧹 Выполнена очистка всех кэшей")


# Периодическая очистка кэшей
def start_cache_cleanup_scheduler():
    """Запуск планировщика очистки кэшей"""
    def cleanup_loop():
        while True:
            time.sleep(300)  # Каждые 5 минут
            try:
                cleanup_all_caches()
                smart_cache.update_popular_keys()
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике очистки кэшей: {e}")
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("⏰ Запущен планировщик очистки кэшей (каждые 5 минут)")


if __name__ == "__main__":
    # 🚫 Mock тесты удалены согласно ТЗ
    # Используйте test_components.py для тестирования с реальными данными BSC
    print("🚫 Mock тесты удалены согласно ТЗ. Используйте test_components.py")
