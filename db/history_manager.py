"""
PLEX Dynamic Staking Manager - History Manager

Система логирования и управления историей операций:
- Детальное логирование всех операций
- Аудит системы
- Восстановление после сбоев
- Анализ производительности

Автор: GitHub Copilot
Дата: 2024
Версия: 1.0.0
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal
from enum import Enum
import gzip
import os

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class OperationType(Enum):
    """Типы операций для логирования"""
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete" 
    PARTICIPANT_CATEGORIZED = "participant_categorized"
    REWARD_CALCULATED = "reward_calculated"
    PAYMENT_REGISTERED = "payment_registered"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"
    BLOCKCHAIN_QUERY = "blockchain_query"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGED = "config_changed"
    DATABASE_BACKUP = "database_backup"
    DATA_EXPORT = "data_export"

@dataclass
class HistoryRecord:
    """Запись в истории операций"""
    id: str
    timestamp: datetime
    operation_type: OperationType
    user_id: Optional[str]
    session_id: str
    component: str  # blockchain, analyzer, ui, database, etc.
    details: Dict[str, Any]
    success: bool
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для сериализации"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['operation_type'] = self.operation_type.value
        
        # Конвертируем Decimal в строки
        data['details'] = self._convert_decimals(data['details'])
        if data['metadata']:
            data['metadata'] = self._convert_decimals(data['metadata'])
        
        return data
    
    def _convert_decimals(self, obj: Any) -> Any:
        """Рекурсивная конвертация Decimal в строки"""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HistoryRecord':
        """Создание из словаря"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['operation_type'] = OperationType(data['operation_type'])
        return cls(**data)

class HistoryManager:
    """Менеджер истории операций"""
    
    def __init__(self, db_path: Optional[str] = None, session_id: Optional[str] = None):
        # Определяем путь к БД
        if db_path is None:
            base_dir = getattr(settings, 'BASE_DIR', '.')
            db_path = os.path.join(base_dir, "data", "history.db")
        
        self.db_path = db_path
        self.session_id = session_id or f"session_{int(datetime.now().timestamp())}"
        self.lock = threading.Lock()
        
        # Убеждаемся что директория существует
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
        self._log_system_start()
        
        logger.info(f"HistoryManager инициализирован (session: {self.session_id})")
    
    def _init_database(self):
        """Инициализация базы данных истории"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS operation_history (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        user_id TEXT,
                        session_id TEXT NOT NULL,
                        component TEXT NOT NULL,
                        details TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        execution_time_ms REAL,
                        error_message TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Индексы для быстрого поиска
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_timestamp ON operation_history(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_operation_type ON operation_history(operation_type)",
                    "CREATE INDEX IF NOT EXISTS idx_session ON operation_history(session_id)",
                    "CREATE INDEX IF NOT EXISTS idx_component ON operation_history(component)",
                    "CREATE INDEX IF NOT EXISTS idx_success ON operation_history(success)",
                    "CREATE INDEX IF NOT EXISTS idx_user_session ON operation_history(user_id, session_id)"
                ]
                
                for index_sql in indexes:
                    conn.execute(index_sql)
                
                # Таблица для архивных данных
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS operation_history_archive (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        user_id TEXT,
                        session_id TEXT NOT NULL,
                        component TEXT NOT NULL,
                        details TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        execution_time_ms REAL,
                        error_message TEXT,
                        metadata TEXT,
                        archived_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("База данных истории операций инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД истории: {e}")
            raise
    
    def _log_system_start(self):
        """Логирование запуска системы"""
        self.log_operation(
            operation_type=OperationType.SYSTEM_START,
            component="system",
            details={
                "version": "1.0.0",
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat()
            },
            success=True
        )
    
    def generate_record_id(self) -> str:
        """Генерация уникального ID записи"""
        import uuid
        return f"hist_{uuid.uuid4().hex[:16]}"
    
    def log_operation(self,
                     operation_type: OperationType,
                     component: str,
                     details: Dict[str, Any],
                     success: bool,
                     user_id: Optional[str] = None,
                     execution_time_ms: Optional[float] = None,
                     error_message: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Логирование операции
        
        Returns:
            str: ID созданной записи
        """
        with self.lock:
            try:
                record = HistoryRecord(
                    id=self.generate_record_id(),
                    timestamp=datetime.now(),
                    operation_type=operation_type,
                    user_id=user_id,
                    session_id=self.session_id,
                    component=component,
                    details=details,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_message=error_message,
                    metadata=metadata
                )
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO operation_history 
                        (id, timestamp, operation_type, user_id, session_id, 
                         component, details, success, execution_time_ms, 
                         error_message, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.id,
                        record.timestamp.isoformat(),
                        record.operation_type.value,
                        record.user_id,
                        record.session_id,
                        record.component,
                        json.dumps(record.details),
                        record.success,
                        record.execution_time_ms,
                        record.error_message,
                        json.dumps(record.metadata) if record.metadata else None
                    ))
                    conn.commit()
                
                logger.debug(f"Операция залогирована: {record.id} ({operation_type.value})")
                return record.id
                
            except Exception as e:
                logger.error(f"Ошибка логирования операции: {e}")
                raise
    
    def log_analysis_start(self, 
                          analysis_type: str,
                          parameters: Dict[str, Any],
                          user_id: Optional[str] = None) -> str:
        """Логирование начала анализа"""
        return self.log_operation(
            operation_type=OperationType.ANALYSIS_START,
            component="analyzer",
            details={
                "analysis_type": analysis_type,
                "parameters": parameters
            },
            success=True,
            user_id=user_id
        )
    
    def log_analysis_complete(self,
                            analysis_type: str,
                            participants_processed: int,
                            execution_time_ms: float,
                            user_id: Optional[str] = None) -> str:
        """Логирование завершения анализа"""
        return self.log_operation(
            operation_type=OperationType.ANALYSIS_COMPLETE,
            component="analyzer",
            details={
                "analysis_type": analysis_type,
                "participants_processed": participants_processed
            },
            success=True,
            execution_time_ms=execution_time_ms,
            user_id=user_id
        )
    
    def log_participant_categorized(self,
                                  participant_address: str,
                                  category: str,
                                  confidence: float,
                                  user_id: Optional[str] = None) -> str:
        """Логирование категоризации участника"""
        return self.log_operation(
            operation_type=OperationType.PARTICIPANT_CATEGORIZED,
            component="category_analyzer",
            details={
                "participant_address": participant_address,
                "category": category,
                "confidence": confidence
            },
            success=True,
            user_id=user_id
        )
    
    def log_reward_calculated(self,
                            participant_address: str,
                            reward_amount: Decimal,
                            tier: str,
                            multipliers: Dict[str, float],
                            user_id: Optional[str] = None) -> str:
        """Логирование расчета награды"""
        return self.log_operation(
            operation_type=OperationType.REWARD_CALCULATED,
            component="reward_manager",
            details={
                "participant_address": participant_address,
                "reward_amount": str(reward_amount),
                "tier": tier,
                "multipliers": multipliers
            },
            success=True,
            user_id=user_id
        )
    
    def log_payment_registered(self,
                             payment_id: str,
                             participant_address: str,
                             amount: Decimal,
                             user_id: Optional[str] = None) -> str:
        """Логирование регистрации выплаты"""
        return self.log_operation(
            operation_type=OperationType.PAYMENT_REGISTERED,
            component="duplicate_protection",
            details={
                "payment_id": payment_id,
                "participant_address": participant_address,
                "amount": str(amount)
            },
            success=True,
            user_id=user_id
        )
    
    def log_blockchain_query(self,
                           query_type: str,
                           contract_address: str,
                           method: str,
                           parameters: List[Any],
                           execution_time_ms: float,
                           success: bool,
                           error_message: Optional[str] = None,
                           user_id: Optional[str] = None) -> str:
        """Логирование blockchain запроса"""
        return self.log_operation(
            operation_type=OperationType.BLOCKCHAIN_QUERY,
            component="blockchain",
            details={
                "query_type": query_type,
                "contract_address": contract_address,
                "method": method,
                "parameters": parameters
            },
            success=success,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            user_id=user_id
        )
    
    def log_cache_operation(self,
                          cache_type: str,
                          key: str,
                          hit: bool,
                          user_id: Optional[str] = None) -> str:
        """Логирование операций с кэшем"""
        operation_type = OperationType.CACHE_HIT if hit else OperationType.CACHE_MISS
        return self.log_operation(
            operation_type=operation_type,
            component="cache",
            details={
                "cache_type": cache_type,
                "key": key
            },
            success=True,
            user_id=user_id
        )
    
    def log_error(self,
                 component: str,
                 error_type: str,
                 error_message: str,
                 context: Dict[str, Any],
                 user_id: Optional[str] = None) -> str:
        """Логирование ошибки"""
        return self.log_operation(
            operation_type=OperationType.ERROR_OCCURRED,
            component=component,
            details={
                "error_type": error_type,
                "context": context
            },
            success=False,
            error_message=error_message,
            user_id=user_id
        )
    
    def get_history(self,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   operation_types: Optional[List[OperationType]] = None,
                   component: Optional[str] = None,
                   session_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   success: Optional[bool] = None,
                   limit: int = 1000) -> List[HistoryRecord]:
        """Получение истории операций с фильтрами"""
        try:
            conditions = []
            params = []
            
            # Фильтр по дате
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date.isoformat())
            
            # Фильтр по типам операций
            if operation_types:
                placeholders = ",".join("?" for _ in operation_types)
                conditions.append(f"operation_type IN ({placeholders})")
                params.extend([op.value for op in operation_types])
            
            # Фильтр по компоненту
            if component:
                conditions.append("component = ?")
                params.append(component)
            
            # Фильтр по сессии
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            # Фильтр по пользователю
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            # Фильтр по успешности
            if success is not None:
                conditions.append("success = ?")
                params.append(success)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"""
                    SELECT id, timestamp, operation_type, user_id, session_id,
                           component, details, success, execution_time_ms,
                           error_message, metadata
                    FROM operation_history
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, params + [limit])
                
                records = []
                for row in cursor.fetchall():
                    record = HistoryRecord(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        operation_type=OperationType(row[2]),
                        user_id=row[3],
                        session_id=row[4],
                        component=row[5],
                        details=json.loads(row[6]) if row[6] else {},
                        success=bool(row[7]),
                        execution_time_ms=row[8],
                        error_message=row[9],
                        metadata=json.loads(row[10]) if row[10] else None
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
            return []
    
    def get_statistics(self, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение статистики операций"""
        try:
            conditions = []
            params = []
            
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())
            
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date.isoformat())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            with sqlite3.connect(self.db_path) as conn:
                # Общая статистика
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_operations,
                        COUNT(CASE WHEN success = 1 THEN 1 END) as successful_operations,
                        COUNT(CASE WHEN success = 0 THEN 1 END) as failed_operations,
                        AVG(execution_time_ms) as avg_execution_time,
                        MAX(execution_time_ms) as max_execution_time,
                        COUNT(DISTINCT session_id) as unique_sessions,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM operation_history
                    WHERE {where_clause}
                """, params)
                
                stats = cursor.fetchone()
                
                # Статистика по типам операций
                cursor = conn.execute(f"""
                    SELECT operation_type, COUNT(*) as count,
                           COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                           AVG(execution_time_ms) as avg_time
                    FROM operation_history
                    WHERE {where_clause}
                    GROUP BY operation_type
                    ORDER BY count DESC
                """, params)
                
                operation_stats = {}
                for row in cursor.fetchall():
                    operation_stats[row[0]] = {
                        "count": row[1],
                        "successful": row[2],
                        "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                        "avg_time": row[3] or 0
                    }
                
                # Статистика по компонентам
                cursor = conn.execute(f"""
                    SELECT component, COUNT(*) as count,
                           COUNT(CASE WHEN success = 1 THEN 1 END) as successful
                    FROM operation_history
                    WHERE {where_clause}
                    GROUP BY component
                    ORDER BY count DESC
                """, params)
                
                component_stats = {}
                for row in cursor.fetchall():
                    component_stats[row[0]] = {
                        "count": row[1],
                        "successful": row[2],
                        "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0
                    }
                
                return {
                    "total_operations": stats[0],
                    "successful_operations": stats[1],
                    "failed_operations": stats[2],
                    "success_rate": (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
                    "avg_execution_time": stats[3] or 0,
                    "max_execution_time": stats[4] or 0,
                    "unique_sessions": stats[5],
                    "unique_users": stats[6],
                    "operation_statistics": operation_stats,
                    "component_statistics": component_stats
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def export_history(self, 
                      file_path: str,
                      format: str = "json",
                      compress: bool = True,
                      **filters) -> bool:
        """Экспорт истории в файл"""
        try:
            records = self.get_history(**filters)
            
            if format.lower() == "json":
                data = [record.to_dict() for record in records]
                content = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Неподдерживаемый формат: {format}")
            
            if compress:
                with gzip.open(f"{file_path}.gz", "wt", encoding="utf-8") as f:
                    f.write(content)
                final_path = f"{file_path}.gz"
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                final_path = file_path
            
            self.log_operation(
                operation_type=OperationType.DATA_EXPORT,
                component="history_manager",
                details={
                    "file_path": final_path,
                    "format": format,
                    "compressed": compress,
                    "records_count": len(records)
                },
                success=True
            )
            
            logger.info(f"История экспортирована: {final_path} ({len(records)} записей)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта истории: {e}")
            return False
    
    def archive_old_records(self, days: int = 90) -> int:
        """Архивирование старых записей"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                # Копируем старые записи в архив
                conn.execute("""
                    INSERT INTO operation_history_archive 
                    SELECT * FROM operation_history 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                # Удаляем из основной таблицы
                cursor = conn.execute("""
                    DELETE FROM operation_history 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                archived_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Архивировано {archived_count} записей")
                return archived_count
                
        except Exception as e:
            logger.error(f"Ошибка архивирования: {e}")
            return 0
    
    def cleanup(self):
        """Очистка ресурсов при завершении"""
        self.log_operation(
            operation_type=OperationType.SYSTEM_STOP,
            component="system",
            details={
                "session_id": self.session_id,
                "stop_time": datetime.now().isoformat()
            },
            success=True
        )
