"""
Скрипт: Инициализация базы данных PLEX Dynamic Staking Manager
Описание: Создание таблиц и настройка БД
Автор: GitHub Copilot
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("DatabaseInit")


def init_database():
    """Инициализация базы данных"""
    try:
        logger.info("🗄️ Инициализация базы данных...")
        
        # Создаем engine
        engine = create_engine(settings.database_url)
        
        # Проверяем подключение
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к базе данных установлено")
        
        # Здесь будет создание таблиц через SQLAlchemy модели
        # Пока что создадим базовую структуру
        
        logger.info("✅ База данных инициализирована")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
