"""
PLEX Dynamic Staking Manager - Staking Manager
Главный оркестратор системы динамического стейкинга PLEX ONE.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from utils.retry import with_retry
from utils.validators import validate_address
from utils.converters import wei_to_token, token_to_wei

# Импорт модулей системы
from blockchain.node_client import Web3Manager
from blockchain.swap_analyzer import SwapAnalyzer
from blockchain.transfer_collector import TransferCollector
from blockchain.balance_checker import BalanceChecker
from blockchain.gas_manager import GasManager, GasMode

from core.participant_analyzer_v2 import ParticipantAnalyzer
from core.category_analyzer import CategoryAnalyzer
from core.eligibility import EligibilityEngine
from core.reward_manager import RewardManager
from core.amnesty_manager import AmnestyManager
from core.duplicate_protection import DuplicateProtectionManager

from db.models import *
from db.history_manager import HistoryManager
from db.backup_manager import BackupManager

# Импорты только необходимых констант без GasMode 
from config.constants import (
    TOKEN_ADDRESS, TOKEN_DECIMALS, 
    QUICKNODE_HTTP, QUICKNODE_WSS,
    TRANSFER_EVENT_SIGNATURE, SWAP_EVENT_SIGNATURE,
    MIN_BALANCE, DAILY_PURCHASE_MIN, DAILY_PURCHASE_MAX,
    DEFAULT_GAS_PRICE_GWEI, MAX_GAS_PRICE_GWEI,
    MULTICALL_BATCH_SIZE, RETRY_ATTEMPTS, RETRY_DELAY_BASE,
    BLOCK_CACHE_TTL, BALANCE_CACHE_TTL,
    ParticipantCategory, AMNESTY_RULES, TIER_MULTIPLIERS
)

logger = get_logger(__name__)


class StakingStatus(Enum):
    """Статусы системы стейкинга."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class SystemStats:
    """Статистика системы стейкинга."""
    total_participants: int
    active_participants: int
    total_volume_usd: Decimal
    total_rewards_distributed: Decimal
    current_block: int
    last_update: datetime
    status: StakingStatus


@dataclass
class AnalysisResult:
    """Результат анализа стейкинга."""
    period_start: datetime
    period_end: datetime
    participants_analyzed: int
    rewards_calculated: Decimal
    categories_distribution: Dict[str, int]
    eligibility_stats: Dict[str, int]
    processing_time: float


class StakingManager:
    """
    Главный оркестратор системы динамического стейкинга PLEX ONE.
    
    Координирует работу всех модулей:
    - Анализ участников и транзакций
    - Расчет наград и категоризация
    - Управление данными и кэшем
    - Интеграция с блокчейном
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация StakingManager.
        
        Args:
            config: Дополнительная конфигурация системы
        """
        self.config = config or {}
        self.status = StakingStatus.INITIALIZING
        
        # Основные компоненты системы
        self.web3_manager: Optional[Web3Manager] = None
        self.swap_analyzer: Optional[SwapAnalyzer] = None
        self.transfer_collector: Optional[TransferCollector] = None
        self.balance_checker: Optional[BalanceChecker] = None
        self.gas_manager: Optional[GasManager] = None
        
        # Бизнес-логика
        self.participant_analyzer: Optional[ParticipantAnalyzer] = None
        self.category_analyzer: Optional[CategoryAnalyzer] = None
        self.eligibility_checker: Optional[EligibilityEngine] = None
        self.reward_manager: Optional[RewardManager] = None
        self.amnesty_manager: Optional[AmnestyManager] = None
        self.duplicate_protection: Optional[DuplicateProtectionManager] = None
        
        # Управление данными
        self.history_manager: Optional[HistoryManager] = None
        self.backup_manager: Optional[BackupManager] = None
        
        # Статистика и мониторинг
        self.stats = SystemStats(
            total_participants=0,
            active_participants=0,
            total_volume_usd=Decimal('0'),
            total_rewards_distributed=Decimal('0'),
            current_block=0,
            last_update=datetime.now(),
            status=StakingStatus.INITIALIZING
        )
        
        # Настройки по умолчанию
        self.default_settings = {
            'analysis_period_hours': 24,
            'min_volume_usd': 100,
            'auto_backup_enabled': True,
            'backup_interval_hours': 6,
            'gas_mode': GasMode.ADAPTIVE,
            'batch_size': 1000,
            'max_concurrent_requests': 10
        }
        
        # Трекинг background задач для корректного завершения
        self.background_tasks: Set[asyncio.Task] = set()
        
        logger.info("🚀 StakingManager инициализирован")
    
    async def initialize(self) -> bool:
        """
        Инициализация всех компонентов системы.
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            logger.info("🔧 Начинаем инициализацию системы...")
            
            # 1. Инициализация Web3 и блокчейн компонентов
            await self._initialize_blockchain_components()
            
            # 2. Инициализация бизнес-логики
            await self._initialize_business_components()
            
            # 3. Инициализация управления данными
            await self._initialize_data_components()
            
            # 4. Проверка работоспособности
            await self._perform_health_check()
            
            # 5. Обновление статистики
            await self._update_system_stats()
            
            self.status = StakingStatus.RUNNING
            logger.info("✅ Система успешно инициализирована")
            return True            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации системы: {e}")
            self.status = StakingStatus.ERROR
            return False
    
    async def _initialize_blockchain_components(self) -> None:
        """Инициализация блокчейн компонентов."""
        logger.info("🔗 Инициализация блокчейн компонентов...")
        
        # Web3 Manager
        self.web3_manager = Web3Manager()
        # Web3Manager инициализируется в конструкторе        # Gas Manager
        gas_mode_config = self.config.get('gas_mode', self.default_settings['gas_mode'])
        # Преобразуем в enum, если это строка
        if isinstance(gas_mode_config, str):
            # Ищем enum по значению
            gas_mode = None
            for mode in GasMode:
                if mode.value == gas_mode_config.lower():
                    gas_mode = mode
                    break
            if gas_mode is None:
                gas_mode = GasMode.ADAPTIVE  # По умолчанию
        else:
            gas_mode = gas_mode_config
        self.gas_manager = GasManager(self.web3_manager, gas_mode)
        
        # Swap Analyzer
        self.swap_analyzer = SwapAnalyzer(self.web3_manager)
        # Проверяем, есть ли метод initialize у SwapAnalyzer
        if hasattr(self.swap_analyzer, 'initialize'):
            await self.swap_analyzer.initialize()
        
        # Transfer Collector
        self.transfer_collector = TransferCollector(self.web3_manager)
        
        # Balance Checker
        self.balance_checker = BalanceChecker(self.web3_manager)
        
        logger.info("✅ Блокчейн компоненты инициализированы")
    
    async def _initialize_business_components(self) -> None:
        """Инициализация компонентов бизнес-логики."""
        logger.info("💼 Инициализация бизнес-логики...")
        
        # Participant Analyzer
        self.participant_analyzer = ParticipantAnalyzer()
        
        # Category Analyzer
        self.category_analyzer = CategoryAnalyzer()
        
        # Eligibility Checker
        self.eligibility_checker = EligibilityEngine()
        
        # Reward Manager
        self.reward_manager = RewardManager()
        
        # Amnesty Manager
        self.amnesty_manager = AmnestyManager()
        
        # Duplicate Protection
        self.duplicate_protection = DuplicateProtectionManager()
        
        logger.info("✅ Бизнес-логика инициализирована")
    
    async def _initialize_data_components(self) -> None:
        """Инициализация компонентов управления данными."""
        logger.info("💾 Инициализация управления данными...")
        
        # History Manager
        self.history_manager = HistoryManager()
        
        # Backup Manager
        self.backup_manager = BackupManager()
          # Автоматические резервные копии
        if self.config.get('auto_backup_enabled', self.default_settings['auto_backup_enabled']):
            backup_task = asyncio.create_task(self._auto_backup_task())
            self.background_tasks.add(backup_task)
            backup_task.add_done_callback(self.background_tasks.discard)
        
        logger.info("✅ Управление данными инициализировано")
    
    async def _perform_health_check(self) -> None:
        """Проверка работоспособности всех компонентов."""
        logger.info("🩺 Проверка работоспособности системы...")
        
        # Проверка подключения к блокчейну
        current_block = self.web3_manager.w3_http.eth.block_number
        if current_block == 0:
            raise RuntimeError("Нет подключения к блокчейну")
        
        # Проверка доступности контрактов
        plex_balance = await asyncio.to_thread(
            self.balance_checker.get_plex_balance,
            TOKEN_ADDRESS  # Проверяем баланс самого контракта
        )
        
        # Проверка газа
        gas_prices = await self.gas_manager.get_gas_price()
        if gas_prices.standard_gas_price == 0:
            raise RuntimeError("Не удалось получить цены газа")
        
        logger.info("✅ Проверка работоспособности пройдена")
    
    async def run_analysis(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        force_refresh: bool = False
    ) -> AnalysisResult:
        """
        Запуск полного анализа стейкинга за период.
        
        Args:
            period_start: Начало периода анализа
            period_end: Конец периода анализа
            force_refresh: Принудительное обновление данных
            
        Returns:
            AnalysisResult: Результаты анализа
        """
        start_time = time.time()
        
        try:
            logger.info("🔍 Запуск анализа стейкинга...")
            
            # Определение периода анализа
            if not period_end:
                period_end = datetime.now()
            if not period_start:
                period_hours = self.config.get('analysis_period_hours', self.default_settings['analysis_period_hours'])
                period_start = period_end - timedelta(hours=period_hours)
            
            logger.info(f"📅 Период анализа: {period_start} - {period_end}")
            
            # 1. Сбор данных о транзакциях
            logger.info("📊 Сбор данных о транзакциях...")
            swap_data = await self._collect_swap_data(period_start, period_end, force_refresh)
            transfer_data = await self._collect_transfer_data(period_start, period_end, force_refresh)
            
            # 2. Анализ участников
            logger.info("👥 Анализ участников...")
            participants = await self._analyze_participants(swap_data, transfer_data)
            
            # 3. Категоризация участников
            logger.info("🏷️ Категоризация участников...")
            categories = await self._categorize_participants(participants)
            
            # 4. Проверка права на награды
            logger.info("✅ Проверка права на награды...")
            eligibility_results = await self._check_eligibility(participants)
            
            # 5. Расчет наград
            logger.info("💰 Расчет наград...")
            rewards = await self._calculate_rewards(participants, eligibility_results)
            
            # 6. Сохранение результатов
            logger.info("💾 Сохранение результатов...")
            await self._save_analysis_results(participants, categories, rewards)
            
            # 7. Обновление статистики
            await self._update_system_stats()
            
            # Подготовка результата
            processing_time = time.time() - start_time
            result = AnalysisResult(
                period_start=period_start,
                period_end=period_end,
                participants_analyzed=len(participants),
                rewards_calculated=sum(reward.amount for reward in rewards),
                categories_distribution=self._get_category_distribution(categories),
                eligibility_stats=self._get_eligibility_stats(eligibility_results),
                processing_time=processing_time
            )
            
            logger.info(f"✅ Анализ завершен за {processing_time:.2f}с. "
                       f"Участников: {result.participants_analyzed}, "
                       f"Наград: {result.rewards_calculated}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа стейкинга: {e}")
            raise
    
    async def _collect_swap_data(
        self,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """Сбор данных о свапах за период."""
        try:
            # Конвертация дат в блоки
            start_block = await self.web3_manager.get_block_by_timestamp(
                int(start_date.timestamp())
            )
            end_block = await self.web3_manager.get_block_by_timestamp(
                int(end_date.timestamp())
            )
            
            # Сбор свапов
            swaps = await self.swap_analyzer.get_swaps(
                start_block=start_block,
                end_block=end_block,
                force_refresh=force_refresh
            )
            
            logger.info(f"📈 Собрано {len(swaps)} свапов за период")
            return swaps
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора данных о свапах: {e}")
            return []
    
    async def _collect_transfer_data(
        self,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """Сбор данных о трансферах за период."""
        try:
            # Конвертация дат в блоки
            start_block = await self.web3_manager.get_block_by_timestamp(
                int(start_date.timestamp())
            )
            end_block = await self.web3_manager.get_block_by_timestamp(
                int(end_date.timestamp())
            )
            
            # Сбор трансферов
            transfers = await self.transfer_collector.collect_transfers(
                start_block=start_block,
                end_block=end_block,
                batch_size=self.config.get('batch_size', self.default_settings['batch_size'])
            )
            
            logger.info(f"💸 Собрано {len(transfers)} трансферов за период")
            return transfers
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора данных о трансферах: {e}")
            return []
    
    async def _analyze_participants(
        self,
        swap_data: List[Dict[str, Any]],
        transfer_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Анализ участников на основе транзакций."""
        try:
            # Объединение данных
            all_transactions = swap_data + transfer_data
            
            # Анализ участников
            participants = await asyncio.to_thread(
                self.participant_analyzer.analyze_participants,
                all_transactions
            )
            
            # Получение текущих балансов
            addresses = [p['address'] for p in participants]
            if addresses:
                balances = self.balance_checker.get_multiple_balances(addresses)
                
                # Обновление данных участников
                for participant in participants:
                    address = participant['address']
                    if address in balances:
                        participant['current_balance'] = balances[address]
            
            return participants
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа участников: {e}")
            return []
    
    async def _categorize_participants(
        self,
        participants: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Категоризация участников."""
        try:
            categories = await asyncio.to_thread(
                self.category_analyzer.categorize_participants,
                participants
            )
            return categories
            
        except Exception as e:
            logger.error(f"❌ Ошибка категоризации: {e}")
            return []
    
    async def _check_eligibility(
        self,
        participants: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Проверка права на награды."""
        try:
            eligibility_results = []
            
            for participant in participants:
                is_eligible = await asyncio.to_thread(
                    self.eligibility_checker.check_eligibility,
                    participant
                )
                
                eligibility_results.append({
                    'address': participant['address'],
                    'is_eligible': is_eligible,
                    'participant_data': participant
                })
            
            return eligibility_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки права на награды: {e}")
            return []
    
    async def _calculate_rewards(
        self,
        participants: List[Dict[str, Any]],
        eligibility_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Расчет наград для участников."""
        try:
            # Фильтрация только подходящих участников
            eligible_participants = [
                result['participant_data'] 
                for result in eligibility_results 
                if result['is_eligible']
            ]
            
            if not eligible_participants:
                logger.warning("⚠️ Нет участников, подходящих для наград")
                return []
            
            # Расчет наград
            rewards = await asyncio.to_thread(
                self.reward_manager.calculate_rewards,
                eligible_participants
            )
            
            # Проверка на дубликаты
            if self.duplicate_protection:
                rewards = await asyncio.to_thread(
                    self.duplicate_protection.filter_duplicates,
                    rewards
                )
            
            return rewards
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета наград: {e}")
            return []
    
    async def _save_analysis_results(
        self,
        participants: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        rewards: List[Dict[str, Any]]
    ) -> None:
        """Сохранение результатов анализа в базу данных."""
        try:
            # Сохранение в истории
            if self.history_manager:
                await asyncio.to_thread(
                    self.history_manager.save_analysis_session,
                    {
                        'participants': participants,
                        'categories': categories,
                        'rewards': rewards,
                        'timestamp': datetime.now()
                    }
                )
            
            logger.info("💾 Результаты анализа сохранены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения результатов: {e}")
    
    def _get_category_distribution(self, categories: List[Dict[str, Any]]) -> Dict[str, int]:
        """Получение распределения по категориям."""
        distribution = {}
        for category in categories:
            cat_name = category.get('category', 'Unknown')
            distribution[cat_name] = distribution.get(cat_name, 0) + 1
        return distribution
    
    def _get_eligibility_stats(self, eligibility_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Получение статистики по праву на награды."""
        eligible = sum(1 for result in eligibility_results if result['is_eligible'])
        not_eligible = len(eligibility_results) - eligible
        
        return {
            'eligible': eligible,
            'not_eligible': not_eligible,
            'total': len(eligibility_results)
        }
    
    async def _update_system_stats(self) -> None:
        """Обновление системной статистики."""
        try:
            # Получение текущего блока
            current_block = self.web3_manager.w3_http.eth.block_number
            
            # Подсчет участников из базы данных
            # TODO: Реализовать запросы к БД для получения статистики
              # Обновление статистики
            self.stats.current_block = current_block
            self.stats.last_update = datetime.now()
            self.stats.status = self.status
            
            logger.debug(f"📊 Статистика обновлена: блок {current_block}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")
    
    async def _auto_backup_task(self) -> None:
        """Задача автоматического резервного копирования."""
        backup_interval = self.config.get('backup_interval_hours', self.default_settings['backup_interval_hours'])
        
        while self.status != StakingStatus.ERROR:
            try:
                await asyncio.sleep(backup_interval * 3600)  # Часы в секунды
                
                if self.backup_manager:
                    await asyncio.to_thread(self.backup_manager.create_backup)
                    logger.info("📦 Автоматическое резервное копирование выполнено")
                
            except Exception as e:
                logger.error(f"❌ Ошибка автоматического резервного копирования: {e}")
    
    async def pause(self) -> None:
        """Приостановка работы системы."""
        self.status = StakingStatus.PAUSED
        logger.info("⏸️ Система приостановлена")
    
    async def resume(self) -> None:
        """Возобновление работы системы."""
        self.status = StakingStatus.RUNNING
        logger.info("▶️ Система возобновлена")
    
    async def shutdown(self) -> None:
        """Корректное завершение работы системы."""
        try:
            logger.info("🛑 Завершение работы системы...")
            
            self.status = StakingStatus.MAINTENANCE
            
            # Завершение всех background задач
            if self.background_tasks:
                logger.info(f"⏹️ Завершение {len(self.background_tasks)} background задач...")
                for task in self.background_tasks:
                    if not task.done():
                        task.cancel()
                
                # Ждём завершения всех задач с таймаутом
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.background_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                    logger.info("✅ Все background задачи завершены")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Некоторые задачи не завершились в срок")
            
            # Создание финального бэкапа
            if self.backup_manager:
                await asyncio.to_thread(self.backup_manager.create_backup)
            
            # Закрытие соединений
            if self.web3_manager:
                await self.web3_manager.close()
            
            logger.info("✅ Система корректно завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка завершения системы: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса системы.
        
        Returns:
            Dict: Подробная информация о статусе
        """
        return {
            'status': self.status.value,
            'stats': {
                'total_participants': self.stats.total_participants,
                'active_participants': self.stats.active_participants,
                'total_volume_usd': float(self.stats.total_volume_usd),
                'total_rewards_distributed': float(self.stats.total_rewards_distributed),
                'current_block': self.stats.current_block,
                'last_update': self.stats.last_update.isoformat()
            },
            'components': {
                'web3_manager': self.web3_manager is not None,
                'swap_analyzer': self.swap_analyzer is not None,
                'transfer_collector': self.transfer_collector is not None,
                'balance_checker': self.balance_checker is not None,
                'gas_manager': self.gas_manager is not None,
                'participant_analyzer': self.participant_analyzer is not None,
                'category_analyzer': self.category_analyzer is not None,
                'eligibility_checker': self.eligibility_checker is not None,
                'reward_manager': self.reward_manager is not None
            }
        }


# Экспорт для удобного импорта
__all__ = ['StakingManager', 'StakingStatus', 'SystemStats', 'AnalysisResult']


if __name__ == "__main__":
    # Тестовый запуск для проверки модуля
    async def test_staking_manager():
        """Тестирование StakingManager."""
        try:
            print("🧪 Тестирование StakingManager...")
            
            # Создание и инициализация
            staking_manager = StakingManager({
                'analysis_period_hours': 1,  # Короткий период для тестирования
                'gas_mode': GasMode.STANDARD
            })
            
            # Инициализация
            success = await staking_manager.initialize()
            if not success:
                print("❌ Ошибка инициализации")
                return
            
            # Получение статуса
            status = staking_manager.get_status()
            print(f"📊 Статус системы: {status}")
            
            # Тестовый анализ (с короткими периодами)
            from datetime import datetime, timedelta
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=30)  # Последние 30 минут
            
            print(f"🔍 Запуск тестового анализа...")
            result = await staking_manager.run_analysis(start_time, end_time)
            
            print(f"✅ Анализ завершен:")
            print(f"  - Участников: {result.participants_analyzed}")
            print(f"  - Наград: {result.rewards_calculated}")
            print(f"  - Время: {result.processing_time:.2f}с")
            
            # Завершение
            await staking_manager.shutdown()
            print("✅ Тестирование StakingManager завершено успешно")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    # Запуск тестирования
    # asyncio.run(test_staking_manager())
    print("💡 Для тестирования раскомментируй последнюю строку")
