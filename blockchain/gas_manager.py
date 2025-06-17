"""
PLEX Dynamic Staking Manager - Gas Manager
Модуль для управления газом на BSC в различных режимах работы.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
import time
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from web3 import Web3
from web3.types import TxParams
from utils.logger import get_logger
from utils.retry import with_retry
from utils.validators import validate_address
from utils.converters import wei_to_token, token_to_wei

logger = get_logger(__name__)


class GasMode(Enum):
    """Режимы управления газом."""
    ADAPTIVE = "adaptive"      # Адаптивное управление на основе сети
    STANDARD = "standard"      # Стандартные значения
    BATCHING = "batching"      # Оптимизация для батчинга


@dataclass
class GasPrice:
    """Структура цены газа."""
    safe_gas_price: int       # Безопасная цена (gwei)
    standard_gas_price: int   # Стандартная цена (gwei)
    fast_gas_price: int       # Быстрая цена (gwei)
    base_fee: Optional[int] = None  # Базовая комиссия для EIP-1559


@dataclass
class GasEstimate:
    """Оценка газа для транзакции."""
    gas_limit: int
    gas_price: int
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    estimated_cost_wei: int = 0
    estimated_cost_bnb: Decimal = Decimal('0')


class GasManager:
    """
    Production-ready класс для управления газом на BSC.
    
    Функциональность:
    - Адаптивное управление ценами газа
    - Поддержка различных режимов оптимизации
    - Мониторинг состояния сети
    - Батчинг транзакций для экономии газа
    """
    
    def __init__(self, web3_manager, mode: GasMode = GasMode.ADAPTIVE):
        """
        Инициализация GasManager.
        
        Args:
            web3_manager: Экземпляр Web3Manager
            mode: Режим управления газом
        """
        self.w3_manager = web3_manager
        self.w3 = web3_manager.w3_http
        self.mode = mode
        
        # Кэш цен газа
        self.gas_price_cache: Optional[GasPrice] = None
        self.cache_timestamp = 0
        self.cache_ttl = 30  # секунд
        
        # Конфигурация по умолчанию для BSC
        self.default_config = {
            'safe_gas_price': 3_000_000_000,      # 3 gwei
            'standard_gas_price': 5_000_000_000,  # 5 gwei
            'fast_gas_price': 10_000_000_000,     # 10 gwei
            'max_gas_price': 50_000_000_000,      # 50 gwei - максимум для BSC
            'gas_limit_multiplier': 1.2,          # Множитель для gas limit
            'priority_fee': 1_000_000_000,        # 1 gwei для EIP-1559
        }
        
        # Лимиты газа для различных операций
        self.gas_limits = {
            'transfer': 21000,
            'erc20_transfer': 65000,
            'erc20_approve': 65000,
            'swap': 200000,
            'multicall': 300000,
            'complex_transaction': 500000
        }
        
        logger.info(f"✅ GasManager инициализирован в режиме: {mode.value}")
    
    @with_retry(max_attempts=3, delay=1.0)
    async def get_gas_price(self, refresh_cache: bool = False) -> GasPrice:
        """
        Получение актуальных цен газа с кэшированием.
        
        Args:
            refresh_cache: Принудительное обновление кэша
            
        Returns:
            GasPrice: Структура с ценами газа
        """
        # Проверка кэша
        if not refresh_cache and self._is_cache_valid():
            logger.debug("📋 Возврат цены газа из кэша")
            return self.gas_price_cache
        
        try:
            if self.mode == GasMode.ADAPTIVE:
                gas_price = await self._get_adaptive_gas_price()
            elif self.mode == GasMode.STANDARD:
                gas_price = self._get_standard_gas_price()
            elif self.mode == GasMode.BATCHING:
                gas_price = await self._get_batching_gas_price()
            else:
                gas_price = self._get_standard_gas_price()
              # Кэширование результата
            self.gas_price_cache = gas_price
            self.cache_timestamp = time.time()
            
            logger.debug(f"⛽ Цены газа обновлены: {gas_price}")
            return gas_price
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены газа: {e}")
            # Возврат дефолтных значений в случае ошибки
            return self._get_standard_gas_price()
    async def _get_adaptive_gas_price(self) -> GasPrice:
        """
        Адаптивное получение цены газа на основе состояния сети.
        
        Returns:
            GasPrice: Адаптивные цены газа
        """
        try:
            # Получение текущей цены газа из сети (синхронный вызов)
            current_gas_price = self.w3.eth.gas_price
            
            # Простые множители без сложной логики
            multipliers = {'safe': 0.9, 'standard': 1.0, 'fast': 1.2}
            
            # Безопасное приведение типов с проверками
            try:
                safe_price = max(
                    int(current_gas_price * multipliers['safe']),
                    self.default_config['safe_gas_price']
                )
                standard_price = max(
                    int(current_gas_price * multipliers['standard']),
                    self.default_config['standard_gas_price']
                )
                fast_price = max(
                    int(current_gas_price * multipliers['fast']),
                    self.default_config['fast_gas_price']
                )
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Ошибка в расчетах цен газа: {e}, используем значения по умолчанию")
                return self._get_standard_gas_price()
            
            # Ограничение максимальной ценой
            max_price = self.default_config['max_gas_price']
            safe_price = min(safe_price, max_price)
            standard_price = min(standard_price, max_price)
            fast_price = min(fast_price, max_price)
            
            logger.debug(f"🧠 Адаптивные цены: safe={safe_price}, standard={standard_price}, fast={fast_price}")
            
            return GasPrice(
                safe_gas_price=safe_price,
                standard_gas_price=standard_price,
                fast_gas_price=fast_price,
                base_fee=None
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка адаптивного расчета газа: {e}")
            logger.error(f"🔍 Тип ошибки: {type(e).__name__}")
            return self._get_standard_gas_price()
    
    async def _calculate_network_multipliers(self) -> Dict[str, float]:
        """
        Расчет множителей на основе состояния сети.
        
        Returns:
            Dict: Множители для различных скоростей
        """
        try:
            # Получение статистики последних блоков
            latest_block = await asyncio.to_thread(self.w3.eth.get_block, 'latest')
            current_block_number = latest_block.number
            
            # Анализ заполненности блоков за последние 10 блоков
            blocks_to_analyze = 10
            total_gas_used = 0
            total_gas_limit = 0
            
            for i in range(blocks_to_analyze):
                try:
                    block_number = current_block_number - i
                    block = await asyncio.to_thread(self.w3.eth.get_block, block_number)
                    total_gas_used += block.gasUsed
                    total_gas_limit += block.gasLimit
                except:
                    continue
            
            # Расчет загруженности сети
            if total_gas_limit > 0:
                network_utilization = total_gas_used / total_gas_limit
            else:
                network_utilization = 0.5  # По умолчанию
            
            # Определение множителей на основе загруженности
            if network_utilization > 0.9:
                # Высокая загруженность
                multipliers = {'safe': 0.8, 'standard': 1.2, 'fast': 2.0}
            elif network_utilization > 0.7:
                # Средняя загруженность
                multipliers = {'safe': 0.9, 'standard': 1.1, 'fast': 1.5}
            else:
                # Низкая загруженность
                multipliers = {'safe': 1.0, 'standard': 1.0, 'fast': 1.2}
            
            logger.debug(f"📊 Загруженность сети: {network_utilization:.2%}, множители: {multipliers}")
            return multipliers
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа сети: {e}")
            return {'safe': 1.0, 'standard': 1.0, 'fast': 1.2}
    
    def _get_standard_gas_price(self) -> GasPrice:
        """
        Получение стандартных цен газа для BSC.
        
        Returns:
            GasPrice: Стандартные цены газа
        """
        return GasPrice(
            safe_gas_price=self.default_config['safe_gas_price'],
            standard_gas_price=self.default_config['standard_gas_price'],
            fast_gas_price=self.default_config['fast_gas_price']
        )
    
    async def _get_batching_gas_price(self) -> GasPrice:
        """
        Оптимизированные цены газа для батчинга транзакций.
        
        Returns:
            GasPrice: Оптимизированные цены для батчинга
        """
        try:
            # Для батчинга используем более консервативные цены
            adaptive_prices = await self._get_adaptive_gas_price()
            
            # Снижение цен на 20% для батчинга (больше времени на обработку)
            batch_multiplier = 0.8
            
            return GasPrice(
                safe_gas_price=int(adaptive_prices.safe_gas_price * batch_multiplier),
                standard_gas_price=int(adaptive_prices.standard_gas_price * batch_multiplier),
                fast_gas_price=int(adaptive_prices.fast_gas_price * batch_multiplier),
                base_fee=adaptive_prices.base_fee
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета цен для батчинга: {e}")
            return self._get_standard_gas_price()
    
    @with_retry(max_attempts=3, delay=1.0)
    async def estimate_gas(
        self,
        transaction: Dict[str, Any],
        speed: str = 'standard'
    ) -> GasEstimate:
        """
        Оценка газа для транзакции.
        
        Args:
            transaction: Параметры транзакции
            speed: Скорость обработки ('safe', 'standard', 'fast')
            
        Returns:
            GasEstimate: Оценка газа и стоимости
        """
        try:
            # Получение актуальных цен газа
            gas_prices = await self.get_gas_price()
            
            # Выбор цены газа в зависимости от скорости
            if speed == 'safe':
                gas_price = gas_prices.safe_gas_price
            elif speed == 'fast':
                gas_price = gas_prices.fast_gas_price
            else:
                gas_price = gas_prices.standard_gas_price
            
            # Оценка лимита газа
            try:
                estimated_gas = await asyncio.to_thread(
                    self.w3.eth.estimate_gas, 
                    transaction
                )
                # Добавление буфера
                gas_limit = int(estimated_gas * self.default_config['gas_limit_multiplier'])
            except Exception as e:
                logger.warning(f"⚠️ Не удалось оценить газ, использую дефолтный: {e}")
                # Определение типа операции и использование дефолтного лимита
                if 'data' in transaction and transaction['data'] != '0x':
                    gas_limit = self.gas_limits['complex_transaction']
                else:
                    gas_limit = self.gas_limits['transfer']
            
            # Расчет стоимости
            estimated_cost_wei = gas_limit * gas_price
            estimated_cost_bnb = wei_to_token(estimated_cost_wei, 18)
            
            # Подготовка EIP-1559 параметров если поддерживается
            max_fee_per_gas = None
            max_priority_fee_per_gas = None
            
            if gas_prices.base_fee is not None:
                max_priority_fee_per_gas = self.default_config['priority_fee']
                max_fee_per_gas = gas_prices.base_fee * 2 + max_priority_fee_per_gas
            
            estimate = GasEstimate(
                gas_limit=gas_limit,
                gas_price=gas_price,
                max_fee_per_gas=max_fee_per_gas,
                max_priority_fee_per_gas=max_priority_fee_per_gas,
                estimated_cost_wei=estimated_cost_wei,
                estimated_cost_bnb=estimated_cost_bnb
            )
            
            logger.debug(f"⛽ Оценка газа: {estimate}")
            return estimate
            
        except Exception as e:
            logger.error(f"❌ Ошибка оценки газа: {e}")
            # Возврат дефолтной оценки
            return GasEstimate(
                gas_limit=self.gas_limits['transfer'],
                gas_price=self.default_config['standard_gas_price'],
                estimated_cost_wei=self.gas_limits['transfer'] * self.default_config['standard_gas_price'],
                estimated_cost_bnb=wei_to_token(
                    self.gas_limits['transfer'] * self.default_config['standard_gas_price'], 
                    18
                )
            )
    
    def prepare_transaction_params(
        self,
        base_transaction: Dict[str, Any],
        gas_estimate: GasEstimate
    ) -> Dict[str, Any]:
        """
        Подготовка параметров транзакции с правильным газом.
        
        Args:
            base_transaction: Базовые параметры транзакции
            gas_estimate: Оценка газа
            
        Returns:
            Dict: Готовые параметры транзакции
        """
        transaction = base_transaction.copy()
        
        # Установка лимита газа
        transaction['gas'] = gas_estimate.gas_limit
        
        # Установка цены газа
        if gas_estimate.max_fee_per_gas and gas_estimate.max_priority_fee_per_gas:
            # EIP-1559 параметры
            transaction['maxFeePerGas'] = gas_estimate.max_fee_per_gas
            transaction['maxPriorityFeePerGas'] = gas_estimate.max_priority_fee_per_gas
            # Удаляем gasPrice для EIP-1559
            transaction.pop('gasPrice', None)
        else:
            # Legacy параметры
            transaction['gasPrice'] = gas_estimate.gas_price
            # Удаляем EIP-1559 параметры
            transaction.pop('maxFeePerGas', None)
            transaction.pop('maxPriorityFeePerGas', None)
        
        logger.debug(f"📝 Подготовлены параметры транзакции: gas={gas_estimate.gas_limit}")
        return transaction
    
    async def optimize_batch_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Оптимизация батча транзакций для экономии газа.
        
        Args:
            transactions: Список транзакций для оптимизации
            
        Returns:
            List: Оптимизированные транзакции
        """
        if not transactions:
            return []
        
        try:
            optimized_transactions = []
            
            # Получение оптимизированных цен для батчинга
            old_mode = self.mode
            self.mode = GasMode.BATCHING
            
            for tx in transactions:
                try:
                    # Оценка газа для каждой транзакции
                    gas_estimate = await self.estimate_gas(tx, speed='safe')
                    
                    # Подготовка оптимизированных параметров
                    optimized_tx = self.prepare_transaction_params(tx, gas_estimate)
                    optimized_transactions.append(optimized_tx)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка оптимизации транзакции: {e}")
                    # Добавляем транзакцию как есть
                    optimized_transactions.append(tx)
            
            # Восстановление режима
            self.mode = old_mode
            
            logger.info(f"✅ Оптимизировано {len(optimized_transactions)} транзакций")
            return optimized_transactions
            
        except Exception as e:
            logger.error(f"❌ Ошибка оптимизации батча: {e}")
            return transactions
    
    def _is_cache_valid(self) -> bool:
        """
        Проверка валидности кэша цен газа.
        
        Returns:
            bool: True если кэш валидный
        """
        if self.gas_price_cache is None:
            return False
        
        cache_age = time.time() - self.cache_timestamp
        return cache_age < self.cache_ttl
    
    def clear_cache(self) -> None:
        """Очистка кэша цен газа."""
        self.gas_price_cache = None
        self.cache_timestamp = 0
        logger.info("🗑️ Кэш цен газа очищен")
    
    def set_mode(self, mode: GasMode) -> None:
        """
        Изменение режима управления газом.
        
        Args:
            mode: Новый режим управления газом
        """
        old_mode = self.mode
        self.mode = mode
        self.clear_cache()  # Очистка кэша при смене режима
        logger.info(f"🔄 Режим газа изменен с {old_mode.value} на {mode.value}")
    
    def get_gas_limit_for_operation(self, operation_type: str) -> int:
        """
        Получение лимита газа для типа операции.
        
        Args:
            operation_type: Тип операции
            
        Returns:
            int: Лимит газа
        """
        return self.gas_limits.get(operation_type, self.gas_limits['transfer'])
    
    async def get_network_stats(self) -> Dict[str, Any]:
        """
        Получение статистики сети для мониторинга.
        
        Returns:
            Dict: Статистика сети
        """
        try:
            current_gas_price = await asyncio.to_thread(self.w3.eth.gas_price)
            latest_block = await asyncio.to_thread(self.w3.eth.get_block, 'latest')
            
            # Расчет загруженности
            utilization = (latest_block.gasUsed / latest_block.gasLimit) * 100
            
            gas_prices = await self.get_gas_price()
            
            return {
                'current_block': latest_block.number,
                'current_gas_price_gwei': current_gas_price / 1e9,
                'network_utilization_percent': round(utilization, 2),
                'recommended_gas_prices': {
                    'safe_gwei': gas_prices.safe_gas_price / 1e9,
                    'standard_gwei': gas_prices.standard_gas_price / 1e9,
                    'fast_gwei': gas_prices.fast_gas_price / 1e9
                },
                'mode': self.mode.value,
                'cache_valid': self._is_cache_valid()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики сети: {e}")
            return {'error': str(e)}


# Экспорт для удобного импорта
__all__ = ['GasManager', 'GasMode', 'GasPrice', 'GasEstimate']


if __name__ == "__main__":
    # Тестовый запуск для проверки модуля
    from blockchain.node_client import Web3Manager
    
    async def test_gas_manager():
        """Тестирование GasManager с реальными данными BSC."""
        try:
            # Инициализация
            web3_manager = Web3Manager()
            await web3_manager.initialize()
            
            # Тестирование всех режимов
            for mode in GasMode:
                print(f"\n🧪 Тестирование режима: {mode.value}")
                
                gas_manager = GasManager(web3_manager, mode)
                
                # Получение цен газа
                gas_prices = await gas_manager.get_gas_price()
                print(f"⛽ Цены газа: safe={gas_prices.safe_gas_price/1e9:.1f} gwei, "
                      f"standard={gas_prices.standard_gas_price/1e9:.1f} gwei, "
                      f"fast={gas_prices.fast_gas_price/1e9:.1f} gwei")
                
                # Тестовая транзакция
                test_tx = {
                    'to': '0x1234567890123456789012345678901234567890',
                    'value': 0,
                    'data': '0x'
                }
                
                # Оценка газа
                estimate = await gas_manager.estimate_gas(test_tx)
                print(f"📊 Оценка газа: limit={estimate.gas_limit}, "
                      f"cost={estimate.estimated_cost_bnb:.6f} BNB")
                
                # Статистика сети
                network_stats = await gas_manager.get_network_stats()
                print(f"📈 Сеть: блок={network_stats.get('current_block', 'N/A')}, "
                      f"загруженность={network_stats.get('network_utilization_percent', 'N/A')}%")
            
            print("\n✅ Тестирование GasManager завершено успешно")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    # Запуск тестирования
    # asyncio.run(test_gas_manager())
    print("💡 Для тестирования раскомментируй последнюю строку")
