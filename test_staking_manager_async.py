"""
Проверка кнопки подключения кошелька и статуса подключения
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from core.staking_manager import StakingManager

async def test_staking_manager():
    """Тестирование StakingManager с правильной инициализацией"""
    print("🚀 Инициализация StakingManager...")
    
    sm = StakingManager()
      # Правильная асинхронная инициализация
    success = await sm.initialize()
    
    if success:
        print("✅ StakingManager инициализирован")
        print(f"🌐 Web3 подключен: {sm.web3_manager.is_connected}")
        print(f"📊 Последний блок: {sm.web3_manager.get_latest_block_number()}")
        print(f"📈 Статус системы: {sm.status}")
    else:
        print("❌ Ошибка инициализации StakingManager")

if __name__ == "__main__":
    asyncio.run(test_staking_manager())
