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
