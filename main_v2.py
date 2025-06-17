#!/usr/bin/env python3
"""
PLEX Dynamic Staking Manager - Главный файл приложения
Описание: Production-ready система анализа динамического стейкинга PLEX ONE
Версия: 1.0.0
Автор: GitHub Copilot
"""

import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from config.constants import TOKEN_NAME, TOKEN_SYMBOL, TOKEN_DECIMALS
from utils.logger import get_logger
from utils.converters import format_number
from utils.batch_processor import BatchProcessor
from blockchain.node_client import Web3Manager
from blockchain.swap_analyzer import SwapAnalyzer
from core.participant_analyzer_v2 import ParticipantAnalyzer
from core.reward_manager import RewardManager
from core.duplicate_protection import DuplicateProtectionManager
from db.models import DatabaseManager
from db.history_manager import HistoryManager
from db.backup_manager import BackupManager
from scripts.export_data import DataExporter

# UI импорт (опционально)
try:
    from ui.main_window import PLEXStakingUI
    from ui.main_window_v3 import PLEXStakingUI_V3
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False

logger = get_logger("PLEX_Main")

class PLEXStakingManager:
    """Главный класс управления системой динамического стейкинга"""
    
    def __init__(self):
        """Инициализация системы"""
        logger.info("🚀 Инициализация PLEX Dynamic Staking Manager")
        logger.info("=" * 80)
        logger.info("🚀 PLEX Dynamic Staking Manager v1.0.0 STARTING")
        logger.info("=" * 80)
        logger.info(f"🔧 Version: 1.0.0")
        logger.info(f"🔧 Token: {TOKEN_NAME} ({TOKEN_SYMBOL})")
        logger.info(f"🔧 QuickNode: {settings.quicknode_http[:50]}...")
        logger.info(f"🔧 Database: {settings.database_url}")
        logger.info(f"🔧 Gas Mode: {settings.gas_optimization_mode}")
        logger.info(f"🔧 Log Level: {settings.log_level}")
        logger.info("=" * 80)
        
        try:
            # Инициализация компонентов
            logger.info("🔗 Инициализация Web3 менеджера...")
            self.web3_manager = Web3Manager()
            logger.info("✅ Web3 менеджер инициализирован")
            
            logger.info("📊 Инициализация анализатора swap'ов...")
            self.swap_analyzer = SwapAnalyzer()
            logger.info("✅ Анализатор swap'ов инициализирован")
            
            logger.info("👥 Инициализация анализатора участников...")
            self.participant_analyzer = ParticipantAnalyzer()
            logger.info("✅ Анализатор участников инициализирован")
            
            logger.info("🏆 Инициализация менеджера наград...")
            self.reward_manager = RewardManager()
            logger.info("✅ Менеджер наград инициализирован")
            
            logger.info("🗄️ Инициализация менеджера БД...")
            self.db_manager = DatabaseManager()
            logger.info("✅ Менеджер БД инициализирован")
            
            logger.info("🔒 Инициализация защиты от дубликатов...")
            self.duplicate_protection = DuplicateProtectionManager()
            logger.info("✅ Защита от дубликатов инициализирована")
            
            logger.info("📝 Инициализация менеджера истории...")
            self.history_manager = HistoryManager()
            logger.info("✅ Менеджер истории инициализирован")
            
            logger.info("💾 Инициализация менеджера бэкапов...")
            self.backup_manager = BackupManager(auto_backup=False)  # Отключим для тестов
            logger.info("✅ Менеджер бэкапов инициализирован")
            
            logger.info("⚡ Инициализация батч-процессора...")
            self.batch_processor = BatchProcessor()
            logger.info("✅ Батч-процессор инициализирован")
            
            logger.info("📤 Инициализация экспортера данных...")
            self.data_exporter = DataExporter()
            logger.info("✅ Экспортер данных инициализирован")
            
            # Проверяем подключение
            latest_block = self.web3_manager.get_latest_block_number()
            logger.info(f"📦 Подключен к блоку #{latest_block:,}")
            
            logger.info("✅ Инициализация завершена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    def analyze_participants(self, 
                          start_block: Optional[int] = None,
                          end_block: Optional[int] = None,
                          days_back: int = 30) -> Dict:
        """
        Анализ участников динамического стейкинга
        
        Args:
            start_block: Начальный блок (если None, вычисляется автоматически)
            end_block: Конечный блок (если None, используется последний)
            days_back: Количество дней назад для анализа
            
        Returns:
            Dict: Результаты анализа
        """
        logger.info("🔍 Запуск анализа участников динамического стейкинга")
        
        try:
            # Определяем диапазон блоков
            if end_block is None:
                end_block = self.web3_manager.get_latest_block_number()
            
            if start_block is None:
                # Вычисляем начальный блок на основе дней назад
                blocks_per_day = 24 * 60 * 60 // 3  # BSC ~3 сек на блок
                start_block = end_block - (days_back * blocks_per_day)
            
            logger.info(f"📊 Анализ блоков {start_block:,} - {end_block:,} ({days_back} дней)")
              # Выполняем анализ участников
            participants = self.participant_analyzer.analyze_participants(
                start_block, end_block
            )
            
            # Получаем статистику
            summary = self.participant_analyzer.export_participants_summary()
            
            logger.info("✅ Анализ участников завершен")
            logger.info(f"👥 Найдено участников: {len(participants)}")
            logger.info(f"🎯 Квалифицированных: {summary.get('reward_tiers', {}).get('Bronze', 0) + summary.get('reward_tiers', {}).get('Silver', 0) + summary.get('reward_tiers', {}).get('Gold', 0) + summary.get('reward_tiers', {}).get('Platinum', 0)}")
            
            return {
                "participants": participants,
                "summary": summary,
                "analysis_blocks": {
                    "start": start_block,
                    "end": end_block,
                    "total": end_block - start_block
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа участников: {e}")
            raise

    def calculate_rewards(self, participants: Dict, total_reward_pool: float = 100000) -> Dict:
        """
        Расчет наград для участников
        
        Args:
            participants: Словарь участников из анализа
            total_reward_pool: Общий пул наград в PLEX
            
        Returns:
            Dict: Результаты распределения наград
        """
        logger.info(f"💰 Расчет наград. Пул: {format_number(total_reward_pool)} PLEX")
        
        try:
            from decimal import Decimal
            
            # Создаем пул наград
            reward_pool = self.reward_manager.create_reward_pool(
                total_amount=Decimal(str(total_reward_pool)),
                period_start=datetime.now() - timedelta(days=30),
                period_end=datetime.now()
            )
            
            # Рассчитываем распределение наград
            distributions = self.reward_manager.calculate_rewards(participants, reward_pool)
            
            # Получаем сводку
            summary = self.reward_manager.get_reward_summary()
            
            logger.info("✅ Расчет наград завершен")
            logger.info(f"🎁 Распределений: {len(distributions)}")
            logger.info(f"💎 Общая сумма: {format_number(float(summary.get('total_rewards', 0)))} PLEX")
            
            return {
                "distributions": distributions,
                "summary": summary,
                "pool_info": {
                    "total": total_reward_pool,
                    "distributed": float(reward_pool.distributed_amount),
                    "remaining": float(reward_pool.remaining_amount)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета наград: {e}")
            raise

    def export_all_data(self) -> List[str]:
        """Экспорт всех данных системы"""
        try:
            logger.info("📤 Начинаем полный экспорт данных...")
            
            exported_files = []
            
            # Экспорт участников
            try:
                file_path = self.data_exporter.export_participants_analysis()
                exported_files.append(file_path)
                logger.info(f"✅ Участники экспортированы: {file_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка экспорта участников: {e}")
            
            # Экспорт наград
            try:
                file_path = self.data_exporter.export_rewards_summary()
                exported_files.append(file_path)
                logger.info(f"✅ Награды экспортированы: {file_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка экспорта наград: {e}")
            
            # Экспорт системных метрик
            try:
                file_path = self.data_exporter.export_system_metrics()
                exported_files.append(file_path)
                logger.info(f"✅ Метрики экспортированы: {file_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка экспорта метрик: {e}")
            
            # Экспорт дашборда
            try:
                file_path = self.data_exporter.create_dashboard_data()
                exported_files.append(file_path)
                logger.info(f"✅ Дашборд экспортирован: {file_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка экспорта дашборда: {e}")
            
            logger.info(f"📁 Полный экспорт завершен: {len(exported_files)} файлов")
            return exported_files
            
        except Exception as e:
            logger.error(f"❌ Ошибка полного экспорта: {e}")
            return []

    def get_system_statistics(self) -> Dict:
        """Получение статистики системы"""
        try:
            stats = {}
            
            # Статистика БД
            try:
                db_stats = self.db_manager.get_connection_stats()
                stats["database"] = db_stats
            except Exception as e:
                logger.warning(f"Не удалось получить статистику БД: {e}")
                stats["database"] = {"error": str(e)}
            
            # Статистика истории
            try:
                history_stats = self.history_manager.get_statistics()
                stats["history"] = history_stats
            except Exception as e:
                logger.warning(f"Не удалось получить статистику истории: {e}")
                stats["history"] = {"error": str(e)}
            
            # Статистика бэкапов
            try:
                backup_stats = self.backup_manager.get_backup_statistics()
                stats["backups"] = backup_stats
            except Exception as e:
                logger.warning(f"Не удалось получить статистику бэкапов: {e}")
                stats["backups"] = {"error": str(e)}
            
            # Статистика батч-процессора
            try:
                batch_stats = self.batch_processor.get_statistics()
                stats["batch_processor"] = batch_stats
            except Exception as e:
                logger.warning(f"Не удалось получить статистику батч-процессора: {e}")
                stats["batch_processor"] = {"error": str(e)}
            
            # Статистика защиты от дубликатов
            try:
                duplicate_stats = self.duplicate_protection.get_statistics()
                stats["duplicate_protection"] = duplicate_stats
            except Exception as e:
                logger.warning(f"Не удалось получить статистику защиты от дубликатов: {e}")
                stats["duplicate_protection"] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики системы: {e}")
            return {"error": str(e)}

    def export_data(self, data: Dict, export_type: str = "analysis", filename: Optional[str] = None):
        """Экспорт данных анализа"""
        try:
            import json
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"plex_staking_{export_type}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📁 Данные экспортированы: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта: {e}")
            return None

    def run_cli_interface(self):
        """Запуск CLI интерфейса"""
        logger.info("🎮 Интерактивный режим")
        
        while True:
            print("\n" + "=" * 50)
            print("PLEX Dynamic Staking Manager")
            print("=" * 50)
            print("1. Тест подключения")
            print("2. Анализ участников")
            print("3. Расчет наград")
            print("4. Статистика API")
            print("5. Экспорт данных")
            print("6. Запуск UI")
            print("7. Выход")
            print("=" * 50)
            
            try:
                choice = input("Выберите действие (1-7): ").strip()
                
                if choice == "1":
                    self._run_connection_test()
                elif choice == "2":
                    self._run_participant_analysis()
                elif choice == "3":
                    self._run_reward_calculation()
                elif choice == "4":
                    self._show_api_stats()
                elif choice == "5":
                    self._run_data_export()
                elif choice == "6":
                    self._launch_ui()
                elif choice == "7":
                    break
                else:
                    print("❌ Неверный выбор. Попробуйте еще раз.")
                    
            except KeyboardInterrupt:
                print("\n🔄 Выход из программы...")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка CLI: {e}")
                print(f"❌ Ошибка: {e}")

    def _run_connection_test(self):
        """Запуск тестов подключения"""
        try:
            from scripts.test_connection import main as test_main
            test_main()
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования: {e}")

    def _run_participant_analysis(self):
        """Запуск анализа участников"""
        try:
            print("\n📊 Настройка анализа участников")
            
            days_back = input("Количество дней назад для анализа (по умолчанию 30): ").strip()
            days_back = int(days_back) if days_back else 30
            
            print(f"\n🔍 Запуск анализа за последние {days_back} дней...")
            
            # Вычисляем блоки
            current_block = self.web3_manager.get_current_block()
            blocks_per_day = 28800  # BSC: ~3 секунды на блок
            start_block = current_block - (days_back * blocks_per_day)
            end_block = current_block
              # Запускаем анализ
            results = self.participant_analyzer.analyze_participants(start_block, end_block)
              # Показываем результаты
            print(f"\n✅ Анализ завершен!")
            print(f"👥 Всего участников: {len(results)}")
            
            # Показываем категории
            categories = {}
            for participant in results.values():
                cat = getattr(participant, 'category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print("📊 Категории:")
            for cat, count in categories.items():
                print(f"   {cat}: {count}")
            
            # Предлагаем экспорт
            export = input("\nЭкспортировать результаты? (y/n): ").strip().lower()
            if export == 'y':
                filename = f"participants_analysis_{days_back}d.xlsx"
                print(f"📁 Экспорт в {filename}...")
                # TODO: реализовать экспорт
                    
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            print(f"❌ Ошибка анализа: {e}")

    def _run_reward_calculation(self):
        """Запуск расчета наград"""
        print("\n🏆 Функция расчета наград будет реализована после анализа участников")

    def _show_api_stats(self):
        """Показ статистики API"""
        try:
            stats = self.web3_manager.get_api_usage()
            print(f"\n📊 Статистика API:")
            print(f"📈 Запросов выполнено: {stats['requests_made']}")
            print(f"💳 Кредитов использовано: {stats['credits_used']}")
            print(f"⚡ Текущий RPS: {stats['current_rps']}")
            print(f"📅 Прогноз на месяц: {stats['monthly_projection']:,} кредитов")
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")

    def _run_data_export(self):
        """Запуск экспорта данных"""
        print("\n📁 Функция экспорта будет доступна после анализа")

    def _launch_ui(self):
        """Запуск графического интерфейса"""
        if not UI_AVAILABLE:
            print("❌ UI недоступен. Установите зависимости: pip install customtkinter")
            return
        
        try:
            print("🎨 Запуск графического интерфейса...")
            ui = PLEXStakingUI()
            ui.run()
        except Exception as e:
            logger.error(f"❌ Ошибка UI: {e}")
            print(f"❌ Ошибка UI: {e}")

    def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🔄 Завершение работы системы...")
        try:
            if hasattr(self, 'web3_manager'):
                self.web3_manager.close()
            logger.info("✅ Система корректно завершена")
        except Exception as e:
            logger.error(f"❌ Ошибка завершения: {e}")


def main():
    """Главная функция приложения"""
    try:
        # Парсинг аргументов командной строки
        parser = argparse.ArgumentParser(description="PLEX Dynamic Staking Manager")
        parser.add_argument("command", nargs="?", choices=["test", "analyze", "rewards", "ui", "ui3", "export", "backup", "history", "stats", "batch"], 
                          help="Команда для выполнения")
        parser.add_argument("--days", type=int, default=30, 
                          help="Количество дней для анализа")
        parser.add_argument("--export", action="store_true", 
                          help="Экспортировать результаты")
        
        args = parser.parse_args()
        
        # Инициализация системы
        manager = PLEXStakingManager()
        
        try:
            if args.command == "test":
                logger.info("🧪 Запуск тестов подключения...")
                from scripts.test_connection import main as test_main
                test_main()
                
            elif args.command == "analyze":
                logger.info(f"📊 Запуск анализа участников ({args.days} дней)...")
                
                results = manager.analyze_participants(days_back=args.days)
                
                if args.export:
                    filename = manager.export_data(results, "analysis")
                    logger.info(f"📁 Результаты экспортированы: {filename}")
                    
            elif args.command == "rewards":
                logger.info("🏆 Расчет наград...")
                print("🏆 Функция расчета наград будет реализована в следующей версии")
                
            elif args.command == "ui":
                if UI_AVAILABLE:
                    logger.info("🎨 Запуск UI...")
                    ui = PLEXStakingUI()
                    ui.run()
                else:
                    logger.error("❌ UI недоступен. Установите: pip install customtkinter")
                    
            elif args.command == "ui3":
                if UI_AVAILABLE:
                    logger.info("🎨 Запуск расширенного UI V3...")
                    ui = PLEXStakingUI_V3()
                    ui.run()
                else:
                    logger.error("❌ UI недоступен. Установите: pip install customtkinter")
                    
            elif args.command == "export":
                logger.info("📤 Экспорт данных...")
                exports = manager.export_all_data()
                logger.info(f"📁 Экспортировано {len(exports)} файлов")
                for export in exports:
                    logger.info(f"  - {export}")
                    
            elif args.command == "backup":
                logger.info("💾 Создание резервной копии...")
                backup_info = manager.backup_manager.create_full_backup("Ручной бэкап через CLI")
                if backup_info and backup_info.success:
                    logger.info(f"✅ Бэкап создан: {backup_info.backup_id}")
                else:
                    logger.error("❌ Ошибка создания бэкапа")
                    
            elif args.command == "history":
                logger.info("📝 Просмотр истории операций...")
                history = manager.history_manager.get_history(limit=50)
                logger.info(f"📋 Найдено {len(history)} операций:")
                for record in history[:10]:  # Показываем только последние 10
                    status = "✅" if record.success else "❌"
                    logger.info(f"  {status} {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {record.operation_type.value} | {record.component}")
                    
            elif args.command == "stats":
                logger.info("📊 Статистика системы...")
                stats = manager.get_system_statistics()
                logger.info("📈 Системная статистика:")
                for key, value in stats.items():
                    logger.info(f"  {key}: {value}")
                    
            elif args.command == "batch":
                logger.info("⚡ Запуск батч-обработки...")
                # Пример батч-операций
                if manager.batch_processor.get_total_pending_tasks() > 0:
                    results = manager.batch_processor.process_all_tasks()
                    logger.info(f"⚡ Обработано {len(results)} задач")
                else:
                    logger.info("ℹ️ Нет задач для обработки")
            
            else:
                # Интерактивный режим
                manager.run_cli_interface()
                
        finally:
            manager.cleanup()
            
    except KeyboardInterrupt:
        logger.info("🔄 Программа прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
