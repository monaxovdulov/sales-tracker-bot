# Собственная система FSM

## Описание

Мы создали собственную простую и надежную систему управления состояниями (FSM) вместо использования встроенной FSM из pytelegrambotapi.

## Преимущества

- **Простота**: Легко понять и модифицировать
- **Надежность**: Отсутствие зависимости от сложных встроенных модулей
- **Гибкость**: Можно легко расширить функциональность
- **Отладка**: Простое логирование и отслеживание состояний

## Компоненты

### 1. SimpleFSM класс (fsm.py)

Основной класс для управления состояниями:

```python
# Установить состояние
fsm.set_state(user_id, chat_id, States.CLIENT_PHONE)

# Получить состояние
state = fsm.get_state(user_id, chat_id)

# Очистить состояние
fsm.clear_state(user_id, chat_id)

# Сохранить данные
fsm.set_data(user_id, chat_id, 'phone', phone)

# Получить данные
data = fsm.get_data(user_id, chat_id)
```

### 2. States класс

Константы состояний для различных процессов:

```python
class States:
    # Добавление клиента
    CLIENT_PHONE = "client_phone"
    CLIENT_NAME = "client_name"
    CLIENT_MESSENGER = "client_messenger"
    # ... и т.д.
    
    # Вывод средств
    WITHDRAWAL_AMOUNT = "withdrawal_amount"
```

### 3. Обработчики

Централизованные обработчики проверяют состояние и вызывают соответствующие функции:

```python
def handle_text_message(message: Message):
    """Обработчик всех текстовых сообщений с проверкой состояния"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    
    if user_state == States.CLIENT_PHONE:
        process_phone(message)
    elif user_state == States.CLIENT_NAME:
        process_name(message)
    # ... и т.д.
```

## Как добавить новое состояние

1. Добавить константу в класс `States`
2. Добавить обработку в соответствующем обработчике (`handle_text_message`, `handle_callback_query` и т.д.)
3. Создать функцию обработки состояния

## Команды

- `/cancel` - отменить текущую операцию
- Все остальные команды работают как обычно

## Логирование

Система автоматически логирует:
- Установку состояний
- Сохранение данных (в debug режиме)
- Очистку состояний

## Хранение данных

В текущей реализации данные хранятся в памяти. При необходимости можно легко расширить для работы с:
- Redis
- База данных
- Файлы

## Пример полного цикла

1. Пользователь нажимает "Добавить клиента"
2. `fsm.set_state(user_id, chat_id, States.CLIENT_PHONE)`
3. Пользователь вводит телефон
4. `handle_text_message` → `process_phone`
5. `fsm.set_data(user_id, chat_id, 'phone', phone)`
6. `fsm.set_state(user_id, chat_id, States.CLIENT_NAME)`
7. ... и так далее до завершения
8. `fsm.clear_state(user_id, chat_id)` - очистка 