"""
Модуль: Анализатор PancakeSwap операций для PLEX/USDT пула
Описание: Сбор и анализ Swap событий, определение покупок/продаж, расчет USD стоимости
Зависимости: web3, decimal
Автор: GitHub Copilot
"""

import time
from typing import List, Dict, Optional, Tuple, Set
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
from web3 import Web3

from config.constants import (
    PLEX_USDT_POOL, TOKEN_ADDRESS, USDT_BSC, TOKEN_DECIMALS,
    SWAP_EVENT_SIGNATURE, DAILY_PURCHASE_MIN, DAILY_PURCHASE_MAX
)
from blockchain.node_client import get_web3_manager
from utils.logger import get_logger
from utils.retry import api_call_retry, critical_operation_retry
from utils.validators import SwapDataValidator, AddressValidator
from utils.converters import TokenConverter, PriceConverter, TimeConverter
from utils.cache_manager import block_cache, smart_cache
from utils.chunk_strategy import AdaptiveChunkStrategy, ProgressiveChunkManager
from utils.multicall_manager import MulticallManager

logger = get_logger("SwapAnalyzer")


# Глобальная стратегия чанкования
chunk_strategy = AdaptiveChunkStrategy(
    initial_chunk_size=1000,  # Уменьшаем начальный размер
    max_logs_per_request=500,  # Уменьшаем лимит логов
    min_chunk_size=50,
    max_chunk_size=2000
)


class SwapEventProcessor:
    """Обработчик событий Swap"""
    
    def __init__(self):
        self.token0_is_plex = None  # Будет определено при первом вызове
        self.usdt_decimals = 18
        
    def _determine_token_order(self) -> bool:
        """Определить порядок токенов в пуле (token0/token1)"""
        if self.token0_is_plex is not None:
            return self.token0_is_plex
        
        try:
            web3_manager = get_web3_manager()
            
            # Получаем адреса токенов из пула
            # Вызываем token0() и token1() функции
            token0_call = web3_manager.call_contract_function(
                PLEX_USDT_POOL,
                "0x0dfe1681"  # token0() selector
            )
            
            token1_call = web3_manager.call_contract_function(
                PLEX_USDT_POOL,
                "0xd21220a7"  # token1() selector
            )
            
            # Декодируем адреса
            token0_address = Web3.to_checksum_address("0x" + token0_call[-40:])
            token1_address = Web3.to_checksum_address("0x" + token1_call[-40:])
            
            # Определяем, какой токен PLEX
            self.token0_is_plex = (token0_address.lower() == TOKEN_ADDRESS.lower())
            
            logger.info(f"🔍 Pool tokens: token0={token0_address}, token1={token1_address}")
            logger.info(f"🔍 Token0 is PLEX: {self.token0_is_plex}")
            
            return self.token0_is_plex
            
        except Exception as e:
            logger.error(f"❌ Error determining token order: {e}")
            # Предполагаем что PLEX = token1 (обычная практика)
            self.token0_is_plex = False
            return False
    
    def process_swap_log(self, log: Dict) -> Optional[Dict]:
        """Обработать лог события Swap"""
        try:            # Проверяем, что это правильное событие
            topic0 = log['topics'][0]
            if isinstance(topic0, str):
                signature = topic0
            else:
                signature = topic0.hex()
                
            if signature != SWAP_EVENT_SIGNATURE:
                return None
              # Декодируем данные из topics
            try:
                # sender - topic[1]
                if len(log['topics']) > 1:
                    topic1 = log['topics'][1]
                    if isinstance(topic1, str):
                        sender_hex = topic1[2:] if topic1.startswith('0x') else topic1
                    else:
                        sender_hex = topic1.hex()
                    sender = Web3.to_checksum_address("0x" + sender_hex[-40:])
                else:
                    sender = "0x" + "0" * 40
                
                # to - topic[2]
                if len(log['topics']) > 2:
                    topic2 = log['topics'][2]
                    if isinstance(topic2, str):
                        to_hex = topic2[2:] if topic2.startswith('0x') else topic2
                    else:
                        to_hex = topic2.hex()
                    to = Web3.to_checksum_address("0x" + to_hex[-40:])
                else:
                    to = "0x" + "0" * 40
                    
            except Exception as e:
                logger.error(f"❌ Error parsing topics: {e}")
                sender = "0x" + "0" * 40
                to = "0x" + "0" * 40
              # Декодируем amounts из data
            data = log['data']
            if isinstance(data, str):
                data = data[2:] if data.startswith('0x') else data  # Убираем 0x
            else:
                data = data.hex()
            
            # Каждое значение uint256 занимает 64 hex символа (32 байта)
            try:
                amount0_in = int(data[0:64], 16) if len(data) >= 64 else 0
                amount1_in = int(data[64:128], 16) if len(data) >= 128 else 0
                amount0_out = int(data[128:192], 16) if len(data) >= 192 else 0
                amount1_out = int(data[192:256], 16) if len(data) >= 256 else 0
            except ValueError as ve:
                logger.error(f"❌ Error parsing hex amounts: {ve}, data length: {len(data)}")
                return None
              # Получаем transaction hash
            tx_hash = log['transactionHash']
            if isinstance(tx_hash, str):
                tx_hash_str = tx_hash
            else:
                tx_hash_str = tx_hash.hex()
                
            # Валидация swap данных
            if not SwapDataValidator.validate_swap_amounts(amount0_in, amount1_in, amount0_out, amount1_out):
                logger.warning(f"⚠️ Invalid swap amounts in tx {tx_hash_str}")
                return None
            
            # Определяем направление
            token0_is_plex = self._determine_token_order()
            direction = SwapDataValidator.determine_swap_direction(
                amount0_in, amount1_in, amount0_out, amount1_out, token0_is_plex
            )
            
            # Рассчитываем USD стоимость
            usd_value = SwapDataValidator.calculate_usd_value(
                amount0_in, amount1_in, amount0_out, amount1_out, not token0_is_plex
            )
              # Определяем количество PLEX
            if token0_is_plex:
                plex_amount = amount0_out if amount0_out > 0 else amount0_in
            else:
                plex_amount = amount1_out if amount1_out > 0 else amount1_in
            
            plex_tokens = TokenConverter.wei_to_token(plex_amount)
            
            return {
                "transaction_hash": tx_hash_str,
                "block_number": log['blockNumber'],
                "log_index": log['logIndex'],
                "sender": sender,
                "to": to,
                "direction": direction,  # "buy" или "sell"
                "plex_amount": plex_tokens,
                "usd_value": usd_value,
                "amount0_in": amount0_in,
                "amount1_in": amount1_in,
                "amount0_out": amount0_out,
                "amount1_out": amount1_out,
                "timestamp": None  # Будет заполнено позже
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing swap log: {e}")
            return None


class SwapAnalyzer:
    """Главный анализатор PancakeSwap операций"""
    
    def __init__(self, web3_manager=None):
        self.web3_manager = web3_manager or get_web3_manager()
        self.chunk_strategy = AdaptiveChunkStrategy()
        self.swap_processor = SwapEventProcessor()
        self.processed_blocks = set()
        self.swap_cache = {}  # Кэш обработанных swap'ов
    
    @critical_operation_retry()
    def get_pool_swaps(self, start_block: int, end_block: int) -> List[Dict]:
        """Получить swap события из пула за диапазон блоков с оптимизацией"""
        
        blocks_count = end_block - start_block + 1
        logger.info(f"📊 Collecting swaps from blocks {start_block:,} to {end_block:,}")
        
        # Проверяем кэш сначала
        cache_key = f"swaps:{PLEX_USDT_POOL}:{start_block}:{end_block}"
        cached_swaps = smart_cache.get(cache_key)
        
        if cached_swaps is not None:
            logger.info(f"📦 Возвращено {len(cached_swaps)} swap'ов из кэша")
            return cached_swaps
        
        try:
            # Используем адаптивную стратегию чанкования для больших диапазонов
            if blocks_count > 1000:
                return self._get_swaps_with_chunking(start_block, end_block)
            
            # Для небольших диапазонов - прямой запрос
            filter_params = {
                'fromBlock': hex(start_block),
                'toBlock': hex(end_block),
                'address': Web3.to_checksum_address(PLEX_USDT_POOL),
                'topics': [SWAP_EVENT_SIGNATURE]
            }
            
            logs = self.web3_manager.get_logs(filter_params)
            
            # Парсим события
            processed_swaps = []
            for log in logs:
                swap_data = self.swap_processor.process_swap_log(log)
                if swap_data:
                    processed_swaps.append(swap_data)
            
            # Сохраняем в кэш
            smart_cache.set(cache_key, processed_swaps, ttl=300)
            
            logger.info(f"✅ Processed {len(processed_swaps)} swaps from {len(logs)} logs")
            return processed_swaps
            
        except Exception as e:
            if "payload too large" in str(e).lower():
                logger.error(f"❌ Payload too large for blocks {start_block}-{end_block}")
                # Автоматически уменьшаем размер чанка
                new_size = chunk_strategy.handle_payload_too_large(blocks_count)
                logger.warning(f"🚨 Предлагаемый новый размер чанка: {new_size}")
                raise Exception("Payload too large - reduce block range")
            else:
                raise e
    
    def _get_swaps_with_chunking(self, start_block: int, end_block: int) -> List[Dict]:
        """Получить swap'ы с использованием адаптивного чанкования"""
        
        def fetch_chunk_swaps(chunk_start: int, chunk_end: int) -> List[Dict]:
            """Получить swap'ы для одного чанка"""
            try:
                start_time = time.time()
                
                filter_params = {
                    'fromBlock': hex(chunk_start),
                    'toBlock': hex(chunk_end),
                    'address': Web3.to_checksum_address(PLEX_USDT_POOL),
                    'topics': [SWAP_EVENT_SIGNATURE]
                }
                
                logs = self.web3_manager.get_logs(filter_params)
                
                processed_swaps = []
                for log in logs:
                    swap_data = self.swap_processor.process_swap_log(log)
                    if swap_data:
                        processed_swaps.append(swap_data)
                
                # Записываем результат в стратегию
                execution_time = time.time() - start_time
                chunk_strategy.record_result(
                    chunk_size=chunk_end - chunk_start + 1,
                    logs_count=len(logs),
                    execution_time=execution_time,
                    success=True,
                    contract_address=PLEX_USDT_POOL
                )
                
                return processed_swaps
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_type = 'payload_too_large' if '413' in str(e) else 'unknown'
                
                chunk_strategy.record_result(
                    chunk_size=chunk_end - chunk_start + 1,
                    logs_count=0,
                    execution_time=execution_time,
                    success=False,
                    error_type=error_type,
                    contract_address=PLEX_USDT_POOL
                )
                
                if '413' in str(e) or 'payload too large' in str(e).lower():
                    # Автоматически уменьшаем размер чанка
                    new_size = chunk_strategy.handle_payload_too_large(chunk_end - chunk_start + 1)
                    logger.warning(f"🚨 Payload too large, новый размер чанка: {new_size}")
                
                raise
        
        # Используем прогрессивный менеджер чанков
        progressive_manager = ProgressiveChunkManager(chunk_strategy)
        
        all_swaps = progressive_manager.process_large_range(
            start_block=start_block,
            end_block=end_block,
            fetch_func=fetch_chunk_swaps,
            contract_address=PLEX_USDT_POOL,
            progress_callback=self._log_progress
        )
        
        logger.info(f"🎯 Собрано {len(all_swaps)} swap'ов с адаптивным чанкованием")
        
        return all_swaps
    
    def _log_progress(self, progress_info: Dict):
        """Логирование прогресса обработки"""
        pct = progress_info['percentage']
        current = progress_info['current']
        total = progress_info['total']
        remaining = progress_info.get('estimated_remaining', 0)
        
        if int(pct) % 10 == 0:  # Логируем каждые 10%
            logger.info(f"📈 Прогресс: {pct:.1f}% ({current:,}/{total:,} блоков)")
            logger.info(f"   Осталось: ~{remaining:.0f}s")
    
    def get_swaps_in_range(self, start_block: int, end_block: int) -> List[Dict]:
        """Получить swap события в диапазоне блоков"""
        return self.get_pool_swaps(start_block, end_block)

    def collect_all_swaps(self, stop_block: int, progress_callback=None) -> List[Dict]:
        """Собрать ВСЕ swap события пула оптимизированным способом"""
        
        logger.info(f"🚀 Starting optimized swap collection up to block {stop_block}")
        start_time = time.time()
        
        all_swaps = []
        current_block = 1
        total_blocks = stop_block - current_block
        
        while current_block <= stop_block:
            # Адаптивный размер чанка
            chunk_size = self.chunk_strategy.get_optimal_chunk_size(current_block)
            end_block = min(current_block + chunk_size - 1, stop_block)
            
            try:
                # Получаем swap'ы для чанка
                chunk_swaps = self.get_pool_swaps(current_block, end_block)
                all_swaps.extend(chunk_swaps)
                
                # Обновляем стратегию
                self.chunk_strategy.record_result(chunk_size, len(chunk_swaps))
                
                # Прогресс
                progress = ((end_block - 1) / total_blocks) * 100
                if progress_callback:
                    progress_callback(f"Collecting swaps: {progress:.1f}%", progress)
                
                logger.debug(f"📈 Progress: {progress:.1f}% | Chunk: {current_block}-{end_block} | Swaps: {len(chunk_swaps)}")
                
                current_block = end_block + 1
                
            except Exception as e:
                if "payload too large" in str(e).lower():
                    # Уменьшаем размер чанка и повторяем
                    chunk_size = max(100, chunk_size // 2)
                    end_block = min(current_block + chunk_size - 1, stop_block)
                    logger.warning(f"⚠️ Reducing chunk size to {chunk_size}")
                    continue
                else:
                    logger.error(f"❌ Error collecting swaps for blocks {current_block}-{end_block}: {e}")
                    current_block = end_block + 1
        
        # Добавляем timestamp к swap'ам
        self._add_timestamps_to_swaps(all_swaps)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Collected {len(all_swaps)} swaps in {elapsed:.1f}s")
        
        return all_swaps
    
    def _add_timestamps_to_swaps(self, swaps: List[Dict]):
        """Добавить timestamp к swap операциям"""
        
        # Группируем по блокам для оптимизации
        blocks_needed = set(swap['block_number'] for swap in swaps)
        block_timestamps = {}
        
        logger.info(f"🕐 Adding timestamps for {len(blocks_needed)} unique blocks")
        
        # Получаем timestamp'ы блоков
        for block_num in blocks_needed:
            try:
                block_data = self.web3_manager.get_block(block_num)
                block_timestamps[block_num] = block_data['timestamp']
            except Exception as e:
                logger.warning(f"⚠️ Could not get timestamp for block {block_num}: {e}")
                block_timestamps[block_num] = 0
        
        # Добавляем timestamp'ы к swap'ам
        for swap in swaps:
            swap['timestamp'] = block_timestamps.get(swap['block_number'], 0)
    
    def analyze_address_swaps(self, address: str, swaps: List[Dict]) -> Dict:
        """Анализировать swap операции конкретного адреса"""
        
        address = AddressValidator.normalize_address(address)
        address_swaps = []
        
        # Фильтруем swap'ы по адресу
        for swap in swaps:
            if swap['to'].lower() == address.lower():
                address_swaps.append(swap)
        
        if not address_swaps:
            return {
                "address": address,
                "total_swaps": 0,
                "total_buys": 0,
                "total_sells": 0,
                "total_buy_usd": Decimal(0),
                "total_sell_usd": Decimal(0),
                "daily_purchases": {},
                "has_sells": False,
                "missed_days": []
            }
        
        # Анализируем операции
        total_buys = 0
        total_sells = 0
        total_buy_usd = Decimal(0)
        total_sell_usd = Decimal(0)
        daily_purchases = defaultdict(list)
        
        for swap in address_swaps:
            if swap['direction'] == 'buy':
                total_buys += 1
                total_buy_usd += swap['usd_value']
                
                # Группируем по дням
                swap_date = datetime.fromtimestamp(swap['timestamp']).date()
                daily_purchases[swap_date].append(swap)
                
            elif swap['direction'] == 'sell':
                total_sells += 1
                total_sell_usd += swap['usd_value']
        
        # Анализируем ежедневные покупки
        valid_daily_purchases = {}
        for date, day_swaps in daily_purchases.items():
            day_total_usd = sum(swap['usd_value'] for swap in day_swaps)
            
            # Проверяем, попадает ли в дневной диапазон
            if Decimal(str(DAILY_PURCHASE_MIN)) <= day_total_usd <= Decimal(str(DAILY_PURCHASE_MAX)):
                valid_daily_purchases[date] = {
                    "total_usd": day_total_usd,
                    "swaps_count": len(day_swaps),
                    "swaps": day_swaps
                }
        
        return {
            "address": address,
            "total_swaps": len(address_swaps),
            "total_buys": total_buys,
            "total_sells": total_sells,
            "total_buy_usd": total_buy_usd,
            "total_sell_usd": total_sell_usd,
            "daily_purchases": valid_daily_purchases,
            "has_sells": total_sells > 0,
            "all_swaps": address_swaps
        }
    
    def get_unique_participants(self, swaps: List[Dict]) -> Set[str]:
        """Получить уникальных участников swap операций"""
        participants = set()
        
        for swap in swaps:
            # Добавляем адрес получателя
            participants.add(swap['to'].lower())
            
            # Если sender отличается от to, добавляем и его
            if swap['sender'].lower() != swap['to'].lower():
                participants.add(swap['sender'].lower())
        
        return participants
    
    def categorize_participants(self, swaps: List[Dict], period_days: int) -> Dict:
        """Категоризировать всех участников swap операций"""
        
        participants = self.get_unique_participants(swaps)
        
        logger.info(f"📊 Categorizing {len(participants)} unique participants")
        
        categories = {
            "perfect": [],
            "missed_purchase": [],
            "sold_token": [],
            "transferred": []  # Будет заполнено в другом модуле
        }
        
        # Определяем ожидаемые дни покупок
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)
        expected_dates = set()
        
        current_date = start_date
        while current_date <= end_date:
            expected_dates.add(current_date)
            current_date += timedelta(days=1)
        
        for address in participants:
            analysis = self.analyze_address_swaps(address, swaps)
            
            # Определяем категорию
            if analysis['has_sells']:
                # Продавал токены - блокировка
                category_data = {
                    "address": address,
                    "category": "sold_token",
                    "analysis": analysis,
                    "reason": f"Sold {analysis['total_sell_usd']} USD worth of PLEX"
                }
                categories["sold_token"].append(category_data)
                
            else:
                # Проверяем пропущенные дни
                purchased_dates = set(analysis['daily_purchases'].keys())
                missed_dates = expected_dates - purchased_dates
                
                if missed_dates:
                    # Пропустил дни - возможна амнистия
                    category_data = {
                        "address": address,
                        "category": "missed_purchase",
                        "analysis": analysis,
                        "missed_days": list(missed_dates),
                        "reason": f"Missed {len(missed_dates)} days of purchases"
                    }
                    categories["missed_purchase"].append(category_data)
                    
                else:
                    # Идеальный участник
                    category_data = {
                        "address": address,
                        "category": "perfect",
                        "analysis": analysis,
                        "reason": "All daily purchases completed"
                    }
                    categories["perfect"].append(category_data)
        
        logger.info(f"✅ Categorization complete:")
        logger.info(f"   Perfect: {len(categories['perfect'])}")
        logger.info(f"   Missed purchases: {len(categories['missed_purchase'])}")
        logger.info(f"   Sold tokens: {len(categories['sold_token'])}")
        
        return categories
    
    def get_cache_stats(self) -> Dict:
        """Получить статистику кэша"""
        return {
            "processed_blocks": len(self.processed_blocks),
            "cached_swaps": len(self.swap_cache),
            "chunk_history_size": len(self.chunk_strategy.history)
        }


# Глобальный экземпляр анализатора
swap_analyzer = SwapAnalyzer()


def get_swap_analyzer() -> SwapAnalyzer:
    """Получить глобальный экземпляр SwapAnalyzer"""
    return swap_analyzer


if __name__ == "__main__":
    # Тестирование SwapAnalyzer
    
    analyzer = SwapAnalyzer()
    
    # Тест получения swap'ов для небольшого диапазона
    try:
        latest_block = analyzer.web3_manager.get_latest_block_number()
        start_block = latest_block - 100
        
        swaps = analyzer.get_pool_swaps(start_block, latest_block)
        print(f"✅ Found {len(swaps)} swaps in last 100 blocks")
        
        if swaps:
            # Показываем первый swap для примера
            first_swap = swaps[0]
            print(f"📊 Example swap:")
            print(f"   Direction: {first_swap['direction']}")
            print(f"   PLEX amount: {first_swap['plex_amount']}")
            print(f"   USD value: ${first_swap['usd_value']}")
            print(f"   To: {first_swap['to']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Статистика
    stats = analyzer.get_cache_stats()
    print(f"📈 Cache stats: {stats}")
    
    print("✅ SwapAnalyzer tested successfully")
