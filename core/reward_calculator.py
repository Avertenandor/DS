"""
PLEX Dynamic Staking Manager - Reward Calculator
Специализированный модуль для расчета наград участников стейкинга.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import math
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from utils.converters import wei_to_token, token_to_wei
from config.constants import TOKEN_DECIMALS, TOKEN_TOTAL_SUPPLY

logger = get_logger(__name__)


class RewardTier(Enum):
    """Уровни наград."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


@dataclass
class RewardFormula:
    """Формула расчета наград."""
    base_rate: Decimal           # Базовая ставка (%)
    volume_multiplier: Decimal   # Множитель объема
    holding_bonus: Decimal       # Бонус за холдинг (%)
    loyalty_bonus: Decimal       # Бонус за лояльность (%)
    tier_multiplier: Decimal     # Множитель уровня


@dataclass
class RewardCalculation:
    """Результат расчета награды."""
    address: str
    base_reward: Decimal
    volume_bonus: Decimal
    holding_bonus: Decimal
    loyalty_bonus: Decimal
    tier_bonus: Decimal
    total_reward: Decimal
    tier: RewardTier
    calculation_details: Dict[str, Any]


class RewardCalculator:
    """
    Production-ready калькулятор наград для динамического стейкинга PLEX ONE.
    
    Функциональность:
    - Многоуровневая система расчета наград
    - Учет объема торговли, холдинга и лояльности
    - Адаптивные коэффициенты на основе активности
    - Защита от инфляции и переплат
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация RewardCalculator.
        
        Args:
            config: Конфигурация калькулятора
        """
        self.config = config or {}
        
        # Формулы наград по уровням
        self.reward_formulas = {
            RewardTier.BRONZE: RewardFormula(
                base_rate=Decimal('0.1'),      # 0.1% от объема
                volume_multiplier=Decimal('1.0'),
                holding_bonus=Decimal('0.05'),  # +5% за холдинг
                loyalty_bonus=Decimal('0.02'),  # +2% за лояльность
                tier_multiplier=Decimal('1.0')
            ),
            RewardTier.SILVER: RewardFormula(
                base_rate=Decimal('0.15'),     # 0.15% от объема
                volume_multiplier=Decimal('1.1'),
                holding_bonus=Decimal('0.08'),
                loyalty_bonus=Decimal('0.04'),
                tier_multiplier=Decimal('1.2')
            ),
            RewardTier.GOLD: RewardFormula(
                base_rate=Decimal('0.2'),      # 0.2% от объема
                volume_multiplier=Decimal('1.2'),
                holding_bonus=Decimal('0.12'),
                loyalty_bonus=Decimal('0.06'),
                tier_multiplier=Decimal('1.5')
            ),
            RewardTier.PLATINUM: RewardFormula(
                base_rate=Decimal('0.25'),     # 0.25% от объема
                volume_multiplier=Decimal('1.3'),
                holding_bonus=Decimal('0.15'),
                loyalty_bonus=Decimal('0.08'),
                tier_multiplier=Decimal('1.8')
            ),
            RewardTier.DIAMOND: RewardFormula(
                base_rate=Decimal('0.3'),      # 0.3% от объема
                volume_multiplier=Decimal('1.5'),
                holding_bonus=Decimal('0.2'),
                loyalty_bonus=Decimal('0.1'),
                tier_multiplier=Decimal('2.0')
            )
        }
        
        # Пороги для уровней (в USDT)
        self.tier_thresholds = {
            RewardTier.BRONZE: Decimal('100'),      # $100+
            RewardTier.SILVER: Decimal('1000'),     # $1,000+
            RewardTier.GOLD: Decimal('5000'),       # $5,000+
            RewardTier.PLATINUM: Decimal('25000'),  # $25,000+
            RewardTier.DIAMOND: Decimal('100000')   # $100,000+
        }
        
        # Лимиты и ограничения
        self.limits = {
            'max_reward_per_user': Decimal('10000'),     # Максимум 10,000 PLEX на пользователя
            'max_total_distribution': Decimal('50000'),   # Максимум 50,000 PLEX за период
            'min_reward_threshold': Decimal('1'),         # Минимум 1 PLEX
            'inflation_protection_rate': Decimal('0.95') # Защита от инфляции
        }
        
        # Состояние калькулятора
        self.total_distributed = Decimal('0')
        self.calculation_history: List[RewardCalculation] = []
        
        logger.info("💰 RewardCalculator инициализирован")
    
    def calculate_participant_reward(
        self,
        participant: Dict[str, Any],
        period_stats: Optional[Dict[str, Any]] = None
    ) -> RewardCalculation:
        """
        Расчет награды для конкретного участника.
        
        Args:
            participant: Данные участника
            period_stats: Статистика периода для нормализации
            
        Returns:
            RewardCalculation: Результат расчета
        """
        try:
            address = participant['address']
            
            # 1. Определение уровня участника
            tier = self._determine_tier(participant)
            formula = self.reward_formulas[tier]
            
            # 2. Расчет базовой награды
            base_reward = self._calculate_base_reward(participant, formula)
            
            # 3. Расчет бонусов
            volume_bonus = self._calculate_volume_bonus(participant, formula, period_stats)
            holding_bonus = self._calculate_holding_bonus(participant, formula)
            loyalty_bonus = self._calculate_loyalty_bonus(participant, formula)
            tier_bonus = self._calculate_tier_bonus(participant, formula)
            
            # 4. Итоговый расчет
            total_reward = (
                base_reward + 
                volume_bonus + 
                holding_bonus + 
                loyalty_bonus + 
                tier_bonus
            )
            
            # 5. Применение лимитов и защиты
            total_reward = self._apply_limits_and_protection(total_reward, participant)
            
            # 6. Подготовка результата
            calculation = RewardCalculation(
                address=address,
                base_reward=base_reward,
                volume_bonus=volume_bonus,
                holding_bonus=holding_bonus,
                loyalty_bonus=loyalty_bonus,
                tier_bonus=tier_bonus,
                total_reward=total_reward,
                tier=tier,
                calculation_details=self._get_calculation_details(participant, formula)
            )
            
            # 7. Сохранение в истории
            self.calculation_history.append(calculation)
            self.total_distributed += total_reward
            
            logger.debug(f"💰 Награда для {address[:10]}...: {total_reward} PLEX ({tier.value})")
            return calculation
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета награды для {participant.get('address', 'Unknown')}: {e}")
            # Возврат нулевой награды в случае ошибки
            return RewardCalculation(
                address=participant.get('address', ''),
                base_reward=Decimal('0'),
                volume_bonus=Decimal('0'),
                holding_bonus=Decimal('0'),
                loyalty_bonus=Decimal('0'),
                tier_bonus=Decimal('0'),
                total_reward=Decimal('0'),
                tier=RewardTier.BRONZE,
                calculation_details={'error': str(e)}
            )
    
    def _determine_tier(self, participant: Dict[str, Any]) -> RewardTier:
        """
        Определение уровня участника на основе объема торговли.
        
        Args:
            participant: Данные участника
            
        Returns:
            RewardTier: Уровень участника
        """
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        
        # Определение уровня от высшего к низшему
        for tier in [RewardTier.DIAMOND, RewardTier.PLATINUM, RewardTier.GOLD, 
                     RewardTier.SILVER, RewardTier.BRONZE]:
            if volume_usd >= self.tier_thresholds[tier]:
                return tier
        
        return RewardTier.BRONZE  # По умолчанию
    
    def _calculate_base_reward(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula
    ) -> Decimal:
        """
        Расчет базовой награды на основе объема торговли.
        
        Args:
            participant: Данные участника
            formula: Формула расчета
            
        Returns:
            Decimal: Базовая награда в PLEX
        """
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        
        # Базовая награда = объем * базовая ставка
        base_reward = volume_usd * (formula.base_rate / 100)
        
        return base_reward.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
    
    def _calculate_volume_bonus(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula,
        period_stats: Optional[Dict[str, Any]]
    ) -> Decimal:
        """
        Расчет бонуса за объем торговли относительно других участников.
        
        Args:
            participant: Данные участника
            formula: Формула расчета
            period_stats: Статистика периода
            
        Returns:
            Decimal: Бонус за объем
        """
        if not period_stats:
            return Decimal('0')
        
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        avg_volume = period_stats.get('average_volume_usd', Decimal('1'))
        
        # Бонус за превышение среднего объема
        if volume_usd > avg_volume:
            volume_ratio = min(volume_usd / avg_volume, Decimal('3'))  # Максимум 3x
            volume_bonus = volume_usd * (formula.base_rate / 100) * (volume_ratio - 1) * formula.volume_multiplier
            return volume_bonus.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
        
        return Decimal('0')
    
    def _calculate_holding_bonus(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula
    ) -> Decimal:
        """
        Расчет бонуса за холдинг токенов.
        
        Args:
            participant: Данные участника
            formula: Формула расчета
            
        Returns:
            Decimal: Бонус за холдинг
        """
        current_balance = participant.get('current_balance', {}).get('plex', Decimal('0'))
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        
        # Бонус зависит от соотношения баланса к объему торговли
        if current_balance > 0 and volume_usd > 0:
            # Предположим среднюю цену PLEX = $0.001 для расчета
            estimated_plex_price = Decimal('0.001')
            balance_usd = current_balance * estimated_plex_price
            
            # Холдинг-соотношение (баланс к объему торговли)
            holding_ratio = min(balance_usd / volume_usd, Decimal('1'))  # Максимум 1
            
            base_reward = volume_usd * (formula.base_rate / 100)
            holding_bonus = base_reward * formula.holding_bonus * holding_ratio
            
            return holding_bonus.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
        
        return Decimal('0')
    
    def _calculate_loyalty_bonus(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula
    ) -> Decimal:
        """
        Расчет бонуса за лояльность (длительность участия).
        
        Args:
            participant: Данные участника
            formula: Формула расчета
            
        Returns:
            Decimal: Бонус за лояльность
        """
        first_transaction = participant.get('first_transaction_date')
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        
        if first_transaction and volume_usd > 0:
            # Расчет дней участия
            if isinstance(first_transaction, str):
                first_transaction = datetime.fromisoformat(first_transaction.replace('Z', '+00:00'))
            
            days_active = (datetime.now(first_transaction.tzinfo) - first_transaction).days
            
            # Бонус за каждые 30 дней (максимум 6 месяцев)
            loyalty_multiplier = min(days_active / 30, 6) * Decimal('0.1')  # 10% за месяц, максимум 60%
            
            base_reward = volume_usd * (formula.base_rate / 100)
            loyalty_bonus = base_reward * formula.loyalty_bonus * loyalty_multiplier
            
            return loyalty_bonus.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
        
        return Decimal('0')
    
    def _calculate_tier_bonus(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula
    ) -> Decimal:
        """
        Расчет бонуса за уровень участника.
        
        Args:
            participant: Данные участника
            formula: Формула расчета
            
        Returns:
            Decimal: Бонус за уровень
        """
        volume_usd = participant.get('total_volume_usd', Decimal('0'))
        
        if volume_usd > 0:
            base_reward = volume_usd * (formula.base_rate / 100)
            tier_bonus = base_reward * (formula.tier_multiplier - 1)  # Дополнительный множитель
            
            return tier_bonus.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
        
        return Decimal('0')
    
    def _apply_limits_and_protection(
        self,
        reward: Decimal,
        participant: Dict[str, Any]
    ) -> Decimal:
        """
        Применение лимитов и защиты от инфляции.
        
        Args:
            reward: Рассчитанная награда
            participant: Данные участника
            
        Returns:
            Decimal: Скорректированная награда
        """
        # 1. Минимальный порог
        if reward < self.limits['min_reward_threshold']:
            return Decimal('0')
        
        # 2. Максимум на пользователя
        reward = min(reward, self.limits['max_reward_per_user'])
        
        # 3. Проверка общего лимита распределения
        if self.total_distributed + reward > self.limits['max_total_distribution']:
            remaining = self.limits['max_total_distribution'] - self.total_distributed
            reward = max(remaining, Decimal('0'))
        
        # 4. Защита от инфляции
        reward = reward * self.limits['inflation_protection_rate']
        
        return reward.quantize(Decimal('0.000000001'), rounding=ROUND_DOWN)
    
    def _get_calculation_details(
        self,
        participant: Dict[str, Any],
        formula: RewardFormula
    ) -> Dict[str, Any]:
        """
        Получение детальной информации о расчете.
        
        Args:
            participant: Данные участника
            formula: Использованная формула
            
        Returns:
            Dict: Детали расчета
        """
        return {
            'participant_address': participant.get('address'),
            'volume_usd': float(participant.get('total_volume_usd', 0)),
            'current_balance_plex': float(participant.get('current_balance', {}).get('plex', 0)),
            'formula_used': {
                'base_rate': float(formula.base_rate),
                'volume_multiplier': float(formula.volume_multiplier),
                'holding_bonus': float(formula.holding_bonus),
                'loyalty_bonus': float(formula.loyalty_bonus),
                'tier_multiplier': float(formula.tier_multiplier)
            },
            'calculation_timestamp': datetime.now().isoformat(),
            'total_distributed_so_far': float(self.total_distributed)
        }
    
    def calculate_batch_rewards(
        self,
        participants: List[Dict[str, Any]],
        normalize_by_period: bool = True
    ) -> List[RewardCalculation]:
        """
        Расчет наград для группы участников с нормализацией.
        
        Args:
            participants: Список участников
            normalize_by_period: Использовать нормализацию по периоду
            
        Returns:
            List[RewardCalculation]: Результаты расчетов
        """
        if not participants:
            return []
        
        try:
            # Расчет статистики периода для нормализации
            period_stats = None
            if normalize_by_period:
                period_stats = self._calculate_period_stats(participants)
            
            # Расчет наград для каждого участника
            calculations = []
            for participant in participants:
                calculation = self.calculate_participant_reward(participant, period_stats)
                calculations.append(calculation)
            
            # Сортировка по размеру награды (от большей к меньшей)
            calculations.sort(key=lambda x: x.total_reward, reverse=True)
            
            logger.info(f"💰 Рассчитаны награды для {len(calculations)} участников. "
                       f"Общая сумма: {sum(c.total_reward for c in calculations)} PLEX")
            
            return calculations
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета наград для группы: {e}")
            return []
    
    def _calculate_period_stats(self, participants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Расчет статистики периода для нормализации наград.
        
        Args:
            participants: Список участников
            
        Returns:
            Dict: Статистика периода
        """
        if not participants:
            return {}
        
        volumes = [p.get('total_volume_usd', Decimal('0')) for p in participants]
        volumes = [v for v in volumes if v > 0]  # Только положительные объемы
        
        if not volumes:
            return {}
        
        total_volume = sum(volumes)
        avg_volume = total_volume / len(volumes)
        median_volume = sorted(volumes)[len(volumes) // 2]
        max_volume = max(volumes)
        min_volume = min(volumes)
        
        return {
            'total_participants': len(participants),
            'active_participants': len(volumes),
            'total_volume_usd': total_volume,
            'average_volume_usd': avg_volume,
            'median_volume_usd': median_volume,
            'max_volume_usd': max_volume,
            'min_volume_usd': min_volume,
            'volume_std_dev': self._calculate_std_dev(volumes, avg_volume)
        }
    
    def _calculate_std_dev(self, values: List[Decimal], mean: Decimal) -> Decimal:
        """Расчет стандартного отклонения."""
        if len(values) < 2:
            return Decimal('0')
        
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance.sqrt()
    
    def get_tier_distribution(self) -> Dict[str, int]:
        """
        Получение распределения участников по уровням.
        
        Returns:
            Dict: Количество участников по уровням
        """
        distribution = {tier.value: 0 for tier in RewardTier}
        
        for calculation in self.calculation_history:
            distribution[calculation.tier.value] += 1
        
        return distribution
    
    def get_total_distributed(self) -> Decimal:
        """
        Получение общей суммы распределенных наград.
        
        Returns:
            Decimal: Общая сумма в PLEX
        """
        return self.total_distributed
    
    def reset_calculator(self) -> None:
        """Сброс состояния калькулятора."""
        self.total_distributed = Decimal('0')
        self.calculation_history.clear()
        logger.info("🔄 Калькулятор наград сброшен")
    
    def get_calculator_stats(self) -> Dict[str, Any]:
        """
        Получение статистики калькулятора.
        
        Returns:
            Dict: Статистика работы калькулятора
        """
        if not self.calculation_history:
            return {
                'total_calculations': 0,
                'total_distributed': 0,
                'tier_distribution': {},
                'avg_reward': 0,
                'max_reward': 0,
                'min_reward': 0
            }
        
        rewards = [c.total_reward for c in self.calculation_history if c.total_reward > 0]
        
        return {
            'total_calculations': len(self.calculation_history),
            'successful_calculations': len(rewards),
            'total_distributed': float(self.total_distributed),
            'tier_distribution': self.get_tier_distribution(),
            'avg_reward': float(sum(rewards) / len(rewards)) if rewards else 0,
            'max_reward': float(max(rewards)) if rewards else 0,
            'min_reward': float(min(rewards)) if rewards else 0,
            'remaining_distribution_capacity': float(
                self.limits['max_total_distribution'] - self.total_distributed
            )
        }


# Экспорт для удобного импорта
__all__ = ['RewardCalculator', 'RewardTier', 'RewardFormula', 'RewardCalculation']


if __name__ == "__main__":
    # Тестовый запуск для проверки модуля
    def test_reward_calculator():
        """Тестирование RewardCalculator."""
        try:
            print("🧪 Тестирование RewardCalculator...")
            
            # Создание калькулятора
            calculator = RewardCalculator()
            
            # Тестовые участники
            test_participants = [
                {
                    'address': '0x1234567890123456789012345678901234567890',
                    'total_volume_usd': Decimal('50000'),  # Platinum уровень
                    'current_balance': {'plex': Decimal('100000')},
                    'first_transaction_date': datetime.now() - timedelta(days=60)
                },
                {
                    'address': '0x2345678901234567890123456789012345678901',
                    'total_volume_usd': Decimal('2000'),   # Gold уровень
                    'current_balance': {'plex': Decimal('10000')},
                    'first_transaction_date': datetime.now() - timedelta(days=30)
                },
                {
                    'address': '0x3456789012345678901234567890123456789012',
                    'total_volume_usd': Decimal('500'),    # Silver уровень
                    'current_balance': {'plex': Decimal('5000')},
                    'first_transaction_date': datetime.now() - timedelta(days=15)
                }
            ]
            
            # Расчет наград
            print("💰 Расчет наград для тестовых участников...")
            calculations = calculator.calculate_batch_rewards(test_participants)
            
            # Вывод результатов
            for calc in calculations:
                print(f"\n👤 Участник: {calc.address[:10]}...")
                print(f"   🏆 Уровень: {calc.tier.value}")
                print(f"   💰 Базовая награда: {calc.base_reward}")
                print(f"   📈 Бонус объема: {calc.volume_bonus}")
                print(f"   🤝 Бонус холдинга: {calc.holding_bonus}")
                print(f"   ⭐ Бонус лояльности: {calc.loyalty_bonus}")
                print(f"   🎯 Бонус уровня: {calc.tier_bonus}")
                print(f"   🎉 ИТОГО: {calc.total_reward} PLEX")
            
            # Статистика калькулятора
            stats = calculator.get_calculator_stats()
            print(f"\n📊 Статистика калькулятора:")
            print(f"   Всего расчетов: {stats['total_calculations']}")
            print(f"   Распределено: {stats['total_distributed']} PLEX")
            print(f"   Средняя награда: {stats['avg_reward']:.2f} PLEX")
            print(f"   Распределение по уровням: {stats['tier_distribution']}")
            
            print("\n✅ Тестирование RewardCalculator завершено успешно")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    # Запуск тестирования
    # test_reward_calculator()
    print("💡 Для тестирования раскомментируй последнюю строку")
