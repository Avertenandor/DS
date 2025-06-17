"""
Модуль: Web3 менеджер для подключения к QuickNode BSC
Описание: Управление подключениями, мониторинг API кредитов, retry логика
Зависимости: web3, requests, asyncio
Автор: GitHub Copilot
"""

import asyncio
import time
from typing import Optional, Dict, List, Any, Union
from decimal import Decimal
import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.providers import HTTPProvider, WebsocketProvider
import websockets

from config.settings import settings
from config.constants import (
    QUICKNODE_HTTP, QUICKNODE_WSS, QUICKNODE_API_KEY,
    RATE_LIMIT, API_CREDITS_MONTHLY, CREDITS_PER_GETLOGS, CREDITS_PER_CALL,
    SECONDS_PER_BLOCK
)
from utils.logger import get_logger
from utils.retry import api_call_retry, critical_operation_retry
from utils.validators import TransactionValidator, AddressValidator

logger = get_logger("Web3Manager")


class APIUsageTracker:
    """Трекер использования API кредитов QuickNode"""
    
    def __init__(self):
        self.credits_used = 0
        self.requests_count = 0
        self.start_time = time.time()
        self.last_request_time = 0
        self.requests_per_second = []
        
    def record_request(self, credits_used: int):
        """Записать использование API"""
        current_time = time.time()
        self.credits_used += credits_used
        self.requests_count += 1
        
        # Трекинг RPS
        self.requests_per_second.append(current_time)
        # Удаляем запросы старше 1 секунды
        self.requests_per_second = [
            t for t in self.requests_per_second 
            if current_time - t <= 1.0
        ]
        
        self.last_request_time = current_time
        
        logger.debug(f"📊 API Usage: +{credits_used} credits | Total: {self.credits_used} | RPS: {len(self.requests_per_second)}")
    
    def get_current_rps(self) -> int:
        """Получить текущий RPS"""
        current_time = time.time()
        self.requests_per_second = [
            t for t in self.requests_per_second 
            if current_time - t <= 1.0
        ]
        return len(self.requests_per_second)
    
    def should_wait_for_rate_limit(self) -> float:
        """Проверить, нужно ли ждать из-за rate limit"""
        current_rps = self.get_current_rps()
        if current_rps >= RATE_LIMIT:
            # Рассчитываем время ожидания
            return 1.0 - (time.time() - self.requests_per_second[0])
        return 0.0
    
    def get_usage_stats(self) -> Dict:
        """Получить статистику использования"""
        uptime = time.time() - self.start_time
        daily_credits_used = self.credits_used
        monthly_projection = daily_credits_used * 30 if uptime > 0 else 0
        
        return {
            "credits_used": self.credits_used,
            "requests_count": self.requests_count,
            "uptime_hours": uptime / 3600,
            "avg_credits_per_request": self.credits_used / max(1, self.requests_count),
            "current_rps": self.get_current_rps(),
            "monthly_projection": monthly_projection,
            "remaining_monthly_credits": API_CREDITS_MONTHLY - monthly_projection
        }


class BlockNumberCache:
    """Кэш номера блока с TTL для экономии 90% запросов"""
    
    def __init__(self, ttl_seconds: int = 60):
        self._cache = None
        self._timestamp = 0
        self.ttl = ttl_seconds
        
    def get_block_number(self, w3: Web3) -> int:
        """Получить номер блока из кэша или сети"""
        now = time.time()
        if self._cache and (now - self._timestamp) < self.ttl:
            logger.debug(f"📦 Block number from cache: {self._cache}")
            return self._cache
            
        # Получаем свежий номер блока
        self._cache = w3.eth.block_number
        self._timestamp = now
        logger.debug(f"🔄 Block number refreshed: {self._cache}")
        return self._cache
    
    def invalidate(self):
        """Инвалидировать кэш"""
        self._cache = None
        self._timestamp = 0


class Web3Manager:
    """Менеджер Web3 подключений к QuickNode BSC"""
    
    def __init__(self):
        self.http_provider = None
        self.ws_provider = None
        self.w3_http = None
        self.w3_ws = None
        self.api_usage = APIUsageTracker()
        self.block_cache = BlockNumberCache()
        self.connection_pool_size = 10
        self.is_connected = False
        
        # Инициализация подключений
        self._setup_http_connection()
        self._setup_websocket_connection()
        
    def _setup_http_connection(self):
        """Настройка HTTP подключения с connection pooling"""
        try:
            # Создаем HTTP провайдер с пулом подключений
            request_kwargs = {
                'timeout': settings.connection_timeout,
                'headers': {'User-Agent': 'PLEX-Dynamic-Staking-Manager/1.0'}
            }
            
            self.http_provider = HTTPProvider(
                QUICKNODE_HTTP,
                request_kwargs=request_kwargs
            )
            
            # Создаем Web3 инстанс
            self.w3_http = Web3(self.http_provider)
            
            # Добавляем middleware для BSC (Proof of Authority)
            self.w3_http.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Проверяем подключение
            latest_block = self.w3_http.eth.block_number
            logger.info(f"✅ HTTP connection established. Latest block: {latest_block}")
            self.is_connected = True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup HTTP connection: {e}")
            self.is_connected = False
            
    def _setup_websocket_connection(self):
        """Настройка WebSocket подключения"""
        try:
            self.ws_provider = WebsocketProvider(QUICKNODE_WSS)
            self.w3_ws = Web3(self.ws_provider)
            self.w3_ws.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Проверяем WebSocket подключение
            latest_block = self.w3_ws.eth.block_number
            logger.info(f"✅ WebSocket connection established. Latest block: {latest_block}")
            
        except Exception as e:
            logger.warning(f"⚠️ WebSocket connection failed: {e}")
            self.w3_ws = None
    
    @api_call_retry()
    def get_latest_block_number(self, use_cache: bool = True) -> int:
        """Получить номер последнего блока"""
        if use_cache:
            block_number = self.block_cache.get_block_number(self.w3_http)
        else:
            block_number = self.w3_http.eth.block_number
            
        self.api_usage.record_request(CREDITS_PER_CALL)
        return block_number
    
    @api_call_retry()
    def get_block(self, block_identifier: Union[int, str], full_transactions: bool = False) -> Dict:
        """Получить данные блока"""
        # Проверяем rate limit
        wait_time = self.api_usage.should_wait_for_rate_limit()
        if wait_time > 0:
            logger.debug(f"⏳ Rate limit wait: {wait_time:.2f}s")
            time.sleep(wait_time)
        
        block = self.w3_http.eth.get_block(block_identifier, full_transactions)
        self.api_usage.record_request(CREDITS_PER_CALL)
        
        return dict(block)
    
    @critical_operation_retry()
    def get_logs(self, filter_params: Dict) -> List[Dict]:
        """Получить логи с оптимизацией запросов"""
        # Проверяем rate limit
        wait_time = self.api_usage.should_wait_for_rate_limit()
        if wait_time > 0:
            logger.debug(f"⏳ Rate limit wait: {wait_time:.2f}s")
            time.sleep(wait_time)
        
        try:
            logs = self.w3_http.eth.get_logs(filter_params)
            self.api_usage.record_request(CREDITS_PER_GETLOGS)
            
            logger.debug(f"📊 Retrieved {len(logs)} logs for blocks {filter_params.get('fromBlock', '?')}-{filter_params.get('toBlock', '?')}")
            
            return [dict(log) for log in logs]
            
        except Exception as e:
            error_msg = str(e).lower()
            if "payload too large" in error_msg:
                logger.error(f"❌ Payload too large error - reduce block range")
                raise Exception("Payload too large - reduce block range")
            else:
                raise e
    
    @api_call_retry()
    def call_contract_function(self, contract_address: str, function_data: str, block: int = None) -> str:
        """Вызвать функцию контракта"""
        call_params = {
            'to': Web3.to_checksum_address(contract_address),
            'data': function_data
        }
        
        if block:
            block_identifier = block
        else:
            block_identifier = 'latest'
        
        result = self.w3_http.eth.call(call_params, block_identifier)
        self.api_usage.record_request(CREDITS_PER_CALL)
        
        return result.hex()
    
    @api_call_retry()
    def batch_call(self, calls: List[Dict]) -> List[str]:
        """Выполнить батч вызовов через обычные eth_call"""
        results = []
        
        for call in calls:
            try:
                result = self.call_contract_function(
                    call['to'],
                    call['data'],
                    call.get('block')
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"⚠️ Batch call failed: {e}")
                results.append("0x")
        
        return results
    
    def find_block_by_timestamp(self, target_timestamp: int, tolerance: int = 60) -> Optional[int]:
        """Оптимизированный поиск блока по timestamp"""
        logger.info(f"🔍 Finding block for timestamp {target_timestamp}")
        
        # Получаем текущий блок (1 запрос)
        current_block = self.get_latest_block_number()
        current_block_data = self.get_block(current_block)
        current_timestamp = current_block_data['timestamp']
        
        # Предсказываем примерный блок
        time_diff = current_timestamp - target_timestamp
        blocks_diff = int(time_diff / SECONDS_PER_BLOCK)
        estimated_block = max(1, current_block - blocks_diff)
        
        logger.debug(f"🎯 Estimated block: {estimated_block} (diff: {blocks_diff} blocks)")
        
        # Проверяем предсказание (1 запрос)
        check_block_data = self.get_block(estimated_block)
        
        # Если попали близко (±100 блоков), делаем линейный поиск
        if abs(check_block_data['timestamp'] - target_timestamp) < 300:  # ~5 минут
            return self._linear_search_block(estimated_block, target_timestamp)
        else:
            # Иначе бинарный поиск с уточненными границами
            return self._binary_search_block(estimated_block, target_timestamp, current_block)
    
    def _linear_search_block(self, start_block: int, target_timestamp: int) -> int:
        """Линейный поиск блока (для точной настройки)"""
        current_block = start_block
        
        for _ in range(200):  # Максимум 200 блоков
            block_data = self.get_block(current_block)
            block_timestamp = block_data['timestamp']
            
            if block_timestamp <= target_timestamp:
                return current_block
            
            current_block -= 1
            
        logger.warning(f"⚠️ Linear search limit reached")
        return current_block
    
    def _binary_search_block(self, estimated_block: int, target_timestamp: int, max_block: int) -> int:
        """Бинарный поиск блока"""
        left = 1
        right = max_block
        result = estimated_block
        
        while left <= right:
            mid = (left + right) // 2
            block_data = self.get_block(mid)
            block_timestamp = block_data['timestamp']
            
            if block_timestamp <= target_timestamp:
                result = mid
                left = mid + 1
            else:
                right = mid - 1
        
        logger.info(f"✅ Binary search found block: {result}")
        return result
    
    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Получить receipt транзакции"""
        try:
            validated_hash = TransactionValidator.validate_tx_hash(tx_hash)
            receipt = self.w3_http.eth.get_transaction_receipt(validated_hash)
            self.api_usage.record_request(CREDITS_PER_CALL)
            
            return dict(receipt)
            
        except Exception as e:
            logger.error(f"❌ Error getting transaction receipt {tx_hash}: {e}")
            return None
    
    def estimate_gas(self, transaction: Dict) -> int:
        """Оценить газ для транзакции"""
        try:
            gas_estimate = self.w3_http.eth.estimate_gas(transaction)
            self.api_usage.record_request(CREDITS_PER_CALL)
            
            return gas_estimate
            
        except Exception as e:
            logger.error(f"❌ Error estimating gas: {e}")
            return 21000  # Базовый газ для transfer
    
    def get_gas_price(self) -> int:
        """Получить текущую цену газа"""
        try:
            gas_price = self.w3_http.eth.gas_price
            self.api_usage.record_request(CREDITS_PER_CALL)
            
            return gas_price
            
        except Exception as e:
            logger.error(f"❌ Error getting gas price: {e}")
            return Web3.to_wei(7, 'gwei')  # Fallback для BSC
    
    def check_connection_health(self) -> Dict:
        """Проверить состояние подключения"""
        health = {
            "http_connected": False,
            "ws_connected": False,
            "latest_block": None,
            "node_syncing": None,
            "api_usage": self.api_usage.get_usage_stats()
        }
        
        try:
            # Проверяем HTTP
            if self.w3_http and self.w3_http.is_connected():
                health["http_connected"] = True
                health["latest_block"] = self.get_latest_block_number()
                health["node_syncing"] = self.w3_http.eth.syncing
            
            # Проверяем WebSocket
            if self.w3_ws and self.w3_ws.is_connected():
                health["ws_connected"] = True
            
        except Exception as e:
            logger.error(f"❌ Connection health check failed: {e}")
        
        return health
    
    def reconnect(self):
        """Переподключиться к нодам"""
        logger.info("🔄 Reconnecting to QuickNode...")
        
        try:
            # Переподключение HTTP
            self._setup_http_connection()
            
            # Переподключение WebSocket
            if self.w3_ws:
                self._setup_websocket_connection()
            
            # Инвалидируем кэши
            self.block_cache.invalidate()
            
            logger.info("✅ Reconnection completed")
            
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")
    
    def get_web3_instance(self, websocket: bool = False) -> Web3:
        """Получить Web3 инстанс"""
        if websocket and self.w3_ws:
            return self.w3_ws
        return self.w3_http
    
    def close_connections(self):
        """Закрыть все подключения"""
        try:
            if self.ws_provider:
                # WebSocket не имеет явного метода close в web3.py
                pass
            
            logger.info("🔌 All connections closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing connections: {e}")
    
    def close(self):
        """Закрыть соединения"""
        try:
            logger.info("🔌 Закрытие Web3 соединений...")
            if hasattr(self, 'web3_http') and self.web3_http:
                # HTTP соединения закрываются автоматически
                pass
            if hasattr(self, 'web3_ws') and self.web3_ws:
                # WebSocket соединения закрываются автоматически
                pass
            logger.info("✅ Web3 соединения закрыты")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия соединений: {e}")


# Глобальный экземпляр менеджера
web3_manager = Web3Manager()


def get_web3_manager() -> Web3Manager:
    """Получить глобальный экземпляр Web3Manager"""
    return web3_manager


if __name__ == "__main__":
    # Тестирование Web3Manager
    
    manager = Web3Manager()
    
    # Проверка подключения
    health = manager.check_connection_health()
    print(f"📊 Connection health: {health}")
    
    # Тест получения блока
    try:
        latest_block = manager.get_latest_block_number()
        print(f"📦 Latest block: {latest_block}")
        
        block_data = manager.get_block(latest_block)
        print(f"🕐 Block timestamp: {block_data['timestamp']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Тест поиска блока по времени
    try:
        # Ищем блок 1 час назад
        target_time = int(time.time()) - 3600
        found_block = manager.find_block_by_timestamp(target_time)
        print(f"🎯 Block 1 hour ago: {found_block}")
        
    except Exception as e:
        print(f"❌ Block search failed: {e}")
    
    # Статистика API
    stats = manager.api_usage.get_usage_stats()
    print(f"📈 API Usage: {stats}")
    
    print("✅ Web3Manager tested successfully")
