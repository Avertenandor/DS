"""
Модуль: Модели базы данных для PLEX Dynamic Staking Manager
Описание: SQLAlchemy модели для хранения данных участников и анализа
Автор: GitHub Copilot
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Numeric, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict

from config.settings import settings
from utils.logger import get_logger

logger = get_logger("PLEX_Database")

Base = declarative_base()

class Participant(Base):
    """Модель участника динамического стейкинга"""
    __tablename__ = 'participants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(42), unique=True, nullable=False, index=True)
    first_activity = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, nullable=False)
    total_swaps = Column(Integer, default=0)
    total_volume_usd = Column(Numeric(20, 8), default=0)
    total_plex_bought = Column(Numeric(20, 9), default=0)  # 9 decimals для PLEX
    total_plex_sold = Column(Numeric(20, 9), default=0)
    avg_swap_size_usd = Column(Numeric(20, 8), default=0)
    unique_days_active = Column(Integer, default=0)
    max_consecutive_days = Column(Integer, default=0)
    category = Column(String(50), default='Unknown', index=True)
    eligibility_score = Column(Numeric(5, 4), default=0)  # 0.0000 - 1.0000
    reward_tier = Column(String(20), default='None', index=True)
    is_qualified = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_participant_activity', 'last_activity', 'is_qualified'),
        Index('idx_participant_category', 'category', 'eligibility_score'),
        Index('idx_participant_volume', 'total_volume_usd'),
    )

class SwapTransaction(Base):
    """Модель swap транзакции"""
    __tablename__ = 'swap_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(String(66), unique=True, nullable=False, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    block_timestamp = Column(DateTime, nullable=False, index=True)
    sender = Column(String(42), nullable=False, index=True)
    
    # Swap данные
    amount0_in = Column(Numeric(30, 9), default=0)
    amount1_in = Column(Numeric(30, 9), default=0)
    amount0_out = Column(Numeric(30, 9), default=0)
    amount1_out = Column(Numeric(30, 9), default=0)
    
    # Расчетные поля
    plex_amount = Column(Numeric(20, 9), nullable=False)  # Количество PLEX (+ покупка, - продажа)
    usdt_amount = Column(Numeric(20, 8), nullable=False)  # Количество USDT
    plex_price_usdt = Column(Numeric(20, 8), nullable=False)  # Цена PLEX в USDT
    volume_usd = Column(Numeric(20, 8), nullable=False)  # Объем в USD
    is_buy = Column(Boolean, nullable=False, index=True)  # True = покупка PLEX, False = продажа
    
    # Газ и комиссии
    gas_used = Column(Integer)
    gas_price = Column(Numeric(20, 0))
    gas_fee_bnb = Column(Numeric(20, 18))
    gas_fee_usd = Column(Numeric(10, 2))
    
    created_at = Column(DateTime, default=func.now())
    
    # Индексы для анализа
    __table_args__ = (
        Index('idx_swap_sender_time', 'sender', 'block_timestamp'),
        Index('idx_swap_volume', 'volume_usd', 'is_buy'),
        Index('idx_swap_time_volume', 'block_timestamp', 'volume_usd'),
    )

class DailyActivity(Base):
    """Модель ежедневной активности участников"""
    __tablename__ = 'daily_activity'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    participant_address = Column(String(42), nullable=False, index=True)
    activity_date = Column(DateTime, nullable=False, index=True)  # Дата (без времени)
    
    # Дневная статистика
    swaps_count = Column(Integer, default=0)
    volume_usd = Column(Numeric(20, 8), default=0)
    plex_bought = Column(Numeric(20, 9), default=0)
    plex_sold = Column(Numeric(20, 9), default=0)
    net_plex_change = Column(Numeric(20, 9), default=0)  # Чистое изменение PLEX
    avg_price_usdt = Column(Numeric(20, 8), default=0)
    
    created_at = Column(DateTime, default=func.now())
    
    # Уникальный индекс для одного участника в день
    __table_args__ = (
        Index('idx_daily_unique', 'participant_address', 'activity_date', unique=True),
        Index('idx_daily_volume', 'activity_date', 'volume_usd'),
    )

class AnalysisSession(Base):
    """Модель сессии анализа"""
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False)  # UUID
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    
    # Параметры анализа
    start_block = Column(Integer, nullable=False)
    end_block = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Результаты
    total_participants = Column(Integer, default=0)
    total_swaps = Column(Integer, default=0)
    total_volume_usd = Column(Numeric(20, 8), default=0)
    qualified_participants = Column(Integer, default=0)
    
    # Статус
    status = Column(String(20), default='Running')  # Running, Completed, Failed
    error_message = Column(Text)
    
    # Метаданные
    analysis_version = Column(String(10), default='1.0.0')
    created_at = Column(DateTime, default=func.now())

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        """Инициализация менеджера БД"""
        self.engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.is_debug()  # Включаем SQL логи в debug режиме
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"🗄️ Подключение к БД: {settings.database_url}")

    def create_tables(self):
        """Создание всех таблиц"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Таблицы БД созданы успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise

    def get_session(self) -> Session:
        """Получение сессии БД"""
        return self.SessionLocal()

    def save_participant(self, session: Session, participant_data: Dict):
        """Сохранение данных участника"""
        try:
            # Проверяем существующего участника
            existing = session.query(Participant).filter_by(
                address=participant_data['address']
            ).first()
            
            if existing:
                # Обновляем существующего
                for key, value in participant_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.now()
                participant = existing
            else:
                # Создаем нового
                participant = Participant(**participant_data)
                session.add(participant)
            
            session.commit()
            return participant
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка сохранения участника {participant_data.get('address')}: {e}")
            raise

    def save_swap_transaction(self, session: Session, swap_data: Dict):
        """Сохранение swap транзакции"""
        try:
            # Проверяем дубликат по tx_hash
            existing = session.query(SwapTransaction).filter_by(
                tx_hash=swap_data['tx_hash']
            ).first()
            
            if existing:
                return existing  # Уже существует
            
            swap = SwapTransaction(**swap_data)
            session.add(swap)
            session.commit()
            return swap
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка сохранения swap {swap_data.get('tx_hash')}: {e}")
            raise

    def save_daily_activity(self, session: Session, activity_data: Dict):
        """Сохранение ежедневной активности"""
        try:
            # Ищем существующую запись
            existing = session.query(DailyActivity).filter_by(
                participant_address=activity_data['participant_address'],
                activity_date=activity_data['activity_date']
            ).first()
            
            if existing:
                # Обновляем данные
                for key, value in activity_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                activity = existing
            else:
                # Создаем новую запись
                activity = DailyActivity(**activity_data)
                session.add(activity)
            
            session.commit()
            return activity
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка сохранения дневной активности: {e}")
            raise

    def get_participants_by_category(self, session: Session, category: str) -> List[Participant]:
        """Получение участников по категории"""
        try:
            return session.query(Participant).filter_by(category=category).all()
        except Exception as e:
            logger.error(f"❌ Ошибка получения участников категории {category}: {e}")
            return []

    def get_qualified_participants(self, session: Session) -> List[Participant]:
        """Получение квалифицированных участников"""
        try:
            return session.query(Participant).filter_by(is_qualified=True)\
                         .order_by(Participant.eligibility_score.desc()).all()
        except Exception as e:
            logger.error(f"❌ Ошибка получения квалифицированных участников: {e}")
            return []

    def get_participant_stats(self, session: Session) -> Dict:
        """Получение общей статистики участников"""
        try:
            total = session.query(Participant).count()
            qualified = session.query(Participant).filter_by(is_qualified=True).count()
            
            # Статистика по категориям
            categories = session.query(
                Participant.category, 
                func.count(Participant.id)
            ).group_by(Participant.category).all()
            
            # Статистика по наградам
            tiers = session.query(
                Participant.reward_tier,
                func.count(Participant.id)
            ).group_by(Participant.reward_tier).all()
            
            return {
                'total_participants': total,
                'qualified_participants': qualified,
                'qualification_rate': (qualified / total * 100) if total > 0 else 0,
                'categories': dict(categories),
                'reward_tiers': dict(tiers)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}

    def cleanup_old_sessions(self, session: Session, days_old: int = 30):
        """Очистка старых сессий анализа"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            deleted = session.query(AnalysisSession).filter(
                AnalysisSession.created_at < cutoff_date
            ).delete()
            session.commit()
            logger.info(f"🧹 Удалено {deleted} старых сессий анализа")
            return deleted
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка очистки старых сессий: {e}")
            return 0
