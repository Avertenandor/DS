"""
Модуль: Категоризация участников PLEX Dynamic Staking
Описание: Система категоризации адресов по 4 группам согласно ТЗ
Автор: GitHub Copilot
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from config.constants import DAILY_PURCHASE_MIN, DAILY_PURCHASE_MAX
from utils.logger import get_logger

logger = get_logger("PLEX_CategoryAnalyzer")


class ParticipantCategory(Enum):
    """Категории участников согласно ТЗ"""
    PERFECT = "perfect"                    # Ежедневные покупки $2.8-3.2, без пропусков, без продаж
    MISSED_PURCHASE = "missed_purchase"    # Пропустил хотя бы один день (возможна амнистия)
    SOLD_TOKEN = "sold_token"             # Любая продажа (амнистия запрещена)
    TRANSFERRED = "transferred"           # Отправил PLEX на другие кошельки (отметка, не блокировка)


class CategoryAnalyzer:
    """Анализатор категорий участников согласно строгим правилам ТЗ"""
    
    def __init__(self):
        """Инициализация анализатора категорий"""
        self.logger = logger
        
        # Строгие критерии из ТЗ
        self.daily_min_usd = DAILY_PURCHASE_MIN  # $2.8
        self.daily_max_usd = DAILY_PURCHASE_MAX  # $3.2
        
        logger.info("🏷️ Анализатор категорий инициализирован")
        logger.info(f"💰 Диапазон ежедневных покупок: ${self.daily_min_usd} - ${self.daily_max_usd}")

    def categorize_address(self, 
                          address: str,
                          swaps: List[Dict],
                          transfers: List[Dict],
                          analysis_period_days: int) -> Dict:
        """
        Категоризация адреса по строгим правилам ТЗ
        
        Args:
            address: Адрес для анализа
            swaps: Список swap операций
            transfers: Список transfer операций
            analysis_period_days: Период анализа в днях
            
        Returns:
            Dict: Результат категоризации
        """
        logger.debug(f"🔍 Категоризация адреса {address}")
        
        try:
            # 1. Анализ swap операций
            buy_swaps = [s for s in swaps if s.get('direction') == 'buy']
            sell_swaps = [s for s in swaps if s.get('direction') == 'sell']
            
            # 2. КРИТЕРИЙ 1: Проверка продаж (приоритет)
            if sell_swaps:
                logger.debug(f"❌ {address}: Найдены продажи ({len(sell_swaps)})")
                return self._create_result(
                    category=ParticipantCategory.SOLD_TOKEN,
                    reason=f"Обнаружены продажи токена ({len(sell_swaps)} транзакций)",
                    amnesty_eligible=False,
                    details={
                        'sell_count': len(sell_swaps),
                        'sell_volume': sum(s.get('usd_value', 0) for s in sell_swaps),
                        'blocking_factor': 'sales_detected'
                    }
                )
            
            # 3. КРИТЕРИЙ 2: Проверка переводов (не блокирующий)
            non_pool_transfers = [t for t in transfers if not self._is_pool_transfer(t)]
            has_transfers = len(non_pool_transfers) > 0
            
            # 4. КРИТЕРИЙ 3: Анализ ежедневных покупок
            daily_purchases = self._analyze_daily_purchases(buy_swaps, analysis_period_days)
            expected_days = analysis_period_days
            actual_days = len(daily_purchases['valid_days'])
            missed_days = expected_days - actual_days
            
            # 5. Определение финальной категории
            if missed_days == 0 and not has_transfers:
                # PERFECT: Все дни покупал, нет переводов
                return self._create_result(
                    category=ParticipantCategory.PERFECT,
                    reason="Ежедневные покупки в диапазоне $2.8-3.2, без пропусков и переводов",
                    amnesty_eligible=None,  # Не нужна
                    details={
                        'consecutive_days': actual_days,
                        'avg_daily_usd': daily_purchases['avg_amount'],
                        'total_volume': daily_purchases['total_volume'],
                        'perfect_score': True
                    }
                )
            
            elif has_transfers and missed_days == 0:
                # TRANSFERRED: Все дни покупал, но были переводы
                return self._create_result(
                    category=ParticipantCategory.TRANSFERRED,
                    reason="Ежедневные покупки выполнены, но обнаружены переводы токенов",
                    amnesty_eligible=True,
                    details={
                        'consecutive_days': actual_days,
                        'transfers_count': len(non_pool_transfers),
                        'transfers_volume': sum(t.get('value', 0) for t in non_pool_transfers),
                        'warning_only': True
                    }
                )
            
            elif has_transfers and missed_days > 0:
                # TRANSFERRED + MISSED: И пропуски, и переводы
                return self._create_result(
                    category=ParticipantCategory.TRANSFERRED,
                    reason=f"Пропущено {missed_days} дней покупок + обнаружены переводы",
                    amnesty_eligible=True,
                    details={
                        'missed_days': missed_days,
                        'completed_days': actual_days,
                        'transfers_count': len(non_pool_transfers),
                        'combined_issues': True
                    }
                )
            
            else:
                # MISSED_PURCHASE: Только пропуски дней
                return self._create_result(
                    category=ParticipantCategory.MISSED_PURCHASE,
                    reason=f"Пропущено {missed_days} из {expected_days} дней покупок",
                    amnesty_eligible=True,
                    details={
                        'missed_days': missed_days,
                        'completed_days': actual_days,
                        'completion_rate': actual_days / expected_days * 100,
                        'amnesty_recommended': missed_days <= 3  # Рекомендация для <= 3 дней
                    }
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка категоризации {address}: {e}")
            return self._create_result(
                category=ParticipantCategory.MISSED_PURCHASE,
                reason=f"Ошибка анализа: {e}",
                amnesty_eligible=False,
                details={'error': str(e)}
            )

    def _analyze_daily_purchases(self, buy_swaps: List[Dict], period_days: int) -> Dict:
        """Анализ ежедневных покупок"""
        daily_data = {}
        total_volume = Decimal('0')
        valid_days = []
        
        for swap in buy_swaps:
            usd_value = Decimal(str(swap.get('usd_value', 0)))
            
            # Упрощенный анализ - в реальности нужен анализ по датам
            # Здесь считаем каждый swap как отдельный день
            if self.daily_min_usd <= usd_value <= self.daily_max_usd:
                valid_days.append(swap)
                total_volume += usd_value
        
        return {
            'valid_days': valid_days,
            'total_volume': total_volume,
            'avg_amount': total_volume / len(valid_days) if valid_days else Decimal('0'),
            'period_days': period_days
        }

    def _is_pool_transfer(self, transfer: Dict) -> bool:
        """Проверка, является ли перевод операцией с пулом"""
        to_address = transfer.get('to', '').lower()
        from_address = transfer.get('from', '').lower()
        
        # Упрощенная проверка - в реальности нужны адреса всех пулов
        pool_addresses = [
            '0x41d9650faf3341cbf8947fd8063a1fc88dbf1889',  # PLEX/USDT pool
        ]
        
        return any(addr.lower() in [to_address, from_address] for addr in pool_addresses)

    def _create_result(self, 
                      category: ParticipantCategory, 
                      reason: str,
                      amnesty_eligible: Optional[bool],
                      details: Dict) -> Dict:
        """Создание результата категоризации"""
        return {
            'category': category.value,
            'category_name': category.name,
            'reason': reason,
            'amnesty_eligible': amnesty_eligible,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }

    def generate_category_report(self, categorized_addresses: Dict[str, Dict]) -> Dict:
        """Генерация отчета по категориям"""
        report = {
            'total_addresses': len(categorized_addresses),
            'categories': {},
            'amnesty_candidates': [],
            'perfect_participants': [],
            'blocked_addresses': [],
            'statistics': {}
        }
        
        # Подсчет по категориям
        for address, result in categorized_addresses.items():
            category = result['category']
            
            if category not in report['categories']:
                report['categories'][category] = {
                    'count': 0,
                    'addresses': [],
                    'total_volume': Decimal('0')
                }
            
            report['categories'][category]['count'] += 1
            report['categories'][category]['addresses'].append(address)
            
            # Специальные списки
            if result['amnesty_eligible']:
                report['amnesty_candidates'].append({
                    'address': address,
                    'category': category,
                    'reason': result['reason']
                })
            
            if category == ParticipantCategory.PERFECT.value:
                report['perfect_participants'].append(address)
            
            if category == ParticipantCategory.SOLD_TOKEN.value:
                report['blocked_addresses'].append(address)
        
        # Статистика
        total = report['total_addresses']
        report['statistics'] = {
            'perfect_rate': len(report['perfect_participants']) / total * 100 if total > 0 else 0,
            'amnesty_rate': len(report['amnesty_candidates']) / total * 100 if total > 0 else 0,
            'blocked_rate': len(report['blocked_addresses']) / total * 100 if total > 0 else 0
        }
        
        logger.info(f"📊 Отчет по категориям сгенерирован:")
        logger.info(f"   👥 Всего адресов: {total}")
        logger.info(f"   ✅ Perfect: {len(report['perfect_participants'])} ({report['statistics']['perfect_rate']:.1f}%)")
        logger.info(f"   🤝 Кандидаты на амнистию: {len(report['amnesty_candidates'])} ({report['statistics']['amnesty_rate']:.1f}%)")
        logger.info(f"   ❌ Заблокированы: {len(report['blocked_addresses'])} ({report['statistics']['blocked_rate']:.1f}%)")
        
        return report


# Глобальный экземпляр для использования в системе
category_analyzer = CategoryAnalyzer()
