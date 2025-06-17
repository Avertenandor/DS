"""
PLEX Dynamic Staking Manager - Main Application Entry Point V4
Точка входа в приложение с полным UI.

Автор: PLEX Dynamic Staking Team
Версия: 4.0.0
"""

import os
import sys
import traceback
from datetime import datetime

# Добавление корневой директории в путь
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils.logger import get_logger
from config.constants import *
from config.settings import settings

# Настройка логирования
logger = get_logger(__name__)


def check_dependencies():
    """Проверка зависимостей."""
    missing_deps = []
    
    try:
        import customtkinter
    except ImportError:
        missing_deps.append("customtkinter")
    
    try:
        import web3
    except ImportError:
        missing_deps.append("web3")
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import sqlite3
    except ImportError:
        missing_deps.append("sqlite3")
    
    if missing_deps:
        print("❌ Отсутствуют необходимые зависимости:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\\n📦 Установите зависимости: pip install -r requirements.txt")
        return False
    
    return True


def print_banner():
    """Печать баннера приложения."""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        💎 PLEX Dynamic Staking Manager v4.0                 ║
║                                                              ║
║        🔗 BSC Network Analysis & Reward Distribution         ║
║        📊 Advanced Participant Analytics                     ║
║        🎁 Automated Reward Calculation                       ║
║        📚 Complete Operation History                         ║
║        ⚙️ Comprehensive Settings                             ║
║                                                              ║
║        Автор: PLEX Dynamic Staking Team                      ║
║        Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Главная функция приложения."""
    try:
        # Печать баннера
        print_banner()
        
        # Проверка зависимостей
        print("🔍 Проверка зависимостей...")
        if not check_dependencies():
            return 1
        print("✅ Все зависимости установлены")
        
        # Проверка конфигурации
        print("⚙️ Проверка конфигурации...")
        
        # Проверка наличия .env файла
        env_file = os.path.join(BASE_DIR, '.env')
        if not os.path.exists(env_file):
            print("⚠️ Файл .env не найден. Создайте его на основе .env.example")
            print("📝 Скопируйте .env.example в .env и настройте параметры")
        
        # Проверка ключевых настроек
        if not hasattr(settings, 'QUICKNODE_RPC_URL') or not settings.QUICKNODE_RPC_URL:
            print("⚠️ QuickNode RPC URL не настроен")
            print("💡 Настройте его во вкладке 'Настройки' или в файле .env")
        
        print("✅ Конфигурация проверена")
        
        # Создание необходимых директорий
        print("📁 Создание директорий...")
        directories = ['logs', 'backups', 'exports', 'cache']
        for directory in directories:
            dir_path = os.path.join(BASE_DIR, directory)
            os.makedirs(dir_path, exist_ok=True)
        print("✅ Директории созданы")
        
        # Инициализация БД
        print("🗄️ Инициализация базы данных...")
        try:
            from db.database import DatabaseManager
            db_manager = DatabaseManager()
            db_manager.initialize_database()
            print("✅ База данных инициализирована")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации БД: {e}")
            logger.warning(f"Ошибка инициализации БД: {e}")
        
        # Запуск GUI
        print("🎨 Запуск пользовательского интерфейса...")
        logger.info("🚀 Запуск PLEX Dynamic Staking Manager v4.0")
        
        from ui.main_window_v4 import PLEXStakingMainWindow
        
        app = PLEXStakingMainWindow()
        app.run()
        
        print("👋 Приложение завершено")
        logger.info("👋 Приложение завершено")
        return 0
        
    except KeyboardInterrupt:
        print("\\n⏹️ Приложение остановлено пользователем")
        logger.info("Приложение остановлено пользователем")
        return 0
        
    except Exception as e:
        print(f"\\n❌ Критическая ошибка: {e}")
        print("\\n📋 Детали ошибки:")
        traceback.print_exc()
        
        logger.error(f"Критическая ошибка: {e}")
        logger.error(f"Трассировка: {traceback.format_exc()}")
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
