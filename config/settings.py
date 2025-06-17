"""
Модуль: Настройки для PLEX Dynamic Staking Manager
Описание: Pydantic класс для настроек с валидацией и загрузкой из .env
Зависимости: pydantic, python-dotenv
Автор: GitHub Copilot
"""

from typing import Optional, Literal
from decimal import Decimal
from pydantic import validator, Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path

# Константы по умолчанию из файла констант
from .constants import (
    TOKEN_ADDRESS, TOKEN_DECIMALS, TOKEN_TOTAL_SUPPLY, TOKEN_NAME, TOKEN_SYMBOL,
    QUICKNODE_HTTP, QUICKNODE_WSS, QUICKNODE_API_KEY,
    PANCAKE_ROUTER_V2, PANCAKE_FACTORY_V2, USDT_BSC, PLEX_USDT_POOL, MULTICALL3_BSC,
    RATE_LIMIT, API_CREDITS_MONTHLY, CREDITS_PER_GETLOGS, CREDITS_PER_CALL,
    MAX_BLOCKS_PER_CHUNK, SECONDS_PER_BLOCK, BSC_CHAIN_ID, UI_COLORS
)


class PLEXStakingSettings(BaseSettings):
    """Настройки для PLEX Dynamic Staking Manager с валидацией"""
    
    # QuickNode подключение
    quicknode_http: str = Field(default=QUICKNODE_HTTP, description="QuickNode HTTP endpoint")
    quicknode_wss: str = Field(default=QUICKNODE_WSS, description="QuickNode WebSocket endpoint")
    quicknode_api_key: str = Field(default=QUICKNODE_API_KEY, description="QuickNode API ключ")
    
    # Параметры токена PLEX ONE (НЕ ИЗМЕНЯТЬ!)
    token_address: str = Field(default=TOKEN_ADDRESS, description="Адрес контракта PLEX ONE")
    token_decimals: int = Field(default=TOKEN_DECIMALS, description="Количество знаков после запятой")
    token_total_supply: int = Field(default=TOKEN_TOTAL_SUPPLY, description="Общее количество токенов")
    token_name: str = Field(default=TOKEN_NAME, description="Название токена")
    token_symbol: str = Field(default=TOKEN_SYMBOL, description="Символ токена")
    
    # BSC контракты
    pancake_router_v2: str = Field(default=PANCAKE_ROUTER_V2, description="PancakeSwap Router V2")
    pancake_factory_v2: str = Field(default=PANCAKE_FACTORY_V2, description="PancakeSwap Factory V2")
    usdt_bsc: str = Field(default=USDT_BSC, description="USDT на BSC")
    plex_usdt_pool: str = Field(default=PLEX_USDT_POOL, description="PLEX/USDT пул")
    multicall3_bsc: str = Field(default=MULTICALL3_BSC, description="Multicall3 контракт")
      # База данных
    database_url: str = Field(default="sqlite:///plex_staking.db", description="URL базы данных")
    debug_sql: bool = Field(default=False, description="Включить отладку SQL запросов")
    
    # API лимиты и оптимизация
    rate_limit: int = Field(default=RATE_LIMIT, description="Лимит запросов в секунду")
    api_credits_monthly: int = Field(default=API_CREDITS_MONTHLY, description="Месячный лимит кредитов")
    credits_per_getlogs: int = Field(default=CREDITS_PER_GETLOGS, description="Кредитов за getLogs")
    credits_per_call: int = Field(default=CREDITS_PER_CALL, description="Кредитов за обычный вызов")
    max_blocks_per_chunk: int = Field(default=MAX_BLOCKS_PER_CHUNK, description="Максимум блоков в чанке")
    
    # Параметры стейкинга
    min_balance: Decimal = Field(default=Decimal('100'), description="Минимальный баланс для участия")
    daily_purchase_min: Decimal = Field(default=Decimal('10'), description="Минимальная дневная покупка USD")
    daily_purchase_max: Decimal = Field(default=Decimal('10000'), description="Максимальная дневная покупка USD")
    
    # Управление газом
    gas_optimization_mode: Literal["adaptive", "standard", "batching"] = Field(default="adaptive", description="Режим управления газом")
    max_gas_price_gwei: int = Field(default=20, description="Максимальная цена газа в Gwei")
    default_gas_price_gwei: int = Field(default=5, description="Стандартная цена газа в Gwei")
    transaction_interval_seconds: int = Field(default=5, description="Интервал между транзакциями")
    batch_size: int = Field(default=100, description="Размер батча для multicall")
    
    # Корпоративный кошелек
    corporate_wallet: str = Field(default="0x0000000000000000000000000000000000000000", description="Адрес корпоративного кошелька")
    
    # Логирование
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", description="Уровень логирования")
    log_file: str = Field(default="logs/plex_staking.log", description="Файл для логов")
    
    # UI настройки
    theme: Literal["dark", "light"] = Field(default="dark", description="Тема интерфейса")
    auto_refresh_seconds: int = Field(default=30, description="Автообновление интерфейса")
    
    # Оптимизация кэширования
    block_cache_ttl: int = Field(default=60, description="TTL кэша блоков в секундах")
    balance_cache_ttl: int = Field(default=300, description="TTL кэша балансов в секундах")
    swap_cache_ttl: int = Field(default=86400, description="TTL кэша swap событий в секундах")
    
    # Retry настройки
    retry_attempts: int = Field(default=5, description="Количество повторных попыток")
    retry_delay_base: float = Field(default=1.0, description="Базовая задержка retry в секундах")
    
    # Лимиты для безопасности
    max_logs_per_request: int = Field(default=750, description="Максимум логов за запрос")
    multicall_batch_size: int = Field(default=50, description="Размер батча multicall")
    connection_timeout: int = Field(default=30, description="Таймаут подключения в секундах")
    
    class Config:
        """Конфигурация Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("token_address", "pancake_router_v2", "pancake_factory_v2", 
              "usdt_bsc", "plex_usdt_pool", "multicall3_bsc", "corporate_wallet")
    def validate_address(cls, v):
        """Валидация Ethereum адресов"""
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError(f"Неверный формат адреса: {v}")
        try:
            int(v, 16)  # Проверка на hex
        except ValueError:
            raise ValueError(f"Адрес содержит неверные hex символы: {v}")
        return v.lower()  # Приводим к нижнему регистру для консистентности
    
    @validator("quicknode_http", "quicknode_wss")
    def validate_urls(cls, v):
        """Валидация URL endpoints"""
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("wss://")):
            raise ValueError(f"Неверный формат URL: {v}")
        return v
    
    @validator("token_decimals")
    def validate_decimals(cls, v):
        """Критическая проверка: decimals должен быть 9 для PLEX"""
        if v != 9:
            raise ValueError(f"КРИТИЧЕСКАЯ ОШИБКА: token_decimals должен быть 9, получен {v}")
        return v
    
    @validator("min_balance", "daily_purchase_min", "daily_purchase_max")
    def validate_positive_decimals(cls, v):
        """Проверка положительных чисел"""
        if v <= 0:
            raise ValueError(f"Значение должно быть больше 0: {v}")
        return v
    
    @validator("daily_purchase_max")
    def validate_purchase_range(cls, v, values):
        """Проверка корректности диапазона покупок"""
        if "daily_purchase_min" in values and v <= values["daily_purchase_min"]:
            raise ValueError("daily_purchase_max должен быть больше daily_purchase_min")
        return v
    
    @validator("max_gas_price_gwei", "default_gas_price_gwei")
    def validate_gas_prices(cls, v):
        """Проверка разумных цен на газ"""
        if v <= 0 or v > 100:  # BSC обычно не требует больше 20 Gwei
            raise ValueError(f"Неразумная цена газа: {v} Gwei")
        return v    
    @validator("rate_limit")
    def validate_rate_limit(cls, v):
        """Проверка соответствия лимитам QuickNode"""
        if v > 50:  # QuickNode лимит 50 RPS
            raise ValueError(f"Rate limit не может быть больше 50 RPS: {v}")
        return v
    
    def get_ui_colors(self) -> dict:
        """Получить цвета для текущей темы"""
        return UI_COLORS
    
    def get_ui_sizes(self) -> dict:
        """Получить размеры UI элементов"""
        return {
            "window_width": 1400,
            "window_height": 900,
            "min_width": 1200,
            "min_height": 800
        }
    
    def get_web3_http_provider_uri(self) -> str:
        """Получить URI для HTTP провайдера Web3"""
        return self.quicknode_http
    
    def get_web3_wss_provider_uri(self) -> str:
        """Получить URI для WebSocket провайдера Web3"""
        return self.quicknode_wss
    
    def calculate_max_api_calls_per_day(self) -> int:
        """Рассчитать максимум API вызовов в день при текущих настройках"""
        seconds_per_day = 24 * 60 * 60
        max_calls_by_rate = seconds_per_day // (1 / self.rate_limit)
        max_calls_by_credits = self.api_credits_monthly // self.credits_per_call // 30
        return min(max_calls_by_rate, max_calls_by_credits)
    
    def get_optimal_chunk_size(self, expected_logs_density: float = 1.0) -> int:
        """Рассчитать оптимальный размер чанка на основе плотности логов"""
        if expected_logs_density <= 0:
            expected_logs_density = 1.0
        
        optimal_blocks = int(self.max_logs_per_request / expected_logs_density)
        return min(max(optimal_blocks, 100), self.max_blocks_per_chunk)
    
    def is_debug(self) -> bool:
        """Проверка debug режима"""
        return self.log_level == "DEBUG"
    
    def is_development_mode(self) -> bool:
        """Проверка режима разработки"""
        return self.log_level == "DEBUG"
    
    def validate_connection_settings(self) -> bool:
        """Валидация настроек подключения"""
        required_fields = [
            self.quicknode_http, self.quicknode_api_key, self.token_address,
            self.plex_usdt_pool, self.multicall3_bsc
        ]
        return all(field for field in required_fields)


# Глобальный экземпляр настроек
settings = PLEXStakingSettings()


def get_settings() -> PLEXStakingSettings:
    """Получить глобальный экземпляр настроек"""
    return settings


# Функция для перезагрузки настроек
def reload_settings(env_file: Optional[str] = None) -> PLEXStakingSettings:
    """Перезагрузить настройки из файла окружения"""
    global settings
    if env_file:
        settings = PLEXStakingSettings(_env_file=env_file)
    else:
        settings = PLEXStakingSettings()
    return settings


# Функция для создания тестовых настроек
def create_test_settings(**overrides) -> PLEXStakingSettings:
    """Создать настройки для тестирования с переопределениями"""
    test_data = {
        "database_url": "sqlite:///:memory:",
        "log_level": "DEBUG",
        **overrides
    }
    return PLEXStakingSettings(**test_data)


if __name__ == "__main__":
    # Пример использования настроек
    print("🔧 PLEX Dynamic Staking Manager - Настройки")
    print(f"Token: {settings.token_name} ({settings.token_symbol})")
    print(f"Decimals: {settings.token_decimals}")
    print(f"QuickNode: {settings.quicknode_http}")
    print(f"Database: {settings.database_url}")
    print(f"Gas Optimization Mode: {settings.gas_optimization_mode}")
    print(f"Max API calls/day: {settings.calculate_max_api_calls_per_day():,}")
    print(f"Connection valid: {settings.validate_connection_settings()}")
    
    # Проверка валидации
    try:
        settings.validate_connection_settings()
        print("✅ Все настройки валидны")
    except Exception as e:
        print(f"❌ Ошибка валидации: {e}")
