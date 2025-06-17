"""
PLEX Dynamic Staking Manager - Balance Checker
Модуль для проверки балансов токенов на BSC через QuickNode API.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
from web3 import Web3
from web3.contract import Contract
from utils.logger import get_logger
from utils.retry import with_retry
from utils.validators import validate_address
from utils.converters import wei_to_token, token_to_wei
from config.constants import (
    TOKEN_ADDRESS, TOKEN_DECIMALS, USDT_BSC,
    MULTICALL3_BSC, RATE_LIMIT
)

logger = get_logger(__name__)


class BalanceChecker:
    """
    Production-ready класс для проверки балансов токенов на BSC.
    
    Функциональность:
    - Проверка балансов PLEX ONE и USDT
    - Поддержка Multicall для батчинга запросов
    - Кэширование результатов
    - Валидация адресов и автоматические retry
    """
    
    def __init__(self, web3_manager):
        """
        Инициализация BalanceChecker.
        
        Args:
            web3_manager: Экземпляр Web3Manager для подключения к BSC
        """
        self.w3_manager = web3_manager
        self.w3 = web3_manager.w3_http
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 30  # секунд
        
        # Инициализация контрактов
        self._init_contracts()
        
    def _init_contracts(self) -> None:
        """Инициализация контрактов ERC20 и Multicall3."""
        try:
            # ERC20 ABI для токенов
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "symbol",
                    "outputs": [{"name": "", "type": "string"}],
                    "type": "function"
                }
            ]
            
            # Multicall3 ABI (упрощенная версия)
            multicall3_abi = [
                {
                    "inputs": [
                        {
                            "components": [
                                {"name": "target", "type": "address"},
                                {"name": "callData", "type": "bytes"}
                            ],
                            "name": "calls",
                            "type": "tuple[]"
                        }
                    ],
                    "name": "aggregate",
                    "outputs": [
                        {"name": "blockNumber", "type": "uint256"},
                        {"name": "returnData", "type": "bytes[]"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # Создание контрактов
            self.plex_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(TOKEN_ADDRESS),
                abi=erc20_abi
            )
            
            self.usdt_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDT_BSC),
                abi=erc20_abi
            )
            
            self.multicall_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(MULTICALL3_BSC),
                abi=multicall3_abi
            )
            
            logger.info("✅ Контракты BalanceChecker инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации контрактов: {e}")
            raise
    
    @with_retry(max_attempts=3, delay=1.0)
    def get_plex_balance(self, address: str) -> Decimal:
        """
        Получение баланса PLEX ONE для адреса.
        
        Args:
            address: Адрес кошелька
            
        Returns:
            Decimal: Баланс PLEX ONE (с учетом decimals)
            
        Raises:
            ValueError: Если адрес невалидный
        """
        if not validate_address(address):
            raise ValueError(f"Невалидный адрес: {address}")
        
        try:
            # Проверка кэша
            cache_key = f"plex_{address}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"📋 Возврат PLEX баланса из кэша для {address[:10]}...")
                return self.cache[cache_key]['balance']
            
            # Получение баланса
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.plex_contract.functions.balanceOf(checksum_address).call()
            balance_tokens = wei_to_token(balance_wei, TOKEN_DECIMALS)
            
            # Кэширование результата
            self._cache_balance(cache_key, balance_tokens)
            
            logger.debug(f"💰 PLEX баланс для {address[:10]}...: {balance_tokens}")
            return balance_tokens
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения PLEX баланса для {address}: {e}")
            raise
    
    @with_retry(max_attempts=3, delay=1.0)
    def get_usdt_balance(self, address: str) -> Decimal:
        """
        Получение баланса USDT для адреса.
        
        Args:
            address: Адрес кошелька
            
        Returns:
            Decimal: Баланс USDT (с учетом decimals)
        """
        if not validate_address(address):
            raise ValueError(f"Невалидный адрес: {address}")
        
        try:
            # Проверка кэша
            cache_key = f"usdt_{address}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"📋 Возврат USDT баланса из кэша для {address[:10]}...")
                return self.cache[cache_key]['balance']
            
            # Получение баланса
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.usdt_contract.functions.balanceOf(checksum_address).call()
            balance_tokens = wei_to_token(balance_wei, 18)  # USDT has 18 decimals on BSC
            
            # Кэширование результата
            self._cache_balance(cache_key, balance_tokens)
            
            logger.debug(f"💵 USDT баланс для {address[:10]}...: {balance_tokens}")
            return balance_tokens
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения USDT баланса для {address}: {e}")
            raise
    
    @with_retry(max_attempts=3, delay=1.0)
    def get_bnb_balance(self, address: str) -> Decimal:
        """
        Получение баланса BNB для адреса.
        
        Args:
            address: Адрес кошелька
            
        Returns:
            Decimal: Баланс BNB в эфирах
        """
        if not validate_address(address):
            raise ValueError(f"Невалидный адрес: {address}")
        
        try:
            # Проверка кэша
            cache_key = f"bnb_{address}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"📋 Возврат BNB баланса из кэша для {address[:10]}...")
                return self.cache[cache_key]['balance']
            
            # Получение баланса
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(checksum_address)
            balance_bnb = wei_to_token(balance_wei, 18)  # BNB has 18 decimals
            
            # Кэширование результата
            self._cache_balance(cache_key, balance_bnb)
            
            logger.debug(f"🟡 BNB баланс для {address[:10]}...: {balance_bnb}")
            return balance_bnb
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения BNB баланса для {address}: {e}")
            raise
    
    def get_multiple_balances(self, addresses: List[str]) -> Dict[str, Dict[str, Decimal]]:
        """
        Получение балансов нескольких токенов для списка адресов с использованием Multicall.
        
        Args:
            addresses: Список адресов кошельков
            
        Returns:
            Dict: {address: {'plex': balance, 'usdt': balance, 'bnb': balance}}
        """
        if not addresses:
            return {}
        
        # Валидация адресов
        valid_addresses = []
        for addr in addresses:
            if validate_address(addr):
                valid_addresses.append(Web3.to_checksum_address(addr))
            else:
                logger.warning(f"⚠️ Пропуск невалидного адреса: {addr}")
        
        if not valid_addresses:
            logger.warning("⚠️ Нет валидных адресов для проверки балансов")
            return {}
        
        try:
            results = {}
            
            # Батчи по 50 адресов для оптимизации
            batch_size = 50
            for i in range(0, len(valid_addresses), batch_size):
                batch_addresses = valid_addresses[i:i+batch_size]
                batch_results = self._get_batch_balances(batch_addresses)
                results.update(batch_results)
            
            logger.info(f"✅ Получены балансы для {len(results)} адресов")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения множественных балансов: {e}")
            # Fallback к индивидуальным запросам
            return self._get_balances_individually(valid_addresses)
    
    def _get_batch_balances(self, addresses: List[str]) -> Dict[str, Dict[str, Decimal]]:
        """
        Получение балансов для батча адресов через Multicall.
        
        Args:
            addresses: Список валидных checksum адресов
            
        Returns:
            Dict: Результаты балансов для батча
        """
        try:
            # Подготовка calls для Multicall
            calls = []
            
            # Для каждого адреса добавляем вызовы balanceOf для PLEX и USDT
            for address in addresses:
                # PLEX balanceOf call
                plex_call_data = self.plex_contract.encodeABI(
                    fn_name='balanceOf',
                    args=[address]
                )
                calls.append((TOKEN_ADDRESS, plex_call_data))
                
                # USDT balanceOf call
                usdt_call_data = self.usdt_contract.encodeABI(
                    fn_name='balanceOf',
                    args=[address]
                )
                calls.append((USDT_BSC, usdt_call_data))
            
            # Выполнение Multicall
            block_number, return_data = self.multicall_contract.functions.aggregate(calls).call()
            
            # Парсинг результатов
            results = {}
            for i, address in enumerate(addresses):
                plex_idx = i * 2
                usdt_idx = i * 2 + 1
                
                # Декодирование PLEX баланса
                plex_balance_wei = int.from_bytes(return_data[plex_idx], byteorder='big')
                plex_balance = wei_to_token(plex_balance_wei, TOKEN_DECIMALS)
                
                # Декодирование USDT баланса
                usdt_balance_wei = int.from_bytes(return_data[usdt_idx], byteorder='big')
                usdt_balance = wei_to_token(usdt_balance_wei, 18)
                
                # BNB баланс нужно получать отдельно
                bnb_balance = self.get_bnb_balance(address)
                
                results[address] = {
                    'plex': plex_balance,
                    'usdt': usdt_balance,
                    'bnb': bnb_balance
                }
                
                # Кэширование результатов
                self._cache_balance(f"plex_{address}", plex_balance)
                self._cache_balance(f"usdt_{address}", usdt_balance)
                self._cache_balance(f"bnb_{address}", bnb_balance)
            
            logger.debug(f"📦 Multicall: получены балансы для {len(addresses)} адресов")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка Multicall батча: {e}")
            # Fallback к индивидуальным запросам
            return self._get_balances_individually(addresses)
    
    def _get_balances_individually(self, addresses: List[str]) -> Dict[str, Dict[str, Decimal]]:
        """
        Fallback: получение балансов индивидуальными запросами.
        
        Args:
            addresses: Список адресов
            
        Returns:
            Dict: Результаты балансов
        """
        results = {}
        
        for address in addresses:
            try:
                results[address] = {
                    'plex': self.get_plex_balance(address),
                    'usdt': self.get_usdt_balance(address),
                    'bnb': self.get_bnb_balance(address)
                }
            except Exception as e:
                logger.error(f"❌ Ошибка получения баланса для {address}: {e}")
                results[address] = {
                    'plex': Decimal('0'),
                    'usdt': Decimal('0'),
                    'bnb': Decimal('0')
                }
        
        return results
    
    def _cache_balance(self, cache_key: str, balance: Decimal) -> None:
        """
        Кэширование баланса с TTL.
        
        Args:
            cache_key: Ключ кэша
            balance: Баланс для кэширования
        """
        import time
        self.cache[cache_key] = {
            'balance': balance,
            'timestamp': time.time()
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Проверка валидности кэша.
        
        Args:
            cache_key: Ключ кэша
            
        Returns:
            bool: True если кэш валидный
        """
        if cache_key not in self.cache:
            return False
        
        import time
        cache_age = time.time() - self.cache[cache_key]['timestamp']
        return cache_age < self.cache_ttl
    
    def clear_cache(self) -> None:
        """Очистка кэша балансов."""
        self.cache.clear()
        logger.info("🗑️ Кэш балансов очищен")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Получение статистики кэша.
        
        Returns:
            Dict: Статистика кэша
        """
        import time
        current_time = time.time()
        
        total_entries = len(self.cache)
        valid_entries = sum(
            1 for entry in self.cache.values()
            if current_time - entry['timestamp'] < self.cache_ttl
        )
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries
        }


# Экспорт для удобного импорта
__all__ = ['BalanceChecker']


if __name__ == "__main__":
    # Тестовый запуск для проверки модуля
    from blockchain.node_client import Web3Manager
    
    async def test_balance_checker():
        """Тестирование BalanceChecker с реальными данными BSC."""
        try:
            # Инициализация
            web3_manager = Web3Manager()
            await web3_manager.initialize()
            
            balance_checker = BalanceChecker(web3_manager)
            
            # Тестовый адрес (известный холдер PLEX)
            test_address = "0x1234567890123456789012345678901234567890"  # Замени на реальный
            
            print(f"🧪 Тестирование BalanceChecker для {test_address[:10]}...")
            
            # Тест индивидуальных балансов
            plex_balance = balance_checker.get_plex_balance(test_address)
            usdt_balance = balance_checker.get_usdt_balance(test_address)
            bnb_balance = balance_checker.get_bnb_balance(test_address)
            
            print(f"💰 PLEX: {plex_balance}")
            print(f"💵 USDT: {usdt_balance}")
            print(f"🟡 BNB: {bnb_balance}")
            
            # Тест множественных балансов
            test_addresses = [test_address]  # Добавь больше адресов
            batch_results = balance_checker.get_multiple_balances(test_addresses)
            
            print(f"📦 Батч результаты: {batch_results}")
            
            # Статистика кэша
            cache_stats = balance_checker.get_cache_stats()
            print(f"📊 Кэш статистика: {cache_stats}")
            
            print("✅ Тестирование BalanceChecker завершено успешно")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    # Запуск тестирования
    # asyncio.run(test_balance_checker())
    print("💡 Для тестирования раскомментируй последнюю строку")
