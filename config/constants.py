"""
Модуль: Константы проекта PLEX Dynamic Staking Manager
Описание: Критически важные константы для работы с блокчейном BSC
Автор: GitHub Copilot
"""

import os
from typing import Final

# 🏗️ Системные константы
BASE_DIR: Final[str] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🚫 ОБЯЗАТЕЛЬНЫЕ КОНСТАНТЫ ПРОЕКТА - НЕ ИЗМЕНЯЙ!
TOKEN_ADDRESS: Final[str] = "0xdf179b6cAdBC61FFD86A3D2e55f6d6e083ade6c1"  # PLEX ONE
TOKEN_DECIMALS: Final[int] = 9  # НЕ 18! Это критически важно
TOKEN_TOTAL_SUPPLY: Final[int] = 12_600_000
TOKEN_NAME: Final[str] = "PLEX ONE"
TOKEN_SYMBOL: Final[str] = "PLEX"

# QuickNode endpoints - ТОЛЬКО ЭТИ
QUICKNODE_HTTP: Final[str] = "https://old-patient-butterfly.bsc.quiknode.pro/4f77305d4e6f7ce51cace16a02b88659c7ec249d/"
QUICKNODE_WSS: Final[str] = "wss://old-patient-butterfly.bsc.quiknode.pro/4f77305d4e6f7ce51cace16a02b88659c7ec249d/"
QUICKNODE_API_KEY: Final[str] = "4f77305d4e6f7ce51cace16a02b88659c7ec249d"

# BSC контракты и адреса
PANCAKE_ROUTER_V2: Final[str] = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_FACTORY_V2: Final[str] = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
USDT_BSC: Final[str] = "0x55d398326f99059fF775485246999027B3197955"
PLEX_USDT_POOL: Final[str] = "0x41d9650faf3341CBF8947FD8063a1Fc88dbF1889"
MULTICALL3_BSC: Final[str] = "0xcA11bde05977b3631167028862bE2a173976CA11"
BATCH_TRANSFER_CONTRACT: Final[str] = "0x0000000000000000000000000000000000000001"  # Заглушка для демо

# Корпоративные адреса  
CORP_WALLET_ADDRESS: Final[str] = "0x0000000000000000000000000000000000000000"  # Заглушка

# QuickNode лимиты
RATE_LIMIT: Final[int] = 50  # запросов в секунду
API_CREDITS_MONTHLY: Final[int] = 80_000_000
CREDITS_PER_GETLOGS: Final[int] = 75
CREDITS_PER_CALL: Final[int] = 20
MAX_BLOCKS_PER_CHUNK: Final[int] = 1000

# BSC блокчейн параметры
SECONDS_PER_BLOCK: Final[int] = 3  # BSC производит блок каждые ~3 секунды
BSC_CHAIN_ID: Final[int] = 56

# Цветовая схема ChatGPT Dark Theme
UI_COLORS: Final[dict] = {
    'bg_primary': '#212121',      # Основной фон
    'bg_secondary': '#2A2A2A',    # Второстепенный фон
    'bg_tertiary': '#333333',     # Третичный фон
    'accent': '#10A37F',          # Зеленый акцент
    'accent_hover': '#0E8F6F',    # Зеленый при наведении
    'text_primary': '#ECECEC',    # Основной текст
    'text_secondary': '#A0A0A0',  # Второстепенный текст
    'error': '#EF4444',           # Красный для ошибок
    'warning': '#F59E0B',         # Желтый для предупреждений
    'success': '#10B981',         # Зеленый для успеха
    'border': '#404040'           # Цвет границ
}

# Размеры и отступы UI
UI_SIZES: Final[dict] = {
    'button_height': 40,
    'input_height': 36,
    'padding_large': 20,
    'padding_medium': 15,
    'padding_small': 10,
    'border_radius': 8,
    'font_size_large': 16,
    'font_size_medium': 14,
    'font_size_small': 12
}

# Параметры стейкинга
MIN_BALANCE: Final[int] = 100  # Минимальный баланс PLEX для участия
DAILY_PURCHASE_MIN: Final[float] = 2.8  # Минимальная дневная покупка в USD
DAILY_PURCHASE_MAX: Final[float] = 3.2  # Максимальная дневная покупка в USD

# Категории участников
class ParticipantCategory:
    PERFECT = "perfect"                  # Ежедневные покупки, нет пропусков, нет продаж
    MISSED_PURCHASE = "missed_purchase"  # Пропустил дни (возможна амнистия)
    SOLD_TOKEN = "sold_token"           # Продавал токены (блокировка)
    TRANSFERRED = "transferred"          # Переводил токены (отметка)

# Правила амнистии
AMNESTY_RULES: Final[dict] = {
    ParticipantCategory.MISSED_PURCHASE: True,   # Можно амнистировать
    ParticipantCategory.SOLD_TOKEN: False,       # НИКОГДА не амнистировать
    ParticipantCategory.TRANSFERRED: True,       # Можно амнистировать
    ParticipantCategory.PERFECT: None            # Не нужна амнистия
}

# Уровни участия и множители наград
TIER_MULTIPLIERS: Final[dict] = {
    'bronze': 1.0,     # Базовый уровень
    'silver': 1.25,    # +25% к наградам
    'gold': 1.5,       # +50% к наградам
    'platinum': 2.0    # +100% к наградам
}

# Газ и транзакции
class GasMode:
    ADAPTIVE = "adaptive"    # Умное управление газом
    STANDARD = "standard"    # Фиксированная цена
    BATCHING = "batching"    # Батч-транзакции

DEFAULT_GAS_PRICE_GWEI: Final[int] = 7
MAX_GAS_PRICE_GWEI: Final[int] = 15
BATCH_SIZE: Final[int] = 50  # Размер батча для multicall

# Интервалы обновления
BLOCK_CACHE_TTL: Final[int] = 60        # Кэш номера блока (секунды)
BALANCE_CACHE_TTL: Final[int] = 300     # Кэш балансов (секунды)
SWAP_CACHE_TTL: Final[int] = 86400      # Кэш swap событий (сутки)

# Лимиты запросов для оптимизации
MAX_LOGS_PER_REQUEST: Final[int] = 750   # Оптимальное количество логов
MULTICALL_BATCH_SIZE: Final[int] = 50    # Количество вызовов в одном multicall
RETRY_ATTEMPTS: Final[int] = 5           # Количество повторных попыток
RETRY_DELAY_BASE: Final[float] = 1.0     # Базовая задержка для retry (секунды)

# Event signatures
TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
SWAP_EVENT_SIGNATURE = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"

# Форматы экспорта
EXPORT_FORMATS: Final[list] = ['xlsx', 'csv', 'json']

# Проверочные значения для тестирования подключения
TEST_VALUES: Final[dict] = {
    'latest_blocks_to_check': 10,
    'test_transfer_count': 100,
    'connection_timeout': 30
}
