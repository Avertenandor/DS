"""
PLEX Dynamic Staking Manager - Export Data Script

Скрипт для экспорта данных анализа и отчетности:
- Экспорт результатов анализа
- Генерация отчетов
- Различные форматы (JSON, CSV, Excel)
- Статистика и метрики

Автор: GitHub Copilot
Дата: 2024
Версия: 1.0.0
"""

import os
import json
import csv
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import argparse

from config.settings import settings
from utils.logger import get_logger
from db.models import DatabaseManager
from core.participant_analyzer_v2 import ParticipantAnalyzer
from core.category_analyzer import CategoryAnalyzer
from core.eligibility import EligibilityEngine
from core.reward_manager import RewardManager

logger = get_logger(__name__)

class DataExporter:
    """Экспортер данных анализа"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.settings = settings
        
        # Создаем директорию для экспорта
        base_dir = getattr(settings, 'BASE_DIR', '.')
        self.export_dir = os.path.join(base_dir, "exports")
        os.makedirs(self.export_dir, exist_ok=True)
        
        logger.info("DataExporter инициализирован")
    
    def export_participants_analysis(self, 
                                   output_format: str = "json",
                                   include_details: bool = True,
                                   date_from: Optional[datetime] = None,
                                   date_to: Optional[datetime] = None) -> str:
        """Экспорт результатов анализа участников"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"participants_analysis_{timestamp}.{output_format.lower()}"
            filepath = os.path.join(self.export_dir, filename)
            
            # Получаем данные из БД
            with sqlite3.connect(self.settings.DATABASE_PATH) as conn:
                query = """
                    SELECT 
                        address,
                        category,
                        tier,
                        total_swaps,
                        total_volume,
                        avg_swap_size,
                        first_swap_date,
                        last_swap_date,
                        is_eligible,
                        eligibility_score,
                        reward_amount,
                        created_at,
                        updated_at
                    FROM participants
                """
                
                params = []
                conditions = []
                
                if date_from:
                    conditions.append("created_at >= ?")
                    params.append(date_from.isoformat())
                
                if date_to:
                    conditions.append("created_at <= ?")
                    params.append(date_to.isoformat())
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY total_volume DESC"
                
                cursor = conn.execute(query, params)
                participants = cursor.fetchall()
                
                columns = [
                    "address", "category", "tier", "total_swaps", "total_volume",
                    "avg_swap_size", "first_swap_date", "last_swap_date",
                    "is_eligible", "eligibility_score", "reward_amount",
                    "created_at", "updated_at"
                ]
            
            # Экспорт в зависимости от формата
            if output_format.lower() == "json":
                self._export_to_json(participants, columns, filepath, include_details)
            elif output_format.lower() == "csv":
                self._export_to_csv(participants, columns, filepath)
            else:
                raise ValueError(f"Неподдерживаемый формат: {output_format}")
            
            logger.info(f"Экспорт участников завершен: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка экспорта участников: {e}")
            raise
    
    def export_rewards_summary(self, output_format: str = "json") -> str:
        """Экспорт сводки по наградам"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rewards_summary_{timestamp}.{output_format.lower()}"
            filepath = os.path.join(self.export_dir, filename)
            
            with sqlite3.connect(self.settings.DATABASE_PATH) as conn:
                # Статистика по категориям
                cursor = conn.execute("""
                    SELECT 
                        category,
                        COUNT(*) as participants_count,
                        SUM(CAST(reward_amount AS REAL)) as total_rewards,
                        AVG(CAST(reward_amount AS REAL)) as avg_reward,
                        MIN(CAST(reward_amount AS REAL)) as min_reward,
                        MAX(CAST(reward_amount AS REAL)) as max_reward
                    FROM participants 
                    WHERE is_eligible = 1
                    GROUP BY category
                    ORDER BY total_rewards DESC
                """)
                
                category_stats = []
                for row in cursor.fetchall():
                    category_stats.append({
                        "category": row[0],
                        "participants_count": row[1],
                        "total_rewards": row[2],
                        "avg_reward": row[3],
                        "min_reward": row[4],
                        "max_reward": row[5]
                    })
                
                # Статистика по тирам
                cursor = conn.execute("""
                    SELECT 
                        tier,
                        COUNT(*) as participants_count,
                        SUM(CAST(reward_amount AS REAL)) as total_rewards,
                        AVG(CAST(reward_amount AS REAL)) as avg_reward
                    FROM participants 
                    WHERE is_eligible = 1
                    GROUP BY tier
                    ORDER BY total_rewards DESC
                """)
                
                tier_stats = []
                for row in cursor.fetchall():
                    tier_stats.append({
                        "tier": row[0],
                        "participants_count": row[1],
                        "total_rewards": row[2],
                        "avg_reward": row[3]
                    })
                
                # Общая статистика
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_participants,
                        COUNT(CASE WHEN is_eligible = 1 THEN 1 END) as eligible_participants,
                        SUM(CASE WHEN is_eligible = 1 THEN CAST(reward_amount AS REAL) ELSE 0 END) as total_rewards_amount,
                        AVG(CASE WHEN is_eligible = 1 THEN CAST(reward_amount AS REAL) END) as avg_reward_amount
                    FROM participants
                """)
                
                general_stats = cursor.fetchone()
                
                summary = {
                    "export_timestamp": datetime.now().isoformat(),
                    "general_statistics": {
                        "total_participants": general_stats[0],
                        "eligible_participants": general_stats[1],
                        "eligibility_rate": (general_stats[1] / general_stats[0] * 100) if general_stats[0] > 0 else 0,
                        "total_rewards_amount": general_stats[2] or 0,
                        "avg_reward_amount": general_stats[3] or 0
                    },
                    "category_statistics": category_stats,
                    "tier_statistics": tier_stats
                }
            
            if output_format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Неподдерживаемый формат: {output_format}")
            
            logger.info(f"Экспорт сводки наград завершен: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка экспорта сводки наград: {e}")
            raise
    
    def export_swap_events(self, 
                          participant_address: Optional[str] = None,
                          output_format: str = "json",
                          limit: int = 10000) -> str:
        """Экспорт событий swap"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"swap_events_{timestamp}.{output_format.lower()}"
            filepath = os.path.join(self.export_dir, filename)
            
            with sqlite3.connect(self.settings.DATABASE_PATH) as conn:
                query = """
                    SELECT 
                        transaction_hash,
                        block_number,
                        participant_address,
                        swap_type,
                        amount0_in,
                        amount1_in,
                        amount0_out,
                        amount1_out,
                        timestamp,
                        gas_used,
                        gas_price
                    FROM swap_events
                """
                
                params = []
                if participant_address:
                    query += " WHERE participant_address = ?"
                    params.append(participant_address)
                
                query += " ORDER BY block_number DESC, timestamp DESC"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor = conn.execute(query, params)
                swap_events = cursor.fetchall()
                
                columns = [
                    "transaction_hash", "block_number", "participant_address",
                    "swap_type", "amount0_in", "amount1_in", "amount0_out", "amount1_out",
                    "timestamp", "gas_used", "gas_price"
                ]
            
            if output_format.lower() == "json":
                self._export_to_json(swap_events, columns, filepath)
            elif output_format.lower() == "csv":
                self._export_to_csv(swap_events, columns, filepath)
            else:
                raise ValueError(f"Неподдерживаемый формат: {output_format}")
            
            logger.info(f"Экспорт swap событий завершен: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка экспорта swap событий: {e}")
            raise
    
    def export_system_metrics(self, 
                            days: int = 7,
                            output_format: str = "json") -> str:
        """Экспорт системных метрик"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_metrics_{timestamp}.{output_format.lower()}"
            filepath = os.path.join(self.export_dir, filename)
              # История операций
            base_dir = getattr(settings, 'BASE_DIR', '.')
            history_db_path = os.path.join(base_dir, "data", "history.db")
            metrics = {
                "export_timestamp": datetime.now().isoformat(),
                "period_days": days,
                "database_metrics": {},
                "operation_metrics": {},
                "performance_metrics": {}
            }
            
            # Метрики основной БД
            if os.path.exists(self.settings.DATABASE_PATH):
                with sqlite3.connect(self.settings.DATABASE_PATH) as conn:
                    # Размер БД
                    db_size = os.path.getsize(self.settings.DATABASE_PATH)
                    
                    # Количество записей
                    cursor = conn.execute("SELECT COUNT(*) FROM participants")
                    participants_count = cursor.fetchone()[0]
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM swap_events")
                    swap_events_count = cursor.fetchone()[0]
                    
                    metrics["database_metrics"] = {
                        "database_size_bytes": db_size,
                        "database_size_mb": db_size / 1024 / 1024,
                        "participants_count": participants_count,
                        "swap_events_count": swap_events_count
                    }
            
            # Метрики операций из истории
            if os.path.exists(history_db_path):
                since_date = datetime.now() - timedelta(days=days)
                
                with sqlite3.connect(history_db_path) as conn:
                    # Операции по типам
                    cursor = conn.execute("""
                        SELECT operation_type, COUNT(*) as count,
                               COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                               AVG(execution_time_ms) as avg_time
                        FROM operation_history 
                        WHERE timestamp > ?
                        GROUP BY operation_type
                    """, (since_date.isoformat(),))
                    
                    operation_stats = {}
                    for row in cursor.fetchall():
                        operation_stats[row[0]] = {
                            "count": row[1],
                            "successful": row[2],
                            "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                            "avg_execution_time_ms": row[3] or 0
                        }
                    
                    metrics["operation_metrics"] = operation_stats
                    
                    # Производительность по компонентам
                    cursor = conn.execute("""
                        SELECT component, COUNT(*) as count,
                               AVG(execution_time_ms) as avg_time,
                               MAX(execution_time_ms) as max_time
                        FROM operation_history 
                        WHERE timestamp > ? AND execution_time_ms IS NOT NULL
                        GROUP BY component
                    """, (since_date.isoformat(),))
                    
                    performance_stats = {}
                    for row in cursor.fetchall():
                        performance_stats[row[0]] = {
                            "operations_count": row[1],
                            "avg_execution_time_ms": row[2] or 0,
                            "max_execution_time_ms": row[3] or 0
                        }
                    
                    metrics["performance_metrics"] = performance_stats
            
            if output_format.lower() == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Неподдерживаемый формат: {output_format}")
            
            logger.info(f"Экспорт системных метрик завершен: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка экспорта системных метрик: {e}")
            raise
    
    def _export_to_json(self, 
                       data: List[tuple], 
                       columns: List[str], 
                       filepath: str,
                       include_metadata: bool = True):
        """Экспорт в JSON формат"""
        records = []
        for row in data:
            record = {}
            for i, column in enumerate(columns):
                record[column] = row[i]
            records.append(record)
        
        output = {
            "export_timestamp": datetime.now().isoformat(),
            "records_count": len(records),
            "records": records
        }
        
        if include_metadata:
            output["metadata"] = {
                "exported_by": "PLEX Dynamic Staking Manager",
                "version": "1.0.0",
                "columns": columns
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
    
    def _export_to_csv(self, data: List[tuple], columns: List[str], filepath: str):
        """Экспорт в CSV формат"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Заголовки
            writer.writerow(columns)
            
            # Данные
            for row in data:
                writer.writerow(row)
    
    def create_dashboard_data(self) -> str:
        """Создание данных для дашборда"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_data_{timestamp}.json"
            filepath = os.path.join(self.export_dir, filename)
            
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "overview": {},
                "charts": {},
                "tables": {}
            }
            
            with sqlite3.connect(self.settings.DATABASE_PATH) as conn:
                # Обзорная статистика
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_participants,
                        COUNT(CASE WHEN is_eligible = 1 THEN 1 END) as eligible_participants,
                        SUM(total_swaps) as total_swaps,
                        SUM(CAST(total_volume AS REAL)) as total_volume,
                        AVG(CAST(total_volume AS REAL)) as avg_volume
                    FROM participants
                """)
                
                overview = cursor.fetchone()
                dashboard_data["overview"] = {
                    "total_participants": overview[0],
                    "eligible_participants": overview[1],
                    "eligibility_rate": (overview[1] / overview[0] * 100) if overview[0] > 0 else 0,
                    "total_swaps": overview[2] or 0,
                    "total_volume": overview[3] or 0,
                    "avg_volume": overview[4] or 0
                }
                
                # Данные для графиков - распределение по категориям
                cursor = conn.execute("""
                    SELECT category, COUNT(*) as count
                    FROM participants
                    GROUP BY category
                    ORDER BY count DESC
                """)
                
                dashboard_data["charts"]["category_distribution"] = [
                    {"category": row[0], "count": row[1]}
                    for row in cursor.fetchall()
                ]
                
                # Распределение по тирам
                cursor = conn.execute("""
                    SELECT tier, COUNT(*) as count
                    FROM participants
                    WHERE is_eligible = 1
                    GROUP BY tier
                    ORDER BY count DESC
                """)
                
                dashboard_data["charts"]["tier_distribution"] = [
                    {"tier": row[0], "count": row[1]}
                    for row in cursor.fetchall()
                ]
                
                # Топ участники
                cursor = conn.execute("""
                    SELECT address, category, tier, total_volume, reward_amount
                    FROM participants
                    WHERE is_eligible = 1
                    ORDER BY CAST(total_volume AS REAL) DESC
                    LIMIT 20
                """)
                
                dashboard_data["tables"]["top_participants"] = [
                    {
                        "address": row[0],
                        "category": row[1],
                        "tier": row[2],
                        "total_volume": row[3],
                        "reward_amount": row[4]
                    }
                    for row in cursor.fetchall()
                ]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Данные дашборда созданы: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка создания данных дашборда: {e}")
            raise
    
    def list_exports(self) -> List[Dict[str, Any]]:
        """Список созданных экспортов"""
        exports = []
        
        if os.path.exists(self.export_dir):
            for filename in os.listdir(self.export_dir):
                filepath = os.path.join(self.export_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    exports.append({
                        "filename": filename,
                        "filepath": filepath,
                        "size_bytes": stat.st_size,
                        "size_mb": stat.st_size / 1024 / 1024,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return sorted(exports, key=lambda x: x["created_at"], reverse=True)

def main():
    """Главная функция скрипта"""
    parser = argparse.ArgumentParser(description="Экспорт данных PLEX Dynamic Staking Manager")
    
    parser.add_argument("--export-type", 
                       choices=["participants", "rewards", "swaps", "metrics", "dashboard", "all"],
                       default="all",
                       help="Тип экспорта")
    
    parser.add_argument("--format", 
                       choices=["json", "csv"],
                       default="json",
                       help="Формат экспорта")
    
    parser.add_argument("--participant-address",
                       help="Адрес конкретного участника для экспорта")
    
    parser.add_argument("--days",
                       type=int,
                       default=30,
                       help="Количество дней для экспорта метрик")
    
    parser.add_argument("--limit",
                       type=int,
                       default=10000,
                       help="Лимит записей для экспорта")
    
    args = parser.parse_args()
    
    try:
        exporter = DataExporter()
        exported_files = []
        
        if args.export_type in ["participants", "all"]:
            file_path = exporter.export_participants_analysis(output_format=args.format)
            exported_files.append(file_path)
        
        if args.export_type in ["rewards", "all"]:
            file_path = exporter.export_rewards_summary(output_format=args.format)
            exported_files.append(file_path)
        
        if args.export_type in ["swaps", "all"]:
            file_path = exporter.export_swap_events(
                participant_address=args.participant_address,
                output_format=args.format,
                limit=args.limit
            )
            exported_files.append(file_path)
        
        if args.export_type in ["metrics", "all"]:
            file_path = exporter.export_system_metrics(
                days=args.days,
                output_format=args.format
            )
            exported_files.append(file_path)
        
        if args.export_type in ["dashboard", "all"]:
            file_path = exporter.create_dashboard_data()
            exported_files.append(file_path)
        
        print(f"\nЭкспорт завершен! Созданы файлы:")
        for file_path in exported_files:
            print(f"  - {file_path}")
        
        print(f"\nВсего файлов: {len(exported_files)}")
        
    except Exception as e:
        print(f"Ошибка экспорта: {e}")
        logger.error(f"Критическая ошибка экспорта: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
