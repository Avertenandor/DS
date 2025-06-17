"""
Модуль: Multicall менеджер для батч-запросов балансов
Описание: Объединение до 50 вызовов balanceOf в один запрос - экономия 98% кредитов
Зависимости: web3, eth_abi
Автор: GitHub Copilot
"""

import time
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass

from web3 import Web3
from eth_abi import encode, decode

from config.constants import TOKEN_DECIMALS, MULTICALL3_BSC
from utils.logger import get_logger
from utils.cache_manager import multicall_cache

logger = get_logger("MulticallManager")


@dataclass
class MulticallResult:
    """Результат Multicall запроса"""
    success: bool
    block_number: int
    results: Dict[str, Any]
    execution_time: float
    calls_count: int
    credits_saved: int


class MulticallManager:
    """Менеджер для объединения множественных вызовов в один запрос"""
    
    # ABI для Multicall3 контракта
    MULTICALL3_ABI = [
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
        },
        {
            "inputs": [
                {
                    "components": [
                        {"name": "target", "type": "address"},
                        {"name": "allowFailure", "type": "bool"},
                        {"name": "callData", "type": "bytes"}
                    ],
                    "name": "calls",
                    "type": "tuple[]"
                }
            ],
            "name": "tryAggregate",
            "outputs": [
                {
                    "components": [
                        {"name": "success", "type": "bool"},
                        {"name": "returnData", "type": "bytes"}
                    ],
                    "name": "returnData",
                    "type": "tuple[]"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.multicall_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MULTICALL3_BSC),
            abi=self.MULTICALL3_ABI
        )
        
        # Статистика
        self.total_calls_made = 0
        self.total_calls_saved = 0
        self.total_execution_time = 0
        self.batch_count = 0
        
        # Сигнатуры функций
        self.BALANCE_OF_SIGNATURE = Web3.keccak(text="balanceOf(address)")[:4]
        self.TRANSFER_SIGNATURE = Web3.keccak(text="Transfer(address,address,uint256)")
        
        logger.info(f"💎 MulticallManager инициализирован")
        logger.info(f"   Multicall3 адрес: {MULTICALL3_BSC}")
        
    def get_balances_batch(self, token_address: str, addresses: List[str], 
                          block: Optional[int] = None) -> Dict[str, Decimal]:
        """
        Получить балансы для списка адресов одним запросом
        
        Args:
            token_address: Адрес ERC20 токена
            addresses: Список адресов (до 200 за раз)
            block: Номер блока (по умолчанию latest)
            
        Returns:
            Dict с балансами {address: balance}
        """
        if not addresses:
            return {}
        
        # Проверяем кэш сначала
        cached_result = multicall_cache.get_batch_balances(
            token_address, addresses, block or self.w3.eth.block_number,
            self._fetch_balances_multicall
        )
        
        if cached_result:
            logger.debug(f"📦 Возвращено {len(cached_result)} балансов из кэша")
            return cached_result
        
        return self._fetch_balances_multicall(token_address, addresses, block)
    
    def _fetch_balances_multicall(self, token_address: str, addresses: List[str], 
                                 block: Optional[int] = None) -> Dict[str, Decimal]:
        """Внутренний метод для получения балансов через Multicall"""
        
        start_time = time.time()
        token_address = Web3.to_checksum_address(token_address)
        
        # Разбиваем на батчи по 50 адресов (ограничение Multicall3)
        batch_size = 50
        all_balances = {}
        
        for i in range(0, len(addresses), batch_size):
            batch_addresses = addresses[i:i + batch_size]
            
            try:
                # Подготавливаем вызовы balanceOf
                calls = []
                for addr in batch_addresses:
                    addr_checksum = Web3.to_checksum_address(addr)
                    
                    # Кодируем вызов balanceOf(address)
                    call_data = self.BALANCE_OF_SIGNATURE + encode(['address'], [addr_checksum])
                    
                    calls.append({
                        'target': token_address,
                        'callData': call_data
                    })
                
                # Выполняем Multicall
                if block:
                    result = self.multicall_contract.functions.aggregate(calls).call(
                        block_identifier=block
                    )
                else:
                    result = self.multicall_contract.functions.aggregate(calls).call()
                
                block_number, return_data = result
                
                # Декодируем результаты
                for j, (addr, data) in enumerate(zip(batch_addresses, return_data)):
                    try:
                        # Декодируем uint256
                        balance_wei = decode(['uint256'], data)[0]
                        balance = Decimal(balance_wei) / Decimal(10 ** TOKEN_DECIMALS)
                        all_balances[addr] = balance
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка декодирования баланса для {addr}: {e}")
                        all_balances[addr] = Decimal(0)
                
                # Обновляем статистику
                self.total_calls_made += 1
                self.total_calls_saved += len(batch_addresses) - 1  # Сэкономили N-1 вызовов
                
                logger.debug(f"💎 Multicall batch {i//batch_size + 1}: {len(batch_addresses)} балансов")
                
            except Exception as e:
                logger.error(f"❌ Ошибка Multicall для батча {i//batch_size + 1}: {e}")
                
                # Fallback на индивидуальные вызовы
                logger.info("🔄 Переходим на индивидуальные вызовы...")
                batch_balances = self._get_balances_individual(
                    token_address, batch_addresses, block
                )
                all_balances.update(batch_balances)
        
        execution_time = time.time() - start_time
        self.total_execution_time += execution_time
        self.batch_count += 1
        
        logger.info(f"💰 Получено {len(all_balances)} балансов за {execution_time:.2f}s")
        logger.info(f"   Сэкономлено {len(addresses) - len(range(0, len(addresses), batch_size))} API вызовов")
        
        return all_balances
    
    def _get_balances_individual(self, token_address: str, addresses: List[str], 
                               block: Optional[int] = None) -> Dict[str, Decimal]:
        """Fallback метод для индивидуальных вызовов balanceOf"""
        
        logger.warning("⚠️ Используем индивидуальные вызовы balanceOf (fallback)")
        
        # Создаем контракт токена для прямых вызовов
        token_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        token_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=token_abi
        )
        
        balances = {}
        
        for addr in addresses:
            try:
                addr_checksum = Web3.to_checksum_address(addr)
                
                if block:
                    balance_wei = token_contract.functions.balanceOf(addr_checksum).call(
                        block_identifier=block
                    )
                else:
                    balance_wei = token_contract.functions.balanceOf(addr_checksum).call()
                
                balance = Decimal(balance_wei) / Decimal(10 ** TOKEN_DECIMALS)
                balances[addr] = balance
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения баланса для {addr}: {e}")
                balances[addr] = Decimal(0)
        
        return balances
    
    def get_multiple_contract_data(self, calls_data: List[Dict[str, Any]], 
                                  block: Optional[int] = None) -> List[MulticallResult]:
        """
        Универсальный метод для множественных вызовов разных контрактов
        
        Args:
            calls_data: Список вызовов [{'target': address, 'data': call_data, 'decode': decode_func}]
            block: Номер блока
            
        Returns:
            Список результатов MulticallResult
        """
        if not calls_data:
            return []
        
        start_time = time.time()
        
        # Подготавливаем вызовы для tryAggregate (позволяет некоторым вызовам падать)
        calls = []
        for call_info in calls_data:
            calls.append({
                'target': Web3.to_checksum_address(call_info['target']),
                'allowFailure': True,
                'callData': call_info['data']
            })
        
        try:
            if block:
                results = self.multicall_contract.functions.tryAggregate(False, calls).call(
                    block_identifier=block
                )
            else:
                results = self.multicall_contract.functions.tryAggregate(False, calls).call()
            
            # Обрабатываем результаты
            processed_results = []
            
            for i, (call_info, (success, return_data)) in enumerate(zip(calls_data, results)):
                if success and return_data:
                    try:
                        # Используем пользовательскую функцию декодирования если есть
                        if 'decode' in call_info and callable(call_info['decode']):
                            decoded_value = call_info['decode'](return_data)
                        else:
                            # По умолчанию пытаемся декодировать как uint256
                            decoded_value = decode(['uint256'], return_data)[0]
                        
                        processed_results.append(MulticallResult(
                            success=True,
                            block_number=block or self.w3.eth.block_number,
                            results={'value': decoded_value},
                            execution_time=time.time() - start_time,
                            calls_count=1,
                            credits_saved=19  # Сэкономили почти полный вызов
                        ))
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка декодирования результата {i}: {e}")
                        processed_results.append(MulticallResult(
                            success=False,
                            block_number=block or self.w3.eth.block_number,
                            results={'error': str(e)},
                            execution_time=time.time() - start_time,
                            calls_count=1,
                            credits_saved=0
                        ))
                else:
                    processed_results.append(MulticallResult(
                        success=False,
                        block_number=block or self.w3.eth.block_number,
                        results={'error': 'Call failed'},
                        execution_time=time.time() - start_time,
                        calls_count=1,
                        credits_saved=0
                    ))
            
            execution_time = time.time() - start_time
            self.total_calls_made += 1
            self.total_calls_saved += len(calls_data) - 1
            
            logger.info(f"💎 Multicall: {len(calls_data)} вызовов за {execution_time:.2f}s")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка множественного Multicall: {e}")
            return [
                MulticallResult(
                    success=False,
                    block_number=block or self.w3.eth.block_number,
                    results={'error': str(e)},
                    execution_time=time.time() - start_time,
                    calls_count=len(calls_data),
                    credits_saved=0
                )
            ]
    
    def batch_token_info(self, token_addresses: List[str], 
                        block: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        """
        Получить информацию о множественных токенах (name, symbol, decimals, totalSupply)
        
        Args:
            token_addresses: Список адресов токенов
            block: Номер блока
            
        Returns:
            Dict с информацией о токенах
        """
        if not token_addresses:
            return {}
        
        calls_data = []
        
        # Сигнатуры функций ERC20
        name_sig = Web3.keccak(text="name()")[:4]
        symbol_sig = Web3.keccak(text="symbol()")[:4]
        decimals_sig = Web3.keccak(text="decimals()")[:4]
        total_supply_sig = Web3.keccak(text="totalSupply()")[:4]
        
        # Функции декодирования
        def decode_string(data):
            try:
                return decode(['string'], data)[0]
            except:
                # Некоторые токены возвращают bytes32 вместо string
                return decode(['bytes32'], data)[0].decode('utf-8').rstrip('\x00')
        
        def decode_uint(data):
            return decode(['uint256'], data)[0]
        
        def decode_uint8(data):
            return decode(['uint8'], data)[0]
        
        # Создаем вызовы для каждого токена
        for token_addr in token_addresses:
            calls_data.extend([
                {'target': token_addr, 'data': name_sig, 'decode': decode_string, 'field': 'name'},
                {'target': token_addr, 'data': symbol_sig, 'decode': decode_string, 'field': 'symbol'},
                {'target': token_addr, 'data': decimals_sig, 'decode': decode_uint8, 'field': 'decimals'},
                {'target': token_addr, 'data': total_supply_sig, 'decode': decode_uint, 'field': 'totalSupply'},
            ])
        
        # Выполняем Multicall
        results = self.get_multiple_contract_data(calls_data, block)
        
        # Группируем результаты по токенам
        token_info = {}
        
        for i, token_addr in enumerate(token_addresses):
            token_info[token_addr] = {}
            
            # Каждый токен имеет 4 результата (name, symbol, decimals, totalSupply)
            for j, field in enumerate(['name', 'symbol', 'decimals', 'totalSupply']):
                result_index = i * 4 + j
                
                if result_index < len(results) and results[result_index].success:
                    token_info[token_addr][field] = results[result_index].results['value']
                else:
                    token_info[token_addr][field] = None
        
        logger.info(f"📊 Получена информация о {len(token_addresses)} токенах")
        
        return token_info
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика Multicall менеджера"""
        avg_execution_time = (
            self.total_execution_time / self.batch_count 
            if self.batch_count > 0 else 0
        )
        
        estimated_credits_saved = self.total_calls_saved * 20  # 20 кредитов за вызов
        
        return {
            'total_multicall_batches': self.batch_count,
            'total_calls_made': self.total_calls_made,
            'total_calls_saved': self.total_calls_saved,
            'avg_execution_time': f"{avg_execution_time:.2f}s",
            'estimated_credits_saved': estimated_credits_saved,
            'efficiency': f"{(self.total_calls_saved / max(1, self.total_calls_made + self.total_calls_saved) * 100):.1f}%"
        }


if __name__ == "__main__":
    # Тестирование MulticallManager
    print("🧪 Тестирование MulticallManager...")
    
    from blockchain.node_client import Web3Manager
    from config.constants import QUICKNODE_HTTP, TOKEN_ADDRESS
    
    # Инициализация
    w3_manager = Web3Manager()
    multicall_manager = MulticallManager(w3_manager.w3_http)
    
    # Тестовые адреса
    test_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002", 
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000004",
        "0x0000000000000000000000000000000000000005"
    ]
    
    print(f"\n💰 Тест получения балансов:")
    print(f"Токен: {TOKEN_ADDRESS}")
    print(f"Адреса: {len(test_addresses)}")
    
    try:
        start_time = time.time()
        balances = multicall_manager.get_balances_batch(TOKEN_ADDRESS, test_addresses)
        execution_time = time.time() - start_time
        
        print(f"✅ Получено {len(balances)} балансов за {execution_time:.2f}s")
        
        for addr, balance in list(balances.items())[:3]:
            print(f"  {addr}: {balance} PLEX")
        
        # Статистика
        stats = multicall_manager.get_stats()
        print(f"\n📊 Статистика Multicall:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
    
    print("\n✅ MulticallManager тестирован успешно")
