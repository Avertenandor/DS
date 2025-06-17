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
    
    async def initialize_async(self) -> bool:
        """
        Инициализация асинхронного подключения к БД.
        
        Returns:
            bool: True если инициализация успешна
        """
        try:
            logger.info("🔧 Инициализация асинхронного подключения к БД...")
            
            # Преобразование URL для async
            async_url = self._convert_to_async_url()
            
            # Создание асинхронного движка
            if async_url.startswith('sqlite+aiosqlite'):
                self.async_engine = create_async_engine(
                    async_url,
                    poolclass=StaticPool,
                    connect_args={'check_same_thread': False},
                    echo=self.settings.debug_sql
                )
            else:
                self.async_engine = create_async_engine(
                    async_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo=self.settings.debug_sql
                )
            
            # Создание фабрики асинхронных сессий
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # Создание таблиц асинхронно
            await self._create_tables_async()
            
            # Проверка подключения
            await self._test_async_connection()
            
            self.is_async_initialized = True
            logger.info("✅ Асинхронное подключение к БД успешно инициализировано")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации асинхронного подключения: {e}")
            return False
    
    def _convert_to_async_url(self) -> str:
        """Преобразование URL для асинхронного подключения."""
        if self.database_url.startswith('sqlite:'):
            return self.database_url.replace('sqlite:', 'sqlite+aiosqlite:')
        elif self.database_url.startswith('postgresql:'):
            return self.database_url.replace('postgresql:', 'postgresql+asyncpg:')
        else:
            return self.database_url
    
    def _create_tables(self) -> None:
        """Создание таблиц синхронно."""
        try:
            Base.metadata.create_all(bind=self.sync_engine)
            logger.info("📊 Таблицы БД созданы/обновлены (синхронно)")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise
    
    async def _create_tables_async(self) -> None:
        """Создание таблиц асинхронно."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("📊 Таблицы БД созданы/обновлены (асинхронно)")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц асинхронно: {e}")
            raise
    
    def _test_sync_connection(self) -> None:
        """Тестирование синхронного подключения."""
        try:
            with self.get_session() as session:
                session.execute('SELECT 1')
            logger.debug("✅ Синхронное подключение к БД проверено")
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования синхронного подключения: {e}")
            raise
    
    async def _test_async_connection(self) -> None:
        """Тестирование асинхронного подключения."""
        try:
            async with self.get_async_session() as session:
                await session.execute('SELECT 1')
            logger.debug("✅ Асинхронное подключение к БД проверено")
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования асинхронного подключения: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Контекстный менеджер для получения синхронной сессии БД.
        
        Yields:
            Session: Сессия SQLAlchemy
            
        Raises:
            RuntimeError: Если БД не инициализирована
        """
        if not self.is_initialized or not self.sync_session_factory:
            raise RuntimeError("Синхронная БД не инициализирована. Вызовите initialize_sync()")
        
        session = self.sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка в сессии БД: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Асинхронный контекстный менеджер для получения сессии БД.
        
        Yields:
            AsyncSession: Асинхронная сессия SQLAlchemy
            
        Raises:
            RuntimeError: Если асинхронная БД не инициализирована
        """
        if not self.is_async_initialized or not self.async_session_factory:
            raise RuntimeError("Асинхронная БД не инициализирована. Вызовите initialize_async()")
        
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка в асинхронной сессии БД: {e}")
                raise
    
    def get_raw_session(self) -> Session:
        """
        Получение сырой сессии без контекстного менеджера.
        ВНИМАНИЕ: Требует ручного управления commit/rollback/close!
        
        Returns:
            Session: Сессия SQLAlchemy
        """
        if not self.is_initialized or not self.sync_session_factory:
            raise RuntimeError("Синхронная БД не инициализирована")
        
        return self.sync_session_factory()
    
    async def get_raw_async_session(self) -> AsyncSession:
        """
        Получение сырой асинхронной сессии без контекстного менеджера.
        ВНИМАНИЕ: Требует ручного управления commit/rollback/close!
        
        Returns:
            AsyncSession: Асинхронная сессия SQLAlchemy
        """
        if not self.is_async_initialized or not self.async_session_factory:
            raise RuntimeError("Асинхронная БД не инициализирована")
        
        return self.async_session_factory()
    
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
    
    def get_connection_info(self) -> dict:
        """
        Получение информации о подключениях.
        
        Returns:
            dict: Информация о состоянии подключений
        """
        sync_pool_info = {}
        async_pool_info = {}
        
        try:
            if self.sync_engine and hasattr(self.sync_engine, 'pool'):
                pool = self.sync_engine.pool
                sync_pool_info = {
                    'size': getattr(pool, 'size', lambda: 0)(),
                    'checked_in': getattr(pool, 'checkedin', lambda: 0)(),
                    'checked_out': getattr(pool, 'checkedout', lambda: 0)(),
                    'invalid': getattr(pool, 'invalid', lambda: 0)()
                }
        except:
            pass
        
        try:
            if self.async_engine and hasattr(self.async_engine, 'pool'):
                pool = self.async_engine.pool
                async_pool_info = {
                    'size': getattr(pool, 'size', lambda: 0)(),
                    'checked_in': getattr(pool, 'checkedin', lambda: 0)(),
                    'checked_out': getattr(pool, 'checkedout', lambda: 0)(),
                    'invalid': getattr(pool, 'invalid', lambda: 0)()
                }
        except:
            pass
        
        return {
            'database_url_masked': self._mask_db_url(),
            'sync_initialized': self.is_initialized,
            'async_initialized': self.is_async_initialized,
            'sync_pool': sync_pool_info,
            'async_pool': async_pool_info
        }


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


async def initialize_async_database(database_url: Optional[str] = None) -> bool:
    """
    Инициализация глобального асинхронного подключения к БД.
    
    Args:
        database_url: URL базы данных
        
    Returns:
        bool: True если инициализация успешна
    """
    db_manager = get_database_manager()
    
    if database_url:
        db_manager.database_url = database_url
    
    return await db_manager.initialize_async()


# Удобные функции для получения сессий
def get_db_session():
    """Получение синхронной сессии БД."""
    return get_database_manager().get_session()


def get_async_db_session():
    """Получение асинхронной сессии БД."""
    return get_database_manager().get_async_session()


# Экспорт для удобного импорта
__all__ = [
    'DatabaseManager',
    'get_database_manager',
    'initialize_database',
    'initialize_async_database',
    'get_db_session',
    'get_async_db_session'
]


if __name__ == "__main__":
    # Тестовый запуск для проверки модуля
    async def test_database():
        """Тестирование DatabaseManager."""
        try:
            print("🧪 Тестирование DatabaseManager...")
            
            # Создание менеджера
            db_manager = DatabaseManager()
            
            # Инициализация синхронного подключения
            print("🔧 Инициализация синхронного подключения...")
            sync_success = db_manager.initialize_sync()
            print(f"Результат: {'✅ Успешно' if sync_success else '❌ Ошибка'}")
            
            # Тест синхронной сессии
            if sync_success:
                print("📊 Тест синхронной сессии...")
                with db_manager.get_session() as session:
                    result = session.execute('SELECT 1 as test').fetchone()
                    print(f"Результат запроса: {result}")
            
            # Инициализация асинхронного подключения
            print("🔧 Инициализация асинхронного подключения...")
            async_success = await db_manager.initialize_async()
            print(f"Результат: {'✅ Успешно' if async_success else '❌ Ошибка'}")
            
            # Тест асинхронной сессии
            if async_success:
                print("📊 Тест асинхронной сессии...")
                async with db_manager.get_async_session() as session:
                    result = await session.execute('SELECT 1 as test')
                    row = result.fetchone()
                    print(f"Результат асинхронного запроса: {row}")
            
            # Информация о подключении
            conn_info = db_manager.get_connection_info()
            print(f"📈 Информация о подключении: {conn_info}")
            
            # Закрытие подключений
            await db_manager.close_all()
            print("✅ Тестирование DatabaseManager завершено успешно")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
    
    # Запуск тестирования
    # asyncio.run(test_database())
    print("💡 Для тестирования раскомментируй последнюю строку")
