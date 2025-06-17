"""
PLEX Dynamic Staking Manager - Database Connection
Модуль для подключения к базе данных и управления сессиями.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

import os
import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Generator, Optional, Any, AsyncGenerator
from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from utils.logger import get_logger
from config.settings import get_settings
from db.models import Base

logger = get_logger(__name__)


class DatabaseManager:
    """
    Production-ready менеджер базы данных для PLEX Dynamic Staking Manager.
    
    Функциональность:
    - Поддержка синхронных и асинхронных соединений
    - Автоматическое создание таблиц
    - Управление пулом соединений
    - Graceful connection handling
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Инициализация DatabaseManager.
        
        Args:
            database_url: URL базы данных (если не указан, берется из настроек)
        """
        self.settings = get_settings()
        self.database_url = database_url or self.settings.database_url
        
        # Движки БД
        self.sync_engine: Optional[Engine] = None
        self.async_engine: Optional[Any] = None
        
        # Фабрики сессий
        self.sync_session_factory: Optional[sessionmaker] = None
        self.async_session_factory: Optional[async_sessionmaker] = None
        
        # Флаги состояния
        self.is_initialized = False
        self.is_async_initialized = False
        
        logger.info(f"📊 DatabaseManager инициализирован для: {self._mask_db_url()}")
    
    def _mask_db_url(self) -> str:
        """Маскирование URL БД для логов."""
        if not self.database_url:
            return "None"
        
        # Скрываем пароль в URL
        if '@' in self.database_url:
            parts = self.database_url.split('@')
            if len(parts) >= 2:
                return f"{parts[0].split('://')[0]}://***@{parts[1]}"
        
        return self.database_url[:50] + "..." if len(self.database_url) > 50 else self.database_url
    
    def initialize_sync(self) -> bool:
        """
        Инициализация синхронного подключения к БД.
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            logger.info("🔧 Инициализация синхронного подключения к БД...")
            
            # Создание движка
            if self.database_url.startswith('sqlite'):
                # Настройки для SQLite
                self.sync_engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={
                        'check_same_thread': False,
                        'timeout': 30
                    },
                    echo=self.settings.debug_sql
                )
            else:
                # Настройки для PostgreSQL
                self.sync_engine = create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo=self.settings.debug_sql
                )
            
            # Создание фабрики сессий
            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Создание таблиц
            self._create_tables()
              # Проверка подключения
            self._test_sync_connection()
            
            self.is_initialized = True
            logger.info("✅ Синхронное подключение к БД успешно инициализировано")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации синхронного подключения: {e}")
            return False
    
    def _create_tables(self) -> None:
        """Создание всех таблиц в БД."""
        try:
            Base.metadata.create_all(bind=self.sync_engine)
            logger.info("✅ Таблицы БД созданы или уже существуют")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise

    def _test_sync_connection(self) -> None:
        """Тестирование синхронного подключения."""
        try:
            from sqlalchemy import text
            with self.sync_session_factory() as session:
                session.execute(text('SELECT 1'))
            logger.info("✅ Тестовое подключение к БД успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка тестового подключения: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Получение синхронной сессии БД с контекстным менеджером.
        
        Yields:
            Session: Сессия SQLAlchemy
        """
        if not self.is_initialized or not self.sync_session_factory:
            raise RuntimeError("Синхронная БД не инициализирована")
        
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_raw_session(self) -> Session:
        """
        Получение "сырой" синхронной сессии без контекстного менеджера.
        
        Внимание: Необходимо вручную управлять жизненным циклом сессии!
        
        Returns:
            Session: Сессия SQLAlchemy
        """
        if not self.is_initialized or not self.sync_session_factory:
            raise RuntimeError("Синхронная БД не инициализирована")
        
        return self.sync_session_factory()
    
    def close_sync(self) -> None:
        """Закрытие синхронных соединений."""
        try:
            if self.sync_engine:
                self.sync_engine.dispose()
                self.sync_engine = None
            
            self.sync_session_factory = None
            self.is_initialized = False
            
            logger.info("🔒 Синхронные соединения с БД закрыты")
            
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия синхронных соединений: {e}")
    
    async def close_async(self) -> None:
        """Закрытие асинхронных соединений."""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
                self.async_engine = None
            
            self.async_session_factory = None
            self.is_async_initialized = False
            
            logger.info("🔒 Асинхронные соединения с БД закрыты")
            
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия асинхронных соединений: {e}")
    
    async def close_all(self) -> None:
        """Закрытие всех соединений."""
        self.close_sync()
        await self.close_async()
        logger.info("🔒 Все соединения с БД закрыты")
    
    def close(self) -> None:
        """Синхронное закрытие всех соединений."""
        self.close_sync()
        logger.info("🔒 Синхронные соединения с БД закрыты")
    
    def initialize_database(self) -> bool:
        """Инициализация БД (метод экземпляра)."""
        return self.initialize_sync()


# Глобальный экземпляр менеджера БД
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Получение глобального экземпляра менеджера БД.
    
    Returns:
        DatabaseManager: Экземпляр менеджера БД
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
    
    return _db_manager


def initialize_database(database_url: Optional[str] = None) -> bool:
    """
    Инициализация глобального подключения к БД.
    
    Args:
        database_url: URL базы данных
        
    Returns:
        bool: True если инициализация успешна
    """
    db_manager = get_database_manager()
    
    if database_url:
        db_manager.database_url = database_url
    
    return db_manager.initialize_sync()


# Удобные функции для получения сессий
def get_db_session():
    """Получение синхронной сессии БД."""
    return get_database_manager().get_session()


# Экспорт для удобного импорта
__all__ = [
    'DatabaseManager',
    'get_database_manager',
    'initialize_database',
    'get_db_session'
]