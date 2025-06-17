"""
Модуль: Анализатор участников PLEX Dynamic Staking
Описание: Анализ активности участников, категоризация и расчет eligibility
Автор: GitHub Copilot
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from decimal import Decimal

from config.constants import *
from utils.logger import get_logger
from utils.converters import wei_to_token, format_number
from utils.validators import validate_address
from blockchain.node_client import Web3Manager
from blockchain.swap_analyzer import SwapAnalyzer
from core.category_analyzer import CategoryAnalyzer
from core.eligibility import EligibilityCalculator
from core.amnesty_manager import AmnestyManager

logger = get_logger("PLEX_ParticipantAnalyzer")

@dataclass
class ParticipantData:
    """Данные участника"""
    address: str
    first_activity: datetime
    last_activity: datetime
    total_swaps: int = 0
    total_volume_usd: Decimal = field(default_factory=lambda: Decimal('0'))
    total_plex_bought: Decimal = field(default_factory=lambda: Decimal('0'))
    total_plex_sold: Decimal = field(default_factory=lambda: Decimal('0'))
    avg_swap_size_usd: Decimal = field(default_factory=lambda: Decimal('0'))
    unique_days_active: int = 0
    consecutive_days: int = 0
    max_consecutive_days: int = 0
    category: str = "Unknown"
    eligibility_score: float = 0.0
    reward_tier: str = "None"
    is_qualified: bool = False

@dataclass
class ActivityPeriod:
    """Период активности"""
    start_date: datetime
    end_date: datetime
    swaps_count: int
    volume_usd: Decimal
    net_plex_change: Decimal  # Положительное = покупка, отрицательное = продажа

class ParticipantAnalyzer:
    """Анализатор участников динамического стейкинга"""
    
    def __init__(self):
        """Инициализация анализатора"""
        self.web3_manager = Web3Manager()
        self.swap_analyzer = SwapAnalyzer()
        self.category_analyzer = CategoryAnalyzer()
        self.eligibility_calculator = EligibilityCalculator()
        self.amnesty_manager = AmnestyManager()
        self.participants: Dict[str, ParticipantData] = {}
        
        logger.info("🔧 Анализатор участников инициализирован с интегрированными модулями")

    def analyze_participants(self, 
                          start_block: int, 
                          end_block: int,
                          progress_callback=None) -> Dict[str, ParticipantData]:
        """
        Основной метод анализа участников
        
        Args:
            start_block: Начальный блок для анализа
            end_block: Конечный блок для анализа
            progress_callback: Функция для отображения прогресса
            
        Returns:
            Dict[str, ParticipantData]: Словарь участников
        """
        logger.info(f"🔍 Начинаем анализ участников в блоках {start_block:,} - {end_block:,}")
        
        # Очищаем предыдущие данные
        self.participants.clear()
        
        try:            # Получаем все swap события в указанном диапазоне
            swaps = self.swap_analyzer.get_swaps_in_range(start_block, end_block)
            logger.info(f"📊 Найдено {len(swaps)} swap событий для анализа")
            
            if not swaps:
                logger.warning("⚠️ Не найдено swap событий в указанном диапазоне")
                return self.participants
              # Обрабатываем каждый swap
            for i, swap in enumerate(swaps):
                self._process_swap(swap)
                
                # Вызываем callback для отображения прогресса
                if progress_callback and i % 100 == 0:
                    progress = (i + 1) / len(swaps) * 100
                    progress_callback(f"Обработано {i+1}/{len(swaps)} swap событий ({progress:.1f}%)")
              # Анализируем каждого участника
            logger.info(f"👥 Анализируем {len(self.participants)} уникальных участников")
            
            for address, participant in self.participants.items():
                self._calculate_participant_metrics(participant)
                
                # Используем новые модули для категоризации и eligibility
                category_result = self.category_analyzer.categorize_participant(participant)
                participant.category = category_result.category
                
                eligibility_result = self.eligibility_calculator.calculate_eligibility(participant)
                participant.eligibility_score = eligibility_result.score
                participant.reward_tier = eligibility_result.tier
                participant.is_qualified = eligibility_result.is_qualified
                
                # Проверяем амнистии для участника
                self.amnesty_manager.apply_amnesty_if_eligible(participant)
            
            # Статистика по категориям
            self._log_category_statistics()
            
            logger.info(f"✅ Анализ участников завершен. Обработано {len(self.participants)} участников")
            return self.participants            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа участников: {e}")
            raise

    def _process_swap(self, swap_data: Dict):
        """Обработка одного swap события"""
        try:
            # Извлекаем sender из swap данных
            sender = swap_data.get('sender', '')
            to = swap_data.get('to', '')
            
            # Определяем участника транзакции (исключаем адрес пула)
            participant_address = None
            if sender and sender.lower() != PLEX_USDT_POOL.lower():
                participant_address = sender.lower()
            elif to and to.lower() != PLEX_USDT_POOL.lower():
                participant_address = to.lower()
            
            if not participant_address:
                return
                
            # Создаем участника если его нет
            if participant_address not in self.participants:
                current_time = datetime.now()
                self.participants[participant_address] = ParticipantData(
                    address=participant_address,
                    first_activity=current_time,
                    last_activity=current_time
                )
            
            participant = self.participants[participant_address]
            
            # Обновляем базовые метрики
            participant.total_swaps += 1
            current_time = datetime.now()
            participant.last_activity = current_time
            
            # Добавляем объемы
            usd_value = swap_data.get('usd_value', Decimal('0'))
            participant.total_volume_usd += usd_value
              # Отслеживаем покупки/продажи PLEX
            plex_amount = swap_data.get('plex_amount', Decimal('0'))
            direction = swap_data.get('direction', 'unknown')
            
            if direction == 'buy':
                participant.total_plex_bought += abs(plex_amount)
            elif direction == 'sell':
                participant.total_plex_sold += abs(plex_amount)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки swap: {e}")

    def _calculate_participant_metrics(self, participant: ParticipantData):
        """Расчет дополнительных метрик участника"""
        try:
            # Средний размер swap
            if participant.total_swaps > 0:
                participant.avg_swap_size_usd = participant.total_volume_usd / participant.total_swaps
            
            # Количество уникальных дней активности
            # (Здесь упрощенный расчет, в реальности нужен анализ по дням)
            days_active = (participant.last_activity - participant.first_activity).days + 1
            participant.unique_days_active = min(days_active, participant.total_swaps)
            
            # Максимальная последовательность дней
            # (Упрощенный расчет - нужна более сложная логика для точного подсчета)
            participant.max_consecutive_days = min(7, participant.unique_days_active)
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета метрик для {participant.address}: {e}")

    def _log_category_statistics(self):
        """Логирование статистики по категориям"""
        try:
            categories = {}
            qualified_count = 0
            
            for participant in self.participants.values():
                category = participant.category
                categories[category] = categories.get(category, 0) + 1
                
                if participant.is_qualified:
                    qualified_count += 1
            
            logger.info("📊 Статистика по категориям участников:")
            for category, count in sorted(categories.items()):
                percentage = (count / len(self.participants)) * 100 if self.participants else 0
                logger.info(f"   {category}: {count} ({percentage:.1f}%)")
            
            logger.info(f"🎯 Квалифицированных для наград: {qualified_count}/{len(self.participants)} ({(qualified_count/len(self.participants)*100) if self.participants else 0:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка статистики: {e}")

    def get_top_participants(self, category: str = None, limit: int = 100) -> List[ParticipantData]:
        """Получение топ участников по категории"""
        try:
            participants = list(self.participants.values())
            
            # Фильтрация по категории
            if category:
                participants = [p for p in participants if p.category == category]
            
            # Сортировка по eligibility score
            participants.sort(key=lambda x: x.eligibility_score, reverse=True)
            
            return participants[:limit]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения топ участников: {e}")
            return []

    def export_participants_summary(self) -> Dict:
        """Экспорт сводной информации об участниках"""
        try:
            summary = {
                "total_participants": len(self.participants),
                "analysis_timestamp": datetime.now().isoformat(),
                "categories": {},
                "reward_tiers": {},
                "top_by_volume": [],
                "top_by_activity": []
            }
            
            # Статистика по категориям
            for participant in self.participants.values():
                cat = participant.category
                tier = participant.reward_tier
                
                summary["categories"][cat] = summary["categories"].get(cat, 0) + 1
                summary["reward_tiers"][tier] = summary["reward_tiers"].get(tier, 0) + 1
            
            # Топ по объему
            top_volume = sorted(self.participants.values(), 
                              key=lambda x: x.total_volume_usd, reverse=True)[:10]
            summary["top_by_volume"] = [
                {
                    "address": p.address,
                    "volume_usd": str(p.total_volume_usd),
                    "category": p.category,
                    "reward_tier": p.reward_tier
                }
                for p in top_volume
            ]
            
            # Топ по активности
            top_activity = sorted(self.participants.values(), 
                                key=lambda x: x.total_swaps, reverse=True)[:10]
            summary["top_by_activity"] = [
                {
                    "address": p.address,
                    "total_swaps": p.total_swaps,
                    "unique_days": p.unique_days_active,
                    "category": p.category
                }
                for p in top_activity
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта сводки: {e}")
            return {}
