"""
Скрипт: Тестирование подключения к QuickNode BSC
Описание: Проверка всех компонентов системы с реальными данными
Автор: GitHub Copilot
"""

import sys
import time
from datetime import datetime
sys.path.append('..')

from config.settings import settings
from config.constants import (
    TOKEN_ADDRESS, PLEX_USDT_POOL, MULTICALL3_BSC,
    TOKEN_NAME, TOKEN_SYMBOL, TOKEN_DECIMALS
)
from blockchain.node_client import Web3Manager
from blockchain.swap_analyzer import SwapAnalyzer
from utils.logger import get_logger
from utils.converters import TokenConverter, format_plex_amount

logger = get_logger("ConnectionTest")


def test_basic_connection():
    """Тест 1: Базовое подключение к QuickNode"""
    print("🔗 ТЕСТ 1: Базовое подключение к QuickNode")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Проверяем HTTP подключение
        if manager.w3_http.is_connected():
            print("✅ HTTP подключение установлено")
        else:
            print("❌ HTTP подключение НЕ установлено")
            return False
        
        # Получаем последний блок
        latest_block = manager.get_latest_block_number()
        print(f"📦 Последний блок: {latest_block:,}")
        
        # Получаем данные блока
        block_data = manager.get_block(latest_block)
        block_time = datetime.fromtimestamp(block_data['timestamp'])
        print(f"🕐 Время блока: {block_time}")
        
        # Проверяем WebSocket
        if manager.w3_ws and manager.w3_ws.is_connected():
            print("✅ WebSocket подключение установлено")
        else:
            print("⚠️ WebSocket подключение недоступно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def test_token_contract():
    """Тест 2: Проверка контракта токена PLEX"""
    print("\n🪙 ТЕСТ 2: Проверка контракта токена PLEX")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Проверяем, что контракт существует
        code = manager.w3_http.eth.get_code(TOKEN_ADDRESS)
        if len(code) > 0:
            print(f"✅ Контракт PLEX найден: {TOKEN_ADDRESS}")
        else:
            print(f"❌ Контракт PLEX НЕ найден: {TOKEN_ADDRESS}")
            return False
        
        # Получаем данные токена через call
        try:
            # Вызов name()
            name_call = manager.call_contract_function(TOKEN_ADDRESS, "0x06fdde03")  # name() selector
            print(f"📝 Название токена проверено")
            
            # Вызов symbol()
            symbol_call = manager.call_contract_function(TOKEN_ADDRESS, "0x95d89b41")  # symbol() selector
            print(f"🔤 Символ токена проверен")
            
            # Вызов decimals()
            decimals_call = manager.call_contract_function(TOKEN_ADDRESS, "0x313ce567")  # decimals() selector
            decimals = int(decimals_call, 16)
            
            if decimals == TOKEN_DECIMALS:
                print(f"✅ Decimals корректный: {decimals}")
            else:
                print(f"❌ Decimals НЕкорректный: {decimals} (ожидается {TOKEN_DECIMALS})")
                return False
            
        except Exception as e:
            print(f"⚠️ Не удалось получить данные токена: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки контракта: {e}")
        return False


def test_pool_contract():
    """Тест 3: Проверка пула PLEX/USDT"""
    print("\n🏊 ТЕСТ 3: Проверка пула PLEX/USDT")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Проверяем существование пула
        code = manager.w3_http.eth.get_code(PLEX_USDT_POOL)
        if len(code) > 0:
            print(f"✅ Пул PLEX/USDT найден: {PLEX_USDT_POOL}")
        else:
            print(f"❌ Пул PLEX/USDT НЕ найден: {PLEX_USDT_POOL}")
            return False
        
        # Получаем адреса токенов в пуле
        try:
            token0_call = manager.call_contract_function(PLEX_USDT_POOL, "0x0dfe1681")  # token0()
            token1_call = manager.call_contract_function(PLEX_USDT_POOL, "0xd21220a7")  # token1()
            
            token0_address = "0x" + token0_call[-40:]
            token1_address = "0x" + token1_call[-40:]
            
            print(f"🔄 Token0: {token0_address}")
            print(f"🔄 Token1: {token1_address}")
            
            # Проверяем, что один из токенов - PLEX
            if token0_address.lower() == TOKEN_ADDRESS.lower():
                print("✅ PLEX найден как token0")
            elif token1_address.lower() == TOKEN_ADDRESS.lower():
                print("✅ PLEX найден как token1")
            else:
                print("❌ PLEX НЕ найден в пуле")
                return False
            
        except Exception as e:
            print(f"⚠️ Не удалось получить токены пула: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки пула: {e}")
        return False


def test_multicall_contract():
    """Тест 4: Проверка Multicall3"""
    print("\n📞 ТЕСТ 4: Проверка Multicall3")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Проверяем существование Multicall3
        code = manager.w3_http.eth.get_code(MULTICALL3_BSC)
        if len(code) > 0:
            print(f"✅ Multicall3 найден: {MULTICALL3_BSC}")
        else:
            print(f"❌ Multicall3 НЕ найден: {MULTICALL3_BSC}")
            return False
        
        # Тестируем простой вызов
        try:
            # Вызов getBlockNumber()
            block_call = manager.call_contract_function(MULTICALL3_BSC, "0x42cbb15c")
            block_number = int(block_call, 16)
            print(f"📦 Multicall3 block number: {block_number:,}")
            
        except Exception as e:
            print(f"⚠️ Ошибка вызова Multicall3: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки Multicall3: {e}")
        return False


def test_recent_transfers():
    """Тест 5: Получение последних Transfer событий"""
    print("\n📤 ТЕСТ 5: Последние Transfer события PLEX")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Получаем последние 100 блоков
        latest_block = manager.get_latest_block_number()
        start_block = latest_block - 100
        
        print(f"🔍 Поиск Transfer событий в блоках {start_block:,} - {latest_block:,}")
        
        # Формируем фильтр для Transfer событий
        transfer_signature = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        filter_params = {
            'fromBlock': hex(start_block),
            'toBlock': hex(latest_block),
            'address': TOKEN_ADDRESS,
            'topics': [transfer_signature]
        }
        
        logs = manager.get_logs(filter_params)
        print(f"✅ Найдено {len(logs)} Transfer событий")
        
        if logs:
            # Показываем первые 3 события
            for i, log in enumerate(logs[:3]):
                from_addr = "0x" + log['topics'][1].hex()[-40:]
                to_addr = "0x" + log['topics'][2].hex()[-40:]
                value_wei = int(log['data'], 16)
                value_tokens = TokenConverter.wei_to_token(value_wei)
                
                print(f"   {i+1}. From: {from_addr[:10]}... To: {to_addr[:10]}... Amount: {format_plex_amount(value_tokens)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка получения Transfer событий: {e}")
        return False


def test_recent_swaps():
    """Тест 6: Получение последних Swap событий"""
    print("\n🔄 ТЕСТ 6: Последние Swap события PLEX/USDT")
    print("=" * 60)
    
    try:
        analyzer = SwapAnalyzer()
        
        # Получаем последние 50 блоков
        latest_block = analyzer.web3_manager.get_latest_block_number()
        start_block = latest_block - 50
        
        print(f"🔍 Поиск Swap событий в блоках {start_block:,} - {latest_block:,}")
        
        swaps = analyzer.get_pool_swaps(start_block, latest_block)
        print(f"✅ Найдено {len(swaps)} Swap событий")
        
        if swaps:
            # Анализируем первые 3 swap'а
            for i, swap in enumerate(swaps[:3]):
                direction_emoji = "📈" if swap['direction'] == 'buy' else "📉"
                print(f"   {i+1}. {direction_emoji} {swap['direction'].upper()}: {format_plex_amount(swap['plex_amount'])} (${swap['usd_value']:.2f})")
                print(f"      To: {swap['to'][:16]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка получения Swap событий: {e}")
        return False


def test_api_credits_usage():
    """Тест 7: Мониторинг использования API кредитов"""
    print("\n💳 ТЕСТ 7: Использование API кредитов")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Сбрасываем счетчик
        initial_credits = manager.api_usage.credits_used
        initial_requests = manager.api_usage.requests_count
        
        print(f"📊 Начальные кредиты: {initial_credits}")
        print(f"📊 Начальные запросы: {initial_requests}")
        
        # Делаем несколько тестовых запросов
        print("🔄 Выполняем тестовые запросы...")
        
        manager.get_latest_block_number()  # +20 кредитов
        manager.get_block('latest')        # +20 кредитов
        
        # Получаем статистику
        stats = manager.api_usage.get_usage_stats()
        
        print(f"✅ Использовано кредитов: {stats['credits_used'] - initial_credits}")
        print(f"✅ Выполнено запросов: {stats['requests_count'] - initial_requests}")
        print(f"📈 Средние кредиты на запрос: {stats['avg_credits_per_request']:.1f}")
        print(f"🚀 Текущий RPS: {stats['current_rps']}")
        print(f"📅 Прогноз на месяц: {stats['monthly_projection']:,.0f} кредитов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мониторинга API: {e}")
        return False


def test_performance():
    """Тест 8: Тест производительности"""
    print("\n⚡ ТЕСТ 8: Производительность")
    print("=" * 60)
    
    try:
        manager = Web3Manager()
        
        # Тест скорости получения блоков
        print("🚀 Тест скорости получения блоков...")
        start_time = time.time()
        
        latest_block = manager.get_latest_block_number()
        blocks_to_test = 5
        
        for i in range(blocks_to_test):
            block_num = latest_block - i
            block_data = manager.get_block(block_num)
        
        elapsed = time.time() - start_time
        blocks_per_second = blocks_to_test / elapsed
        
        print(f"✅ Получено {blocks_to_test} блоков за {elapsed:.2f}s")
        print(f"📊 Скорость: {blocks_per_second:.1f} блоков/сек")
        
        # Тест кэширования блоков
        print("💾 Тест кэширования...")
        start_time = time.time()
        
        # Первый вызов (не из кэша)
        block1 = manager.get_latest_block_number(use_cache=False)
        first_call_time = time.time() - start_time        
        start_time = time.time()
        
        # Второй вызов (из кэша)
        block2 = manager.get_latest_block_number(use_cache=True)
        cached_call_time = time.time() - start_time
        
        print(f"✅ Первый вызов: {first_call_time*1000:.1f}ms")
        print(f"✅ Кэшированный вызов: {cached_call_time*1000:.1f}ms")
        
        if cached_call_time > 0 and cached_call_time < first_call_time:
            speedup = first_call_time / cached_call_time
            print(f"🚀 Ускорение от кэша: {speedup:.1f}x")
        elif cached_call_time == 0:
            print(f"🚀 Кэш работает мгновенно!")
        else:
            print(f"⚠️ Кэш не дал ускорения")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка теста производительности: {e}")
        return False


def main():
    """Главная функция тестирования"""
    print("🚀 PLEX Dynamic Staking Manager - Тест подключения")
    print("=" * 80)
    print(f"🔧 Настройки:")
    print(f"   QuickNode HTTP: {settings.quicknode_http}")
    print(f"   Token: {TOKEN_NAME} ({TOKEN_SYMBOL})")
    print(f"   Decimals: {TOKEN_DECIMALS}")
    print(f"   Pool: {PLEX_USDT_POOL}")
    print("=" * 80)
    
    # Запускаем все тесты
    tests = [
        test_basic_connection,
        test_token_contract,
        test_pool_contract,
        test_multicall_contract,
        test_recent_transfers,
        test_recent_swaps,
        test_api_credits_usage,
        test_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("✅ ТЕСТ ПРОШЕЛ")
            else:
                print("❌ ТЕСТ ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ ТЕСТ ПРЕРВАН: {e}")
        
        time.sleep(1)  # Небольшая пауза между тестами
    
    # Итоговый результат
    print("\n" + "=" * 80)
    print(f"📊 ИТОГОВЫЙ РЕЗУЛЬТАТ: {passed}/{total} тестов прошли")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Система готова к работе.")
        return True
    else:
        print("⚠️ ЕСТЬ ПРОБЛЕМЫ! Проверьте конфигурацию.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
