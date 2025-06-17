"""
Модуль: Transfer Events Collector для PLEX Dynamic Staking Manager
Описание: Сбор и анализ Transfer событий токена PLEX
Зависимости: Web3Manager, retry, validators
Автор: GitHub Copilot
"""

import asyncio
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass

from web3 import Web3
from web3.types import LogReceipt

from config.settings import settings
from config.constants import (
    TOKEN_ADDRESS, TOKEN_DECIMALS, CORP_WALLET_ADDRESS,
    TRANSFER_EVENT_SIGNATURE, CREDITS_PER_GETLOGS
)
from utils.logger import get_logger
from utils.retry import blockchain_retry
from utils.validators import AddressValidator
from utils.converters import wei_to_token, format_number
from utils.chunk_strategy import AdaptiveChunkStrategy
from utils.cache_manager import smart_cache
from blockchain.node_client import get_web3_manager

logger = get_logger("TransferCollector")

@dataclass
class TransferEvent:
    """Данные события Transfer"""
    tx_hash: str
    block_number: int
    block_timestamp: int
    from_address: str
    to_address: str
    value: Decimal
    log_index: int
    tx_index: int
    gas_price: int
    gas_used: int
    
    @property
    def value_formatted(self) -> str:
        """Отформатированное значение"""
        return format_number(self.value, TOKEN_DECIMALS)
    
    @property
    def is_to_corporate(self) -> bool:
        """Перевод на корпоративный кошелек"""
        return self.to_address.lower() == CORP_WALLET_ADDRESS.lower()
    
    @property
    def usd_estimate(self) -> Optional[Decimal]:
        """Примерная стоимость в USD (если известен курс)"""
        # TODO: Интегрировать с price oracle
        return None

class TransferCollector:
    """Коллектор Transfer событий PLEX токена"""
    def __init__(self, web3_manager=None):
        self.web3_manager = web3_manager or get_web3_manager()
        self.chunk_strategy = AdaptiveChunkStrategy(
            initial_chunk_size=1000,
            max_logs_per_request=500,
            min_chunk_size=50,
            max_chunk_size=5000
        )
        self.validator = AddressValidator()
        self.processed_blocks = set()
        self.transfer_cache = {}
        
        logger.info("TransferCollector инициализирован")
    
    @blockchain_retry(max_attempts=3)
    def get_transfers_in_range(self, 
                              start_block: int, 
                              end_block: int,
                              from_address: Optional[str] = None,
                              to_address: Optional[str] = None) -> List[TransferEvent]:
        """
        Получить Transfer события в диапазоне блоков
        
        Args:
            start_block: Начальный блок
            end_block: Конечный блок
            from_address: Фильтр по отправителю (опционально)
            to_address: Фильтр по получателю (опционально)
        """
        logger.info(f"📊 Collecting transfers from blocks {start_block:,} to {end_block:,}")
        
        # Кэш ключ
        cache_key = f"transfers_{start_block}_{end_block}_{from_address}_{to_address}"
        if cache_key in self.transfer_cache:
            logger.debug(f"✅ Using cached transfers for {start_block}-{end_block}")
            return self.transfer_cache[cache_key]
        
        # Подготовка фильтра
        topics = [Web3.to_hex(TRANSFER_EVENT_SIGNATURE)]
        
        if from_address:
            if not self.validator.is_valid_address(from_address):
                raise ValueError(f"Invalid from_address: {from_address}")
            topics.append(Web3.to_bytes(hexstr=from_address).rjust(32, b'\x00'))
        else:
            topics.append(None)
            
        if to_address:
            if not self.validator.is_valid_address(to_address):
                raise ValueError(f"Invalid to_address: {to_address}")
            topics.append(Web3.to_bytes(hexstr=to_address).rjust(32, b'\x00'))
        else:
            topics.append(None)
        
        # Фильтр параметры
        filter_params = {
            'fromBlock': hex(start_block),
            'toBlock': hex(end_block),
            'address': Web3.to_checksum_address(TOKEN_ADDRESS),
            'topics': topics
        }
        
        try:
            # Получение логов
            logs = self.web3_manager.w3_http.eth.get_logs(filter_params)
            
            # Трекинг API использования
            self.web3_manager.api_tracker.track_request(CREDITS_PER_GETLOGS)
            
            logger.info(f"✅ Found {len(logs)} transfer events")
            
            # Парсинг событий
            transfers = []
            for log in logs:
                try:
                    transfer = self._parse_transfer_log(log)
                    if transfer:
                        transfers.append(transfer)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse transfer log: {e}")
                    continue
            
            # Кэшируем результат
            self.transfer_cache[cache_key] = transfers
            
            return transfers
            
        except Exception as e:
            logger.error(f"❌ Error collecting transfers: {e}")
            raise
    
    def _parse_transfer_log(self, log: LogReceipt) -> Optional[TransferEvent]:
        """Парсинг лога Transfer события"""
        try:
            # Извлечение адресов из topics
            from_addr = Web3.to_checksum_address("0x" + log['topics'][1].hex()[-40:])
            to_addr = Web3.to_checksum_address("0x" + log['topics'][2].hex()[-40:])
            
            # Значение из data
            value_wei = int(log['data'], 16)
            value = wei_to_token(value_wei, TOKEN_DECIMALS)
            
            # Получение дополнительной информации о транзакции
            tx_receipt = self.web3_manager.w3_http.eth.get_transaction_receipt(log['transactionHash'])
            tx_data = self.web3_manager.w3_http.eth.get_transaction(log['transactionHash'])
            block_data = self.web3_manager.w3_http.eth.get_block(log['blockNumber'])
            
            return TransferEvent(
                tx_hash=log['transactionHash'].hex(),
                block_number=log['blockNumber'],
                block_timestamp=block_data['timestamp'],
                from_address=from_addr,
                to_address=to_addr,
                value=value,
                log_index=log['logIndex'],
                tx_index=tx_receipt['transactionIndex'],
                gas_price=tx_data['gasPrice'],
                gas_used=tx_receipt['gasUsed']
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing transfer log: {e}")
            return None
    
    def get_address_transfers(self, 
                             address: str, 
                             period_days: int = 30,
                             direction: str = "both") -> Dict[str, List[TransferEvent]]:
        """
        Получить все переводы для конкретного адреса
        
        Args:
            address: Ethereum адрес
            period_days: Период анализа в днях
            direction: "sent", "received", "both"
        """
        if not self.validator.is_valid_address(address):
            raise ValueError(f"Invalid address: {address}")
        
        logger.info(f"🔍 Analyzing transfers for {address} ({period_days} days)")
        
        # Определение диапазона блоков
        end_block = self.web3_manager.get_latest_block_number()
        target_timestamp = int((datetime.now() - timedelta(days=period_days)).timestamp())
        start_block = self.web3_manager.find_block_by_timestamp(target_timestamp)
        
        results = {
            "sent": [],
            "received": []
        }
        
        # Получение отправленных переводов
        if direction in ["sent", "both"]:
            sent_transfers = self.get_transfers_in_range(
                start_block=start_block,
                end_block=end_block,
                from_address=address
            )
            results["sent"] = sent_transfers
            logger.info(f"📤 Found {len(sent_transfers)} sent transfers")
        
        # Получение полученных переводов
        if direction in ["received", "both"]:
            received_transfers = self.get_transfers_in_range(
                start_block=start_block,
                end_block=end_block,
                to_address=address
            )
            results["received"] = received_transfers
            logger.info(f"📥 Found {len(received_transfers)} received transfers")
        
        return results
    
    def get_corporate_transfers(self, period_days: int = 30) -> List[TransferEvent]:
        """Получить все переводы на корпоративный кошелек"""
        logger.info(f"🏢 Analyzing corporate transfers ({period_days} days)")
        
        end_block = self.web3_manager.get_latest_block_number()
        target_timestamp = int((datetime.now() - timedelta(days=period_days)).timestamp())
        start_block = self.web3_manager.find_block_by_timestamp(target_timestamp)
        
        corporate_transfers = self.get_transfers_in_range(
            start_block=start_block,
            end_block=end_block,
            to_address=CORP_WALLET_ADDRESS
        )
        
        logger.info(f"🏢 Found {len(corporate_transfers)} corporate transfers")
        return corporate_transfers
    
    def analyze_transfer_patterns(self, 
                                 transfers: List[TransferEvent]) -> Dict[str, Any]:
        """Анализ паттернов переводов"""
        if not transfers:
            return {"error": "No transfers to analyze"}
        
        total_value = sum(t.value for t in transfers)
        total_count = len(transfers)
        
        # Группировка по дням
        daily_stats = {}
        for transfer in transfers:
            date = datetime.fromtimestamp(transfer.block_timestamp).date()
            if date not in daily_stats:
                daily_stats[date] = {"count": 0, "value": Decimal(0)}
            daily_stats[date]["count"] += 1
            daily_stats[date]["value"] += transfer.value
        
        # Статистика по получателям
        recipient_stats = {}
        for transfer in transfers:
            to_addr = transfer.to_address
            if to_addr not in recipient_stats:
                recipient_stats[to_addr] = {"count": 0, "value": Decimal(0)}
            recipient_stats[to_addr]["count"] += 1
            recipient_stats[to_addr]["value"] += transfer.value
        
        # Сортировка по объему
        top_recipients = sorted(
            recipient_stats.items(),
            key=lambda x: x[1]["value"],
            reverse=True
        )[:10]
        
        return {
            "summary": {
                "total_transfers": total_count,
                "total_value": float(total_value),
                "average_value": float(total_value / total_count) if total_count > 0 else 0,
                "date_range": {
                    "start": min(datetime.fromtimestamp(t.block_timestamp) for t in transfers).isoformat(),
                    "end": max(datetime.fromtimestamp(t.block_timestamp) for t in transfers).isoformat()
                }
            },
            "daily_stats": {
                str(date): {
                    "count": stats["count"],
                    "value": float(stats["value"])
                } 
                for date, stats in daily_stats.items()
            },
            "top_recipients": [
                {
                    "address": addr,
                    "count": stats["count"], 
                    "value": float(stats["value"])
                }
                for addr, stats in top_recipients
            ]
        }
    
    def get_bulk_transfers(self, 
                          addresses: List[str], 
                          period_days: int = 30) -> Dict[str, Dict]:
        """Массовое получение переводов для списка адресов"""
        logger.info(f"📊 Bulk transfer analysis for {len(addresses)} addresses")
        
        results = {}
        
        for i, address in enumerate(addresses):
            try:
                transfers = self.get_address_transfers(address, period_days)
                analysis = {}
                
                # Анализ отправленных переводов
                if transfers["sent"]:
                    analysis["sent_analysis"] = self.analyze_transfer_patterns(transfers["sent"])
                
                # Анализ полученных переводов  
                if transfers["received"]:
                    analysis["received_analysis"] = self.analyze_transfer_patterns(transfers["received"])
                
                results[address] = {
                    "transfers": transfers,
                    "analysis": analysis
                }
                
                # Прогресс
                if (i + 1) % 100 == 0:
                    logger.info(f"📊 Processed {i + 1}/{len(addresses)} addresses")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {address}: {e}")
                results[address] = {"error": str(e)}
        
        logger.info(f"✅ Bulk transfer analysis completed")
        return results
    
    def get_cache_stats(self) -> Dict:
        """Статистика кэша"""
        return {
            "cached_ranges": len(self.transfer_cache),
            "processed_blocks": len(self.processed_blocks)
        }

# Глобальный экземпляр коллектора
transfer_collector = TransferCollector()

def get_transfer_collector() -> TransferCollector:
    """Получить глобальный экземпляр TransferCollector"""
    return transfer_collector

if __name__ == "__main__":
    # Тестирование TransferCollector
    
    collector = TransferCollector()
    
    # Тест получения переводов
    try:
        logger.info("🧪 Testing transfer collection...")
        
        # Получение последних переводов на корпоративный кошелек
        corporate_transfers = collector.get_corporate_transfers(period_days=1)
        logger.info(f"📊 Corporate transfers found: {len(corporate_transfers)}")
        
        if corporate_transfers:
            # Анализ паттернов
            analysis = collector.analyze_transfer_patterns(corporate_transfers)
            logger.info(f"📈 Analysis result: {analysis['summary']}")
        
        # Статистика кэша
        cache_stats = collector.get_cache_stats()
        logger.info(f"💾 Cache stats: {cache_stats}")
        
        logger.info("✅ TransferCollector test completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
