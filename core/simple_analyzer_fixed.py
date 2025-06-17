"""
PLEX Dynamic Staking Manager - Простой анализатор участников
Упрощенная но рабочая версия анализа без async/await.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.2
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from web3 import Web3

from config.constants import *
from utils.logger import get_logger
from utils.retry import with_retry

logger = get_logger(__name__)


@dataclass
class SimpleParticipantData:
    """Упрощенные данные участника."""
    address: str
    swaps_count: int = 0
    last_activity: Optional[datetime] = None
    category: str = "Unknown"
    status: str = "Active"


class SimpleAnalyzer:
    """
    Простой анализатор участников для демонстрации работы.
    
    НЕ использует async/await, работает с реальными данными BSC.
    """
    
    def __init__(self):
        self.w3 = None
        self.participants = {}
        self.is_analyzing = False
        
    def initialize(self) -> bool:
        """Инициализация подключения к BSC."""
        try:
            logger.info("🔗 Подключение к BSC QuickNode...")
            self.w3 = Web3(Web3.HTTPProvider(QUICKNODE_HTTP))
            
            if not self.w3.is_connected():
                logger.error("❌ Не удалось подключиться к BSC")
                return False
                
            current_block = self.w3.eth.block_number
            logger.info(f"✅ Подключен к BSC. Текущий блок: {current_block}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к BSC: {e}")
            return False

    @with_retry(max_attempts=3)
    def get_current_block(self) -> int:
        """Получение номера текущего блока."""
        return self.w3.eth.block_number

    @with_retry(max_attempts=3)
    def get_token_balance(self, address: str) -> Decimal:
        """Получение баланса токена для адреса."""
        try:
            # Упрощенный ABI для balanceOf
            balance_abi = [{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(TOKEN_ADDRESS),
                abi=balance_abi
            )
            
            balance_wei = contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            
            # Конвертируем из wei в токены (decimals = 9)
            return Decimal(balance_wei) / Decimal(10 ** TOKEN_DECIMALS)
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения баланса для {address}: {e}")
            return Decimal("0")
    
    def analyze_period(self, hours: int, progress_callback=None) -> Dict[str, Any]:
        """
        Анализ за указанный период.
        
        Args:
            hours: Количество часов для анализа
            progress_callback: Функция для отображения прогресса
            
        Returns:
            Результаты анализа
        """
        try:
            self.is_analyzing = True
            logger.info(f"🔍 Начинаем анализ за последние {hours} часов")
            
            if progress_callback:
                progress_callback("Инициализация...", 0.1)
            
            # Проверяем подключение
            if not self.w3 or not self.w3.is_connected():
                if not self.initialize():
                    raise Exception("Не удалось подключиться к BSC")
            
            if progress_callback:
                progress_callback("Определение блоков...", 0.2)
            
            # Получаем диапазон блоков
            current_block = self.get_current_block()
            # Примерно 3 секунды на блок в BSC
            blocks_per_hour = 1200
            start_block = current_block - (hours * blocks_per_hour)
            
            logger.info(f"📊 Анализ блоков {start_block} - {current_block}")
            
            if progress_callback:
                progress_callback("Сбор Transfer событий...", 0.3)
            
            # Получаем Transfer события
            transfers = self._get_transfer_events(start_block, current_block)
            logger.info(f"📝 Найдено {len(transfers)} Transfer событий")
            
            if progress_callback:
                progress_callback("Анализ участников...", 0.5)
            
            # Анализируем участников
            participants = self._analyze_participants(transfers, progress_callback)
            
            if progress_callback:
                progress_callback("Формирование отчета...", 0.9)
            
            # Формируем результат
            result = {
                'success': True,
                'timestamp': datetime.now(),
                'period_hours': hours,
                'blocks_analyzed': current_block - start_block + 1,
                'start_block': start_block,
                'end_block': current_block,
                'total_transfers': len(transfers),
                'unique_participants': len(participants),
                'participants': participants,
                'summary': self._generate_summary(participants)
            }
            
            if progress_callback:
                progress_callback("Анализ завершен!", 1.0)
                
            logger.info(f"✅ Анализ завершен. Найдено {len(participants)} участников")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            if progress_callback:
                progress_callback(f"Ошибка: {e}", 0.0)
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            }
        finally:
            self.is_analyzing = False

    @with_retry(max_attempts=3)
    def _get_transfer_events(self, start_block: int, end_block: int) -> List[Dict]:
        """Получение Transfer событий с разбиением на чанки."""
        try:
            # Transfer event signature: Transfer(address,address,uint256)
            transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            
            # Максимальный размер чанка для избежания ошибки 413
            max_chunk_size = 2000  # Безопасный размер для QuickNode
            total_blocks = end_block - start_block + 1
            
            transfers = []
            current_start = start_block
            
            logger.info(f"📊 Сбор логов по чанкам: {total_blocks} блоков, размер чанка: {max_chunk_size}")
            
            while current_start <= end_block:
                current_end = min(current_start + max_chunk_size - 1, end_block)
                
                try:
                    # Получаем логи Transfer событий для текущего чанка
                    logs = self.w3.eth.get_logs({
                        'fromBlock': hex(current_start),
                        'toBlock': hex(current_end),
                        'address': TOKEN_ADDRESS,
                        'topics': [transfer_topic]
                    })
                    
                    logger.info(f"📝 Чанк {current_start}-{current_end}: найдено {len(logs)} событий")
                    
                    # Обрабатываем логи текущего чанка
                    chunk_transfers = self._process_transfer_logs(logs)
                    transfers.extend(chunk_transfers)
                    
                except Exception as e:
                    # Если произошла ошибка 413, уменьшаем размер чанка
                    if "413" in str(e) or "Request Entity Too Large" in str(e):
                        max_chunk_size = max(500, max_chunk_size // 2)
                        logger.warning(f"⚠️ Уменьшаем размер чанка до {max_chunk_size} из-за ошибки 413")
                        continue
                    else:
                        logger.error(f"❌ Ошибка получения логов для чанка {current_start}-{current_end}: {e}")
                        
                current_start = current_end + 1
                
                # Небольшая задержка между чанками
                time.sleep(0.1)
            
            logger.info(f"✅ Всего собрано {len(transfers)} Transfer событий")
            return transfers
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка сбора Transfer событий: {e}")
            return []

    def _process_transfer_logs(self, logs: List) -> List[Dict]:
        """Обработка логов Transfer событий."""
        transfers = []
        
        for log in logs:
            try:
                # Декодируем Transfer событие
                # topics[0] = event signature
                # topics[1] = from address (indexed)
                # topics[2] = to address (indexed)
                # data = amount (not indexed)
                
                from_address = self.w3.to_checksum_address("0x" + log['topics'][1].hex()[-40:])
                to_address = self.w3.to_checksum_address("0x" + log['topics'][2].hex()[-40:])
                amount_hex = log['data']
                amount = int(amount_hex, 16)
                
                transfer = {
                    'from': from_address,
                    'to': to_address,
                    'amount': amount,
                    'block_number': log['blockNumber'],
                    'transaction_hash': log['transactionHash'].hex()
                }
                
                transfers.append(transfer)
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка декодирования Transfer лога: {e}")
                continue
        
        return transfers

    def _analyze_participants(self, transfers: List[Dict], progress_callback=None) -> Dict[str, SimpleParticipantData]:
        """Анализ участников на основе Transfer событий."""
        participants = {}
        
        for i, transfer in enumerate(transfers):
            if progress_callback and i % 10 == 0:
                progress = 0.5 + (i / len(transfers)) * 0.4  # 0.5 to 0.9
                progress_callback(f"Анализ Transfer {i+1}/{len(transfers)}...", progress)
            
            # Анализируем отправителя
            from_addr = transfer['from']
            if from_addr not in participants:
                participants[from_addr] = SimpleParticipantData(
                    address=from_addr,
                    swaps_count=1,
                    last_activity=datetime.now(),
                    category="Seller",
                    status="Active"
                )
            else:
                participants[from_addr].swaps_count += 1
                participants[from_addr].last_activity = datetime.now()
            
            # Анализируем получателя
            to_addr = transfer['to']
            if to_addr not in participants:
                participants[to_addr] = SimpleParticipantData(
                    address=to_addr,
                    swaps_count=1,
                    last_activity=datetime.now(),
                    category="Buyer",
                    status="Active"
                )
            else:
                participants[to_addr].swaps_count += 1
                participants[to_addr].last_activity = datetime.now()
        
        return participants

    def _generate_summary(self, participants: Dict[str, SimpleParticipantData]) -> Dict[str, Any]:
        """Генерация сводки по участникам."""
        if not participants:
            return {
                'total_participants': 0,
                'categories': {},
                'statuses': {}
            }
        
        categories = {}
        statuses = {}
        
        for participant in participants.values():
            # Подсчет по категориям
            cat = participant.category
            categories[cat] = categories.get(cat, 0) + 1
            
            # Подсчет по статусам
            status = participant.status
            statuses[status] = statuses.get(status, 0) + 1
        
        return {
            'total_participants': len(participants),
            'categories': categories,
            'statuses': statuses
        }

    def stop_analysis(self):
        """Остановка анализа."""
        self.is_analyzing = False
        logger.info("⏹️ Анализ остановлен пользователем")

    def analyze_participants(self, hours: int = 24) -> Dict[str, Any]:
        """
        Публичный метод для анализа участников.
        
        Args:
            hours: Количество часов для анализа (по умолчанию 24)
            
        Returns:
            Результаты анализа участников
        """
        return self.analyze_period(hours)


# Глобальный экземпляр для использования в UI
simple_analyzer = SimpleAnalyzer()
