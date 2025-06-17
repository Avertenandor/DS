#!/usr/bin/env python3
"""
Тест подключения к BSC ноде.
"""

import os
import sys
sys.path.insert(0, '.')

def test_node_connection():
    """Тест подключения к ноде."""
    try:
        # Загрузка переменных окружения
        from dotenv import load_dotenv
        load_dotenv()
        
        rpc_url = os.getenv('QUICKNODE_HTTP')
        print(f"🔗 RPC URL: {rpc_url}")
        
        if not rpc_url:
            print("❌ RPC URL не найден в переменных окружения")
            return
        
        # Тест подключения
        from blockchain.node_client import Web3Manager
        
        print("🚀 Создание Web3Manager...")
        w3_manager = Web3Manager()
        
        print("📡 Получение последнего блока...")
        latest_block = w3_manager.get_latest_block_number()
        
        if latest_block and latest_block > 0:
            print(f"✅ Подключение успешно! Последний блок: {latest_block}")
            print(f"🌐 Сеть: BSC Mainnet")
        else:
            print("❌ Не удалось получить номер блока")
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Тестирование подключения к BSC ноде...")
    test_node_connection()
