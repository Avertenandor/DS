"""
Модуль: Система логирования для PLEX Dynamic Staking Manager
Описание: Настройка логирования с ротацией файлов и форматированием
Зависимости: logging, pathlib
Автор: GitHub Copilot
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from config.settings import settings


class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консольного вывода"""
    
    # Цветовые коды ANSI
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class PLEXLogger:
    """Централизованная система логирования для PLEX Dynamic Staking Manager"""
    
    def __init__(self, name: str = "PLEX_Staking", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level))
        
        # Предотвращаем дублирование хендлеров
        if self.logger.handlers:
            return
            
        # Создаем директорию для логов
        log_file = log_file or settings.log_file
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Форматтеры
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Файловый хендлер с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Консольный хендлер
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, settings.log_level))
        
        # Добавляем хендлеры
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Логируем запуск
        self.logger.info(f"🚀 PLEX Dynamic Staking Manager Logger initialized")
        self.logger.info(f"📁 Log file: {log_path.absolute()}")
        self.logger.info(f"📊 Log level: {settings.log_level}")
    
    def get_logger(self) -> logging.Logger:
        """Получить настроенный логгер"""
        return self.logger
    
    def log_blockchain_operation(self, operation: str, details: dict):
        """Специализированное логирование блокчейн операций"""
        self.logger.info(f"🔗 {operation}: {details}")
    
    def log_api_usage(self, endpoint: str, credits_used: int, response_time: float):
        """Логирование использования API"""
        self.logger.debug(f"📡 API: {endpoint} | Credits: {credits_used} | Time: {response_time:.3f}s")
    
    def log_gas_transaction(self, tx_hash: str, gas_used: int, gas_price: int, status: str):
        """Логирование газовых транзакций"""
        self.logger.info(f"⛽ TX: {tx_hash} | Gas: {gas_used} | Price: {gas_price} Gwei | Status: {status}")
    
    def log_reward_payment(self, recipient: str, amount: float, tx_hash: str):
        """Логирование выплат наград"""
        self.logger.info(f"💰 REWARD: {recipient} | Amount: {amount} PLEX | TX: {tx_hash}")
    
    def log_category_change(self, address: str, old_category: str, new_category: str, reason: str):
        """Логирование изменений категорий участников"""
        self.logger.warning(f"📊 CATEGORY: {address} | {old_category} → {new_category} | Reason: {reason}")
    
    def log_amnesty_decision(self, address: str, granted: bool, reason: str, admin: str):
        """Логирование решений по амнистии"""
        status = "GRANTED" if granted else "DENIED"
        self.logger.warning(f"🛡️ AMNESTY {status}: {address} | Reason: {reason} | Admin: {admin}")
    
    def log_error_with_context(self, error: Exception, context: dict):
        """Логирование ошибок с контекстом"""
        self.logger.error(f"❌ ERROR: {type(error).__name__}: {error}")
        self.logger.error(f"📍 Context: {context}")
    
    def log_performance_metric(self, operation: str, duration: float, items_processed: int):
        """Логирование метрик производительности"""
        rate = items_processed / duration if duration > 0 else 0
        self.logger.info(f"⚡ PERF: {operation} | Duration: {duration:.2f}s | Items: {items_processed} | Rate: {rate:.1f}/s")
    
    def log_system_startup(self, version: str, config_summary: dict):
        """Логирование запуска системы"""
        self.logger.info("="*80)
        self.logger.info(f"🚀 PLEX Dynamic Staking Manager v{version} STARTING")
        self.logger.info("="*80)
        for key, value in config_summary.items():
            self.logger.info(f"🔧 {key}: {value}")
        self.logger.info("="*80)
    
    def log_checkpoint(self, checkpoint_name: str, status: str, details: dict):
        """Логирование checkpoint'ов обработки"""
        emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⏳"
        self.logger.info(f"{emoji} CHECKPOINT: {checkpoint_name} | Status: {status}")
        for key, value in details.items():
            self.logger.info(f"    📌 {key}: {value}")


# Глобальный логгер
main_logger = PLEXLogger("PLEX_Main")


def get_logger(name: str) -> logging.Logger:
    """Получить логгер для конкретного модуля"""
    module_logger = PLEXLogger(f"PLEX_{name}")
    return module_logger.get_logger()


def log_function_call(func_name: str, args: dict = None, result: any = None, 
                     execution_time: float = None):
    """Декоратор для логирования вызовов функций"""
    logger = get_logger("FunctionCalls")
    
    # Логируем вызов
    if args:
        logger.debug(f"🔄 CALL: {func_name}({args})")
    else:
        logger.debug(f"🔄 CALL: {func_name}()")
    
    # Логируем результат и время выполнения
    if result is not None:
        if execution_time:
            logger.debug(f"✅ RESULT: {func_name} | Time: {execution_time:.3f}s | Result: {type(result).__name__}")
        else:
            logger.debug(f"✅ RESULT: {func_name} | Result: {type(result).__name__}")


def setup_logging_for_external_libs():
    """Настройка логирования для внешних библиотек"""
    # Устанавливаем уровень WARNING для шумных библиотек
    noisy_loggers = ['urllib3', 'requests', 'web3', 'sqlalchemy.engine']
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def create_session_log_file() -> str:
    """Создать уникальный файл лога для текущей сессии"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_log = f"logs/session_{timestamp}.log"
    return session_log


# Инициализация при импорте
setup_logging_for_external_libs()


if __name__ == "__main__":
    # Тестирование системы логирования
    logger = get_logger("Test")
    
    logger.debug("Это debug сообщение")
    logger.info("Это info сообщение")
    logger.warning("Это warning сообщение")
    logger.error("Это error сообщение")
    logger.critical("Это critical сообщение")
    
    # Тестирование специализированных методов
    main_logger.log_blockchain_operation("GetLogs", {"blocks": "1000-2000", "logs": 150})
    main_logger.log_api_usage("/eth_getLogs", 75, 0.245)
    main_logger.log_gas_transaction("0xabc123", 21000, 7, "SUCCESS")
    main_logger.log_reward_payment("0x123456", 100.5, "0xdef456")
    main_logger.log_category_change("0x789abc", "perfect", "transferred", "Manual transfer detected")
    main_logger.log_amnesty_decision("0xghi789", True, "First-time missed purchase", "admin")
    
    print("✅ Логирование протестировано, проверьте файл logs/")
