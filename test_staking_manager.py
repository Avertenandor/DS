"""
Быстрая проверка статуса StakingManager
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.staking_manager import StakingManager
    
    print("🚀 Инициализация StakingManager...")
    sm = StakingManager()
    
    print(f"✅ StakingManager инициализирован")
    print(f"🌐 Web3 подключен: {sm.web3_manager.is_connected()}")
    print(f"📊 Последний блок: {sm.web3_manager.get_latest_block_number()}")
    print(f"💰 Token address: {sm.token_address}")
    print(f"🏭 Pool address: {sm.pool_address}")
    
except Exception as e:
    print(f"❌ Ошибка инициализации StakingManager: {e}")
    import traceback
    traceback.print_exc()
