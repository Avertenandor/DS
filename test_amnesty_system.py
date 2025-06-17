"""
PLEX Dynamic Staking Manager - Расширенное тестирование AmnestyManager
Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import asyncio
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from core.participant_analyzer_v2 import ParticipantData, CategoryAnalyzer, EligibilityEngine, AmnestyManager
from utils.logger import get_logger

logger = get_logger(__name__)


class TestAmnestyManager(unittest.TestCase):
    """Расширенное тестирование системы амнистий."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.amnesty_manager = AmnestyManager()
        
        # Тестовые участники
        self.test_participants = self._create_test_participants()
        
    def _create_test_participants(self) -> Dict[str, ParticipantData]:
        """Создание тестовых участников для различных сценариев амнистий."""
        participants = {}
        
        # Участник 1: VIP с небольшим нарушением
        participants["0x1111"] = ParticipantData(
            address="0x1111",
            first_activity=datetime.now() - timedelta(days=30),
            last_activity=datetime.now() - timedelta(days=2),
            total_swaps=500,
            total_volume_usd=Decimal("50000"),  # VIP уровень
            total_plex_bought=Decimal("25000"),
            total_plex_sold=Decimal("15000"),
            avg_swap_size_usd=Decimal("100"),
            unique_days_active=25,
            consecutive_days=5,
            max_consecutive_days=10,
            category="VIP",
            eligibility_score=85.0,
            reward_tier="Gold",
            is_qualified=True
        )
        
        # Участник 2: Premium с множественными нарушениями
        participants["0x2222"] = ParticipantData(
            address="0x2222",
            first_activity=datetime.now() - timedelta(days=20),
            last_activity=datetime.now() - timedelta(days=1),
            total_swaps=150,
            total_volume_usd=Decimal("15000"),  # Premium уровень
            total_plex_bought=Decimal("8000"),
            total_plex_sold=Decimal("7500"),
            avg_swap_size_usd=Decimal("100"),
            unique_days_active=15,
            consecutive_days=2,
            max_consecutive_days=5,
            category="Premium",
            eligibility_score=65.0,
            reward_tier="Silver",
            is_qualified=False
        )
        
        # Участник 3: Standard без нарушений
        participants["0x3333"] = ParticipantData(
            address="0x3333",
            first_activity=datetime.now() - timedelta(days=10),
            last_activity=datetime.now(),
            total_swaps=50,
            total_volume_usd=Decimal("5000"),  # Standard уровень
            total_plex_bought=Decimal("3000"),
            total_plex_sold=Decimal("1000"),
            avg_swap_size_usd=Decimal("100"),
            unique_days_active=8,
            consecutive_days=3,
            max_consecutive_days=5,
            category="Standard",
            eligibility_score=75.0,
            reward_tier="Bronze",
            is_qualified=True
        )
          # Участник 4: VIP с критическими нарушениями
        participants["0x4444"] = ParticipantData(
            address="0x4444",
            first_activity=datetime.now() - timedelta(days=60),
            last_activity=datetime.now() - timedelta(days=30),  # Долго неактивен
            total_swaps=1000,
            total_volume_usd=Decimal("100000"),  # Высокий VIP
            total_plex_bought=Decimal("60000"),
            total_plex_sold=Decimal("55000"),
            avg_swap_size_usd=Decimal("100"),
            unique_days_active=10,
            consecutive_days=0,
            max_consecutive_days=8,
            category="VIP",
            eligibility_score=30.0,  # Низкий из-за неактивности
            reward_tier="None",
            is_qualified=False
        )
        
        # Участник 5: Новый пользователь
        participants["0x5555"] = ParticipantData(
            address="0x5555",
            first_activity=datetime.now() - timedelta(days=3),
            last_activity=datetime.now(),
            total_swaps=5,
            total_volume_usd=Decimal("500"),
            total_plex_bought=Decimal("300"),
            total_plex_sold=Decimal("100"),
            avg_swap_size_usd=Decimal("100"),
            unique_days_active=3,
            consecutive_days=3,
            max_consecutive_days=3,
            category="Standard",
            eligibility_score=45.0,  # Низкий из-за короткой истории
            reward_tier="None",
            is_qualified=False
        )
        
        return participants
    
    def test_amnesty_rules_loading(self):
        """Тест загрузки правил амнистий."""
        logger.info("🧪 Тестирование загрузки правил амнистий...")
        
        # Проверяем, что правила загружены
        self.assertTrue(hasattr(self.amnesty_manager, 'amnesty_rules'))
        self.assertIsInstance(self.amnesty_manager.amnesty_rules, dict)
        
        # Проверяем наличие правил для каждой категории
        expected_categories = ["VIP", "Premium", "Standard"]
        for category in expected_categories:
            self.assertIn(category, self.amnesty_manager.amnesty_rules)
            
        logger.info("✅ Правила амнистий загружены корректно")
    
    def test_vip_amnesty_application(self):
        """Тест применения амнистий для VIP участников."""
        logger.info("🧪 Тестирование амнистий для VIP участников...")
        
        # VIP с небольшим нарушением
        participant = self.test_participants["0x1111"]
        result = self.amnesty_manager.apply_amnesty(participant)
        
        self.assertTrue(result.amnesty_granted)
        self.assertEqual(result.amnesty_level, "partial")
        self.assertIn("VIP статус", result.amnesty_reason)
        
        # VIP с критическими нарушениями
        participant_critical = self.test_participants["0x4444"]
        result_critical = self.amnesty_manager.apply_amnesty(participant_critical)
        
        # Даже VIP не должен получить полную амнистию при критических нарушениях
        if result_critical.amnesty_granted:
            self.assertEqual(result_critical.amnesty_level, "conditional")
        
        logger.info("✅ Амнистии для VIP протестированы")
    
    def test_premium_amnesty_application(self):
        """Тест применения амнистий для Premium участников."""
        logger.info("🧪 Тестирование амнистий для Premium участников...")
        
        participant = self.test_participants["0x2222"]
        result = self.amnesty_manager.apply_amnesty(participant)
        
        # Premium с множественными нарушениями может получить условную амнистию
        if result.amnesty_granted:
            self.assertIn(result.amnesty_level, ["partial", "conditional"])
        
        logger.info("✅ Амнистии для Premium протестированы")
    
    def test_standard_amnesty_application(self):
        """Тест применения амнистий для Standard участников."""
        logger.info("🧪 Тестирование амнистий для Standard участников...")
        
        # Standard без нарушений - амнистия не нужна
        participant_clean = self.test_participants["0x3333"]
        result_clean = self.amnesty_manager.apply_amnesty(participant_clean)
        
        # Если нет нарушений, амнистия не требуется
        if not participant_clean.eligibility_violations:
            self.assertFalse(result_clean.amnesty_granted)
            self.assertEqual(result_clean.amnesty_reason, "Амнистия не требуется")
        
        # Новый пользователь может получить амнистию для истории
        participant_new = self.test_participants["0x5555"]
        result_new = self.amnesty_manager.apply_amnesty(participant_new)
        
        # Новые пользователи обычно получают амнистию
        self.assertTrue(result_new.amnesty_granted)
        
        logger.info("✅ Амнистии для Standard протестированы")
    
    def test_amnesty_conditions_validation(self):
        """Тест проверки условий амнистий."""
        logger.info("🧪 Тестирование условий амнистий...")
        
        for address, participant in self.test_participants.items():
            result = self.amnesty_manager.apply_amnesty(participant)
            
            # Проверяем, что результат содержит все необходимые поля
            self.assertIsNotNone(result.participant_address)
            self.assertIsNotNone(result.amnesty_granted)
            self.assertIsNotNone(result.amnesty_reason)
            
            if result.amnesty_granted:
                self.assertIsNotNone(result.amnesty_level)
                self.assertIn(result.amnesty_level, ["full", "partial", "conditional"])
                
                if result.conditions:
                    self.assertIsInstance(result.conditions, list)
                    for condition in result.conditions:
                        self.assertIsInstance(condition, str)
            
            logger.info(f"📊 {address}: Амнистия={'Да' if result.amnesty_granted else 'Нет'}, "
                       f"Уровень={result.amnesty_level if result.amnesty_granted else 'N/A'}")
        
        logger.info("✅ Условия амнистий валидированы")
    
    def test_amnesty_statistics(self):
        """Тест статистики применения амнистий."""
        logger.info("🧪 Тестирование статистики амнистий...")
        
        results = []
        for participant in self.test_participants.values():
            result = self.amnesty_manager.apply_amnesty(participant)
            results.append(result)
        
        # Подсчет статистики
        granted_count = sum(1 for r in results if r.amnesty_granted)
        total_count = len(results)
        
        stats = {
            'total_participants': total_count,
            'amnesties_granted': granted_count,
            'amnesties_denied': total_count - granted_count,
            'amnesty_rate': (granted_count / total_count) * 100 if total_count > 0 else 0
        }
        
        logger.info(f"📊 Статистика амнистий:")
        logger.info(f"   Всего участников: {stats['total_participants']}")
        logger.info(f"   Амнистий предоставлено: {stats['amnesties_granted']}")
        logger.info(f"   Амнистий отклонено: {stats['amnesties_denied']}")
        logger.info(f"   Процент амнистий: {stats['amnesty_rate']:.1f}%")
        
        # Проверяем, что статистика разумна
        self.assertGreaterEqual(stats['amnesty_rate'], 0)
        self.assertLessEqual(stats['amnesty_rate'], 100)
        
        logger.info("✅ Статистика амнистий рассчитана")
    
    def test_amnesty_edge_cases(self):
        """Тест граничных случаев для амнистий."""
        logger.info("🧪 Тестирование граничных случаев...")
        
        # Участник с пустыми данными
        empty_participant = ParticipantData(
            address="0x0000",
            total_volume=Decimal("0"),
            transaction_count=0,
            category="Unknown",
            last_activity=None,
            balance=Decimal("0"),
            daily_purchases=[],
            eligibility_violations=[]
        )
        
        result = self.amnesty_manager.apply_amnesty(empty_participant)
        
        # Должен обработать корректно даже пустого участника
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.amnesty_granted)
        
        logger.info("✅ Граничные случаи обработаны")


def run_amnesty_tests():
    """Запуск всех тестов AmnestyManager."""
    logger.info("🚀 Начинаем расширенное тестирование AmnestyManager...")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAmnestyManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        logger.info("🎉 Все тесты AmnestyManager пройдены успешно!")
        return True
    else:
        logger.error("❌ Некоторые тесты AmnestyManager не пройдены")
        return False


if __name__ == "__main__":
    run_amnesty_tests()
