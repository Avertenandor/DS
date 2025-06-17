"""
PLEX Dynamic Staking Manager - UI Tabs Package
Пакет вкладок пользовательского интерфейса.

Автор: PLEX Dynamic Staking Team
Версия: 1.0.0
"""

from .analysis_tab import AnalysisTab
from .rewards_tab import RewardsTab
from .history_tab import HistoryTab
from .settings_tab import SettingsTab

__all__ = [
    'AnalysisTab',
    'RewardsTab', 
    'HistoryTab',
    'SettingsTab'
]

__version__ = '1.0.0'
