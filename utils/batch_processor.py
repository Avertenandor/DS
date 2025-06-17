"""
PLEX Dynamic Staking Manager - Batch Processor

Система массовых операций для оптимизации API запросов:
- Батчинг blockchain запросов
- Массовая обработка участников
- Оптимизация базы данных
- Прогресс-трекинг

Автор: GitHub Copilot
Дата: 2024
Версия: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from config.settings import settings
from utils.logger import get_logger
from utils.retry import blockchain_retry
# Import Web3Manager внутри функций для избежания циклических импортов
from utils.multicall_manager import MulticallManager

logger = get_logger(__name__)

@dataclass
class BatchTask:
    """Задача для батч-обработки"""
    task_id: str
    task_type: str  # 'blockchain_read', 'blockchain_write', 'database', 'analysis'
    data: Any
    priority: int = 1  # 1 = высокий, 5 = низкий
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)
    
@dataclass
class BatchResult:
    """Результат батч-обработки"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    processing_time: float = 0.0
    completed_at: datetime = field(default_factory=datetime.now)

@dataclass
class BatchProgress:
    """Прогресс батч-обработки"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    current_batch: int
    total_batches: int
    estimated_completion: Optional[datetime] = None
    
    @property
    def completion_percentage(self) -> float:
        """Процент завершения"""
        if self.total_tasks == 0:
            return 100.0
        return (self.completed_tasks / self.total_tasks) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Процент успешных операций"""
        processed = self.completed_tasks + self.failed_tasks
        if processed == 0:
            return 100.0
        return (self.completed_tasks / processed) * 100.0

class BatchProcessor:
    """Обработчик массовых операций"""
    
    def __init__(self, 
                 max_workers: int = 5,
                 batch_size: int = 100,
                 max_retries: int = 3):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.max_retries = max_retries
          # Очереди задач по приоритету
        self.task_queues = {
            1: queue.PriorityQueue(),  # Высокий приоритет
            2: queue.PriorityQueue(),
            3: queue.PriorityQueue(),  # Средний приоритет
            4: queue.PriorityQueue(),
            5: queue.PriorityQueue()   # Низкий приоритет
        }
        
        self.results: Dict[str, BatchResult] = {}
        self.progress: Optional[BatchProgress] = None
        self.is_processing = False
        self.lock = threading.Lock()
        
        # Менеджеры для работы с blockchain (lazy import для избежания циклических импортов)
        self.web3_manager = None
        self.multicall_manager = None        
        logger.info(f"BatchProcessor инициализирован: workers={max_workers}, batch_size={batch_size}")
    
    def _ensure_managers(self):
        """Ленивая инициализация менеджеров для избежания циклических импортов"""
        if self.web3_manager is None:
            from blockchain.node_client import Web3Manager
            self.web3_manager = Web3Manager()
            
        if self.multicall_manager is None:
            self.multicall_manager = MulticallManager(self.web3_manager.w3_http)
    
    def add_task(self, task: BatchTask) -> str:
        """Добавление задачи в очередь"""
        try:
            priority = max(1, min(5, task.priority))  # Ограничиваем приоритет
            
            # Добавляем timestamp для уникальности в PriorityQueue
            queue_item = (task.created_at.timestamp(), task)
            self.task_queues[priority].put(queue_item)
            
            logger.debug(f"Задача добавлена: {task.task_id} (приоритет: {priority})")
            return task.task_id
            
        except Exception as e:
            logger.error(f"Ошибка добавления задачи: {e}")
            raise
    
    def add_blockchain_read_tasks(self, 
                                addresses: List[str], 
                                method: str,
                                contract_address: str,
                                abi: List[Dict],
                                priority: int = 3) -> List[str]:
        """Добавление задач чтения blockchain"""
        task_ids = []
        
        for i, address in enumerate(addresses):
            task_id = f"blockchain_read_{method}_{i}_{int(time.time())}"
            task = BatchTask(
                task_id=task_id,
                task_type="blockchain_read",
                data={
                    "address": address,
                    "method": method,
                    "contract_address": contract_address,
                    "abi": abi
                },
                priority=priority
            )
            self.add_task(task)
            task_ids.append(task_id)
        
        logger.info(f"Добавлено {len(task_ids)} задач чтения blockchain")
        return task_ids
    
    def add_balance_check_tasks(self, 
                              addresses: List[str],
                              priority: int = 2) -> List[str]:
        """Добавление задач проверки балансов"""
        task_ids = []
        
        for i, address in enumerate(addresses):
            task_id = f"balance_check_{i}_{int(time.time())}"
            task = BatchTask(
                task_id=task_id,
                task_type="balance_check",
                data={"address": address},
                priority=priority
            )
            self.add_task(task)
            task_ids.append(task_id)
        
        logger.info(f"Добавлено {len(task_ids)} задач проверки балансов")
        return task_ids
    
    def add_analysis_tasks(self, 
                         participants_data: List[Dict],
                         analysis_type: str,
                         priority: int = 3) -> List[str]:
        """Добавление задач анализа"""
        task_ids = []
        
        for i, data in enumerate(participants_data):
            task_id = f"analysis_{analysis_type}_{i}_{int(time.time())}"
            task = BatchTask(
                task_id=task_id,
                task_type="analysis",
                data={
                    "participant_data": data,
                    "analysis_type": analysis_type
                },
                priority=priority
            )
            self.add_task(task)
            task_ids.append(task_id)
        
        logger.info(f"Добавлено {len(task_ids)} задач анализа")
        return task_ids
    
    def get_next_task(self) -> Optional[BatchTask]:
        """Получение следующей задачи по приоритету"""
        # Проверяем очереди в порядке приоритета
        for priority in range(1, 6):
            try:
                if not self.task_queues[priority].empty():
                    _, task = self.task_queues[priority].get_nowait()
                    return task
            except queue.Empty:
                continue
        
        return None
    
    def get_total_pending_tasks(self) -> int:
        """Получение общего количества ожидающих задач"""
        total = 0
        for priority_queue in self.task_queues.values():
            total += priority_queue.qsize()    @blockchain_retry(max_attempts=3)
    def process_blockchain_read_task(self, task: BatchTask) -> BatchResult:
        """Обработка задачи чтения blockchain"""
        start_time = time.time()
        
        try:
            data = task.data
            address = data["address"]
            method = data["method"]
            contract_address = data["contract_address"]
            abi = data["abi"]
            
            # Инициализируем менеджеры при необходимости
            self._ensure_managers()
            
            # Создаем контракт
            contract = self.web3_manager.w3.eth.contract(
                address=contract_address,
                abi=abi
            )
            
            # Вызываем метод
            if hasattr(contract.functions, method):
                func = getattr(contract.functions, method)
                result = func(address).call()
            else:
                raise ValueError(f"Метод {method} не найден в контракте")
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Ошибка обработки blockchain задачи {task.task_id}: {e}")
            
            return BatchResult(
                task_id=task.task_id,
                success=False,                error=str(e),
                processing_time=processing_time
            )
    
    @blockchain_retry(max_attempts=3)
    def process_balance_check_task(self, task: BatchTask) -> BatchResult:
        """Обработка задачи проверки баланса"""
        start_time = time.time()
        
        try:
            address = task.data["address"]
            
            # Инициализируем менеджеры при необходимости
            self._ensure_managers()
            
            # Получаем баланс ETH
            balance_wei = self.web3_manager.w3.eth.get_balance(address)
            balance_eth = self.web3_manager.w3.from_wei(balance_wei, 'ether')
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                task_id=task.task_id,
                success=True,
                result={
                    "address": address,
                    "balance_wei": balance_wei,
                    "balance_eth": float(balance_eth)
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Ошибка проверки баланса {task.task_id}: {e}")
            
            return BatchResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def process_analysis_task(self, task: BatchTask) -> BatchResult:
        """Обработка задачи анализа"""
        start_time = time.time()
        
        try:
            data = task.data
            participant_data = data["participant_data"]
            analysis_type = data["analysis_type"]
            
            # Заглушка для различных типов анализа
            if analysis_type == "category_analysis":
                result = self._analyze_category(participant_data)
            elif analysis_type == "eligibility_analysis":
                result = self._analyze_eligibility(participant_data)
            elif analysis_type == "reward_calculation":
                result = self._calculate_rewards(participant_data)
            else:
                raise ValueError(f"Неизвестный тип анализа: {analysis_type}")
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Ошибка анализа {task.task_id}: {e}")
            
            return BatchResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def _analyze_category(self, participant_data: Dict) -> Dict:
        """Анализ категории участника"""
        # Заглушка - реальная логика будет в category_analyzer
        return {
            "address": participant_data.get("address"),
            "category": "whale",  # Заглушка
            "confidence": 0.95
        }
    
    def _analyze_eligibility(self, participant_data: Dict) -> Dict:
        """Анализ права на награды"""
        # Заглушка - реальная логика будет в eligibility
        return {
            "address": participant_data.get("address"),
            "eligible": True,
            "tier": "gold",
            "score": 85.5
        }
    
    def _calculate_rewards(self, participant_data: Dict) -> Dict:
        """Расчет наград"""
        # Заглушка - реальная логика будет в reward_manager
        return {
            "address": participant_data.get("address"),
            "reward_amount": Decimal("100.5"),
            "bonus_multiplier": 1.2
        }
    
    def process_task(self, task: BatchTask) -> BatchResult:
        """Обработка одной задачи"""
        try:
            if task.task_type == "blockchain_read":
                return self.process_blockchain_read_task(task)
            elif task.task_type == "balance_check":
                return self.process_balance_check_task(task)
            elif task.task_type == "analysis":
                return self.process_analysis_task(task)
            else:
                return BatchResult(
                    task_id=task.task_id,
                    success=False,
                    error=f"Неизвестный тип задачи: {task.task_type}"
                )
                
        except Exception as e:
            logger.error(f"Критическая ошибка обработки задачи {task.task_id}: {e}")
            return BatchResult(
                task_id=task.task_id,
                success=False,
                error=str(e)
            )
    
    def process_batch(self, 
                     batch_tasks: List[BatchTask],
                     progress_callback: Optional[Callable] = None) -> List[BatchResult]:
        """Обработка батча задач"""
        results = []
        
        # Группируем задачи по типу для оптимизации
        tasks_by_type = {}
        for task in batch_tasks:
            if task.task_type not in tasks_by_type:
                tasks_by_type[task.task_type] = []
            tasks_by_type[task.task_type].append(task)
        
        # Обрабатываем каждый тип задач
        for task_type, type_tasks in tasks_by_type.items():
            if task_type == "blockchain_read" and len(type_tasks) > 1:
                # Используем multicall для оптимизации
                batch_results = self._process_multicall_batch(type_tasks)
            else:
                # Обычная обработка
                batch_results = []
                for task in type_tasks:
                    result = self.process_task(task)
                    batch_results.append(result)
                    
                    if progress_callback:
                        progress_callback(result)
            
            results.extend(batch_results)
        
        return results
    
    def _process_multicall_batch(self, tasks: List[BatchTask]) -> List[BatchResult]:
        """Обработка батча blockchain задач через multicall"""
        try:
            # Группируем по контракту
            calls_by_contract = {}
            task_mapping = {}
            
            for task in tasks:
                data = task.data
                contract_address = data["contract_address"]
                method = data["method"]
                address = data["address"]
                
                if contract_address not in calls_by_contract:
                    calls_by_contract[contract_address] = {
                        "abi": data["abi"],
                        "calls": []                    }
                
                call_id = f"{method}_{address}"
                calls_by_contract[contract_address]["calls"].append({
                    "method": method,
                    "params": [address],
                    "call_id": call_id
                })
                task_mapping[call_id] = task
            
            results = []
            
            # Инициализируем менеджеры при необходимости
            self._ensure_managers()
            
            # Выполняем multicall для каждого контракта
            for contract_address, contract_data in calls_by_contract.items():
                try:
                    multicall_results = self.multicall_manager.execute_batch(
                        contract_address,
                        contract_data["abi"],
                        contract_data["calls"]
                    )
                    
                    # Обрабатываем результаты
                    for call_id, call_result in multicall_results.items():
                        task = task_mapping[call_id]
                        
                        if call_result["success"]:
                            result = BatchResult(
                                task_id=task.task_id,
                                success=True,
                                result=call_result["result"]
                            )
                        else:
                            result = BatchResult(
                                task_id=task.task_id,
                                success=False,
                                error=call_result["error"]
                            )
                        
                        results.append(result)
                        
                except Exception as e:
                    # Если multicall не удался, обрабатываем задачи по отдельности
                    logger.warning(f"Multicall не удался для {contract_address}, переключаемся на обычную обработку: {e}")
                    
                    for call_data in contract_data["calls"]:
                        call_id = call_data["call_id"]
                        task = task_mapping[call_id]
                        result = self.process_task(task)
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка multicall обработки: {e}")
            # Fallback к обычной обработке
            return [self.process_task(task) for task in tasks]
    
    def process_all_tasks(self, 
                         progress_callback: Optional[Callable] = None) -> Dict[str, BatchResult]:
        """Обработка всех задач в очередях"""
        with self.lock:
            if self.is_processing:
                raise RuntimeError("Обработка уже выполняется")
            
            self.is_processing = True
        
        try:
            total_tasks = self.get_total_pending_tasks()
            if total_tasks == 0:
                logger.info("Нет задач для обработки")
                return {}
            
            # Инициализация прогресса
            self.progress = BatchProgress(
                total_tasks=total_tasks,
                completed_tasks=0,
                failed_tasks=0,
                current_batch=0,
                total_batches=(total_tasks + self.batch_size - 1) // self.batch_size
            )
            
            logger.info(f"Начинаем обработку {total_tasks} задач в {self.progress.total_batches} батчах")
            
            all_results = {}
            batch_num = 0
            
            # Функция для обновления прогресса
            def update_progress(result: BatchResult):
                with self.lock:
                    if result.success:
                        self.progress.completed_tasks += 1
                    else:
                        self.progress.failed_tasks += 1
                    
                    all_results[result.task_id] = result
                    
                    if progress_callback:
                        progress_callback(self.progress, result)
            
            # Обрабатываем задачи батчами
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while self.get_total_pending_tasks() > 0:
                    batch_num += 1
                    self.progress.current_batch = batch_num
                    
                    # Собираем батч задач
                    batch_tasks = []
                    for _ in range(self.batch_size):
                        task = self.get_next_task()
                        if task is None:
                            break
                        batch_tasks.append(task)
                    
                    if not batch_tasks:
                        break
                    
                    logger.info(f"Обрабатываем батч {batch_num}/{self.progress.total_batches} ({len(batch_tasks)} задач)")
                    
                    # Обрабатываем батч
                    batch_results = self.process_batch(batch_tasks, update_progress)
                    
                    # Обновляем результаты
                    for result in batch_results:
                        all_results[result.task_id] = result
            
            # Сохраняем результаты
            self.results.update(all_results)
            
            logger.info(f"Обработка завершена: {self.progress.completed_tasks} успешно, {self.progress.failed_tasks} с ошибками")
            
            return all_results
            
        finally:
            with self.lock:
                self.is_processing = False
    
    def get_results(self, task_ids: Optional[List[str]] = None) -> Dict[str, BatchResult]:
        """Получение результатов обработки"""
        if task_ids is None:
            return self.results.copy()
        
        return {task_id: self.results[task_id] 
                for task_id in task_ids 
                if task_id in self.results}
    
    def get_progress(self) -> Optional[BatchProgress]:
        """Получение текущего прогресса"""
        return self.progress
    
    def clear_completed_tasks(self) -> int:
        """Очистка завершенных задач"""
        completed_count = len(self.results)
        self.results.clear()
        logger.info(f"Очищено {completed_count} завершенных задач")
        return completed_count
    
    def get_statistics(self) -> Dict:
        """Получение статистики обработки"""
        if not self.results:
            return {"total_processed": 0}
        
        successful = sum(1 for r in self.results.values() if r.success)
        failed = len(self.results) - successful
        avg_processing_time = sum(r.processing_time for r in self.results.values()) / len(self.results)
        
        return {
            "total_processed": len(self.results),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(self.results)) * 100,
            "average_processing_time": avg_processing_time,            "pending_tasks": self.get_total_pending_tasks(),
            "is_processing": self.is_processing
        }
