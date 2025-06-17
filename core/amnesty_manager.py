"""
Модуль: Управление амнистиями PLEX Dynamic Staking
Описание: Ручное управление амнистиями участников согласно ТЗ
Автор: GitHub Copilot
"""

import json
from typing import Dict, List, Optional, Set
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from utils.logger import get_logger
from db.models import DatabaseManager

logger = get_logger("PLEX_AmnestyManager")


class AmnestyStatus(Enum):
    """Статусы амнистии"""
    PENDING = "pending"        # Ожидает рассмотрения
    APPROVED = "approved"      # Одобрена
    REJECTED = "rejected"      # Отклонена
    EXPIRED = "expired"        # Истекла


class AmnestyReason(Enum):
    """Причины амнистии"""
    MISSED_DAYS = "missed_days"              # Пропущенные дни покупок
    TECHNICAL_ISSUES = "technical_issues"    # Технические проблемы
    FORCE_MAJEURE = "force_majeure"         # Форс-мажор
    TRANSFER_ONLY = "transfer_only"         # Только переводы токенов
    MANUAL_REVIEW = "manual_review"         # Ручной пересмотр


class AmnestyManager:
    """Менеджер амнистий для участников стейкинга"""
    
    def __init__(self):
        """Инициализация менеджера амнистий"""
        self.logger = logger
        self.db = DatabaseManager()
        
        # Правила амнистий из ТЗ
        self.amnesty_rules = {
            'missed_purchase': {
                'auto_eligible': True,
                'max_missed_days': 7,  # Максимум пропущенных дней для авто-амнистии
                'requires_manual': False
            },
            'transferred': {
                'auto_eligible': True,
                'max_transfer_amount': Decimal('1000'),  # USD
                'requires_manual': False
            },
            'sold_token': {
                'auto_eligible': False,
                'requires_manual': True,
                'default_action': 'reject'  # По умолчанию отклонять
            }
        }
        
        # Кэш решений
        self.amnesty_cache: Dict[str, Dict] = {}
        
        logger.info("🤝 Менеджер амнистий инициализирован")
        logger.info(f"📋 Правила амнистий загружены для {len(self.amnesty_rules)} категорий")

    def request_amnesty(self, 
                       address: str,
                       category: str,
                       reason: AmnestyReason,
                       details: Dict,
                       auto_approve: bool = False) -> Dict:
        """
        Запрос амнистии для участника
        
        Args:
            address: Адрес участника
            category: Категория участника (missed_purchase, transferred, sold_token)
            reason: Причина амнистии
            details: Дополнительные детали
            auto_approve: Автоматическое одобрение (если возможно)
            
        Returns:
            Dict: Результат запроса амнистии
        """
        logger.info(f"🤝 Запрос амнистии для {address} (категория: {category})")
        
        try:
            # 1. Проверка возможности амнистии
            eligibility_check = self._check_amnesty_eligibility(address, category, details)
            
            if not eligibility_check['eligible']:
                return self._create_amnesty_result(
                    address=address,
                    status=AmnestyStatus.REJECTED,
                    reason=eligibility_check['reason'],
                    details=eligibility_check
                )
            
            # 2. Определение типа обработки
            if auto_approve and eligibility_check['auto_approvable']:
                return self._approve_amnesty(address, reason, details, auto=True)
            
            # 3. Создание заявки на ручное рассмотрение
            amnesty_request = {
                'address': address,
                'category': category,
                'reason': reason.value,
                'details': details,
                'status': AmnestyStatus.PENDING.value,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'reviewed_by': None,
                'reviewed_at': None
            }
            
            # Сохраняем в БД
            self._save_amnesty_request(amnesty_request)
            
            # Обновляем кэш
            self.amnesty_cache[address] = amnesty_request
            
            logger.info(f"📝 Заявка на амнистию создана для {address}")
            
            return self._create_amnesty_result(
                address=address,
                status=AmnestyStatus.PENDING,
                reason="Заявка принята на рассмотрение",
                details=amnesty_request
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка запроса амнистии для {address}: {e}")
            return self._create_amnesty_result(
                address=address,
                status=AmnestyStatus.REJECTED,
                reason=f"Техническая ошибка: {e}",
                details={'error': str(e)}
            )

    def review_amnesty(self, 
                      address: str,
                      decision: AmnestyStatus,
                      reviewer: str,
                      comments: str = "") -> Dict:
        """
        Ручное рассмотрение заявки на амнистию
        
        Args:
            address: Адрес участника
            decision: Решение (APPROVED/REJECTED)
            reviewer: Кто рассматривает
            comments: Комментарии к решению
            
        Returns:
            Dict: Результат рассмотрения
        """
        logger.info(f"👨‍⚖️ Рассмотрение амнистии {address} ({decision.value}) - {reviewer}")
        
        try:
            # 1. Получение заявки
            request = self._get_amnesty_request(address)
            if not request:
                return {
                    'success': False,
                    'reason': "Заявка на амнистию не найдена",
                    'address': address
                }
            
            # 2. Проверка статуса
            if request['status'] != AmnestyStatus.PENDING.value:
                return {
                    'success': False,
                    'reason': f"Заявка уже рассмотрена (статус: {request['status']})",
                    'address': address
                }
            
            # 3. Проверка срока действия
            if self._is_expired(request):
                self._update_amnesty_status(address, AmnestyStatus.EXPIRED)
                return {
                    'success': False,
                    'reason': "Срок рассмотрения заявки истек",
                    'address': address
                }
            
            # 4. Обновление статуса
            review_data = {
                'status': decision.value,
                'reviewed_by': reviewer,
                'reviewed_at': datetime.now().isoformat(),
                'review_comments': comments
            }
            
            self._update_amnesty_request(address, review_data)
            
            # 5. Логирование решения
            self._log_amnesty_decision(address, decision, reviewer, comments)
            
            logger.info(f"✅ Амнистия {address} {decision.value} - {reviewer}")
            
            return {
                'success': True,
                'address': address,
                'decision': decision.value,
                'reviewer': reviewer,
                'timestamp': review_data['reviewed_at']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка рассмотрения амнистии {address}: {e}")
            return {
                'success': False,
                'reason': f"Техническая ошибка: {e}",
                'address': address
            }

    def get_amnesty_status(self, address: str) -> Optional[Dict]:
        """Получение статуса амнистии для адреса"""
        
        # Проверяем кэш
        if address in self.amnesty_cache:
            return self.amnesty_cache[address]
        
        # Загружаем из БД
        request = self._get_amnesty_request(address)
        if request:
            self.amnesty_cache[address] = request
            return request
        
        return None

    def is_amnesty_approved(self, address: str) -> bool:
        """Проверка, одобрена ли амнистия"""
        status = self.get_amnesty_status(address)
        return status and status['status'] == AmnestyStatus.APPROVED.value

    def get_pending_requests(self) -> List[Dict]:
        """Получение списка заявок на рассмотрение"""
        try:
            # В реальной реализации - запрос к БД
            pending = []
            for address, request in self.amnesty_cache.items():
                if request['status'] == AmnestyStatus.PENDING.value:
                    if not self._is_expired(request):
                        pending.append(request)
                    else:
                        # Помечаем истекшие
                        self._update_amnesty_status(address, AmnestyStatus.EXPIRED)
            
            logger.info(f"📋 Найдено {len(pending)} заявок на рассмотрение")
            return pending
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения заявок: {e}")
            return []

    def bulk_approve_amnesty(self, 
                           addresses: List[str],
                           reviewer: str,
                           reason: str = "Массовое одобрение") -> Dict:
        """Массовое одобрение амнистий"""
        logger.info(f"🎯 Массовое одобрение амнистий для {len(addresses)} адресов")
        
        results = {
            'approved': [],
            'failed': [],
            'total': len(addresses)
        }
        
        for address in addresses:
            try:
                result = self.review_amnesty(
                    address=address,
                    decision=AmnestyStatus.APPROVED,
                    reviewer=reviewer,
                    comments=reason
                )
                
                if result['success']:
                    results['approved'].append(address)
                else:
                    results['failed'].append({
                        'address': address,
                        'reason': result['reason']
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'address': address,
                    'reason': str(e)
                })
        
        logger.info(f"✅ Массовое одобрение: {len(results['approved'])}/{len(addresses)} успешно")
        return results

    def _check_amnesty_eligibility(self, address: str, category: str, details: Dict) -> Dict:
        """Проверка права на амнистию"""
        
        if category not in self.amnesty_rules:
            return {
                'eligible': False,
                'reason': f"Амнистия недоступна для категории {category}",
                'auto_approvable': False
            }
        
        rules = self.amnesty_rules[category]
        
        if not rules['auto_eligible']:
            return {
                'eligible': rules.get('requires_manual', False),
                'reason': "Требует ручного рассмотрения",
                'auto_approvable': False
            }
        
        # Проверяем специфичные критерии
        if category == 'missed_purchase':
            missed_days = details.get('missed_days', 0)
            if missed_days > rules['max_missed_days']:
                return {
                    'eligible': True,
                    'reason': f"Слишком много пропущенных дней ({missed_days})",
                    'auto_approvable': False
                }
        
        return {
            'eligible': True,
            'reason': "Автоматически квалифицирован",
            'auto_approvable': True
        }

    def _approve_amnesty(self, address: str, reason: AmnestyReason, details: Dict, auto: bool = False) -> Dict:
        """Одобрение амнистии"""
        
        amnesty_data = {
            'address': address,
            'status': AmnestyStatus.APPROVED.value,
            'reason': reason.value,
            'details': details,
            'approved_at': datetime.now().isoformat(),
            'auto_approved': auto,
            'reviewed_by': 'system' if auto else None
        }
        
        self._save_amnesty_request(amnesty_data)
        self.amnesty_cache[address] = amnesty_data
        
        return self._create_amnesty_result(
            address=address,
            status=AmnestyStatus.APPROVED,
            reason="Амнистия одобрена",
            details=amnesty_data
        )

    def _create_amnesty_result(self, address: str, status: AmnestyStatus, reason: str, details: Dict) -> Dict:
        """Создание результата амнистии"""
        return {
            'address': address,
            'status': status.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }

    def _save_amnesty_request(self, request: Dict):
        """Сохранение заявки в БД (заглушка)"""
        # В реальной реализации - сохранение в БД
        logger.debug(f"💾 Сохранение заявки на амнистию: {request['address']}")
    
    def _get_amnesty_request(self, address: str) -> Optional[Dict]:
        """Получение заявки из БД (заглушка)"""
        return self.amnesty_cache.get(address)
    
    def _update_amnesty_request(self, address: str, updates: Dict):
        """Обновление заявки в БД (заглушка)"""
        if address in self.amnesty_cache:
            self.amnesty_cache[address].update(updates)
    
    def _update_amnesty_status(self, address: str, status: AmnestyStatus):
        """Обновление статуса амнистии"""
        self._update_amnesty_request(address, {
            'status': status.value,
            'updated_at': datetime.now().isoformat()
        })
    
    def _is_expired(self, request: Dict) -> bool:
        """Проверка истечения срока заявки"""
        expires_at = datetime.fromisoformat(request['expires_at'])
        return datetime.now() > expires_at
    
    def _log_amnesty_decision(self, address: str, decision: AmnestyStatus, reviewer: str, comments: str):
        """Логирование решения по амнистии"""
        logger.info(f"📋 РЕШЕНИЕ ПО АМНИСТИИ:")
        logger.info(f"   Адрес: {address}")
        logger.info(f"   Решение: {decision.value}")
        logger.info(f"   Рассмотрел: {reviewer}")
        logger.info(f"   Комментарий: {comments}")

    def generate_amnesty_report(self) -> Dict:
        """Генерация отчета по амнистиям"""
        
        report = {
            'total_requests': len(self.amnesty_cache),
            'by_status': {},
            'by_category': {},
            'pending_count': 0,
            'expired_count': 0,
            'auto_approved': 0,
            'manual_reviewed': 0
        }
        
        for address, request in self.amnesty_cache.items():
            status = request['status']
            category = request.get('category', 'unknown')
            
            # По статусам
            if status not in report['by_status']:
                report['by_status'][status] = 0
            report['by_status'][status] += 1
            
            # По категориям
            if category not in report['by_category']:
                report['by_category'][category] = 0
            report['by_category'][category] += 1
            
            # Специальные счетчики
            if status == AmnestyStatus.PENDING.value:
                if self._is_expired(request):
                    report['expired_count'] += 1
                else:
                    report['pending_count'] += 1
            
            if request.get('auto_approved'):
                report['auto_approved'] += 1
            elif request.get('reviewed_by'):
                report['manual_reviewed'] += 1
        
        logger.info(f"📊 Отчет по амнистиям:")
        logger.info(f"   Всего заявок: {report['total_requests']}")
        logger.info(f"   На рассмотрении: {report['pending_count']}")
        logger.info(f"   Истекших: {report['expired_count']}")
        logger.info(f"   Авто-одобрено: {report['auto_approved']}")
        logger.info(f"   Ручной пересмотр: {report['manual_reviewed']}")
        
        return report

    def apply_amnesty(self, participant_data) -> Dict:
        """
        Применение амнистии для участника на основе его данных
        
        Args:
            participant_data: Данные участника (ParticipantData)
            
        Returns:
            Dict: Результат применения амнистии
        """
        logger.info(f"🔍 Проверка амнистии для участника {participant_data.address}")
        
        # Анализируем данные участника для определения потребности в амнистии
        eligibility_result = self._analyze_participant_for_amnesty(participant_data)
        
        if eligibility_result['needs_amnesty']:
            # Определяем категорию амнистии
            category = eligibility_result['category']
            reason = eligibility_result['reason']
            details = eligibility_result['details']
            
            # Запрашиваем амнистию
            return self.request_amnesty(
                address=participant_data.address,
                category=category,
                reason=reason,
                details=details,
                auto_approve=eligibility_result.get('auto_approve', False)
            )
        else:
            return {
                'address': participant_data.address,
                'needs_amnesty': False,
                'reason': 'Участник соответствует всем требованиям'
            }

    def _analyze_participant_for_amnesty(self, participant_data) -> Dict:
        """
        Анализ участника для определения потребности в амнистии
        
        Args:
            participant_data: Данные участника
            
        Returns:
            Dict: Результат анализа
        """
        # Базовая логика определения потребности в амнистии
        result = {
            'needs_amnesty': False,
            'category': None,
            'reason': None,
            'details': {},
            'auto_approve': False
        }
        
        # Проверка на низкий eligibility_score
        if participant_data.eligibility_score < 50.0:
            result['needs_amnesty'] = True
            result['category'] = 'missed_purchase'
            result['reason'] = AmnestyReason.MISSED_DAYS
            result['details'] = {
                'eligibility_score': float(participant_data.eligibility_score),
                'category': participant_data.category
            }
            result['auto_approve'] = participant_data.category in ['VIP', 'Premium']
        
        # Проверка на отсутствие квалификации
        elif not participant_data.is_qualified and participant_data.category in ['VIP', 'Premium']:
            result['needs_amnesty'] = True
            result['category'] = 'manual_review'
            result['reason'] = AmnestyReason.MANUAL_REVIEW
            result['details'] = {
                'category': participant_data.category,
                'total_volume': float(participant_data.total_volume_usd)
            }
            result['auto_approve'] = participant_data.category == 'VIP'
        
        return result

# Глобальный экземпляр для использования в системе
amnesty_manager = AmnestyManager()
