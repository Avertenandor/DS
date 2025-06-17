"""
PLEX Dynamic Staking Manager - Duplicate Protection System

Критическая система защиты от дубликатов выплат:
- Проверка истории выплат
- Блокировка повторных выплат
- Логирование подозрительных операций
- Восстановление после сбоев

Автор: GitHub Copilot
Дата: 2024
Версия: 1.0.0
"""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import sqlite3
import threading
from decimal import Decimal

from config.settings import settings
from utils.logger import get_logger
from utils.validators import validate_address, validate_token_amount

logger = get_logger(__name__)

@dataclass
class PaymentRecord:
    """Запись о выплате"""
    payment_id: str
    participant_address: str
    amount: Decimal
    category: str
    tier: str
    timestamp: datetime
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    status: str = "pending"  # pending, confirmed, failed, cancelled
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON"""
        return {
            "payment_id": self.payment_id,
            "participant_address": self.participant_address,
            "amount": str(self.amount),
            "category": self.category,
            "tier": self.tier,
            "timestamp": self.timestamp.isoformat(),
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PaymentRecord':
        """Создание из словаря"""
        return cls(
            payment_id=data["payment_id"],
            participant_address=data["participant_address"],
            amount=Decimal(data["amount"]),
            category=data["category"],
            tier=data["tier"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            transaction_hash=data.get("transaction_hash"),
            block_number=data.get("block_number"),
            status=data.get("status", "pending")
        )

@dataclass
class DuplicateCheck:
    """Результат проверки на дубликаты"""
    is_duplicate: bool
    reason: str
    existing_payment_id: Optional[str] = None
    existing_timestamp: Optional[datetime] = None
    risk_level: str = "low"  # low, medium, high, critical

class DuplicateProtectionManager:
    """Менеджер защиты от дубликатов выплат"""
    
    def __init__(self, db_path: Optional[str] = None):
        # Извлекаем путь к БД из database_url
        if db_path is None:
            if settings.database_url.startswith("sqlite:///"):
                db_path = settings.database_url.replace("sqlite:///", "")
            else:
                db_path = "plex_staking.db"  # Fallback
        
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
        # Кэш активных выплат в памяти
        self.active_payments: Dict[str, PaymentRecord] = {}
        self.payment_hashes: Set[str] = set()
        
        logger.info("DuplicateProtectionManager инициализирован")
    
    def _init_database(self):
        """Инициализация базы данных для защиты от дубликатов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS payment_history (
                        payment_id TEXT PRIMARY KEY,
                        participant_address TEXT NOT NULL,
                        amount TEXT NOT NULL,
                        category TEXT NOT NULL,
                        tier TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        transaction_hash TEXT,
                        block_number INTEGER,
                        status TEXT DEFAULT 'pending',
                        payment_hash TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Индексы для быстрого поиска
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_payment_participant 
                    ON payment_history(participant_address, timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_payment_hash 
                    ON payment_history(payment_hash)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_payment_status 
                    ON payment_history(status, timestamp)
                """)
                
                conn.commit()
                logger.info("База данных для защиты от дубликатов инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД защиты от дубликатов: {e}")
            raise
    
    def generate_payment_id(self, 
                          participant_address: str, 
                          amount: Decimal, 
                          category: str, 
                          tier: str) -> str:
        """Генерация уникального ID выплаты"""
        timestamp = datetime.now().isoformat()
        data = f"{participant_address}_{amount}_{category}_{tier}_{timestamp}"
        return f"PAY_{hashlib.sha256(data.encode()).hexdigest()[:16]}"
    
    def generate_payment_hash(self, 
                            participant_address: str, 
                            amount: Decimal, 
                            category: str, 
                            tier: str,
                            time_window_hours: int = 24) -> str:
        """
        Генерация хэша выплаты для проверки дубликатов
        Включает окно времени для группировки похожих выплат
        """
        # Округляем время до указанного окна
        now = datetime.now()
        window_start = now.replace(
            hour=(now.hour // time_window_hours) * time_window_hours,
            minute=0, second=0, microsecond=0
        )
        
        data = f"{participant_address}_{amount}_{category}_{tier}_{window_start.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def check_duplicate(self, 
                       participant_address: str, 
                       amount: Decimal, 
                       category: str, 
                       tier: str,
                       time_window_hours: int = 24) -> DuplicateCheck:
        """
        Проверка на дубликаты выплат
        
        Args:
            participant_address: Адрес участника
            amount: Сумма выплаты
            category: Категория участника
            tier: Тир участника
            time_window_hours: Окно времени для проверки (часы)
        
        Returns:
            DuplicateCheck: Результат проверки
        """
        try:
            # Валидация входных данных
            if not validate_address(participant_address):
                return DuplicateCheck(
                    is_duplicate=True,
                    reason="Неверный адрес участника",
                    risk_level="critical"
                )
            
            if not validate_token_amount(amount):
                return DuplicateCheck(
                    is_duplicate=True,
                    reason="Неверная сумма выплаты",
                    risk_level="critical"
                )
            
            payment_hash = self.generate_payment_hash(
                participant_address, amount, category, tier, time_window_hours
            )
            
            # Проверка в кэше активных выплат
            if payment_hash in self.payment_hashes:
                logger.warning(f"Дубликат найден в кэше: {payment_hash}")
                return DuplicateCheck(
                    is_duplicate=True,
                    reason="Выплата уже обрабатывается",
                    risk_level="high"
                )
            
            # Проверка в базе данных
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT payment_id, timestamp, status, transaction_hash
                    FROM payment_history 
                    WHERE payment_hash = ? 
                    AND status IN ('pending', 'confirmed')
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (payment_hash,))
                
                result = cursor.fetchone()
                
                if result:
                    payment_id, timestamp_str, status, tx_hash = result
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    logger.warning(f"Дубликат найден в БД: {payment_id}")
                    return DuplicateCheck(
                        is_duplicate=True,
                        reason=f"Аналогичная выплата уже существует (статус: {status})",
                        existing_payment_id=payment_id,
                        existing_timestamp=timestamp,
                        risk_level="high" if status == "confirmed" else "medium"
                    )
                
                # Дополнительная проверка: похожие выплаты за короткий период
                recent_threshold = datetime.now() - timedelta(hours=1)
                cursor = conn.execute("""
                    SELECT COUNT(*) 
                    FROM payment_history 
                    WHERE participant_address = ? 
                    AND amount = ?
                    AND timestamp > ?
                    AND status IN ('pending', 'confirmed')
                """, (participant_address, str(amount), recent_threshold.isoformat()))
                
                recent_count = cursor.fetchone()[0]
                
                if recent_count > 0:
                    logger.warning(f"Подозрительная активность: {recent_count} похожих выплат за час")
                    return DuplicateCheck(
                        is_duplicate=True,
                        reason=f"Слишком много похожих выплат за короткий период ({recent_count})",
                        risk_level="medium"
                    )
            
            # Дубликат не найден
            return DuplicateCheck(
                is_duplicate=False,
                reason="Дубликат не найден",
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"Ошибка проверки дубликатов: {e}")
            return DuplicateCheck(
                is_duplicate=True,
                reason=f"Ошибка проверки: {e}",
                risk_level="critical"
            )
    
    def register_payment(self, 
                        participant_address: str, 
                        amount: Decimal, 
                        category: str, 
                        tier: str) -> Tuple[bool, str, Optional[PaymentRecord]]:
        """
        Регистрация новой выплаты с проверкой дубликатов
        
        Returns:
            Tuple[bool, str, Optional[PaymentRecord]]: 
                (успех, сообщение, запись_о_выплате)
        """
        with self.lock:
            try:
                # Проверка на дубликаты
                duplicate_check = self.check_duplicate(
                    participant_address, amount, category, tier
                )
                
                if duplicate_check.is_duplicate:
                    logger.error(f"Попытка дублирования выплаты: {duplicate_check.reason}")
                    return False, duplicate_check.reason, None
                
                # Создание записи о выплате
                payment_record = PaymentRecord(
                    payment_id=self.generate_payment_id(
                        participant_address, amount, category, tier
                    ),
                    participant_address=participant_address,
                    amount=amount,
                    category=category,
                    tier=tier,
                    timestamp=datetime.now()
                )
                
                # Генерация хэша для проверки дубликатов
                payment_hash = self.generate_payment_hash(
                    participant_address, amount, category, tier
                )
                
                # Сохранение в базу данных
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO payment_history 
                        (payment_id, participant_address, amount, category, tier, 
                         timestamp, payment_hash, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        payment_record.payment_id,
                        payment_record.participant_address,
                        str(payment_record.amount),
                        payment_record.category,
                        payment_record.tier,
                        payment_record.timestamp.isoformat(),
                        payment_hash,
                        payment_record.status
                    ))
                    conn.commit()
                
                # Добавление в кэш активных выплат
                self.active_payments[payment_record.payment_id] = payment_record
                self.payment_hashes.add(payment_hash)
                
                logger.info(f"Выплата зарегистрирована: {payment_record.payment_id}")
                return True, "Выплата успешно зарегистрирована", payment_record
                
            except Exception as e:
                logger.error(f"Ошибка регистрации выплаты: {e}")
                return False, f"Ошибка регистрации: {e}", None
    
    def update_payment_status(self, 
                            payment_id: str, 
                            status: str, 
                            transaction_hash: Optional[str] = None,
                            block_number: Optional[int] = None) -> bool:
        """Обновление статуса выплаты"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE payment_history 
                    SET status = ?, transaction_hash = ?, block_number = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = ?
                """, (status, transaction_hash, block_number, payment_id))
                conn.commit()
            
            # Обновление кэша
            if payment_id in self.active_payments:
                self.active_payments[payment_id].status = status
                self.active_payments[payment_id].transaction_hash = transaction_hash
                self.active_payments[payment_id].block_number = block_number
                
                # Удаление завершенных выплат из кэша
                if status in ["confirmed", "failed", "cancelled"]:
                    payment_record = self.active_payments.pop(payment_id, None)
                    if payment_record:
                        payment_hash = self.generate_payment_hash(
                            payment_record.participant_address,
                            payment_record.amount,
                            payment_record.category,
                            payment_record.tier
                        )
                        self.payment_hashes.discard(payment_hash)
            
            logger.info(f"Статус выплаты обновлен: {payment_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса выплаты: {e}")
            return False
    
    def get_payment_history(self, 
                          participant_address: Optional[str] = None,
                          days: int = 30,
                          status: Optional[str] = None) -> List[PaymentRecord]:
        """Получение истории выплат"""
        try:
            conditions = []
            params = []
            
            # Фильтр по времени
            since = datetime.now() - timedelta(days=days)
            conditions.append("timestamp > ?")
            params.append(since.isoformat())
            
            # Фильтр по участнику
            if participant_address:
                conditions.append("participant_address = ?")
                params.append(participant_address)
            
            # Фильтр по статусу
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"""
                    SELECT payment_id, participant_address, amount, category, tier,
                           timestamp, transaction_hash, block_number, status
                    FROM payment_history 
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                """, params)
                
                records = []
                for row in cursor.fetchall():
                    record = PaymentRecord(
                        payment_id=row[0],
                        participant_address=row[1],
                        amount=Decimal(row[2]),
                        category=row[3],
                        tier=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        transaction_hash=row[6],
                        block_number=row[7],
                        status=row[8]
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"Ошибка получения истории выплат: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Получение статистики по выплатам"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Общая статистика
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_payments,
                        COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_payments,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
                        SUM(CASE WHEN status = 'confirmed' THEN CAST(amount AS REAL) ELSE 0 END) as total_confirmed_amount
                    FROM payment_history
                """)
                
                stats = cursor.fetchone()
                
                # Статистика по категориям
                cursor = conn.execute("""
                    SELECT category, COUNT(*) as count,
                           SUM(CASE WHEN status = 'confirmed' THEN CAST(amount AS REAL) ELSE 0 END) as total_amount
                    FROM payment_history
                    GROUP BY category
                """)
                
                category_stats = {row[0]: {"count": row[1], "total_amount": row[2]} 
                                for row in cursor.fetchall()}
                
                return {
                    "total_payments": stats[0],
                    "confirmed_payments": stats[1],
                    "pending_payments": stats[2],
                    "failed_payments": stats[3],
                    "total_confirmed_amount": stats[4] or 0,
                    "success_rate": (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
                    "active_payments_cache": len(self.active_payments),
                    "category_statistics": category_stats
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """Очистка старых записей"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM payment_history 
                    WHERE timestamp < ? AND status IN ('confirmed', 'failed', 'cancelled')
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Удалено {deleted_count} старых записей")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Ошибка очистки старых записей: {e}")
            return 0
