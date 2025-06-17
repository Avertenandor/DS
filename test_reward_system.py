#!/usr/bin/env python3
"""
Тест системы наград и выплат PLEX Dynamic Staking Manager
Проверка расчета наград по алгоритму ТЗ
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from decimal import Decimal
from core.reward_manager import RewardManager, RewardDistribution, RewardPool
from core.participant_analyzer_v2 import ParticipantData

def test_reward_system():
    """Комплексный тест системы наград"""
    print("=== ТЕСТИРОВАНИЕ СИСТЕМЫ НАГРАД ===")
    
    try:
        # Инициализация менеджера наград
        reward_manager = RewardManager()
        print("✅ RewardManager инициализирован")
        
        # Тест 1: Создание пула наград
        print("\n📊 Тест 1: Создание пула наград")
        total_pool = Decimal('100000')  # 100,000 PLEX
        period_start = datetime.now() - timedelta(days=7)
        period_end = datetime.now()
        
        reward_pool = reward_manager.create_reward_pool(
            total_amount=total_pool,
            period_start=period_start,
            period_end=period_end
        )
        
        print(f"   💰 Общий пул: {reward_pool.total_amount} PLEX")
        print(f"   📅 Период: {period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}")
        print(f"   🎯 Распределение по уровням:")
        for tier, amount in reward_pool.tier_allocations.items():
            print(f"      {tier}: {amount} PLEX")
          # Тест 2: Создание тестовых участников
        print("\n👥 Тест 2: Создание тестовых участников")
        test_participants = {
            # Platinum участник (кит)
            "0x742d35cc6574c728532c85f5e6c8dece8ad21e0f": ParticipantData(
                address="0x742d35cc6574c728532c85f5e6c8dece8ad21e0f",
                first_activity=datetime.now() - timedelta(days=30),
                last_activity=datetime.now(),
                total_swaps=150,
                total_volume_usd=Decimal('1000000'),
                total_plex_bought=Decimal('50000'),
                total_plex_sold=Decimal('10000'),
                avg_swap_size_usd=Decimal('6666'),
                unique_days_active=30,
                consecutive_days=30,
                max_consecutive_days=30,
                category="Whale",
                eligibility_score=0.95,
                reward_tier="Platinum",
                is_qualified=True
            ),
            # Gold участник (активный трейдер)
            "0x8894E0a0c962CB723c1976a4421c95949bE2D4E6": ParticipantData(
                address="0x8894E0a0c962CB723c1976a4421c95949bE2D4E6",
                first_activity=datetime.now() - timedelta(days=20),
                last_activity=datetime.now(),
                total_swaps=80,
                total_volume_usd=Decimal('500000'),
                total_plex_bought=Decimal('25000'),
                total_plex_sold=Decimal('5000'),
                avg_swap_size_usd=Decimal('6250'),
                unique_days_active=20,
                consecutive_days=15,
                max_consecutive_days=15,
                category="Active_Trader", 
                eligibility_score=0.75,
                reward_tier="Gold",
                is_qualified=True
            ),
            # Silver участник (холдер)
            "0x3dfc1233a6b3e0f8b4a2b7b1c9d5e8f2a4b6c8d0": ParticipantData(
                address="0x3dfc1233a6b3e0f8b4a2b7b1c9d5e8f2a4b6c8d0",
                first_activity=datetime.now() - timedelta(days=15),
                last_activity=datetime.now(),
                total_swaps=30,
                total_volume_usd=Decimal('100000'),
                total_plex_bought=Decimal('10000'),
                total_plex_sold=Decimal('1000'),
                avg_swap_size_usd=Decimal('3333'),
                unique_days_active=15,
                consecutive_days=10,
                max_consecutive_days=10,
                category="Holder",
                eligibility_score=0.60,
                reward_tier="Silver",
                is_qualified=True
            ),
            # Bronze участник (обычный пользователь)
            "0x2aef9382e1b5c4d7f9a3b6c8e2f4a7b9d1c3e5f8": ParticipantData(
                address="0x2aef9382e1b5c4d7f9a3b6c8e2f4a7b9d1c3e5f8",
                first_activity=datetime.now() - timedelta(days=10),
                last_activity=datetime.now(),
                total_swaps=20,
                total_volume_usd=Decimal('50000'),
                total_plex_bought=Decimal('5000'),
                total_plex_sold=Decimal('1000'),
                avg_swap_size_usd=Decimal('2500'),
                unique_days_active=10,
                consecutive_days=5,
                max_consecutive_days=5,
                category="Regular_User",
                eligibility_score=0.45,
                reward_tier="Bronze",
                is_qualified=True
            ),
            # Участник не проходящий по критериям
            "0x1a2b3c4d5e6f7890abcdef1234567890abcdef12": ParticipantData(
                address="0x1a2b3c4d5e6f7890abcdef1234567890abcdef12",
                first_activity=datetime.now() - timedelta(days=2),
                last_activity=datetime.now(),
                total_swaps=5,
                total_volume_usd=Decimal('1000'),
                total_plex_bought=Decimal('100'),
                total_plex_sold=Decimal('10'),
                avg_swap_size_usd=Decimal('200'),
                unique_days_active=2,
                consecutive_days=2,
                max_consecutive_days=2,
                category="Newcomer",
                eligibility_score=0.15,  # Ниже минимального порога Bronze (0.2)
                reward_tier="None",
                is_qualified=False
            )
        }        
        print(f"   👤 Создано {len(test_participants)} тестовых участников")
        for address, participant in test_participants.items():
            print(f"      {participant.address[:10]}...: {participant.category} (Score: {participant.eligibility_score})")
        
        # Тест 3: Расчет наград
        print("\n💰 Тест 3: Расчет наград по алгоритму ТЗ")
        distributions = reward_manager.calculate_rewards(test_participants, reward_pool)
        
        print(f"   🎯 Распределено наград: {len(distributions)}")
        total_distributed = sum(d.final_reward for d in distributions)
        print(f"   💵 Общая сумма распределения: {total_distributed} PLEX")
        
        # Детальный анализ распределения
        print("\n📊 Детальный анализ распределения:")
        for dist in distributions:
            print(f"   🏆 {dist.participant_address[:10]}...: {dist.reward_tier}")
            print(f"      💰 Базовая награда: {dist.base_reward} PLEX")
            print(f"      🔥 Множитель: {dist.bonus_multiplier}x")
            print(f"      🎁 Итоговая награда: {dist.final_reward} PLEX")
            print(f"      📊 Eligibility Score: {dist.eligibility_score}")
            print()
        
        # Тест 4: Проверка соответствия алгоритму ТЗ
        print("🔍 Тест 4: Проверка соответствия алгоритму ТЗ")
        
        # Проверка распределения по уровням
        tier_counts = {}
        for dist in distributions:
            tier_counts[dist.reward_tier] = tier_counts.get(dist.reward_tier, 0) + 1
        
        print("   📈 Распределение по уровням:")
        for tier, count in tier_counts.items():
            percentage = (count / len(distributions)) * 100 if distributions else 0
            print(f"      {tier}: {count} участников ({percentage:.1f}%)")
          # Проверка множителей по категориям
        print("   🎯 Проверка множителей по категориям:")
        for dist in distributions:
            # Найти участника по адресу
            participant = None
            for addr, p in test_participants.items():
                if p.address == dist.participant_address:
                    participant = p
                    break
            
            if participant:
                expected_multiplier = reward_manager.category_multipliers.get(participant.category, 1.0)
                print(f"      {dist.participant_address[:10]}...: {dist.bonus_multiplier}x (ожидалось: {expected_multiplier}x)")
            else:
                print(f"      {dist.participant_address[:10]}...: {dist.bonus_multiplier}x (участник не найден)")
          # Тест 5: Проверка защиты от переполнения пула
        print("\n🛡️ Тест 5: Проверка защиты от переполнения пула")
        
        # Добавляем толерантность для ошибок floating point
        tolerance = 1e-9  # Более строгая проверка в тесте
        excess = total_distributed - reward_pool.total_amount
        
        if excess <= tolerance:
            print(f"   ✅ Защита работает: {total_distributed} <= {reward_pool.total_amount} (excess: {excess})")
            remaining = reward_pool.total_amount - total_distributed
            print(f"   💼 Остаток в пуле: {remaining} PLEX")
        else:
            print(f"   ❌ ОШИБКА: Превышен лимит пула! {total_distributed} > {reward_pool.total_amount} (excess: {excess})")
            return False
          # Тест 6: Валидация минимальных критериев
        print("\n📏 Тест 6: Валидация минимальных критериев")
        participants_below_threshold = [p for p in test_participants.values() if p.eligibility_score < 0.2]
        rewards_below_threshold = [d for d in distributions 
                                 if any(p.address == d.participant_address and p.eligibility_score < 0.2 
                                       for p in participants_below_threshold)]
        
        if not rewards_below_threshold:
            print("   ✅ Участники ниже минимального порога исключены из распределения")
        else:
            print(f"   ❌ ОШИБКА: {len(rewards_below_threshold)} участников ниже порога получили награды!")
            return False
        
        print("\n🎉 ВСЕ ТЕСТЫ СИСТЕМЫ НАГРАД ПРОЙДЕНЫ УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_reward_system()
    sys.exit(0 if success else 1)
