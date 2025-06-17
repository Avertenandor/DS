"""
PLEX Dynamic Staking Manager - Главный файл приложения
Описание: Точка входа в систему динамического стейкинга PLEX ONE v4.0
Автор: PLEX Dynamic Staking Team

Этот файл перенаправляет на main_v4.py для запуска последней версии
с полным набором кнопок и enhanced интерфейсом.
"""

import sys
import subprocess
from pathlib import Path

print("🚀 PLEX Dynamic Staking Manager")
print("🔄 Запуск последней версии v4.0...")
print("✅ Перенаправление на main_v4.py")
print("")

# Запускаем main_v4.py
try:
    # Получаем путь к main_v4.py
    current_dir = Path(__file__).parent
    main_v4_path = current_dir / "main_v4.py"
    
    if main_v4_path.exists():
        # Запускаем main_v4.py с теми же аргументами
        subprocess.run([sys.executable, str(main_v4_path)] + sys.argv[1:], cwd=current_dir)
    else:
        print("❌ Ошибка: main_v4.py не найден!")
        print("💡 Убедитесь, что файл main_v4.py существует в корневой директории.")
        sys.exit(1)
        
except KeyboardInterrupt:
    print("\n⏹️ Приложение остановлено пользователем")
    sys.exit(0)
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")
    print("💡 Попробуйте запустить напрямую: python main_v4.py")
    sys.exit(1)


class PLEXStakingManager:
    """Главный менеджер системы стейкинга PLEX"""
    
    def __init__(self):
        self.web3_manager = None
        self.swap_analyzer = None
        self.is_running = False
        self.version = "1.0.0"
        
    def initialize(self):
        """Инициализация всех компонентов системы"""
        try:
            logger.info("🚀 Инициализация PLEX Dynamic Staking Manager")
            
            # Логируем стартовую информацию
            config_summary = {
                "Version": self.version,
                "Token": f"{TOKEN_NAME} ({TOKEN_SYMBOL})",
                "QuickNode": settings.quicknode_http[:50] + "...",
                "Database": settings.database_url,
                "Gas Mode": settings.gas_mode,
                "Log Level": settings.log_level
            }
            
            main_logger.log_system_startup(self.version, config_summary)
            
            # Инициализация Web3 менеджера
            logger.info("🔗 Инициализация Web3 менеджера...")
            self.web3_manager = get_web3_manager()
            
            if not self.web3_manager.is_connected:
                raise Exception("Не удалось подключиться к QuickNode")
            
            logger.info("✅ Web3 менеджер инициализирован")
            
            # Инициализация анализатора swap'ов
            logger.info("📊 Инициализация анализатора swap'ов...")
            self.swap_analyzer = get_swap_analyzer()
            logger.info("✅ Анализатор swap'ов инициализирован")
            
            # Проверка подключения
            health = self.web3_manager.check_connection_health()
            if not health["http_connected"]:
                raise Exception("HTTP подключение недоступно")
            
            logger.info(f"📦 Подключен к блоку #{health['latest_block']:,}")
            
            self.is_running = True
            logger.info("✅ Инициализация завершена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise
    
    def run_analysis(self, period_days: int = 30):
        """Запустить анализ участников стейкинга"""
        try:
            logger.info(f"📊 Запуск анализа за {period_days} дней")
            
            # Определяем стоп-блок
            from datetime import datetime, timedelta
            stop_timestamp = int((datetime.now() - timedelta(days=period_days)).timestamp())
            stop_block = self.web3_manager.find_block_by_timestamp(stop_timestamp)
            
            logger.info(f"🎯 Анализ до блока #{stop_block:,}")
            
            # Собираем все swap события
            def progress_callback(message, progress):
                logger.info(f"📈 {message}")
            
            swaps = self.swap_analyzer.collect_all_swaps(stop_block, progress_callback)
            
            # Категоризируем участников
            categories = self.swap_analyzer.categorize_participants(swaps, period_days)
            
            # Выводим результаты
            logger.info("📋 РЕЗУЛЬТАТЫ АНАЛИЗА:")
            logger.info(f"   🌟 Идеальные участники: {len(categories['perfect'])}")
            logger.info(f"   ⚠️ Пропустили покупки: {len(categories['missed_purchase'])}")
            logger.info(f"   ❌ Продавали токены: {len(categories['sold_token'])}")
            logger.info(f"   📤 Переводили токены: {len(categories['transferred'])}")
            
            return categories
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
            raise
    
    def shutdown(self):
        """Корректное завершение работы"""
        logger.info("🔄 Завершение работы системы...")
        
        try:
            if self.web3_manager:
                self.web3_manager.close_connections()
            
            self.is_running = False
            logger.info("✅ Система корректно завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при завершении: {e}")


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"🛑 Получен сигнал {signum}, завершение работы...")
    sys.exit(0)


def main():
    """Главная функция"""
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager = PLEXStakingManager()
    
    try:
        # Инициализация
        manager.initialize()
        
        # Проверяем аргументы командной строки
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "test":
                # Запуск тестов подключения
                logger.info("🧪 Запуск тестов подключения...")
                from scripts.test_connection import main as test_main
                return test_main()
                
            elif command == "analyze":
                # Запуск анализа
                period_days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
                results = manager.run_analysis(period_days)
                
                # Сохраняем результаты
                import json
                from datetime import datetime
                
                output_file = f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                # Конвертируем Decimal в float для JSON
                def convert_decimal(obj):
                    if hasattr(obj, '__dict__'):
                        return {k: convert_decimal(v) for k, v in obj.__dict__.items()}
                    elif isinstance(obj, list):
                        return [convert_decimal(item) for item in obj]
                    elif isinstance(obj, dict):
                        return {k: convert_decimal(v) for k, v in obj.items()}
                    elif hasattr(obj, 'isoformat'):  # datetime
                        return obj.isoformat()
                    elif str(type(obj)) == "<class 'decimal.Decimal'>":
                        return float(obj)
                    else:
                        return obj
                
                converted_results = convert_decimal(results)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(converted_results, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"💾 Результаты сохранены в {output_file}")
                
            elif command == "ui":
                # Запуск UI (будет реализовано позже)
                logger.info("🖥️ Запуск пользовательского интерфейса...")
                logger.warning("⚠️ UI пока не реализован")
                
            else:
                print("❌ Неизвестная команда")
                print("Доступные команды:")
                print("  test     - тестирование подключения")
                print("  analyze [дни] - анализ участников (по умолчанию 30 дней)")
                print("  ui       - запуск UI")
                return False
        else:
            # Интерактивный режим
            logger.info("🎮 Интерактивный режим")
            
            while manager.is_running:
                print("\n" + "="*50)
                print("PLEX Dynamic Staking Manager")
                print("="*50)
                print("1. Тест подключения")
                print("2. Анализ участников")
                print("3. Статистика API")
                print("4. Выход")
                print("="*50)
                
                try:
                    choice = input("Выберите действие (1-4): ").strip()
                    
                    if choice == "1":
                        from scripts.test_connection import main as test_main
                        test_main()
                        
                    elif choice == "2":
                        days = input("Количество дней для анализа (по умолчанию 30): ").strip()
                        period_days = int(days) if days.isdigit() else 30
                        
                        results = manager.run_analysis(period_days)
                        
                        # Показываем краткую статистику
                        print(f"\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА ({period_days} дней):")
                        print(f"🌟 Идеальные участники: {len(results['perfect'])}")
                        print(f"⚠️ Пропустили покупки: {len(results['missed_purchase'])}")
                        print(f"❌ Продавали токены: {len(results['sold_token'])}")
                        
                    elif choice == "3":
                        stats = manager.web3_manager.api_usage.get_usage_stats()
                        print(f"\n📈 СТАТИСТИКА API:")
                        print(f"💳 Использовано кредитов: {stats['credits_used']:,}")
                        print(f"🔄 Выполнено запросов: {stats['requests_count']:,}")
                        print(f"⚡ Текущий RPS: {stats['current_rps']}")
                        print(f"📅 Прогноз на месяц: {stats['monthly_projection']:,.0f}")
                        
                    elif choice == "4":
                        break
                        
                    else:
                        print("❌ Неверный выбор")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return False
        
    finally:
        manager.shutdown()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
