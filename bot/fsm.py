"""
Собственная система управления состояниями (FSM)
Простая и надежная альтернатива встроенному FSM
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class UserState:
    """Состояние пользователя"""
    state: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

class SimpleFSM:
    """Простая система управления состояниями"""
    
    def __init__(self):
        # Хранилище состояний: {user_id: {chat_id: UserState}}
        self._states: Dict[int, Dict[int, UserState]] = {}
    
    def _get_user_state(self, user_id: int, chat_id: int) -> UserState:
        """Получить объект состояния пользователя"""
        if user_id not in self._states:
            self._states[user_id] = {}
        
        if chat_id not in self._states[user_id]:
            self._states[user_id][chat_id] = UserState()
        
        return self._states[user_id][chat_id]
    
    def set_state(self, user_id: int, chat_id: int, state: str):
        """Установить состояние пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        user_state.state = state
        logger.info(f"Set state for user {user_id} in chat {chat_id}: {state}")
    
    def get_state(self, user_id: int, chat_id: int) -> Optional[str]:
        """Получить текущее состояние пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        return user_state.state
    
    def clear_state(self, user_id: int, chat_id: int):
        """Очистить состояние пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        user_state.state = None
        user_state.data.clear()
        logger.info(f"Cleared state for user {user_id} in chat {chat_id}")
    
    def set_data(self, user_id: int, chat_id: int, key: str, value: Any):
        """Установить данные пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        user_state.data[key] = value
        logger.debug(f"Set data for user {user_id} in chat {chat_id}: {key}={value}")
    
    def get_data(self, user_id: int, chat_id: int, key: str = None) -> Any:
        """Получить данные пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        if key is None:
            return user_state.data.copy()
        return user_state.data.get(key)
    
    def update_data(self, user_id: int, chat_id: int, **kwargs):
        """Обновить данные пользователя"""
        user_state = self._get_user_state(user_id, chat_id)
        user_state.data.update(kwargs)
        logger.debug(f"Updated data for user {user_id} in chat {chat_id}: {kwargs}")

# Глобальный экземпляр FSM
fsm = SimpleFSM()

# Константы состояний
class States:
    """Константы состояний для форм"""
    
    # Состояния добавления клиента
    CLIENT_PHONE = "client_phone"
    CLIENT_NAME = "client_name" 
    CLIENT_MESSENGER = "client_messenger"
    CLIENT_ORDER_LINK = "client_order_link"
    CLIENT_AMOUNT = "client_amount"
    CLIENT_STATUS = "client_status"
    CLIENT_RECEIPT = "client_receipt"
    CLIENT_CONFIRM = "client_confirm"
    
    # Состояния вывода средств
    WITHDRAWAL_AMOUNT = "withdrawal_amount"

def state_handler(state: str):
    """Декоратор для обработчиков состояний"""
    def decorator(func):
        def wrapper(message):
            user_state = fsm.get_state(message.from_user.id, message.chat.id)
            if user_state == state:
                return func(message)
            return None
        return wrapper
    return decorator

def callback_state_handler(state: str):
    """Декоратор для callback обработчиков состояний"""
    def decorator(func):
        def wrapper(call):
            user_state = fsm.get_state(call.from_user.id, call.message.chat.id)
            if user_state == state:
                return func(call)
            return None
        return wrapper
    return decorator 