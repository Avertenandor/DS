"""
PLEX Dynamic Staking Manager - Batch Transaction Processor
Батчинг транзакций для экономии до 70% на массовых выплатах.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import threading
from queue import Queue, Empty
from collections import defaultdict

from config.constants import TOKEN_ADDRESS, TOKEN_DECIMALS, BATCH_TRANSFER_CONTRACT
from utils.logger import get_logger
from utils.retry import blockchain_retry
from blockchain.gas_manager import GasManager

logger = get_logger(__name__)


@dataclass
class TransferRequest:
    """Запрос на перевод токенов."""
    recipient: str
    amount: Decimal
    priority: int = 1  # 1 = высокий, 5 = низкий
    created_at: datetime = field(default_factory=datetime.now)
    callback: Optional[callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Результат выполнения батча."""
    batch_id: str
    tx_hash: Optional[str] = None
    success: bool = False
    gas_used: int = 0
    gas_price: int = 0
    total_amount: Decimal = field(default_factory=lambda: Decimal('0'))
    recipients_count: int = 0
    processing_time: float = 0.0
    error: Optional[str] = None
    individual_results: List[Dict] = field(default_factory=list)


class BatchTransactionProcessor:
    """
    Процессор батч-транзакций для экономии газа.
    
    Функции:
    - Объединение до 50 переводов в одну транзакцию
    - Автоматическое выполнение по размеру/времени
    - Retry логика для неудачных батчей
    - Отслеживание экономии газа
    - Приоритизация переводов
    """
    
    def __init__(self, web3_manager, batch_size: int = 50, timeout_seconds: int = 300):
        """
        Инициализация процессора батчей.
        
        Args:
            web3_manager: Менеджер Web3 подключений
            batch_size: Максимальный размер батча (до 50)
            timeout_seconds: Тайм-аут для автоматического выполнения батча
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3_http
        self.batch_size = min(batch_size, 50)  # Максимум 50 адресов
        self.timeout_seconds = timeout_seconds
        
        # Очереди переводов по приоритету
        self.pending_transfers = {
            1: Queue(),  # Высокий приоритет
            2: Queue(),  # Нормальный приоритет
            3: Queue(),  # Низкий приоритет
        }
        
        # Статистика
        self.total_batches_executed = 0
        self.total_transfers_processed = 0
        self.total_gas_saved = 0
        self.last_batch_time = datetime.now()
        
        # Контроль потоков
        self.running = False
        self.processor_thread = None
        
        # Gas manager для оптимизации
        self.gas_manager = GasManager(web3_manager)
          logger.info(f"🔥 BatchTransactionProcessor инициализирован (размер батча: {self.batch_size})")
    
    def start(self):
        """Запуск процессора батчей."""
        if self.running:
            logger.warning("⚠️ BatchTransactionProcessor уже запущен")
            return
        
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._process_batches_loop,
            daemon=True
        )
        self.processor_thread.start()
        
        logger.info("🚀 BatchTransactionProcessor запущен")
    
    def stop(self):
        \"\"\"Остановка процессора батчей.\"\"\"
        if not self.running:
            return
        
        logger.info(\"⏹️ Остановка BatchTransactionProcessor...\")
        self.running = False
        
        # Выполнение оставшихся батчей
        self.flush_all_pending()
        
        if self.processor_thread:
            self.processor_thread.join(timeout=10)
        
        logger.info(\"✅ BatchTransactionProcessor остановлен\")
    
    def add_transfer(self, recipient: str, amount: Decimal, priority: int = 2, 
                    callback: Optional[callable] = None, **metadata) -> str:
        \"\"\"
        Добавить перевод в очередь.
        
        Args:
            recipient: Адрес получателя
            amount: Сумма в токенах
            priority: Приоритет (1-3, где 1 = высший)
            callback: Функция обратного вызова
            **metadata: Дополнительные метаданные
            
        Returns:
            str: ID запроса
        \"\"\"
        try:
            # Валидация
            if not self.w3.is_address(recipient):
                raise ValueError(f\"Некорректный адрес: {recipient}\")
            
            if amount <= 0:
                raise ValueError(f\"Некорректная сумма: {amount}\")
            
            priority = max(1, min(3, priority))  # Ограничиваем 1-3
            
            # Создание запроса
            transfer_request = TransferRequest(
                recipient=self.w3.to_checksum_address(recipient),
                amount=amount,
                priority=priority,
                callback=callback,
                metadata=metadata
            )
            
            # Добавление в очередь
            self.pending_transfers[priority].put(transfer_request)
            
            request_id = f\"{recipient[:10]}_{int(time.time() * 1000)}\"
            logger.debug(f\"📝 Перевод добавлен в очередь: {amount} PLEX → {recipient[:10]}... (приоритет {priority})\")
            
            return request_id
            
        except Exception as e:
            logger.error(f\"❌ Ошибка добавления перевода: {e}\")
            raise
    
    def add_bulk_transfers(self, transfers: List[Tuple[str, Decimal]], priority: int = 2) -> List[str]:
        \"\"\"
        Добавить множество переводов одновременно.
        
        Args:
            transfers: Список (адрес, сумма)
            priority: Общий приоритет для всех переводов
            
        Returns:
            List[str]: Список ID запросов
        \"\"\"
        request_ids = []
        
        for recipient, amount in transfers:
            try:
                request_id = self.add_transfer(recipient, amount, priority)
                request_ids.append(request_id)
            except Exception as e:
                logger.error(f\"❌ Ошибка добавления перевода {recipient}: {e}\")
                request_ids.append(None)
        
        logger.info(f\"📦 Добавлено {len([r for r in request_ids if r])} переводов из {len(transfers)}\")
        return request_ids
    
    def flush_all_pending(self) -> List[BatchResult]:
        \"\"\"Принудительное выполнение всех ожидающих переводов.\"\"\"
        logger.info(\"🔄 Принудительное выполнение всех ожидающих батчей...\")
        
        results = []
        
        # Обработка по приоритетам
        for priority in [1, 2, 3]:
            while not self.pending_transfers[priority].empty():
                batch = self._collect_batch(priority)
                if batch:
                    result = self._execute_batch(batch)
                    results.append(result)
        
        logger.info(f\"✅ Выполнено {len(results)} батчей\")
        return results
    
    def get_pending_count(self) -> Dict[int, int]:
        \"\"\"Получить количество ожидающих переводов по приоритетам.\"\"\"
        return {
            priority: queue.qsize() 
            for priority, queue in self.pending_transfers.items()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        \"\"\"Получить статистику работы процессора.\"\"\"
        pending = self.get_pending_count()
        total_pending = sum(pending.values())
        
        return {
            'total_batches_executed': self.total_batches_executed,
            'total_transfers_processed': self.total_transfers_processed,
            'total_gas_saved': self.total_gas_saved,
            'pending_transfers': pending,
            'total_pending': total_pending,
            'average_batch_size': (
                self.total_transfers_processed / self.total_batches_executed 
                if self.total_batches_executed > 0 else 0
            ),
            'last_batch_time': self.last_batch_time,
            'is_running': self.running
        }
    
    def _process_batches_loop(self):
        \"\"\"Основной цикл обработки батчей.\"\"\"
        logger.info(\"🔄 Запущен цикл обработки батчей\")
        
        while self.running:
            try:
                # Проверка на тайм-аут
                time_since_last = (datetime.now() - self.last_batch_time).total_seconds()
                has_pending = sum(self.get_pending_count().values()) > 0
                
                if has_pending and time_since_last >= self.timeout_seconds:
                    logger.info(f\"⏰ Тайм-аут достигнут ({self.timeout_seconds}s), выполнение батча...\")
                    self._process_next_batch()
                
                # Проверка на заполненность батча
                for priority in [1, 2, 3]:  # Обработка по приоритетам
                    if self.pending_transfers[priority].qsize() >= self.batch_size:
                        logger.info(f\"📦 Батч приоритета {priority} заполнен ({self.batch_size} переводов)\")
                        self._process_next_batch(priority)
                        break
                
                time.sleep(1)  # Небольшая пауза
                
            except Exception as e:
                logger.error(f\"❌ Ошибка в цикле обработки батчей: {e}\")
                time.sleep(5)  # Пауза при ошибке
        
        logger.info(\"⏹️ Цикл обработки батчей завершен\")
    
    def _process_next_batch(self, priority: Optional[int] = None):
        \"\"\"Обработка следующего батча.\"\"\"
        try:
            # Определение приоритета для обработки
            if priority is None:
                # Автоматический выбор по приоритету
                for p in [1, 2, 3]:
                    if not self.pending_transfers[p].empty():
                        priority = p
                        break
            
            if priority is None:
                return  # Нет переводов для обработки
            
            # Сбор батча
            batch = self._collect_batch(priority)
            if not batch:
                return
            
            # Выполнение батча
            result = self._execute_batch(batch)
            
            # Обновление статистики
            self.total_batches_executed += 1
            self.total_transfers_processed += len(batch)
            self.last_batch_time = datetime.now()
            
            # Расчет экономии газа
            if result.success:
                individual_gas = len(batch) * 21000  # Примерная стоимость обычного перевода
                saved_gas = individual_gas - result.gas_used
                self.total_gas_saved += saved_gas
                
                logger.info(f\"💰 Батч выполнен: {len(batch)} переводов, сэкономлено {saved_gas:,} газа\")
            
            # Вызов callbacks
            self._execute_callbacks(batch, result)
            
        except Exception as e:
            logger.error(f\"❌ Ошибка обработки батча: {e}\")
    
    def _collect_batch(self, priority: int) -> List[TransferRequest]:
        \"\"\"Сбор батча переводов из очереди.\"\"\"
        batch = []
        queue = self.pending_transfers[priority]
        
        # Собираем до batch_size переводов
        for _ in range(self.batch_size):
            try:
                transfer = queue.get_nowait()
                batch.append(transfer)
            except Empty:
                break
        
        return batch
    
    @blockchain_retry
    def _execute_batch(self, batch: List[TransferRequest]) -> BatchResult:
        \"\"\"Выполнение батча переводов.\"\"\"
        start_time = time.time()
        batch_id = f\"batch_{int(start_time * 1000)}\"
        
        logger.info(f\"🚀 Выполнение батча {batch_id}: {len(batch)} переводов\")
        
        try:
            # Подготовка данных для батч-контракта
            recipients = [transfer.recipient for transfer in batch]
            amounts = [
                int(transfer.amount * Decimal(10 ** TOKEN_DECIMALS)) 
                for transfer in batch
            ]
            
            total_amount = sum(transfer.amount for transfer in batch)
            
            # Получение контракта батч-переводов
            batch_contract = self.w3.eth.contract(
                address=BATCH_TRANSFER_CONTRACT,
                abi=self._get_batch_transfer_abi()
            )
            
            # Подготовка транзакции
            tx = batch_contract.functions.batchTransfer(
                TOKEN_ADDRESS,
                recipients,
                amounts
            ).build_transaction({
                'from': self.gas_manager.sender_address,
                'nonce': self.w3.eth.get_transaction_count(self.gas_manager.sender_address),
                'gasPrice': self.w3.eth.gas_price
            })
            
            # Отправка транзакции через gas manager
            tx_hash = self.gas_manager.send_transaction(tx)
            
            # Ожидание подтверждения
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            processing_time = time.time() - start_time
            
            if receipt.status == 1:
                # Успешное выполнение
                result = BatchResult(
                    batch_id=batch_id,
                    tx_hash=tx_hash.hex(),
                    success=True,
                    gas_used=receipt.gasUsed,
                    gas_price=tx['gasPrice'],
                    total_amount=total_amount,
                    recipients_count=len(recipients),
                    processing_time=processing_time,
                    individual_results=[
                        {'recipient': r, 'amount': a, 'success': True} 
                        for r, a in zip(recipients, amounts)
                    ]
                )
                
                logger.info(f\"✅ Батч {batch_id} успешно выполнен за {processing_time:.1f}s\")
                return result
            else:
                # Неудачное выполнение
                raise Exception(f\"Транзакция отклонена: {tx_hash.hex()}\")
                
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(f\"❌ Ошибка выполнения батча {batch_id}: {e}\")
            
            # Попытка индивидуальных переводов как фоллбэк
            individual_results = self._execute_individual_fallback(batch)
            
            return BatchResult(
                batch_id=batch_id,
                success=False,
                error=str(e),
                processing_time=processing_time,
                recipients_count=len(batch),
                individual_results=individual_results
            )
    
    def _execute_individual_fallback(self, batch: List[TransferRequest]) -> List[Dict]:
        \"\"\"Фоллбэк: индивидуальные переводы при неудаче батча.\"\"\"
        logger.warning(f\"🔄 Фоллбэк: выполнение {len(batch)} индивидуальных переводов\")
        
        results = []
        
        for transfer in batch:
            try:
                # Индивидуальный перевод через ERC20 transfer
                tx_hash = self.gas_manager.send_token_transfer(
                    TOKEN_ADDRESS,
                    transfer.recipient,
                    transfer.amount
                )
                
                results.append({
                    'recipient': transfer.recipient,
                    'amount': transfer.amount,
                    'success': True,
                    'tx_hash': tx_hash
                })
                
            except Exception as e:
                logger.error(f\"❌ Ошибка индивидуального перевода {transfer.recipient}: {e}\")
                results.append({
                    'recipient': transfer.recipient,
                    'amount': transfer.amount,
                    'success': False,
                    'error': str(e)
                })
        
        successful = len([r for r in results if r['success']])
        logger.info(f\"📊 Фоллбэк завершен: {successful}/{len(batch)} успешных переводов\")
        
        return results
    
    def _execute_callbacks(self, batch: List[TransferRequest], result: BatchResult):
        \"\"\"Выполнение callback функций.\"\"\"
        for i, transfer in enumerate(batch):
            if transfer.callback:
                try:
                    individual_result = (
                        result.individual_results[i] 
                        if i < len(result.individual_results) 
                        else {'success': False, 'error': 'No result'}
                    )
                    
                    transfer.callback(transfer, individual_result, result)
                    
                except Exception as e:
                    logger.error(f\"❌ Ошибка callback для {transfer.recipient}: {e}\")
      def _get_batch_transfer_abi(self) -> List[Dict]:
        """Получить ABI для батч-переводов."""
        try:
            import json
            import os
            from config.constants import BASE_DIR
            
            abi_path = os.path.join(BASE_DIR, 'config', 'abi', 'batch_transfer.json')
            
            with open(abi_path, 'r', encoding='utf-8') as f:
                abi = json.load(f)
            
            logger.debug("📋 ABI для батч-переводов загружен из файла")
            return abi
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки ABI из файла: {e}, используем упрощенный ABI")
            # Упрощенный ABI для демонстрации
            return [
                {
                    "inputs": [
                        {"name": "token", "type": "address"},
                        {"name": "recipients", "type": "address[]"},
                        {"name": "amounts", "type": "uint256[]"}
                    ],
                    "name": "batchTransfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]


# Экспорт для удобного импорта
__all__ = ['BatchTransactionProcessor', 'TransferRequest', 'BatchResult']


if __name__ == \"__main__\":
    print(\"🧪 Демонстрация BatchTransactionProcessor...\")
    print(\"💡 Этот модуль требует Web3Manager для инициализации\")
    print(\"🎯 Экономия до 70% газа на массовых выплатах\")
