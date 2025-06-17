"""
Модуль: Система определения права на награды PLEX Dynamic Staking
Описание: Расчет eligibility, тиров участников и размеров наград
Автор: GitHub Copilot
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from config.constants import TOKEN_DECIMALS, CORP_WALLET_ADDRESS
from utils.logger import get_logger
from utils.converters import wei_to_token

logger = get_logger("PLEX_EligibilityEngine")


class EligibilityTier(Enum):
    """Тиры участников для расчета наград"""
    BRONZE = "bronze"      # Минимальный уровень
    SILVER = "silver"      # Средний уровень  
    GOLD = "gold"          # Высокий уровень
    PLATINUM = "platinum"  # Максимальный уровень
    INELIGIBLE = "ineligible"  # Не квалифицирован


class EligibilityEngine:
    """Движок определения права на награды"""
    
    def __init__(self):
        """Инициализация системы eligibility"""
        self.logger = logger
        
        # Критерии eligibility (из ТЗ)
        self.min_balance_plex = Decimal('100')  # Минимум 100 PLEX
        self.min_total_sent = Decimal('500')    # Минимум $500 отправлено в корп. кошелек
        self.min_swaps = 3                      # Минимум 3 swap операции
        self.min_unique_days = 2                # Минимум 2 дня активности
        self.max_days_inactive = 7              # Максимум 7 дней неактивности
        
        # Тиры и мультипликаторы
        self.tier_criteria = {
            EligibilityTier.PLATINUM: {
                'min_sent_usd': Decimal('10000'),
                'min_swaps': 50,
                'min_days': 20,
                'reward_multiplier': Decimal('2.0'),
                'max_reward_usd': Decimal('1000')
            },
            EligibilityTier.GOLD: {
                'min_sent_usd': Decimal('5000'),
                'min_swaps': 25,
                'min_days': 15,
                'reward_multiplier': Decimal('1.5'),
                'max_reward_usd': Decimal('500')
            },
            EligibilityTier.SILVER: {
                'min_sent_usd': Decimal('1000'),
                'min_swaps': 10,
                'min_days': 7,
                'reward_multiplier': Decimal('1.2'),
                'max_reward_usd': Decimal('200')
            },
            EligibilityTier.BRONZE: {
                'min_sent_usd': Decimal('500'),
                'min_swaps': 3,
                'min_days': 2,
                'reward_multiplier': Decimal('1.0'),
                'max_reward_usd': Decimal('100')
            }
        }
        
        logger.info("🎯 Система eligibility инициализирована")
        logger.info(f"💰 Минимальный баланс: {self.min_balance_plex} PLEX")
        logger.info(f"📊 Минимальная отправка: ${self.min_total_sent}")

    def calculate_eligibility(self, 
                            address: str,
                            current_balance: Decimal,
                            total_sent_to_corp: Decimal,
                            swaps_data: List[Dict],
                            category_result: Dict) -> Dict:
        """
        Расчет права на награды для адреса
        
        Args:
            address: Адрес участника
            current_balance: Текущий баланс PLEX
            total_sent_to_corp: Всего отправлено в корп. кошелек (USD)
            swaps_data: Данные swap операций
            category_result: Результат категоризации
            
        Returns:
            Dict: Результат eligibility
        """
        logger.debug(f"🎯 Расчет eligibility для {address}")
        
        try:
            # 1. Базовые проверки
            base_checks = self._perform_base_checks(
                address, current_balance, total_sent_to_corp, swaps_data
            )
            
            if not base_checks['eligible']:
                return self._create_eligibility_result(
                    tier=EligibilityTier.INELIGIBLE,
                    eligible=False,
                    reason=base_checks['reason'],
                    details=base_checks
                )
            
            # 2. Проверка категории
            category = category_result.get('category')
            if category == 'sold_token':
                return self._create_eligibility_result(
                    tier=EligibilityTier.INELIGIBLE,
                    eligible=False,
                    reason="Участник продавал токены - награды заблокированы",
                    details={'blocking_category': category}
                )
            
            # 3. Расчет метрик
            metrics = self._calculate_metrics(swaps_data, total_sent_to_corp)
            
            # 4. Определение тира
            tier = self._determine_tier(metrics)
            
            # 5. Расчет награды
            reward_calculation = self._calculate_reward(tier, metrics, total_sent_to_corp)
            
            # 6. Финальная проверка амнистии
            amnesty_needed = category in ['missed_purchase', 'transferred']
            amnesty_eligible = category_result.get('amnesty_eligible', False)
            
            final_eligible = base_checks['eligible'] and (not amnesty_needed or amnesty_eligible)
            
            return self._create_eligibility_result(
                tier=tier,
                eligible=final_eligible,
                reason=self._generate_eligibility_reason(tier, final_eligible, amnesty_needed),
                details={
                    **base_checks,
                    **metrics,
                    **reward_calculation,
                    'amnesty_needed': amnesty_needed,
                    'amnesty_eligible': amnesty_eligible,
                    'category': category
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета eligibility для {address}: {e}")
            return self._create_eligibility_result(
                tier=EligibilityTier.INELIGIBLE,
                eligible=False,
                reason=f"Ошибка расчета: {e}",
                details={'error': str(e)}
            )

    def _perform_base_checks(self, 
                           address: str,
                           balance: Decimal,
                           total_sent: Decimal,
                           swaps: List[Dict]) -> Dict:
        """Выполнение базовых проверок eligibility"""
        
        checks = {
            'balance_check': balance >= self.min_balance_plex,
            'sent_check': total_sent >= self.min_total_sent,
            'swaps_check': len(swaps) >= self.min_swaps,
            'activity_check': True  # Упрощенная проверка
        }
        
        failed_checks = [k for k, v in checks.items() if not v]
        
        if failed_checks:
            reason = f"Не пройдены проверки: {', '.join(failed_checks)}"
            details = f"Баланс: {balance} PLEX (нужно {self.min_balance_plex}), "
            details += f"Отправлено: ${total_sent} (нужно ${self.min_total_sent}), "
            details += f"Swaps: {len(swaps)} (нужно {self.min_swaps})"
            
            return {
                'eligible': False,
                'reason': reason,
                'details': details,
                **checks,
                'balance': balance,
                'total_sent': total_sent,
                'swaps_count': len(swaps)
            }
        
        return {
            'eligible': True,
            'reason': "Все базовые проверки пройдены",
            **checks,
            'balance': balance,
            'total_sent': total_sent,
            'swaps_count': len(swaps)
        }

    def _calculate_metrics(self, swaps: List[Dict], total_sent: Decimal) -> Dict:
        """Расчет метрик участника"""
        
        total_volume = sum(Decimal(str(swap.get('usd_value', 0))) for swap in swaps)
        unique_days = len(set(swap.get('date', datetime.now().date()) for swap in swaps))
        avg_swap_size = total_volume / len(swaps) if swaps else Decimal('0')
        
        return {
            'total_volume_usd': total_volume,
            'unique_days_active': unique_days,
            'avg_swap_size_usd': avg_swap_size,
            'total_sent_usd': total_sent,
            'contribution_score': self._calculate_contribution_score(total_sent, total_volume)
        }

    def _calculate_contribution_score(self, sent: Decimal, volume: Decimal) -> Decimal:
        """Расчет оценки вклада участника"""
        # Формула: 70% вес отправленного + 30% вес торгового объема
        sent_score = sent / Decimal('1000')  # Нормализация к 1000 USD
        volume_score = volume / Decimal('5000')  # Нормализация к 5000 USD
        
        return (sent_score * Decimal('0.7')) + (volume_score * Decimal('0.3'))

    def _determine_tier(self, metrics: Dict) -> EligibilityTier:
        """Определение тира участника"""
        
        sent_usd = metrics['total_sent_usd']
        swaps_count = metrics.get('swaps_count', 0)
        days_active = metrics['unique_days_active']
        
        # Проверяем тиры от высшего к низшему
        for tier, criteria in self.tier_criteria.items():
            if (sent_usd >= criteria['min_sent_usd'] and
                swaps_count >= criteria['min_swaps'] and
                days_active >= criteria['min_days']):
                return tier
        
        return EligibilityTier.INELIGIBLE

    def _calculate_reward(self, tier: EligibilityTier, metrics: Dict, total_sent: Decimal) -> Dict:
        """Расчет размера награды"""
        
        if tier == EligibilityTier.INELIGIBLE:
            return {
                'base_reward_usd': Decimal('0'),
                'multiplier': Decimal('0'),
                'final_reward_usd': Decimal('0'),
                'max_reward_usd': Decimal('0')
            }
        
        criteria = self.tier_criteria[tier]
        
        # Базовая награда = 0.5% от отправленной суммы
        base_reward = total_sent * Decimal('0.005')
        
        # Применяем мультипликатор тира
        multiplied_reward = base_reward * criteria['reward_multiplier']
        
        # Ограничиваем максимумом тира
        final_reward = min(multiplied_reward, criteria['max_reward_usd'])
        
        return {
            'base_reward_usd': base_reward,
            'multiplier': criteria['reward_multiplier'],
            'final_reward_usd': final_reward,
            'max_reward_usd': criteria['max_reward_usd'],
            'tier_name': tier.value
        }

    def _generate_eligibility_reason(self, tier: EligibilityTier, eligible: bool, amnesty_needed: bool) -> str:
        """Генерация причины eligibility"""
        
        if not eligible:
            if amnesty_needed:
                return f"Требуется амнистия для тира {tier.value}"
            else:
                return f"Не квалифицирован для тира {tier.value}"
        
        return f"Квалифицирован для тира {tier.value}"

    def _create_eligibility_result(self, 
                                 tier: EligibilityTier,
                                 eligible: bool,
                                 reason: str,
                                 details: Dict) -> Dict:
        """Создание результата eligibility"""
        
        return {
            'tier': tier.value,
            'tier_name': tier.name,
            'eligible': eligible,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }

    def generate_eligibility_report(self, eligibility_results: Dict[str, Dict]) -> Dict:
        """Генерация отчета по eligibility"""
        
        report = {
            'total_addresses': len(eligibility_results),
            'eligible_count': 0,
            'tiers': {},
            'total_rewards_usd': Decimal('0'),
            'statistics': {}
        }
        
        # Подсчет по тирам
        for address, result in eligibility_results.items():
            tier = result['tier']
            eligible = result['eligible']
            
            if tier not in report['tiers']:
                report['tiers'][tier] = {
                    'count': 0,
                    'eligible_count': 0,
                    'total_rewards': Decimal('0'),
                    'addresses': []
                }
            
            report['tiers'][tier]['count'] += 1
            report['tiers'][tier]['addresses'].append(address)
            
            if eligible:
                report['eligible_count'] += 1
                report['tiers'][tier]['eligible_count'] += 1
                
                reward = Decimal(str(result['details'].get('final_reward_usd', 0)))
                report['tiers'][tier]['total_rewards'] += reward
                report['total_rewards_usd'] += reward
        
        # Статистика
        total = report['total_addresses']
        report['statistics'] = {
            'eligibility_rate': report['eligible_count'] / total * 100 if total > 0 else 0,
            'avg_reward_usd': report['total_rewards_usd'] / report['eligible_count'] if report['eligible_count'] > 0 else Decimal('0'),
            'tier_distribution': {
                tier: data['count'] / total * 100 if total > 0 else 0
                for tier, data in report['tiers'].items()
            }
        }
        
        logger.info(f"🎯 Отчет по eligibility сгенерирован:")
        logger.info(f"   👥 Всего адресов: {total}")
        logger.info(f"   ✅ Квалифицированных: {report['eligible_count']} ({report['statistics']['eligibility_rate']:.1f}%)")
        logger.info(f"   💰 Общая сумма наград: ${report['total_rewards_usd']}")
        logger.info(f"   📊 Средняя награда: ${report['statistics']['avg_reward_usd']}")
        
        return report


# Глобальный экземпляр для использования в системе
eligibility_engine = EligibilityEngine()
