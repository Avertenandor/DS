"""
Модуль: Адаптивная стратегия чанкования для оптимизации getLogs запросов
Описание: Умное определение размера чанков на основе плотности логов и истории ошибок
Зависимости: time, collections, statistics
Автор: GitHub Copilot
"""

import time
import statistics
from typing import List, Dict, Optional, Tuple, Any
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger("ChunkStrategy")


@dataclass
class ChunkResult:
    """Результат выполнения чанка"""
    chunk_size: int
    logs_count: int
    execution_time: float
    success: bool
    error_type: Optional[str] = None
    block_range: Optional[Tuple[int, int]] = None


class AdaptiveChunkStrategy:
    """Умное определение размера чанка на основе плотности логов и истории"""
    
    def __init__(self, initial_chunk_size: int = 2000, 
                 max_logs_per_request: int = 750,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 5000):
        
        self.initial_chunk_size = initial_chunk_size
        self.max_logs_per_request = max_logs_per_request
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # История результатов для обучения
        self.history: deque[ChunkResult] = deque(maxlen=100)
        
        # Статистика по типам ошибок
        self.error_stats = defaultdict(int)
        
        # Адаптивные параметры
        self.current_optimal_size = initial_chunk_size
        self.last_adjustment_time = time.time()
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        
        # Контекстная информация
        self.contract_densities = {}  # плотность логов по контрактам
        self.time_period_densities = {}  # плотность по временным периодам
        
        logger.info(f"🧠 AdaptiveChunkStrategy инициализирована:")
        logger.info(f"   Initial size: {initial_chunk_size}")
        logger.info(f"   Max logs per request: {max_logs_per_request}")
        logger.info(f"   Size range: {min_chunk_size} - {max_chunk_size}")
    
    def get_optimal_chunk_size(self, start_block: int, 
                             contract_address: Optional[str] = None,
                             estimated_period: Optional[str] = None) -> int:
        """Получить оптимальный размер чанка для текущего контекста"""
        
        # Базовый размер на основе общей истории
        base_size = self._calculate_base_size()
        
        # Корректировка на основе контракта
        contract_multiplier = self._get_contract_multiplier(contract_address)
        
        # Корректировка на основе временного периода
        period_multiplier = self._get_period_multiplier(estimated_period)
        
        # Корректировка на основе недавних ошибок
        error_multiplier = self._get_error_multiplier()
        
        # Итоговый размер
        optimal_size = int(base_size * contract_multiplier * period_multiplier * error_multiplier)
        
        # Ограничиваем диапазоном
        optimal_size = max(self.min_chunk_size, min(optimal_size, self.max_chunk_size))
        
        logger.debug(f"📊 Оптимальный размер чанка: {optimal_size}")
        logger.debug(f"   Base: {base_size}, Contract: {contract_multiplier:.2f}")
        logger.debug(f"   Period: {period_multiplier:.2f}, Error: {error_multiplier:.2f}")
        
        return optimal_size
    
    def _calculate_base_size(self) -> int:
        """Рассчитать базовый размер на основе истории"""
        if not self.history:
            return self.initial_chunk_size
        
        # Анализируем успешные запросы за последние 20 попыток
        recent_successes = [
            result for result in list(self.history)[-20:]
            if result.success and result.logs_count > 0
        ]
        
        if not recent_successes:
            return self.initial_chunk_size
        
        # Находим оптимальную плотность логов
        densities = [result.logs_count / result.chunk_size for result in recent_successes]
        avg_density = statistics.mean(densities)
        
        if avg_density > 0:
            # Рассчитываем размер для достижения целевого количества логов
            target_size = int(self.max_logs_per_request / avg_density)
            return max(self.min_chunk_size, min(target_size, self.max_chunk_size))
        
        return self.initial_chunk_size
    
    def _get_contract_multiplier(self, contract_address: Optional[str]) -> float:
        """Получить множитель для конкретного контракта"""
        if not contract_address or contract_address not in self.contract_densities:
            return 1.0
        
        density = self.contract_densities[contract_address]
        
        # Чем выше плотность, тем меньше чанк
        if density > 2.0:  # Высокая плотность
            return 0.3
        elif density > 1.0:  # Средняя плотность
            return 0.6
        elif density > 0.5:  # Низкая плотность
            return 0.8
        else:  # Очень низкая плотность
            return 1.5
    
    def _get_period_multiplier(self, estimated_period: Optional[str]) -> float:
        """Получить множитель для временного периода"""
        if not estimated_period:
            return 1.0
        
        # Известные периоды высокой активности
        high_activity_periods = ['2024-11', '2024-12', '2025-01']  # Примеры
        
        if estimated_period in high_activity_periods:
            return 0.4  # Уменьшаем чанк для периодов высокой активности
        
        # Анализируем сохраненную статистику периода
        if estimated_period in self.time_period_densities:
            density = self.time_period_densities[estimated_period]
            return max(0.2, min(2.0, 1.0 / max(0.5, density)))
        
        return 1.0
    
    def _get_error_multiplier(self) -> float:
        """Получить множитель на основе недавних ошибок"""
        if not self.history:
            return 1.0
        
        # Анализируем последние 10 попыток
        recent = list(self.history)[-10:]
        recent_errors = [r for r in recent if not r.success]
        
        if not recent_errors:
            # Нет недавних ошибок - можно увеличить размер
            return min(1.2, 1.0 + (self.consecutive_successes * 0.05))
        
        # Есть ошибки - анализируем тип
        payload_errors = sum(1 for r in recent_errors if r.error_type == 'payload_too_large')
        timeout_errors = sum(1 for r in recent_errors if r.error_type == 'timeout')
        
        if payload_errors > 0:
            # Серьезно уменьшаем размер при ошибках payload
            return max(0.1, 0.5 ** payload_errors)
        
        if timeout_errors > 0:
            # Умеренно уменьшаем при таймаутах
            return max(0.3, 0.8 ** timeout_errors)
        
        # Другие ошибки - небольшое уменьшение
        return max(0.7, 1.0 - (len(recent_errors) * 0.1))
    
    def record_result(self, chunk_size: int, logs_count: int, 
                     execution_time: float, success: bool,
                     error_type: Optional[str] = None,
                     block_range: Optional[Tuple[int, int]] = None,
                     contract_address: Optional[str] = None):
        """Записать результат выполнения чанка для обучения"""
        
        result = ChunkResult(
            chunk_size=chunk_size,
            logs_count=logs_count,
            execution_time=execution_time,
            success=success,
            error_type=error_type,
            block_range=block_range
        )
        
        self.history.append(result)
        
        # Обновляем счетчики
        if success:
            self.consecutive_successes += 1
            self.consecutive_errors = 0
        else:
            self.consecutive_errors += 1
            self.consecutive_successes = 0
            self.error_stats[error_type or 'unknown'] += 1
        
        # Обновляем статистику контракта
        if contract_address and success and logs_count > 0:
            density = logs_count / chunk_size
            if contract_address in self.contract_densities:
                # Экспоненциальное сглаживание
                old_density = self.contract_densities[contract_address]
                self.contract_densities[contract_address] = 0.7 * old_density + 0.3 * density
            else:
                self.contract_densities[contract_address] = density
        
        # Логирование
        status = "✅" if success else "❌"
        logger.debug(f"{status} Чанк {chunk_size} блоков: {logs_count} логов за {execution_time:.2f}s")
        
        if not success:
            logger.warning(f"⚠️ Ошибка чанка: {error_type}")
    
    def handle_payload_too_large(self, current_chunk_size: int) -> int:
        """Обработка ошибки 'payload too large'"""
        # Агрессивно уменьшаем размер
        new_size = max(self.min_chunk_size, current_chunk_size // 4)
        
        # Записываем в историю искусственные данные высокой плотности
        self.record_result(
            chunk_size=current_chunk_size,
            logs_count=2000,  # Имитируем высокую плотность
            execution_time=0,
            success=False,
            error_type='payload_too_large'
        )
        
        logger.warning(f"🚨 Payload too large! Уменьшаем чанк: {current_chunk_size} → {new_size}")
        return new_size
    
    def handle_timeout(self, current_chunk_size: int) -> int:
        """Обработка таймаута"""
        # Умеренно уменьшаем размер
        new_size = max(self.min_chunk_size, int(current_chunk_size * 0.7))
        
        self.record_result(
            chunk_size=current_chunk_size,
            logs_count=0,
            execution_time=30.0,  # Предполагаем таймаут
            success=False,
            error_type='timeout'
        )
        
        logger.warning(f"⏰ Timeout! Уменьшаем чанк: {current_chunk_size} → {new_size}")
        return new_size
    
    def suggest_progressive_chunks(self, total_blocks: int, 
                                 start_block: int,
                                 contract_address: Optional[str] = None) -> List[Tuple[int, int]]:
        """Предложить прогрессивную стратегию чанков для большого диапазона"""
        chunks = []
        current_start = start_block
        
        while current_start < start_block + total_blocks:
            # Получаем оптимальный размер для текущей позиции
            chunk_size = self.get_optimal_chunk_size(
                current_start, 
                contract_address=contract_address
            )
            
            # Ограничиваем концом диапазона
            chunk_end = min(current_start + chunk_size - 1, start_block + total_blocks - 1)
            
            chunks.append((current_start, chunk_end))
            current_start = chunk_end + 1
        
        logger.info(f"📋 Сгенерировано {len(chunks)} чанков для {total_blocks} блоков")
        logger.info(f"   Размеры: {[end - start + 1 for start, end in chunks[:5]]}... (первые 5)")
        
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика стратегии чанкования"""
        if not self.history:
            return {'status': 'no_data'}
        
        total_requests = len(self.history)
        successful_requests = sum(1 for r in self.history if r.success)
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Анализ размеров чанков
        chunk_sizes = [r.chunk_size for r in self.history if r.success]
        avg_chunk_size = statistics.mean(chunk_sizes) if chunk_sizes else 0
        
        # Анализ производительности
        execution_times = [r.execution_time for r in self.history if r.success]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        
        # Анализ плотности логов
        densities = [
            r.logs_count / r.chunk_size 
            for r in self.history 
            if r.success and r.chunk_size > 0
        ]
        avg_density = statistics.mean(densities) if densities else 0
        
        return {
            'total_requests': total_requests,
            'success_rate': f"{success_rate:.1f}%",
            'current_optimal_size': self.current_optimal_size,
            'avg_chunk_size': int(avg_chunk_size),
            'avg_execution_time': f"{avg_execution_time:.2f}s",
            'avg_log_density': f"{avg_density:.3f}",
            'consecutive_successes': self.consecutive_successes,
            'consecutive_errors': self.consecutive_errors,
            'error_stats': dict(self.error_stats),
            'known_contracts': len(self.contract_densities),
            'contract_densities': {
                addr: f"{density:.3f}" 
                for addr, density in list(self.contract_densities.items())[:5]
            }
        }
    
    def reset_strategy(self):
        """Сброс стратегии к начальным значениям"""
        self.history.clear()
        self.error_stats.clear()
        self.contract_densities.clear()
        self.time_period_densities.clear()
        self.current_optimal_size = self.initial_chunk_size
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        
        logger.info("🔄 Стратегия чанкования сброшена к начальным значениям")


class ProgressiveChunkManager:
    """Менеджер прогрессивного чанкования для больших диапазонов"""
    
    def __init__(self, strategy: AdaptiveChunkStrategy):
        self.strategy = strategy
        self.current_progress = 0
        self.total_progress = 0
        self.start_time = 0
        
    def process_large_range(self, start_block: int, end_block: int,
                          fetch_func, contract_address: Optional[str] = None,
                          progress_callback=None) -> List[Any]:
        """Обработка большого диапазона блоков с прогрессивным чанкованием"""
        
        total_blocks = end_block - start_block + 1
        self.total_progress = total_blocks
        self.current_progress = 0
        self.start_time = time.time()
        
        logger.info(f"🚀 Начинаем прогрессивную обработку {total_blocks:,} блоков")
        logger.info(f"   Диапазон: {start_block:,} - {end_block:,}")
        
        # Генерируем чанки
        chunks = self.strategy.suggest_progressive_chunks(
            total_blocks, start_block, contract_address
        )
        
        all_results = []
        processed_blocks = 0
        
        for i, (chunk_start, chunk_end) in enumerate(chunks):
            chunk_size = chunk_end - chunk_start + 1
            
            try:
                # Засекаем время
                start_time = time.time()
                
                # Выполняем запрос
                chunk_results = fetch_func(chunk_start, chunk_end)
                
                # Записываем успех
                execution_time = time.time() - start_time
                self.strategy.record_result(
                    chunk_size=chunk_size,
                    logs_count=len(chunk_results) if hasattr(chunk_results, '__len__') else 0,
                    execution_time=execution_time,
                    success=True,
                    block_range=(chunk_start, chunk_end),
                    contract_address=contract_address
                )
                
                all_results.extend(chunk_results if hasattr(chunk_results, '__iter__') else [chunk_results])
                processed_blocks += chunk_size
                self.current_progress = processed_blocks
                
                # Обновляем прогресс
                if progress_callback:
                    progress_pct = (processed_blocks / total_blocks) * 100
                    elapsed = time.time() - self.start_time
                    estimated_total = (elapsed / processed_blocks) * total_blocks if processed_blocks > 0 else 0
                    remaining = max(0, estimated_total - elapsed)
                    
                    progress_callback({
                        'current': processed_blocks,
                        'total': total_blocks,
                        'percentage': progress_pct,
                        'elapsed': elapsed,
                        'estimated_remaining': remaining,
                        'chunks_completed': i + 1,
                        'total_chunks': len(chunks)
                    })
                
                logger.debug(f"✅ Чанк {i+1}/{len(chunks)}: {chunk_size} блоков за {execution_time:.2f}s")
                
            except Exception as e:
                error_type = self._classify_error(e)
                execution_time = time.time() - start_time
                
                # Записываем ошибку
                self.strategy.record_result(
                    chunk_size=chunk_size,
                    logs_count=0,
                    execution_time=execution_time,
                    success=False,
                    error_type=error_type,
                    block_range=(chunk_start, chunk_end),
                    contract_address=contract_address
                )
                
                # Обрабатываем специфичные ошибки
                if error_type == 'payload_too_large':
                    logger.error(f"❌ Payload too large для чанка {chunk_start}-{chunk_end}")
                    # Пробуем разбить чанк пополам
                    if chunk_size > self.strategy.min_chunk_size * 2:
                        mid_block = (chunk_start + chunk_end) // 2
                        
                        # Добавляем два новых чанка в очередь
                        chunks.insert(i + 1, (chunk_start, mid_block))
                        chunks.insert(i + 2, (mid_block + 1, chunk_end))
                        
                        logger.info(f"🔄 Разбиваем чанк на два: {chunk_start}-{mid_block}, {mid_block+1}-{chunk_end}")
                        continue
                
                logger.error(f"❌ Ошибка в чанке {chunk_start}-{chunk_end}: {e}")
                raise
        
        elapsed_total = time.time() - self.start_time
        
        logger.info(f"✅ Прогрессивная обработка завершена:")
        logger.info(f"   Обработано блоков: {processed_blocks:,}")
        logger.info(f"   Время выполнения: {elapsed_total:.1f}s")
        logger.info(f"   Средняя скорость: {processed_blocks/elapsed_total:.1f} блоков/сек")
        logger.info(f"   Всего результатов: {len(all_results):,}")
        
        return all_results
    
    def _classify_error(self, error: Exception) -> str:
        """Классификация типа ошибки"""
        error_str = str(error).lower()
        
        if 'payload too large' in error_str or '413' in error_str:
            return 'payload_too_large'
        elif 'timeout' in error_str or 'timed out' in error_str:
            return 'timeout'
        elif 'rate limit' in error_str or '429' in error_str:
            return 'rate_limit'
        elif 'connection' in error_str:
            return 'connection_error'
        else:
            return 'unknown'


if __name__ == "__main__":
    # Тестирование адаптивной стратегии
    print("🧪 Тестирование AdaptiveChunkStrategy...")
    
    strategy = AdaptiveChunkStrategy()
    
    # Симулируем несколько запросов
    test_scenarios = [
        # (chunk_size, logs_count, execution_time, success, error_type)
        (2000, 500, 1.2, True, None),  # Нормальный запрос
        (2000, 1500, 3.5, False, 'payload_too_large'),  # Слишком много логов
        (500, 200, 0.8, True, None),  # Уменьшенный размер работает
        (500, 150, 0.7, True, None),  # Продолжаем с малым размером
        (750, 300, 1.0, True, None),  # Постепенно увеличиваем
        (1000, 400, 1.3, True, None),  # Еще увеличиваем
        (1500, 800, 2.1, True, None),  # Хороший результат
    ]
    
    for i, (chunk_size, logs_count, exec_time, success, error_type) in enumerate(test_scenarios):
        strategy.record_result(chunk_size, logs_count, exec_time, success, error_type)
        
        optimal = strategy.get_optimal_chunk_size(100000 + i * 1000)
        print(f"Запрос {i+1}: оптимальный размер = {optimal}")
    
    print(f"\n📊 Итоговая статистика:")
    stats = strategy.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Тест прогрессивных чанков
    print(f"\n📋 Тест прогрессивных чанков:")
    chunks = strategy.suggest_progressive_chunks(
        total_blocks=10000,
        start_block=50000000,
        contract_address="0x41d9650faf3341cbf8947fd8063a1fc88dbf1889"
    )
    
    print(f"Сгенерировано {len(chunks)} чанков:")
    for i, (start, end) in enumerate(chunks[:3]):
        print(f"  Чанк {i+1}: {start} - {end} ({end-start+1} блоков)")
    
    print("\n✅ AdaptiveChunkStrategy тестирована успешно")
