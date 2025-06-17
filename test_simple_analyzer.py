#!/usr/bin/env python3
"""
Тест реального анализа участников с SimpleAnalyzer
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from core.simple_analyzer import SimpleAnalyzer

def test_simple_analyzer():
    print("=== ТЕСТИРОВАНИЕ SIMPLE ANALYZER ===")
    
    try:
        analyzer = SimpleAnalyzer()
        print("✅ SimpleAnalyzer инициализирован")
        
        # Тест анализа участников за последние 6 часов (небольшой период для теста)
        hours = 6
        
        print(f"🕐 Период анализа: последние {hours} часов")
        
        # Запускаем анализ
        results = analyzer.analyze_participants(hours)
        
        print(f"✅ Анализ завершен успешно!")
        print(f"� Результатов получено: {len(results) if results else 0}")
        
        # Выводим результаты
        if results and 'participants' in results:
            participants = results['participants']
            print(f"� Найдено участников: {len(participants)}")
              # Показываем первых 5 участников
            for i, (address, data) in enumerate(list(participants.items())[:5]):
                category = data.category if hasattr(data, 'category') else 'unknown'
                swaps_count = data.swaps_count if hasattr(data, 'swaps_count') else 0
                status = data.status if hasattr(data, 'status') else 'unknown'
                
                print(f"🔍 {address[:10]}...: {category} | Статус: {status} | Операций: {swaps_count}")
        else:
            print("ℹ️ Нет данных о участниках")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_analyzer()
    sys.exit(0 if success else 1)
