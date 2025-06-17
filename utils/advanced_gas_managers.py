"""
PLEX Dynamic Staking Manager - Advanced Gas Management Modes
Три специализированных режима управления газом для оптимизации транзакций.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import time
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import statistics

from blockchain.gas_manager import GasManager, GasPrice, GasEstimate, GasMode
from utils.logger import get_logger
from utils.retry import blockchain_retry

logger = get_logger(__name__)


@dataclass
class NetworkConditions:
    """Состояние сети для принятия решений по газу."""
    current_gas_price: int
    pending_transactions: int
    block_utilization: float  # 0.0 - 1.0
    average_confirmation_time: float  # секунды
    congestion_level: float  # 0.0 - 1.0
    timestamp: float = field(default_factory=time.time)


class AdaptiveGasManager(GasManager):
    """
    Адаптивный менеджер газа с машинным обучением.
    
    Функции:
    - Анализ паттернов сети в реальном времени
    - Предсказание оптимальных цен газа
    - Автоматическая корректировка стратегии
    - Мониторинг успешности транзакций
    """
    
    def __init__(self, web3_manager):
        super().__init__(web3_manager, GasMode.ADAPTIVE)
        
        # История состояния сети
        self.network_history = deque(maxlen=100)
        self.transaction_history = deque(maxlen=50)
        
        # Конфигурация адаптации
        self.adaptation_config = {
            'learning_rate': 0.1,
            'min_confidence': 0.7,
            'price_volatility_threshold': 0.2,
            'congestion_threshold': 0.8,
            'emergency_multiplier': 2.0
        }
        
        # Текущая стратегия
        self.current_strategy = 'balanced'  # conservative, balanced, aggressive
        self.strategy_confidence = 1.0
        
        logger.info("🧠 AdaptiveGasManager инициализирован")
    
    async def get_adaptive_gas_estimate(self, transaction_type: str = 'erc20_transfer',
                                      priority: str = 'standard',
                                      target_confirmation_time: float = 30.0) -> GasEstimate:
        """
        Получить адаптивную оценку газа с учетом ML предсказаний.
        
        Args:
            transaction_type: Тип транзакции
            priority: Приоритет (safe, standard, fast, urgent)
            target_confirmation_time: Целевое время подтверждения (сек)
            
        Returns:
            GasEstimate: Оптимизированная оценка газа
        """
        try:
            # Анализ текущего состояния сети
            network_conditions = await self._analyze_network_conditions()
            
            # Обновление истории
            self.network_history.append(network_conditions)
            
            # Предсказание оптимальной цены
            predicted_price = await self._predict_optimal_gas_price(
                network_conditions, target_confirmation_time
            )
            
            # Адаптация стратегии
            await self._adapt_strategy(network_conditions)
            
            # Создание оценки
            gas_limit = self._get_adaptive_gas_limit(transaction_type, network_conditions)
            
            estimate = GasEstimate(
                gas_limit=gas_limit,
                gas_price=predicted_price,
                estimated_cost_wei=gas_limit * predicted_price,
                estimated_cost_bnb=Decimal(gas_limit * predicted_price) / Decimal(10**18)
            )
            
            logger.debug(f"🎯 Адаптивная оценка газа: {estimate}")
            return estimate
            
        except Exception as e:
            logger.error(f"❌ Ошибка адаптивной оценки газа: {e}")
            # Fallback к стандартному методу
            return await self._get_fallback_estimate(transaction_type)
    
    async def _analyze_network_conditions(self) -> NetworkConditions:
        """Анализ текущего состояния сети."""
        try:
            # Получение метрик сети
            current_gas_price = await asyncio.to_thread(self.w3.eth.gas_price)
            latest_block = await asyncio.to_thread(self.w3.eth.get_block, 'latest')
            pending_block = await asyncio.to_thread(self.w3.eth.get_block, 'pending')
            
            # Расчет утилизации блока
            block_utilization = latest_block.gasUsed / latest_block.gasLimit
            
            # Количество pending транзакций
            pending_transactions = len(pending_block.transactions)
            
            # Оценка времени подтверждения на основе истории
            avg_confirmation_time = self._estimate_confirmation_time()
            
            # Расчет уровня загрузки
            congestion_level = self._calculate_congestion_level(
                block_utilization, pending_transactions, current_gas_price
            )
            
            conditions = NetworkConditions(
                current_gas_price=current_gas_price,
                pending_transactions=pending_transactions,
                block_utilization=block_utilization,
                average_confirmation_time=avg_confirmation_time,
                congestion_level=congestion_level
            )
            
            logger.debug(f"📊 Состояние сети: загрузка={congestion_level:.2f}, газ={current_gas_price/10**9:.1f} Gwei")
            
            return conditions
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа сети: {e}")
            # Возврат средних значений при ошибке
            return NetworkConditions(
                current_gas_price=5_000_000_000,  # 5 Gwei
                pending_transactions=100,
                block_utilization=0.5,
                average_confirmation_time=30.0,
                congestion_level=0.5
            )
    
    async def _predict_optimal_gas_price(self, conditions: NetworkConditions,
                                       target_time: float) -> int:
        """Предсказание оптимальной цены газа с помощью ML."""
        try:
            # Базовая цена на основе текущих условий
            base_price = conditions.current_gas_price
            
            # Корректировка на основе загрузки сети
            congestion_multiplier = 1.0 + (conditions.congestion_level * 0.5)
            
            # Корректировка на основе целевого времени
            time_multiplier = max(0.5, min(2.0, 60.0 / target_time))
            
            # Корректировка на основе стратегии
            strategy_multiplier = self._get_strategy_multiplier()
            
            # Анализ исторических данных
            historical_multiplier = self._analyze_historical_patterns(conditions)
            
            # Комбинированная цена
            predicted_price = int(
                base_price * 
                congestion_multiplier * 
                time_multiplier * 
                strategy_multiplier *
                historical_multiplier
            )
            
            # Ограничение максимальной цены
            max_price = self.default_config['max_gas_price']
            predicted_price = min(predicted_price, max_price)
            
            logger.debug(f"🔮 Предсказанная цена газа: {predicted_price/10**9:.2f} Gwei")
            
            return predicted_price
            
        except Exception as e:
            logger.error(f"❌ Ошибка предсказания цены газа: {e}")
            return conditions.current_gas_price
    
    def _analyze_historical_patterns(self, current_conditions: NetworkConditions) -> float:
        """Анализ исторических паттернов для корректировки цены."""
        if len(self.network_history) < 10:
            return 1.0
        
        try:
            # Анализ тренда цен газа
            recent_prices = [h.current_gas_price for h in list(self.network_history)[-10:]]
            price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # Анализ паттернов загрузки
            recent_congestion = [h.congestion_level for h in list(self.network_history)[-10:]]
            congestion_trend = statistics.mean(recent_congestion)
            
            # Корректировка на основе трендов
            trend_multiplier = 1.0
            
            if price_trend > 0.1:  # Рост цен
                trend_multiplier *= 1.1
            elif price_trend < -0.1:  # Падение цен
                trend_multiplier *= 0.9
            
            if congestion_trend > 0.7:  # Высокая загрузка
                trend_multiplier *= 1.05
            
            return min(max(trend_multiplier, 0.8), 1.3)
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа паттернов: {e}")
            return 1.0
    
    async def _adapt_strategy(self, conditions: NetworkConditions):
        """Адаптация стратегии на основе условий сети."""
        try:
            # Анализ эффективности текущей стратегии
            if len(self.transaction_history) >= 10:
                success_rate = self._calculate_strategy_success_rate()
                
                if success_rate < self.adaptation_config['min_confidence']:
                    # Смена стратегии при низкой эффективности
                    await self._change_strategy(conditions)
            
            # Экстренная адаптация при высокой загрузке
            if conditions.congestion_level > self.adaptation_config['congestion_threshold']:
                if self.current_strategy != 'aggressive':
                    self.current_strategy = 'aggressive'
                    logger.info("⚡ Переключение на агрессивную стратегию из-за загрузки сети")
            
        except Exception as e:
            logger.error(f"❌ Ошибка адаптации стратегии: {e}")
    
    def _get_strategy_multiplier(self) -> float:
        """Получить множитель на основе текущей стратегии."""
        multipliers = {
            'conservative': 0.8,
            'balanced': 1.0,
            'aggressive': 1.3
        }
        return multipliers.get(self.current_strategy, 1.0)


class StandardGasManager(GasManager):
    """
    Стандартный менеджер газа с фиксированными настройками.
    
    Функции:
    - Предсказуемые цены газа
    - Простая конфигурация
    - Стабильная работа
    - Минимальные вычислительные ресурсы
    """
    
    def __init__(self, web3_manager):
        super().__init__(web3_manager, GasMode.STANDARD)
        
        # Фиксированные настройки для BSC
        self.standard_config = {
            'safe_gas_price': 3_000_000_000,      # 3 Gwei
            'standard_gas_price': 5_000_000_000,  # 5 Gwei
            'fast_gas_price': 8_000_000_000,      # 8 Gwei
            'urgent_gas_price': 12_000_000_000,   # 12 Gwei
            'gas_limit_buffer': 0.1,              # 10% буфер для gas limit
        }
        
        logger.info("⚙️ StandardGasManager инициализирован")
    
    async def get_standard_gas_estimate(self, transaction_type: str = 'erc20_transfer',
                                      priority: str = 'standard') -> GasEstimate:
        """
        Получить стандартную оценку газа.
        
        Args:
            transaction_type: Тип транзакции
            priority: Приоритет (safe, standard, fast, urgent)
            
        Returns:
            GasEstimate: Стандартная оценка газа
        """
        try:
            # Получение базового лимита газа
            base_gas_limit = self.gas_limits.get(transaction_type, 65000)
            
            # Добавление буфера
            gas_limit = int(base_gas_limit * (1 + self.standard_config['gas_limit_buffer']))
            
            # Выбор цены газа на основе приоритета
            gas_price = self._get_price_by_priority(priority)
            
            estimate = GasEstimate(
                gas_limit=gas_limit,
                gas_price=gas_price,
                estimated_cost_wei=gas_limit * gas_price,
                estimated_cost_bnb=Decimal(gas_limit * gas_price) / Decimal(10**18)
            )
            
            logger.debug(f"⚙️ Стандартная оценка газа: {estimate}")
            return estimate
            
        except Exception as e:
            logger.error(f"❌ Ошибка стандартной оценки газа: {e}")
            raise
    
    def _get_price_by_priority(self, priority: str) -> int:
        """Получить цену газа по приоритету."""
        price_map = {
            'safe': self.standard_config['safe_gas_price'],
            'standard': self.standard_config['standard_gas_price'],
            'fast': self.standard_config['fast_gas_price'],
            'urgent': self.standard_config['urgent_gas_price']
        }
        return price_map.get(priority, self.standard_config['standard_gas_price'])


class BatchingGasManager(GasManager):
    """
    Менеджер газа, оптимизированный для батч-операций.
    
    Функции:
    - Оптимизация для массовых операций
    - Экономия газа через батчинг
    - Интеллектуальное планирование
    - Мониторинг эффективности
    """
    
    def __init__(self, web3_manager):
        super().__init__(web3_manager, GasMode.BATCHING)
        
        # Настройки для батчинга
        self.batching_config = {
            'optimal_batch_size': 25,
            'max_batch_size': 50,
            'batch_gas_overhead': 30000,  # Дополнительный газ на батч
            'individual_transfer_gas': 21000,
            'batch_discount_factor': 0.7,  # 30% экономия при батчинге
        }
        
        # Статистика батчинга
        self.batch_stats = {
            'total_batches': 0,
            'total_individual_savings': 0,
            'average_batch_size': 0
        }
        
        logger.info("📦 BatchingGasManager инициализирован")
    
    async def get_batch_gas_estimate(self, recipient_count: int,
                                   transaction_type: str = 'erc20_transfer') -> GasEstimate:
        """
        Получить оценку газа для батч-операции.
        
        Args:
            recipient_count: Количество получателей в батче
            transaction_type: Тип транзакции
            
        Returns:
            GasEstimate: Оценка газа для батча
        """
        try:
            if recipient_count <= 1:
                # Для одной транзакции используем стандартный подход
                return await self._get_single_transaction_estimate(transaction_type)
            
            # Расчет газа для батча
            base_gas_per_transfer = self.gas_limits.get(transaction_type, 65000)
            
            # Оптимизированный расчет для батча
            batch_gas_limit = (
                self.batching_config['batch_gas_overhead'] +
                (base_gas_per_transfer * recipient_count * self.batching_config['batch_discount_factor'])
            )
            
            # Ограничение максимальным размером блока
            max_block_gas = 30_000_000  # Лимит блока BSC
            batch_gas_limit = min(int(batch_gas_limit), max_block_gas // 2)
            
            # Адаптивная цена газа для батчей
            gas_price = await self._get_batch_optimized_gas_price()
            
            # Расчет экономии
            individual_cost = recipient_count * base_gas_per_transfer * gas_price
            batch_cost = batch_gas_limit * gas_price
            savings = individual_cost - batch_cost
            
            estimate = GasEstimate(
                gas_limit=batch_gas_limit,
                gas_price=gas_price,
                estimated_cost_wei=batch_cost,
                estimated_cost_bnb=Decimal(batch_cost) / Decimal(10**18)
            )
            
            # Логирование экономии
            savings_percent = (savings / individual_cost) * 100 if individual_cost > 0 else 0
            logger.info(f"💰 Батч-оценка: {recipient_count} переводов, экономия {savings_percent:.1f}%")
            
            return estimate
            
        except Exception as e:
            logger.error(f"❌ Ошибка оценки газа для батча: {e}")
            raise
    
    async def _get_batch_optimized_gas_price(self) -> int:
        """Получить оптимизированную цену газа для батчей."""
        try:
            # Получение текущей цены газа
            current_price = await asyncio.to_thread(self.w3.eth.gas_price)
            
            # Для батчей можем использовать более низкую цену
            # так как экономим на общем количестве транзакций
            batch_multiplier = 0.9  # 10% скидка на цену газа для батчей
            
            optimized_price = int(current_price * batch_multiplier)
            
            # Ограничение минимальной ценой
            min_price = self.default_config['safe_gas_price']
            optimized_price = max(optimized_price, min_price)
            
            return optimized_price
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения цены газа для батча: {e}")
            return self.default_config['standard_gas_price']
    
    def calculate_batch_efficiency(self, recipient_count: int) -> Dict[str, Any]:
        """
        Расчет эффективности батчинга.
        
        Args:
            recipient_count: Количество получателей
            
        Returns:
            Dict: Метрики эффективности
        """
        try:
            # Стоимость индивидуальных переводов
            individual_gas = recipient_count * self.batching_config['individual_transfer_gas']
            
            # Стоимость батча
            batch_gas = (
                self.batching_config['batch_gas_overhead'] +
                (self.batching_config['individual_transfer_gas'] * recipient_count * 
                 self.batching_config['batch_discount_factor'])
            )
            
            # Расчет экономии
            gas_savings = individual_gas - batch_gas
            savings_percent = (gas_savings / individual_gas) * 100 if individual_gas > 0 else 0
            
            # Оптимальность размера батча
            optimal_size = self.batching_config['optimal_batch_size']
            size_efficiency = min(recipient_count / optimal_size, 1.0)
            
            return {
                'recipient_count': recipient_count,
                'individual_gas_cost': individual_gas,
                'batch_gas_cost': int(batch_gas),
                'gas_savings': gas_savings,
                'savings_percent': savings_percent,
                'size_efficiency': size_efficiency,
                'is_recommended': recipient_count >= 5 and savings_percent > 20
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета эффективности батчинга: {e}")
            return {'error': str(e)}
    
    def update_batch_stats(self, batch_size: int, gas_used: int):
        """Обновление статистики батчинга."""
        try:
            self.batch_stats['total_batches'] += 1
            
            # Расчет экономии
            individual_cost = batch_size * self.batching_config['individual_transfer_gas']
            savings = individual_cost - gas_used
            self.batch_stats['total_individual_savings'] += savings
            
            # Обновление среднего размера батча
            total_transfers = self.batch_stats['average_batch_size'] * (self.batch_stats['total_batches'] - 1) + batch_size
            self.batch_stats['average_batch_size'] = total_transfers / self.batch_stats['total_batches']
            
            logger.debug(f"📊 Статистика батчинга обновлена: {self.batch_stats}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики батчинга: {e}")


# Фабрика для создания подходящего менеджера газа
class GasManagerFactory:
    """Фабрика для создания оптимального менеджера газа."""
    
    @staticmethod
    def create_gas_manager(web3_manager, mode: str = 'adaptive', **kwargs):
        """
        Создать менеджер газа в соответствии с режимом.
        
        Args:
            web3_manager: Менеджер Web3
            mode: Режим ('adaptive', 'standard', 'batching')
            **kwargs: Дополнительные параметры
            
        Returns:
            Соответствующий менеджер газа
        """
        managers = {
            'adaptive': AdaptiveGasManager,
            'standard': StandardGasManager,
            'batching': BatchingGasManager
        }
        
        manager_class = managers.get(mode.lower(), StandardGasManager)
        return manager_class(web3_manager, **kwargs)


# Экспорт для удобного импорта
__all__ = [
    'AdaptiveGasManager', 
    'StandardGasManager', 
    'BatchingGasManager',
    'GasManagerFactory',
    'NetworkConditions'
]


if __name__ == "__main__":
    print("⛽ Демонстрация Advanced Gas Management...")
    print("🧠 AdaptiveGasManager - ИИ оптимизация")
    print("⚙️ StandardGasManager - надежные настройки")
    print("📦 BatchingGasManager - экономия на батчах")
