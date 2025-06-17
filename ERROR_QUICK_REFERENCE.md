# PLEX Dynamic Staking Manager - Краткий справочник по ошибкам

## 🚨 КРИТИЧЕСКИЕ ОШИБКИ (Быстрое исправление)

### 1. WalletConnectionDialog ошибки
```python
# ❌ ОШИБКА: 'WalletConnectionDialog' object has no attribute 'status_label'
# ✅ РЕШЕНИЕ: Убедиться что все атрибуты инициализированы в __init__

# ❌ ОШИБКА: обращение к self.dialog в наследнике CTkToplevel  
# ✅ РЕШЕНИЕ: использовать self вместо self.dialog

def show(self):
    self.grab_set()  # ✅ НЕ self.dialog.grab_set()
    self.focus()
    self.result = None
    self.parent.wait_window(self)  # ✅ НЕ self.dialog
```

### 2. CustomTkinter неподдерживаемые параметры
```python
# ❌ ОШИБКА: placeholder_text, hover_color, border_width
# ✅ РЕШЕНИЕ: Использовать только поддерживаемые параметры

# НИКОГДА НЕ ИСПОЛЬЗОВАТЬ:
entry = ctk.CTkEntry(placeholder_text="text")  # ❌
button = ctk.CTkButton(hover_color="#333")     # ❌

# ВСЕГДА ИСПОЛЬЗОВАТЬ:
entry = ctk.CTkEntry(height=35, fg_color="#2a2a2a")  # ✅
# Placeholder через программную логику с bind()
```

### 3. Цветовые ошибки "expected str, bytes or os.Path"
```python
# ❌ ОШИБКА: возврат None или неправильного типа
# ✅ РЕШЕНИЕ: всегда возвращать строку с валидацией

def get_status_color(self, status: str) -> str:
    if not isinstance(status, str):
        return self.colors['text_secondary']  # ✅ Дефолтный цвет
    # ... остальная логика
```

### 4. Отступы и синтаксис
```python
# ❌ ОШИБКА: неправильные отступы в except
try:
    code()
except Exception as e:
logger.error("Error")  # ❌ Неправильный отступ

# ✅ РЕШЕНИЕ: правильные отступы
try:
    code()
except Exception as e:
    logger.error("Error")  # ✅ Правильный отступ
```

## 🎯 ЧЕКЛИСТ ПЕРЕД КОММИТОМ

- [ ] ❌ Нет `placeholder_text` в CTkEntry/CTkTextbox
- [ ] ❌ Нет `hover_color`, `border_width` в виджетах  
- [ ] ✅ Все методы возвращают строки для цветов
- [ ] ✅ Правильные отступы в except блоках
- [ ] ✅ Все атрибуты инициализированы в __init__
- [ ] ✅ CTkToplevel использует self, не self.dialog

## 🔧 БЕЗОПАСНЫЕ ПАТТЕРНЫ

### Создание виджетов
```python
# ✅ Безопасный паттерн создания Entry
def create_safe_entry(parent, placeholder=""):
    entry = ctk.CTkEntry(
        parent,
        height=35,
        fg_color="#2a2a2a",
        border_color="#404040"
    )
    if placeholder:
        setup_placeholder(entry, placeholder)
    return entry
```

### Обработка ошибок
```python
# ✅ Безопасный паттерн обработки
def safe_operation(self, operation_name):
    try:
        result = dangerous_operation()
        self._update_status(f"✅ {operation_name} успешно")
        return result
    except Exception as e:
        logger.error(f"❌ {operation_name}: {e}")
        self._update_status(f"❌ Ошибка: {e}")
        return None
```

## 📁 ПРОБЛЕМНЫЕ ФАЙЛЫ (следить особенно)

1. **ui/components/wallet_connection_dialog.py** - Dialog атрибуты
2. **ui/themes/dark_theme.py** - Параметры виджетов  
3. **ui/main_window_v4.py** - Отступы и except блоки
4. **Любые файлы с CTkEntry/CTkTextbox** - placeholder_text

---
**Используй этот файл как контекст для быстрого решения типовых проблем!**
