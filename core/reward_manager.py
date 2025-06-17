"""
Модуль: Менеджер наград PLEX Dynamic Staking
Описание: Расчет и распределение наград для участников
Автор: GitHub Copilot
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
import json

from config.constants import TOKEN_DECIMALS, TOKEN_TOTAL_SUPPLY
from utils.logger import get_logger
from utils.converters import format_number, token_to_wei
from core.participant_analyzer_v2 import ParticipantData

logger = get_logger("PLEX_RewardManager")

@dataclass
class RewardDistribution:
    """Распределение наград"""
    participant_address: str
    category: str
    reward_tier: str
    base_reward: Decimal
    bonus_multiplier: float
    final_reward: Decimal
    eligibility_score: float
    distribution_date: datetime
    notes: str = ""

@dataclass
class RewardPool:
    """Пул наград"""
    total_amount: Decimal
    period_start: datetime
    period_end: datetime
    tier_allocations: Dict[str, Decimal]
    category_bonuses: Dict[str, float]
    distributed_amount: Decimal = Decimal('0')
    remaining_amount: Decimal = Decimal('0')

class RewardManager:
    """Менеджер системы наград"""
    
    def __init__(self):
        """Инициализация менеджера наград"""
        self.distributions: List[RewardDistribution] = []
        
        # Базовые параметры наград (из ТЗ)
        self.reward_tiers = {
            "Platinum": {
                "base_amount": Decimal('10000'),  # PLEX
                "min_score": 0.8,
                "allocation_percent": 40  # 40% от общего пула
            },
            "Gold": {
                "base_amount": Decimal('5000'),
                "min_score": 0.6,
                "allocation_percent": 30
            },
            "Silver": {
                "base_amount": Decimal('2000'),
                "min_score": 0.4,
                "allocation_percent": 20
            },
            "Bronze": {
                "base_amount": Decimal('500'),
                "min_score": 0.2,
                "allocation_percent": 10
            }
        }
          # Бонусы по категориям (уменьшены для предотвращения превышения пула)
        self.category_multipliers = {
            "Whale": 1.4,
            "Active_Trader": 1.2,
            "Holder": 1.1,
            "Regular_User": 1.0,
            "Newcomer": 0.9
        }
        
        # Бонусы за активность (уменьшены)
        self.activity_bonuses = {
            "consecutive_days": {
                "7_days": 1.05,
                "14_days": 1.1,
                "30_days": 1.15
            },
            "volume_milestones": {
                "10k": 1.05,
                "50k": 1.1,
                "100k": 1.2,
                "500k": 1.3
            }
        }
        
        logger.info("🏆 Менеджер наград инициализирован")

    def create_reward_pool(self, 
                          total_amount: Decimal,
                          period_start: datetime,
                          period_end: datetime) -> RewardPool:
        """
        Создание пула наград на период
        
        Args:
            total_amount: Общая сумма наград в PLEX
            period_start: Начало периода
            period_end: Конец периода
            
        Returns:
            RewardPool: Созданный пул наград
        """
        logger.info(f"🏆 Создание пула наград: {format_number(total_amount)} PLEX")
        
        # Распределение по уровням
        tier_allocations = {}
        for tier, config in self.reward_tiers.items():
            allocation = total_amount * Decimal(config["allocation_percent"] / 100)
            tier_allocations[tier] = allocation
            logger.info(f"   {tier}: {format_number(allocation)} PLEX ({config['allocation_percent']}%)")
        
        pool = RewardPool(
            total_amount=total_amount,
            period_start=period_start,
            period_end=period_end,
            tier_allocations=tier_allocations,
            category_bonuses=self.category_multipliers.copy(),
            remaining_amount=total_amount
        )
        
        return pool

    def calculate_rewards(self, 
                         participants: Dict[str, ParticipantData],
                         reward_pool: RewardPool) -> List[RewardDistribution]:
        """
        Расчет наград для всех участников
        
        Args:
            participants: Словарь участников
            reward_pool: Пул наград
            
        Returns:
            List[RewardDistribution]: Список распределений наград
        """
        logger.info(f"💰 Расчет наград для {len(participants)} участников")
        
        distributions = []
        qualified_participants = [p for p in participants.values() if p.is_qualified]
        
        logger.info(f"🎯 Квалифицированных участников: {len(qualified_participants)}")
        
        if not qualified_participants:
            logger.warning("⚠️ Нет квалифицированных участников для наград")
            return distributions
        
        # Группируем участников по уровням наград
        participants_by_tier = {}
        for participant in qualified_participants:
            tier = participant.reward_tier
            if tier != "None":
                if tier not in participants_by_tier:
                    participants_by_tier[tier] = []
                participants_by_tier[tier].append(participant)
        
        # Рассчитываем награды для каждого уровня
        for tier, tier_participants in participants_by_tier.items():
            if tier not in reward_pool.tier_allocations:
                continue
                
            tier_distributions = self._calculate_tier_rewards(
                tier_participants, 
                tier, 
                reward_pool.tier_allocations[tier]
            )
            distributions.extend(tier_distributions)
        
        # Сохраняем распределения
        self.distributions = distributions        # Обновляем информацию о пуле
        total_distributed = sum(d.final_reward for d in distributions)
        
        # Защита от превышения пула с учетом ошибок округления
        # Добавляем толерантность для ошибок floating point (1e-10)
        tolerance = 1e-10
        excess = total_distributed - reward_pool.total_amount
        
        if excess > tolerance:
            logger.warning(f"⚠️ Превышение пула! Нормализация наград: {format_number(total_distributed)} -> {format_number(reward_pool.total_amount)}")
            
            # Пропорциональное уменьшение всех наград
            scale_factor = reward_pool.total_amount / total_distributed
            for distribution in distributions:
                distribution.final_reward *= scale_factor
                distribution.notes += f" | Scaled by {scale_factor:.4f}"
            
            # Пересчитываем с учетом масштабирования
            total_distributed = sum(d.final_reward for d in distributions)
        elif excess > 0:
            # Небольшая ошибка округления - корректируем последнюю награду
            if distributions:
                distributions[-1].final_reward -= excess
                distributions[-1].notes += " | Adjusted for rounding"
                total_distributed = reward_pool.total_amount
          # Финальная проверка и округление до разумной точности
        total_distributed = round(total_distributed, 10)
        reward_pool.distributed_amount = total_distributed
        remaining = round(reward_pool.total_amount - total_distributed, 10)
        
        # Обеспечиваем, что остаток не может быть отрицательным из-за ошибок округления
        reward_pool.remaining_amount = max(0.0, remaining)
        
        logger.info(f"✅ Распределено наград: {format_number(total_distributed)} PLEX")
        logger.info(f"💎 Остаток в пуле: {format_number(reward_pool.remaining_amount)} PLEX")
        
        return distributions

    def _calculate_tier_rewards(self, 
                               participants: List[ParticipantData],
                               tier: str,
                               tier_allocation: Decimal) -> List[RewardDistribution]:
        """Расчет наград для участников одного уровня"""
        if not participants:
            return []
        
        logger.info(f"🎖️ Расчет наград уровня {tier}: {len(participants)} участников")
        
        distributions = []
        
        # Вычисляем общий вес всех участников уровня
        total_weight = sum(self._calculate_participant_weight(p) for p in participants)
        
        if total_weight == 0:
            logger.warning(f"⚠️ Общий вес участников уровня {tier} равен 0")
            return distributions
        
        # Рассчитываем награды пропорционально весу
        for participant in participants:
            weight = self._calculate_participant_weight(participant)
            weight_ratio = weight / total_weight
            
            # Базовая награда
            base_reward = tier_allocation * Decimal(str(weight_ratio))
            
            # Применяем множители
            category_multiplier = self.category_multipliers.get(participant.category, 1.0)
            activity_multiplier = self._calculate_activity_multiplier(participant)
            
            total_multiplier = category_multiplier * activity_multiplier
            final_reward = base_reward * Decimal(str(total_multiplier))
            
            # Создаем распределение
            distribution = RewardDistribution(
                participant_address=participant.address,
                category=participant.category,
                reward_tier=tier,
                base_reward=base_reward,
                bonus_multiplier=total_multiplier,
                final_reward=final_reward,
                eligibility_score=participant.eligibility_score,
                distribution_date=datetime.now(),
                notes=f"Category: {category_multiplier}x, Activity: {activity_multiplier}x"
            )
            
            distributions.append(distribution)
        
        return distributions

    def _calculate_participant_weight(self, participant: ParticipantData) -> float:
        """Расчет веса участника для распределения наград"""
        # Базовый вес = eligibility score
        weight = participant.eligibility_score
        
        # Дополнительные факторы веса
        
        # Объем торгов (логарифмическая шкала)
        volume_factor = min(float(participant.total_volume_usd) / 100000, 2.0)
        
        # Количество дней активности
        activity_factor = min(participant.unique_days_active / 30, 1.5)
        
        # Последовательность активности
        consistency_factor = min(participant.max_consecutive_days / 14, 1.2)
        
        # Итоговый вес
        final_weight = weight * (1 + volume_factor + activity_factor + consistency_factor)
        
        return max(final_weight, 0.1)  # Минимальный вес 0.1

    def _calculate_activity_multiplier(self, participant: ParticipantData) -> float:
        """Расчет множителя за активность"""
        multiplier = 1.0
        
        # Бонус за последовательные дни
        consecutive_days = participant.max_consecutive_days
        if consecutive_days >= 30:
            multiplier *= self.activity_bonuses["consecutive_days"]["30_days"]
        elif consecutive_days >= 14:
            multiplier *= self.activity_bonuses["consecutive_days"]["14_days"]
        elif consecutive_days >= 7:
            multiplier *= self.activity_bonuses["consecutive_days"]["7_days"]
        
        # Бонус за объем торгов
        volume_usd = float(participant.total_volume_usd)
        if volume_usd >= 500000:
            multiplier *= self.activity_bonuses["volume_milestones"]["500k"]
        elif volume_usd >= 100000:
            multiplier *= self.activity_bonuses["volume_milestones"]["100k"]
        elif volume_usd >= 50000:
            multiplier *= self.activity_bonuses["volume_milestones"]["50k"]
        elif volume_usd >= 10000:
            multiplier *= self.activity_bonuses["volume_milestones"]["10k"]
        
        return multiplier

    def get_reward_summary(self) -> Dict:
        """Получение сводки по наградам"""
        if not self.distributions:
            return {}
        
        summary = {
            "total_recipients": len(self.distributions),
            "total_rewards": sum(d.final_reward for d in self.distributions),
            "by_tier": {},
            "by_category": {},
            "top_recipients": [],
            "statistics": {}
        }
        
        # Группировка по уровням
        for distribution in self.distributions:
            tier = distribution.reward_tier
            if tier not in summary["by_tier"]:
                summary["by_tier"][tier] = {
                    "count": 0,
                    "total_amount": Decimal('0'),
                    "avg_amount": Decimal('0')
                }
            
            summary["by_tier"][tier]["count"] += 1
            summary["by_tier"][tier]["total_amount"] += distribution.final_reward
        
        # Вычисляем средние значения
        for tier_data in summary["by_tier"].values():
            if tier_data["count"] > 0:
                tier_data["avg_amount"] = tier_data["total_amount"] / tier_data["count"]
        
        # Группировка по категориям
        for distribution in self.distributions:
            category = distribution.category
            if category not in summary["by_category"]:
                summary["by_category"][category] = {
                    "count": 0,
                    "total_amount": Decimal('0')
                }
            
            summary["by_category"][category]["count"] += 1
            summary["by_category"][category]["total_amount"] += distribution.final_reward
        
        # Топ получателей
        top_recipients = sorted(self.distributions, 
                              key=lambda x: x.final_reward, 
                              reverse=True)[:10]
        
        summary["top_recipients"] = [
            {
                "address": d.participant_address,
                "category": d.category,
                "tier": d.reward_tier,
                "reward": str(d.final_reward),
                "score": d.eligibility_score
            }
            for d in top_recipients
        ]
        
        # Статистика
        rewards = [float(d.final_reward) for d in self.distributions]
        summary["statistics"] = {
            "min_reward": min(rewards),
            "max_reward": max(rewards),
            "avg_reward": sum(rewards) / len(rewards),
            "median_reward": sorted(rewards)[len(rewards) // 2]
        }
        
        return summary

    def export_distributions(self, filepath: str, format: str = "json"):
        """Экспорт распределений наград"""
        try:
            if format.lower() == "json":
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_distributions": len(self.distributions),
                    "summary": self.get_reward_summary(),
                    "distributions": [
                        {
                            "address": d.participant_address,
                            "category": d.category,
                            "reward_tier": d.reward_tier,
                            "base_reward": str(d.base_reward),
                            "bonus_multiplier": d.bonus_multiplier,
                            "final_reward": str(d.final_reward),
                            "eligibility_score": d.eligibility_score,
                            "distribution_date": d.distribution_date.isoformat(),
                            "notes": d.notes
                        }
                        for d in self.distributions
                    ]
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"📁 Экспорт наград сохранен: {filepath}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта наград: {e}")
            return False

    def validate_distributions(self) -> Dict[str, any]:
        """Валидация распределений наград"""
        validation_results = {
            "is_valid": True,
            "total_recipients": len(self.distributions),
            "total_amount": sum(d.final_reward for d in self.distributions),
            "issues": []
        }
        
        # Проверка дубликатов адресов
        addresses = [d.participant_address for d in self.distributions]
        if len(addresses) != len(set(addresses)):
            validation_results["is_valid"] = False
            validation_results["issues"].append("Найдены дублирующиеся адреса")
        
        # Проверка нулевых наград
        zero_rewards = [d for d in self.distributions if d.final_reward <= 0]
        if zero_rewards:
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Найдено {len(zero_rewards)} наград с нулевой суммой")
        
        # Проверка максимальных лимитов
        max_single_reward = max(d.final_reward for d in self.distributions) if self.distributions else 0
        if max_single_reward > TOKEN_TOTAL_SUPPLY * Decimal('0.01'):  # 1% от общего предложения
            validation_results["is_valid"] = False
            validation_results["issues"].append("Найдена награда превышающая 1% от общего предложения")
        
        return validation_results
