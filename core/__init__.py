"""
Модуль core - Основная бизнес-логика PLEX Dynamic Staking Manager
"""

from .participant_analyzer_v2 import ParticipantAnalyzer, ParticipantData
from .reward_manager import RewardManager, RewardDistribution, RewardPool
from .category_analyzer import CategoryAnalyzer
from .eligibility import EligibilityEngine  
from .amnesty_manager import AmnestyManager
from .duplicate_protection import DuplicateProtectionManager, PaymentRecord, DuplicateCheck

__all__ = [
    'ParticipantAnalyzer',
    'ParticipantData',
    'RewardManager',
    'RewardDistribution',
    'RewardPool',
    'CategoryAnalyzer',
    'EligibilityEngine',
    'AmnestyManager',
    'DuplicateProtectionManager',
    'PaymentRecord',
    'DuplicateCheck'
]
