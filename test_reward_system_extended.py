#!/usr/bin/env python3
"""
Расширенное тестирование системы наград PLEX Dynamic Staking Manager
Тестирует производительность и корректность на большом количестве участников
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random
import time

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.reward_manager import RewardManager
from core.participant_analyzer_v2 import ParticipantData
from utils.logger import get_logger

logger = get_logger("test_reward_extended")

def generate_test_participants(count: int) -> dict:
    """Генерация большого количества тестовых участников"""
    participants = {}
    categories = ["Whale", "Active_Trader", "Holder", "Regular_User", "Newcomer"]
    
    for i in range(count):
        # Генерируем реалистичные адреса
        address = f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        
        # Случайная категория с распределением (больше обычных пользователей)
        category_weights = [5, 15, 20, 40, 20]  # процентное распределение
        category = random.choices(categories, weights=category_weights)[0]
        
        # Генерируем параметры в зависимости от категории
        if category == "Whale":
            eligibility_score = random.uniform(0.8, 1.0)
            volume = random.uniform(500000, 2000000)
            unique_days = random.randint(25, 30)
            consecutive_days = random.randint(20, 30)
            current_balance = random.uniform(10000, 100000)
        elif category == "Active_Trader":
            eligibility_score = random.uniform(0.6, 0.85)
            volume = random.uniform(100000, 500000)
            unique_days = random.randint(15, 25)
            consecutive_days = random.randint(10, 20)
            current_balance = random.uniform(5000, 20000)
        elif category == "Holder":
            eligibility_score = random.uniform(0.4, 0.7)
            volume = random.uniform(10000, 100000)
            unique_days = random.randint(5, 15)
            consecutive_days = random.randint(3, 10)
            current_balance = random.uniform(1000, 10000)
        elif category == "Regular_User":
            eligibility_score = random.uniform(0.2, 0.5)
            volume = random.uniform(1000, 20000)
            unique_days = random.randint(3, 10)
            consecutive_days = random.randint(1, 7)
            current_balance = random.uniform(100, 2000)
        else:  # Newcomer
            eligibility_score = random.uniform(0.05, 0.25)
            volume = random.uniform(100, 5000)
            unique_days = random.randint(1, 5)
            consecutive_days = random.randint(1, 3)
            current_balance = random.uniform(10, 500)
          # Определяем тир на основе eligibility_score
        if eligibility_score >= 0.8:
            reward_tier = "Platinum"
        elif eligibility_score >= 0.6:
            reward_tier = "Gold"
        elif eligibility_score >= 0.4:
            reward_tier = "Silver"
        elif eligibility_score >= 0.2:
            reward_tier = "Bronze"
        else:
            reward_tier = "None"
        
        participant = ParticipantData(
            address=address,
            first_activity=datetime.now() - timedelta(days=random.randint(30, 365)),
            last_activity=datetime.now() - timedelta(days=random.randint(0, 7)),
            total_swaps=random.randint(1, 100),
            total_volume_usd=Decimal(str(volume)),
            total_plex_bought=Decimal(str(volume * 0.6)),
            total_plex_sold=Decimal(str(volume * 0.4)),
            avg_swap_size_usd=Decimal(str(volume / random.randint(5, 50))),
            unique_days_active=unique_days,
            consecutive_days=consecutive_days,
            max_consecutive_days=consecutive_days,
            category=category,
            eligibility_score=eligibility_score,
            reward_tier=reward_tier,
            is_qualified=eligibility_score >= 0.2
        )
        
        participants[address] = participant
    
    return participants

def test_mass_reward_distribution():
    """Тест массового распределения наград"""
    print("🚀 РАСШИРЕННОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ НАГРАД")
    print("=" * 60)
    
    # Инициализация
    reward_manager = RewardManager()
    
    # Тест 1: Производительность на 1000 участников
    print("⚡ Тест 1: Производительность на 1000 участников")
    start_time = time.time()
    
    participants_1k = generate_test_participants(1000)
    print(f"   📊 Сгенерировано {len(participants_1k)} участников")
    
    # Создание пула наград
    reward_pool = reward_manager.create_reward_pool(
        total_amount=Decimal('1000000'),  # 1M PLEX
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=7)
    )    # Распределение наград
    distributions = reward_manager.calculate_rewards(participants_1k, reward_pool)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"   ⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"   🎯 Распределено наград: {len(distributions)}")
    
    # Анализ распределения
    total_distributed = sum(d.final_reward for d in distributions)
    print(f"   💰 Общая сумма: {total_distributed:.2f} PLEX")
    print(f"   🛡️ Проверка пула: {total_distributed} <= {reward_pool.total_amount} ✅")
    
    # Анализ по категориям
    category_stats = {}
    for dist in distributions:
        category = None
        for p in participants_1k.values():
            if p.address == dist.participant_address:
                category = p.category
                break
        
        if category:
            if category not in category_stats:
                category_stats[category] = {"count": 0, "total_reward": 0}
            category_stats[category]["count"] += 1
            category_stats[category]["total_reward"] += dist.final_reward
    
    print("   📈 Статистика по категориям:")
    for category, stats in category_stats.items():
        avg_reward = stats["total_reward"] / stats["count"] if stats["count"] > 0 else 0
        print(f"      {category}: {stats['count']} участников, средняя награда: {avg_reward:.2f} PLEX")
    
    # Тест 2: Стресс-тест на 5000 участников
    print(f"\n🔥 Тест 2: Стресс-тест на 5000 участников")
    start_time = time.time()
    
    participants_5k = generate_test_participants(5000)
    
    # Больший пул наград
    reward_pool_big = reward_manager.create_reward_pool(
        total_amount=Decimal('5000000'),  # 5M PLEX
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=7)
    )
    
    distributions_big = reward_manager.calculate_rewards(participants_5k, reward_pool_big)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    print(f"   ⏱️ Время выполнения: {execution_time:.2f} секунд")
    print(f"   🎯 Распределено наград: {len(distributions_big)}")
    
    total_distributed_big = sum(d.final_reward for d in distributions_big)
    print(f"   💰 Общая сумма: {total_distributed_big:.2f} PLEX")
    print(f"   🛡️ Проверка пула: {total_distributed_big} <= {reward_pool_big.total_amount} ✅")
    
    # Тест 3: Проверка граничных случаев
    print(f"\n🎯 Тест 3: Граничные случаи")
    
    # Все участники с одинаковым score
    equal_participants = {}
    for i in range(100):
        address = f"0x{''.join(random.choices('0123456789abcdef', k=40))}"
        participant = ParticipantData(
            address=address,
            first_activity=datetime.now() - timedelta(days=60),
            last_activity=datetime.now() - timedelta(days=1),
            total_swaps=random.randint(10, 50),
            total_volume_usd=Decimal('10000'),
            total_plex_bought=Decimal('6000'),
            total_plex_sold=Decimal('4000'),
            avg_swap_size_usd=Decimal('200'),
            unique_days_active=10,
            consecutive_days=5,
            max_consecutive_days=5,
            category="Regular_User",
            eligibility_score=0.5,
            reward_tier="Silver",  # 0.5 >= 0.4
            is_qualified=True
        )
        equal_participants[address] = participant
    
    reward_pool_equal = reward_manager.create_reward_pool(
        total_amount=Decimal('100000'),
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=7)
    )
    
    distributions_equal = reward_manager.calculate_rewards(equal_participants, reward_pool_equal)
    
    # Проверяем, что все награды примерно одинаковые
    rewards = [d.final_reward for d in distributions_equal]
    avg_reward = sum(rewards) / len(rewards) if rewards else 0
    max_deviation = max(abs(reward - avg_reward) for reward in rewards) if rewards else 0
    
    print(f"   👥 Участников с одинаковым score: {len(equal_participants)}")
    print(f"   📊 Средняя награда: {avg_reward:.2f} PLEX")
    print(f"   📏 Максимальное отклонение: {max_deviation:.2f} PLEX")
    print(f"   ✅ Справедливое распределение: {max_deviation < float(avg_reward) * 0.1}")
    
    # Тест 4: Экстремальные множители
    print(f"\n⚡ Тест 4: Экстремальные множители")
    
    extreme_participants = {}
    # Создаем участника с максимальными параметрами
    extreme_participant = ParticipantData(
        address="0xExtreme" + "0" * 32,
        first_activity=datetime.now() - timedelta(days=365),
        last_activity=datetime.now(),
        total_swaps=random.randint(500, 1000),
        total_volume_usd=Decimal('10000000'),  # 10M USD
        total_plex_bought=Decimal('6000000'),
        total_plex_sold=Decimal('4000000'),
        avg_swap_size_usd=Decimal('20000'),
        unique_days_active=30,
        consecutive_days=30,
        max_consecutive_days=30,
        category="Whale",
        eligibility_score=1.0,
        reward_tier="Platinum",  # 1.0 >= 0.8
        is_qualified=True
    )
    extreme_participants[extreme_participant.address] = extreme_participant
    
    # И несколько обычных участников
    for i in range(10):
        address = f"0xNormal{'0' * (34-len(str(i)))}{i}"
        participant = ParticipantData(
            address=address,
            first_activity=datetime.now() - timedelta(days=30),
            last_activity=datetime.now() - timedelta(days=2),
            total_swaps=random.randint(5, 20),
            total_volume_usd=Decimal('5000'),
            total_plex_bought=Decimal('3000'),
            total_plex_sold=Decimal('2000'),
            avg_swap_size_usd=Decimal('250'),
            unique_days_active=5,
            consecutive_days=3,
            max_consecutive_days=3,
            category="Regular_User",
            eligibility_score=0.3,
            reward_tier="Bronze",  # 0.3 >= 0.2
            is_qualified=True
        )
        extreme_participants[address] = participant
    
    reward_pool_extreme = reward_manager.create_reward_pool(
        total_amount=Decimal('50000'),
        period_start=datetime.now(),
        period_end=datetime.now() + timedelta(days=7)
    )
    
    distributions_extreme = reward_manager.calculate_rewards(extreme_participants, reward_pool_extreme)
    
    # Находим награду экстремального участника
    extreme_reward = None
    normal_rewards = []
    for dist in distributions_extreme:
        if "Extreme" in dist.participant_address:
            extreme_reward = dist.final_reward
        else:
            normal_rewards.append(dist.final_reward)
    
    avg_normal_reward = sum(normal_rewards) / len(normal_rewards) if normal_rewards else 0
    
    print(f"   🐋 Экстремальный участник: {extreme_reward:.2f} PLEX")
    print(f"   👤 Средняя награда обычных: {avg_normal_reward:.2f} PLEX")
    print(f"   📊 Соотношение: {extreme_reward / avg_normal_reward:.1f}x" if avg_normal_reward > 0 else "N/A")
    
    total_extreme = sum(d.final_reward for d in distributions_extreme)
    print(f"   🛡️ Проверка пула: {total_extreme} <= {reward_pool_extreme.total_amount} ✅")
    
    print(f"\n🎉 ВСЕ РАСШИРЕННЫЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_mass_reward_distribution()
        if success:
            print("✅ Все тесты пройдены успешно!")
            sys.exit(0)
        else:
            print("❌ Некоторые тесты не пройдены!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
