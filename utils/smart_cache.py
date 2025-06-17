"""
PLEX Dynamic Staking Manager - Smart Cache System
Интеллектуальный кэш с предзагрузкой и популярностью.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
from decimal import Decimal

from utils.logger import get_logger

logger = get_logger(__name__)


class SmartCache:
    """
    Интеллектуальный кэш с предзагрузкой соседних данных и
    анализом популярности для оптимизации blockchain запросов.
    """
    
    def __init__(self, analyzer, max_size: int = 50000, default_ttl: int = 300):
        """
        Инициализация умного кэша.
        
        Args:
            analyzer: Анализатор для загрузки данных
            max_size: Максимальный размер кэша
            default_ttl: TTL по умолчанию в секундах
        """
        self.analyzer = analyzer
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # Основной кэш: {cache_key: {'value': value, 'timestamp': time, 'ttl': ttl}}
        self.cache: OrderedDict = OrderedDict()
        
        # Статистика доступа: {key: {'count': int, 'last_access': time}}
        self.access_stats: Dict[str, Dict] = defaultdict(lambda: {'count': 0, 'last_access': 0})
        
        # Популярные адреса для предзагрузки
        self.popular_addresses: List[str] = []
        self.popular_blocks: Set[int] = set()
        
        # Кэш соседних данных
        self.neighbor_cache: Dict[str, List[str]] = {}
        
        # Синхронизация
        self.lock = threading.RLock()
        
        # Фоновая задача очистки
        self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"🧠 SmartCache инициализирован: max_size={max_size}, default_ttl={default_ttl}s")
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        Получить значение из кэша.
        
        Args:
            key: Ключ кэша
            ttl: TTL для этого ключа
            
        Returns:
            Any: Значение или None
        """
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                current_time = time.time()
                
                # Проверка TTL
                if current_time - entry['timestamp'] < entry.get('ttl', self.default_ttl):
                    # Обновляем статистику
                    self._update_access_stats(key)
                    
                    # Перемещаем в конец (LRU)
                    self.cache.move_to_end(key)
                    
                    return entry['value']
                else:
                    # Устаревшая запись
                    del self.cache[key]
            
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранить значение в кэш.
        
        Args:
            key: Ключ кэша
            value: Значение
            ttl: TTL для этого ключа
        """
        with self.lock:
            # Проверка размера кэша
            if len(self.cache) >= self.max_size:
                # Удаляем самые старые записи (LRU)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"🗑️ Удален старый ключ: {oldest_key}")
            
            # Сохранение
            self.cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl or self.default_ttl
            }
            
            # Обновляем статистику
            self._update_access_stats(key)
    
    def get_balance_with_preload(self, address: str, block: int, 
                                neighbor_addresses: Optional[List[str]] = None) -> Optional[Decimal]:
        """
        Получить баланс с предзагрузкой соседних адресов.
        
        Args:
            address: Адрес для получения баланса
            block: Номер блока
            neighbor_addresses: Соседние адреса для предзагрузки
            
        Returns:
            Decimal: Баланс или None
        """
        cache_key = f"balance:{address}:{block}"
        
        # Проверяем кэш
        cached_balance = self.get(cache_key)
        if cached_balance is not None:
            self._update_popularity(address, block)
            return cached_balance
        
        # Если есть соседние адреса, загружаем пакетом
        if neighbor_addresses:
            addresses_to_load = [address]
            
            # Добавляем соседние адреса, которых нет в кэше
            for neighbor in neighbor_addresses[:49]:  # Максимум 50 адресов в multicall
                neighbor_key = f"balance:{neighbor}:{block}"
                if self.get(neighbor_key) is None:
                    addresses_to_load.append(neighbor)
            
            # Multicall запрос - ОДИН вместо множества!
            try:
                balances = self.analyzer.get_balances_multicall(
                    self.analyzer.token_address,
                    addresses_to_load,
                    block
                )
                
                # Кэшируем все полученные балансы
                for addr, balance in balances.items():
                    addr_key = f"balance:{addr}:{block}"
                    self.set(addr_key, balance, ttl=300)  # 5 минут TTL для балансов
                
                # Сохраняем соседние адреса для будущих предзагрузок
                self.neighbor_cache[address] = neighbor_addresses[:20]
                
                self._update_popularity(address, block)
                return balances.get(address)
                
            except Exception as e:
                logger.error(f"❌ Ошибка multicall загрузки: {e}")
                return None
        
        return None
    
    def preload_popular(self, top_count: int = 50) -> None:
        """
        Предзагрузка данных для популярных адресов.
        
        Args:
            top_count: Количество топ адресов для предзагрузки
        """
        if not self.popular_addresses:
            return
            
        def preload_task():
            """Фоновая задача предзагрузки."""
            try:
                # Получаем топ адреса
                top_addresses = self.popular_addresses[:top_count]
                
                # Последний актуальный блок
                current_block = self.analyzer.web3_manager.w3_http.eth.block_number
                
                # Предзагружаем балансы
                missing_addresses = []
                for addr in top_addresses:
                    cache_key = f"balance:{addr}:{current_block}"
                    if self.get(cache_key) is None:
                        missing_addresses.append(addr)
                
                if missing_addresses:
                    logger.info(f"📦 Предзагрузка {len(missing_addresses)} популярных адресов...")
                    
                    # Загружаем батчами
                    for i in range(0, len(missing_addresses), 50):
                        batch = missing_addresses[i:i+50]
                        
                        balances = self.analyzer.get_balances_multicall(
                            self.analyzer.token_address,
                            batch,
                            current_block
                        )
                        
                        # Кэшируем
                        for addr, balance in balances.items():
                            cache_key = f"balance:{addr}:{current_block}"
                            self.set(cache_key, balance, ttl=600)  # 10 минут для предзагруженных
                    
                    logger.info(f"✅ Предзагрузка завершена: {len(missing_addresses)} адресов")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка предзагрузки: {e}")
        
        # Запускаем в фоне
        threading.Thread(target=preload_task, daemon=True).start()
    
    def _update_access_stats(self, key: str) -> None:
        """Обновить статистику доступа."""
        self.access_stats[key]['count'] += 1
        self.access_stats[key]['last_access'] = time.time()
    
    def _update_popularity(self, address: str, block: int) -> None:
        """Обновить рейтинг популярности."""
        # Обновляем популярные адреса
        if address not in self.popular_addresses:
            self.popular_addresses.append(address)
        else:
            # Перемещаем в конец (самые актуальные)
            self.popular_addresses.remove(address)
            self.popular_addresses.append(address)
        
        # Ограничиваем размер списка
        if len(self.popular_addresses) > 1000:
            self.popular_addresses = self.popular_addresses[-500:]
        
        # Обновляем популярные блоки
        self.popular_blocks.add(block)
        if len(self.popular_blocks) > 100:
            # Удаляем самые старые блоки
            sorted_blocks = sorted(self.popular_blocks)
            self.popular_blocks = set(sorted_blocks[-50:])
    
    def _background_cleanup(self) -> None:
        """Фоновая очистка устаревших записей."""
        while True:
            try:
                time.sleep(60)  # Проверка каждую минуту
                
                current_time = time.time()
                expired_keys = []
                
                with self.lock:
                    for key, entry in self.cache.items():
                        if current_time - entry['timestamp'] > entry.get('ttl', self.default_ttl):
                            expired_keys.append(key)
                    
                    # Удаляем устаревшие
                    for key in expired_keys:
                        del self.cache[key]
                
                if expired_keys:
                    logger.debug(f"🧹 Очищено {len(expired_keys)} устаревших записей")
                
                # Очистка старой статистики доступа
                old_stats = []
                for key, stats in self.access_stats.items():
                    if current_time - stats['last_access'] > 3600:  # Старше часа
                        old_stats.append(key)
                
                for key in old_stats:
                    del self.access_stats[key]
                
            except Exception as e:
                logger.error(f"❌ Ошибка фоновой очистки: {e}")
                time.sleep(300)  # Пауза при ошибке
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша.
        
        Returns:
            Dict: Статистика работы кэша
        """
        with self.lock:
            total_access = sum(stats['count'] for stats in self.access_stats.values())
            
            # Топ популярных ключей
            popular_keys = sorted(
                self.access_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
            
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'utilization_percent': round(len(self.cache) / self.max_size * 100, 1),
                'total_accesses': total_access,
                'unique_keys': len(self.access_stats),
                'popular_addresses_count': len(self.popular_addresses),
                'popular_blocks_count': len(self.popular_blocks),
                'top_keys': [{'key': k, 'accesses': v['count']} for k, v in popular_keys]
            }
    
    def clear_expired(self) -> int:
        """
        Принудительная очистка устаревших записей.
        
        Returns:
            int: Количество удаленных записей
        """
        current_time = time.time()
        expired_keys = []
        
        with self.lock:
            for key, entry in self.cache.items():
                if current_time - entry['timestamp'] > entry.get('ttl', self.default_ttl):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
        
        logger.info(f"🧹 Принудительно очищено {len(expired_keys)} записей")
        return len(expired_keys)
    
    def warm_up(self, addresses: List[str], blocks: List[int]) -> None:
        """
        Предварительный прогрев кэша для списка адресов и блоков.
        
        Args:
            addresses: Список адресов для прогрева
            blocks: Список блоков для прогрева
        """
        logger.info(f"🔥 Прогрев кэша: {len(addresses)} адресов × {len(blocks)} блоков")
        
        def warm_up_task():
            """Фоновая задача прогрева."""
            try:
                for block in blocks:
                    # Прогреваем батчами по 50 адресов
                    for i in range(0, len(addresses), 50):
                        batch = addresses[i:i+50]
                        
                        try:
                            balances = self.analyzer.get_balances_multicall(
                                self.analyzer.token_address,
                                batch,
                                block
                            )
                            
                            # Кэшируем с длительным TTL для прогрева
                            for addr, balance in balances.items():
                                cache_key = f"balance:{addr}:{block}"
                                self.set(cache_key, balance, ttl=1800)  # 30 минут
                            
                            logger.debug(f"🔥 Прогрев блока {block}: {len(batch)} адресов")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка прогрева блока {block}: {e}")
                            continue
                
                logger.info(f"✅ Прогрев кэша завершен")
                
            except Exception as e:
                logger.error(f"❌ Ошибка прогрева кэша: {e}")
        
        # Запускаем в фоне
        threading.Thread(target=warm_up_task, daemon=True).start()


# Экспорт для удобного импорта
__all__ = ['SmartCache']


if __name__ == "__main__":
    # Демонстрация работы умного кэша    print("🧪 Демонстрация SmartCache...")
    
    # 🚫 Mock тесты удалены согласно ТЗ
    # Используйте test_components.py для тестирования
    print("🚫 Mock тесты удалены согласно ТЗ. Используйте test_components.py")
