"""
PLEX Dynamic Staking Manager - Backup Manager

Система резервного копирования и восстановления:
- Автоматическое резервное копирование БД
- Инкрементальные бэкапы
- Восстановление из бэкапов
- Проверка целостности данных

Автор: GitHub Copilot
Дата: 2024
Версия: 1.0.0
"""

import os
import shutil
import sqlite3
import gzip
import json
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import schedule
import time

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class BackupInfo:
    """Информация о резервной копии"""
    backup_id: str
    timestamp: datetime
    backup_type: str  # full, incremental
    file_path: str
    file_size: int
    checksum: str
    description: str
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            "backup_id": self.backup_id,
            "timestamp": self.timestamp.isoformat(),
            "backup_type": self.backup_type,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "description": self.description,
            "success": self.success,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BackupInfo':
        """Создание из словаря"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class BackupManager:
    """Менеджер резервного копирования"""
    
    def __init__(self, 
                 backup_dir: Optional[str] = None,
                 auto_backup: bool = True,
                 backup_interval_hours: int = 24,
                 max_backups: int = 30):
        
        # Определяем директорию для бэкапов
        if backup_dir is None:
            base_dir = getattr(settings, 'BASE_DIR', '.')
            backup_dir = os.path.join(base_dir, "backups")
            
        self.backup_dir = backup_dir
        self.auto_backup = auto_backup
        self.backup_interval_hours = backup_interval_hours
        self.max_backups = max_backups
        
        # Создаем директорию для бэкапов
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Файл для хранения информации о бэкапах
        self.backup_index_file = os.path.join(self.backup_dir, "backup_index.json")
        
        self.lock = threading.Lock()
        self.backup_history: List[BackupInfo] = []
        
        self._load_backup_index()
        
        if auto_backup:
            self._setup_automatic_backup()
        
        logger.info(f"BackupManager инициализирован: {self.backup_dir}")
    
    def _load_backup_index(self):
        """Загрузка индекса бэкапов"""
        try:
            if os.path.exists(self.backup_index_file):
                with open(self.backup_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.backup_history = [BackupInfo.from_dict(item) for item in data]
                logger.info(f"Загружено {len(self.backup_history)} записей о бэкапах")
            else:
                self.backup_history = []
                self._save_backup_index()
        except Exception as e:
            logger.error(f"Ошибка загрузки индекса бэкапов: {e}")
            self.backup_history = []
    
    def _save_backup_index(self):
        """Сохранение индекса бэкапов"""
        try:
            data = [backup.to_dict() for backup in self.backup_history]
            with open(self.backup_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения индекса бэкапов: {e}")
    
    def _setup_automatic_backup(self):
        """Настройка автоматического резервного копирования"""
        schedule.every(self.backup_interval_hours).hours.do(self._auto_backup_job)
        
        # Запускаем планировщик в отдельном потоке
        def scheduler_thread():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
        
        scheduler_thread = threading.Thread(target=scheduler_thread, daemon=True)
        scheduler_thread.start()
        
        logger.info(f"Автоматический бэкап настроен (каждые {self.backup_interval_hours} часов)")
    
    def _auto_backup_job(self):
        """Задача автоматического бэкапа"""
        try:
            self.create_full_backup("Автоматический бэкап")
            self._cleanup_old_backups()
        except Exception as e:
            logger.error(f"Ошибка автоматического бэкапа: {e}")
    
    def generate_backup_id(self) -> str:
        """Генерация ID бэкапа"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"
    
    def calculate_file_checksum(self, file_path: str) -> str:
        """Расчет контрольной суммы файла"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Ошибка расчета контрольной суммы {file_path}: {e}")
            return ""
    
    def create_full_backup(self, description: str = "") -> Optional[BackupInfo]:
        """Создание полного бэкапа"""
        with self.lock:
            backup_id = self.generate_backup_id()
            timestamp = datetime.now()
            
            try:
                # Определяем файлы для бэкапа
                files_to_backup = {
                    "main_database": settings.DATABASE_PATH,
                    "history_database": os.path.join(settings.BASE_DIR, "data", "history.db"),
                    "config": os.path.join(settings.BASE_DIR, ".env"),
                    "logs": os.path.join(settings.BASE_DIR, "logs")
                }
                
                # Создаем временную директорию для бэкапа
                backup_temp_dir = os.path.join(self.backup_dir, f"temp_{backup_id}")
                os.makedirs(backup_temp_dir, exist_ok=True)
                
                backup_manifest = {
                    "backup_id": backup_id,
                    "timestamp": timestamp.isoformat(),
                    "backup_type": "full",
                    "description": description,
                    "files": {}
                }
                
                # Копируем файлы
                for file_type, source_path in files_to_backup.items():
                    if os.path.exists(source_path):
                        if os.path.isfile(source_path):
                            dest_path = os.path.join(backup_temp_dir, f"{file_type}_{os.path.basename(source_path)}")
                            shutil.copy2(source_path, dest_path)
                            backup_manifest["files"][file_type] = {
                                "source": source_path,
                                "backup_file": os.path.basename(dest_path),
                                "size": os.path.getsize(dest_path),
                                "checksum": self.calculate_file_checksum(dest_path)
                            }
                        elif os.path.isdir(source_path):
                            dest_path = os.path.join(backup_temp_dir, file_type)
                            shutil.copytree(source_path, dest_path)
                            backup_manifest["files"][file_type] = {
                                "source": source_path,
                                "backup_dir": file_type,
                                "type": "directory"
                            }
                
                # Сохраняем манифест
                manifest_path = os.path.join(backup_temp_dir, "backup_manifest.json")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_manifest, f, indent=2, ensure_ascii=False)
                
                # Создаем архив
                archive_path = os.path.join(self.backup_dir, f"{backup_id}.tar.gz")
                shutil.make_archive(archive_path[:-7], 'gztar', backup_temp_dir)
                
                # Удаляем временную директорию
                shutil.rmtree(backup_temp_dir)
                
                # Создаем информацию о бэкапе
                backup_info = BackupInfo(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    backup_type="full",
                    file_path=archive_path,
                    file_size=os.path.getsize(archive_path),
                    checksum=self.calculate_file_checksum(archive_path),
                    description=description,
                    success=True
                )
                
                # Добавляем в историю
                self.backup_history.append(backup_info)
                self._save_backup_index()
                
                logger.info(f"Полный бэкап создан: {backup_id} ({backup_info.file_size} байт)")
                return backup_info
                
            except Exception as e:
                error_msg = f"Ошибка создания бэкапа: {e}"
                logger.error(error_msg)
                
                # Создаем запись об ошибке
                backup_info = BackupInfo(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    backup_type="full",
                    file_path="",
                    file_size=0,
                    checksum="",
                    description=description,
                    success=False,
                    error_message=error_msg
                )
                
                self.backup_history.append(backup_info)
                self._save_backup_index()
                
                return backup_info
    
    def create_incremental_backup(self, 
                                since_backup_id: Optional[str] = None,
                                description: str = "") -> Optional[BackupInfo]:
        """Создание инкрементального бэкапа"""
        with self.lock:
            try:
                # Находим последний успешный бэкап
                if since_backup_id is None:
                    last_backup = self.get_last_successful_backup()
                    if not last_backup:
                        logger.warning("Нет предыдущих бэкапов, создаем полный")
                        return self.create_full_backup(f"Инкрементальный -> Полный: {description}")
                    since_backup_id = last_backup.backup_id
                
                backup_id = self.generate_backup_id()
                timestamp = datetime.now()
                
                # Определяем изменившиеся файлы
                changed_files = self._find_changed_files(since_backup_id)
                
                if not changed_files:
                    logger.info("Нет изменений для инкрементального бэкапа")
                    return None
                
                # Создаем временную директорию
                backup_temp_dir = os.path.join(self.backup_dir, f"temp_{backup_id}")
                os.makedirs(backup_temp_dir, exist_ok=True)
                
                backup_manifest = {
                    "backup_id": backup_id,
                    "timestamp": timestamp.isoformat(),
                    "backup_type": "incremental",
                    "base_backup_id": since_backup_id,
                    "description": description,
                    "files": {}
                }
                
                # Копируем только изменившиеся файлы
                for file_path in changed_files:
                    if os.path.exists(file_path):
                        relative_path = os.path.relpath(file_path, settings.BASE_DIR)
                        dest_path = os.path.join(backup_temp_dir, relative_path.replace(os.sep, '_'))
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        shutil.copy2(file_path, dest_path)
                        
                        backup_manifest["files"][relative_path] = {
                            "source": file_path,
                            "backup_file": os.path.basename(dest_path),
                            "size": os.path.getsize(dest_path),
                            "checksum": self.calculate_file_checksum(dest_path)
                        }
                
                # Сохраняем манифест
                manifest_path = os.path.join(backup_temp_dir, "backup_manifest.json")
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_manifest, f, indent=2, ensure_ascii=False)
                
                # Создаем архив
                archive_path = os.path.join(self.backup_dir, f"{backup_id}.tar.gz")
                shutil.make_archive(archive_path[:-7], 'gztar', backup_temp_dir)
                
                # Удаляем временную директорию
                shutil.rmtree(backup_temp_dir)
                
                backup_info = BackupInfo(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    backup_type="incremental",
                    file_path=archive_path,
                    file_size=os.path.getsize(archive_path),
                    checksum=self.calculate_file_checksum(archive_path),
                    description=description,
                    success=True
                )
                
                self.backup_history.append(backup_info)
                self._save_backup_index()
                
                logger.info(f"Инкрементальный бэкап создан: {backup_id}")
                return backup_info
                
            except Exception as e:
                logger.error(f"Ошибка создания инкрементального бэкапа: {e}")
                return None
    
    def _find_changed_files(self, since_backup_id: str) -> List[str]:
        """Поиск изменившихся файлов с последнего бэкапа"""
        try:
            base_backup = self.get_backup_info(since_backup_id)
            if not base_backup:
                return []
            
            changed_files = []
            files_to_check = [
                settings.DATABASE_PATH,
                os.path.join(settings.BASE_DIR, "data", "history.db"),
                os.path.join(settings.BASE_DIR, ".env")
            ]
            
            for file_path in files_to_check:
                if os.path.exists(file_path):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime > base_backup.timestamp:
                        changed_files.append(file_path)
            
            return changed_files
            
        except Exception as e:
            logger.error(f"Ошибка поиска изменившихся файлов: {e}")
            return []
    
    def restore_backup(self, backup_id: str, restore_path: Optional[str] = None) -> bool:
        """Восстановление из бэкапа"""
        try:
            backup_info = self.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Бэкап {backup_id} не найден")
                return False
            
            if not backup_info.success:
                logger.error(f"Бэкап {backup_id} был неуспешным")
                return False
            
            if not os.path.exists(backup_info.file_path):
                logger.error(f"Файл бэкапа не найден: {backup_info.file_path}")
                return False
            
            # Проверяем контрольную сумму
            current_checksum = self.calculate_file_checksum(backup_info.file_path)
            if current_checksum != backup_info.checksum:
                logger.error(f"Контрольная сумма бэкапа не совпадает")
                return False
            
            # Определяем путь восстановления
            if restore_path is None:
                restore_path = os.path.join(self.backup_dir, f"restore_{backup_id}")
            
            os.makedirs(restore_path, exist_ok=True)
            
            # Извлекаем архив
            shutil.unpack_archive(backup_info.file_path, restore_path)
            
            # Загружаем манифест
            manifest_path = os.path.join(restore_path, "backup_manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                logger.info(f"Бэкап {backup_id} восстановлен в {restore_path}")
                logger.info(f"Манифест: {len(manifest.get('files', {}))} файлов")
                return True
            else:
                logger.warning("Манифест бэкапа не найден")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка восстановления бэкапа {backup_id}: {e}")
            return False
    
    def verify_backup(self, backup_id: str) -> bool:
        """Проверка целостности бэкапа"""
        try:
            backup_info = self.get_backup_info(backup_id)
            if not backup_info:
                return False
            
            if not os.path.exists(backup_info.file_path):
                logger.error(f"Файл бэкапа не найден: {backup_info.file_path}")
                return False
            
            # Проверяем размер файла
            current_size = os.path.getsize(backup_info.file_path)
            if current_size != backup_info.file_size:
                logger.error(f"Размер файла бэкапа не совпадает: {current_size} != {backup_info.file_size}")
                return False
            
            # Проверяем контрольную сумму
            current_checksum = self.calculate_file_checksum(backup_info.file_path)
            if current_checksum != backup_info.checksum:
                logger.error(f"Контрольная сумма бэкапа не совпадает")
                return False
            
            logger.info(f"Бэкап {backup_id} прошел проверку целостности")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки бэкапа {backup_id}: {e}")
            return False
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """Получение информации о бэкапе"""
        for backup in self.backup_history:
            if backup.backup_id == backup_id:
                return backup
        return None
    
    def get_last_successful_backup(self, backup_type: Optional[str] = None) -> Optional[BackupInfo]:
        """Получение последнего успешного бэкапа"""
        for backup in reversed(self.backup_history):
            if backup.success:
                if backup_type is None or backup.backup_type == backup_type:
                    return backup
        return None
    
    def list_backups(self, 
                    backup_type: Optional[str] = None,
                    successful_only: bool = False) -> List[BackupInfo]:
        """Список бэкапов с фильтрами"""
        backups = self.backup_history
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        if successful_only:
            backups = [b for b in backups if b.success]
        
        return sorted(backups, key=lambda x: x.timestamp, reverse=True)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Удаление бэкапа"""
        try:
            backup_info = self.get_backup_info(backup_id)
            if not backup_info:
                logger.error(f"Бэкап {backup_id} не найден")
                return False
            
            # Удаляем файл
            if os.path.exists(backup_info.file_path):
                os.remove(backup_info.file_path)
            
            # Удаляем из истории
            self.backup_history = [b for b in self.backup_history if b.backup_id != backup_id]
            self._save_backup_index()
            
            logger.info(f"Бэкап {backup_id} удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления бэкапа {backup_id}: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Очистка старых бэкапов"""
        try:
            successful_backups = [b for b in self.backup_history if b.success]
            successful_backups.sort(key=lambda x: x.timestamp, reverse=True)
            
            if len(successful_backups) > self.max_backups:
                backups_to_delete = successful_backups[self.max_backups:]
                
                for backup in backups_to_delete:
                    self.delete_backup(backup.backup_id)
                    logger.info(f"Удален старый бэкап: {backup.backup_id}")
                
        except Exception as e:
            logger.error(f"Ошибка очистки старых бэкапов: {e}")
    
    def get_backup_statistics(self) -> Dict:
        """Получение статистики бэкапов"""
        total_backups = len(self.backup_history)
        successful_backups = len([b for b in self.backup_history if b.success])
        failed_backups = total_backups - successful_backups
        
        total_size = sum(b.file_size for b in self.backup_history if b.success)
        
        full_backups = len([b for b in self.backup_history if b.backup_type == "full" and b.success])
        incremental_backups = len([b for b in self.backup_history if b.backup_type == "incremental" and b.success])
        
        last_backup = self.get_last_successful_backup()
        
        return {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "failed_backups": failed_backups,
            "success_rate": (successful_backups / total_backups * 100) if total_backups > 0 else 0,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / 1024 / 1024,
            "full_backups": full_backups,
            "incremental_backups": incremental_backups,
            "last_backup_time": last_backup.timestamp.isoformat() if last_backup else None,
            "backup_directory": self.backup_dir
        }
