#!/usr/bin/env python3
"""
Быстрый тест инициализации всех компонентов
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_components():
    print("=== ТЕСТИРОВАНИЕ ИНИЦИАЛИЗАЦИИ КОМПОНЕНТОВ ===")
    
    try:        # Web3Manager
        from blockchain.node_client import Web3Manager
        web3_manager = Web3Manager()
        print("✅ Web3Manager: OK")
          # GasManager
        from blockchain.gas_manager import GasManager
        gas_manager = GasManager(web3_manager)
        print("✅ GasManager: OK")
        
        # StakingManager
        from core.staking_manager import StakingManager
        staking_manager = StakingManager()
        print("✅ StakingManager: OK")
        
        # TransferCollector
        from blockchain.transfer_collector import TransferCollector
        transfer_collector = TransferCollector(web3_manager)
        print("✅ TransferCollector: OK")
        
        # SwapAnalyzer
        from blockchain.swap_analyzer import SwapAnalyzer
        swap_analyzer = SwapAnalyzer(web3_manager)
        print("✅ SwapAnalyzer: OK")
        
        # SimpleAnalyzer
        from core.simple_analyzer import SimpleAnalyzer
        simple_analyzer = SimpleAnalyzer()
        print("✅ SimpleAnalyzer: OK")
        
        print("\n🎉 ВСЕ КОМПОНЕНТЫ ИНИЦИАЛИЗИРОВАНЫ УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_components()
    sys.exit(0 if success else 1)
