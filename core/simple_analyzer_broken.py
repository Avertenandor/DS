"""
PLEX Dynamic Staking Manager - Простой анализатор участников
Упрощенная но рабочая версия анализа без async/await.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
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
                
            logger.info(f"✅ Подключен к BSC. Текущий блок: {self.w3.eth.block_number}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False

    @with_retry(max_attempts=3)
    def get_current_block(self) -> int:
        """Получение текущего блока."""
        if not self.w3:
            raise Exception("Web3 не инициализирован")
        return self.w3.eth.block_number
    
    @with_retry(max_attempts=3)
    def get_token_balance(self, address: str) -> Decimal:
        """Получение баланса PLEX токена."""
        try:
            if not self.w3:
                return Decimal("0")
                
            # Простой ABI для balanceOf
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
            
            balance_wei = contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
            balance_tokens = Decimal(balance_wei) / Decimal(10 ** TOKEN_DECIMALS)
            
            return balance_tokens
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения баланса для {address}: {e}")
            return Decimal("0")
    
    def analyze_period(self, hours: int = 24, progress_callback=None) -> Dict[str, Any]:
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
                progress_callback("Получение данных блокчейна...", 0.2)
            
            # Получаем текущий блок
            current_block = self.get_current_block()
            logger.info(f"📊 Текущий блок: {current_block:,}")
            
            # Рассчитываем диапазон блоков (примерно 3 секунды на блок)
            blocks_per_hour = 1200  # 3600 секунд / 3 секунды на блок
            start_block = max(1, current_block - (hours * blocks_per_hour))
            
            logger.info(f"🔍 Анализируем блоки {start_block:,} - {current_block:,}")
            
            if progress_callback:
                progress_callback("Поиск транзакций PLEX...", 0.3)
            
            # Получаем Transfer события PLEX токена
            transfers = self._get_transfer_events(start_block, current_block)
            logger.info(f"📋 Найдено {len(transfers)} Transfer событий")
            
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
        """Получение Transfer событий."""
        try:
            # Transfer event signature: Transfer(address,address,uint256)
            transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            
            # Получаем логи Transfer событий
            logs = self.w3.eth.get_logs({
                'fromBlock': hex(start_block),
                'toBlock': hex(end_block),
                'address': TOKEN_ADDRESS,
                'topics': [transfer_topic]
            })
            
            transfers = []
            for log in logs:
                try:
                    # Декодируем Transfer события
                    from_address = "0x" + log['topics'][1].hex()[26:]  # Убираем padding
                    to_address = "0x" + log['topics'][2].hex()[26:]    # Убираем padding
                    amount = int(log['data'], 16)
                    
                    transfers.append({
                        'from': from_address.lower(),
                        'to': to_address.lower(),
                        'amount': amount,
                        'block_number': log['blockNumber'],
                        'transaction_hash': log['transactionHash'].hex()
                    })
                except Exception as decode_error:
                    logger.warning(f"⚠️ Ошибка декодирования лога: {decode_error}")
                    continue
            
            return transfers
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения Transfer событий: {e}")
            return []
    
    def _analyze_participants(self, transfers: List[Dict], progress_callback=None) -> Dict[str, SimpleParticipantData]:
        """Анализ участников на основе Transfer событий."""
        participants = {}
        
        for i, transfer in enumerate(transfers):
            if not self.is_analyzing:
                break
                
            try:
                # Обрабатываем отправителя
                from_addr = transfer['from']
                to_addr = transfer['to']
                
                # Добавляем отправителя
                if from_addr != "0x0000000000000000000000000000000000000000":  # Не mint
                    if from_addr not in participants:
                        participants[from_addr] = SimpleParticipantData(
                            address=from_addr,
                            category="Holder"
                        )
                    participants[from_addr].swaps_count += 1
                
                # Добавляем получателя
                if to_addr != "0x0000000000000000000000000000000000000000":  # Не burn
                    if to_addr not in participants:
                        participants[to_addr] = SimpleParticipantData(
                            address=to_addr,
                            category="Holder"
                        )
                    participants[to_addr].swaps_count += 1
                
                # Обновляем прогресс
                if progress_callback and i % 100 == 0:
                    progress = 0.5 + (i / len(transfers)) * 0.4  # 50% - 90%
                    progress_callback(f"Обработано {i+1}/{len(transfers)} транзакций", progress)
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка обработки transfer: {e}")
                continue
        
        # Получаем балансы для активных участников
        active_participants = {addr: data for addr, data in participants.items() 
                             if data.swaps_count > 0}
        
        logger.info(f"📊 Получение балансов для {len(active_participants)} активных участников...")
        
        for i, (address, participant) in enumerate(active_participants.items()):
            if not self.is_analyzing:
                break
                
            try:
                balance = self.get_token_balance(address)
                participant.status = "Active" if balance > Decimal("100") else "Low Balance"
                
                # Обновляем прогресс
                if progress_callback and i % 10 == 0:
                    progress = 0.9 + (i / len(active_participants)) * 0.1  # 90% - 100%
                    progress_callback(f"Проверка балансов {i+1}/{len(active_participants)}", progress)
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения баланса для {address}: {e}")
                participant.status = "Unknown"
        
        return active_participants
    
    def _generate_summary(self, participants: Dict[str, SimpleParticipantData]) -> Dict[str, Any]:
        """Генерация сводки анализа."""
        if not participants:
            return {
                'total_participants': 0,
                'categories': {},
                'statuses': {}
            }
        
        # Подсчет по категориям
        categories = {}
        statuses = {}
        
        for participant in participants.values():
            # Категории
            cat = participant.category
            categories[cat] = categories.get(cat, 0) + 1
            
            # Статусы
            status = participant.status
            statuses[status] = statuses.get(status, 0) + 1
        
        return {
            'total_participants': len(participants),
            'categories': categories,
            'statuses': statuses,
            'most_active': self._get_most_active_participants(participants, 10)
        }
    
    def _get_most_active_participants(self, participants: Dict[str, SimpleParticipantData], 
                                    limit: int = 10) -> List[Dict[str, Any]]:
        """Получение самых активных участников."""
        sorted_participants = sorted(
            participants.items(),
            key=lambda x: x[1].swaps_count,
            reverse=True
        )
        
        return [
            {
                'address': addr,
                'swaps_count': data.swaps_count,
                'category': data.category,
                'status': data.status
            }
            for addr, data in sorted_participants[:limit]
        ]
    
    def stop_analysis(self):
        """Остановка анализа."""
        self.is_analyzing = False
        logger.info("⏹️ Анализ остановлен пользователем")


# Глобальный экземпляр для использования в UI
simple_analyzer = SimpleAnalyzer()
