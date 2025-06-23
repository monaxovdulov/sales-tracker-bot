"""
Worker handler module
Handles worker functionality: cabinet, adding clients, withdrawal requests
"""

import datetime
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

import sheets
from services import commission, receipts
from utils.validators import is_phone, is_money, normalize_money, is_url
from fsm import fsm, States

logger = logging.getLogger(__name__)

# Bot instance
bot: TeleBot = None

def init_bot(bot_instance: TeleBot):
    """Initialize bot instance"""
    global bot
    bot = bot_instance
    register_handlers()

def register_handlers():
    """Register all handlers for this module"""
    bot.message_handler(commands=['cabinet'])(handle_cabinet)
    bot.callback_query_handler(func=lambda call: call.data == 'add_client')(start_add_client)
    bot.callback_query_handler(func=lambda call: call.data == 'request_withdrawal')(start_withdrawal)
    
    # Обработчик команды отмены
    bot.message_handler(commands=['cancel'])(handle_cancel)
    
    # Обработчики сообщений для состояний FSM (НЕ для всех сообщений)
    bot.message_handler(func=lambda message: _is_fsm_text_state(message), content_types=['text'])(handle_text_message)
    bot.message_handler(func=lambda message: _is_fsm_media_state(message), content_types=['photo', 'document'])(handle_media_message)
    
    # Обработчики callback для состояний FSM (НЕ для всех callback'ов)
    bot.callback_query_handler(func=lambda call: _is_fsm_callback_state(call))(handle_callback_query)

def _is_fsm_text_state(message) -> bool:
    """Проверить, находится ли пользователь в состоянии FSM для текстовых сообщений"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    text_states = [
        States.CLIENT_PHONE,
        States.CLIENT_NAME, 
        States.CLIENT_ORDER_LINK,
        States.CLIENT_AMOUNT,
        States.CLIENT_RECEIPT,  # для пропуска чека
        States.WITHDRAWAL_AMOUNT
    ]
    return user_state in text_states

def _is_fsm_media_state(message) -> bool:
    """Проверить, находится ли пользователь в состоянии FSM для медиа сообщений"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    return user_state == States.CLIENT_RECEIPT

def _is_fsm_callback_state(call) -> bool:
    """Проверить, является ли callback частью процесса FSM"""
    user_state = fsm.get_state(call.from_user.id, call.message.chat.id)
    
    # Состояния FSM для callback'ов
    callback_states = [
        States.CLIENT_MESSENGER,
        States.CLIENT_STATUS,
        States.CLIENT_CONFIRM
    ]
    
    if user_state in callback_states:
        return True
    
    # Также проверяем специфичные callback данные для FSM
    fsm_callbacks = [
        'messenger_', 'status_', 'confirm_'
    ]
    
    return any(call.data.startswith(prefix) for prefix in fsm_callbacks)

def handle_cabinet(message: Message):
    """Handle /cabinet command"""
    from handlers.start import show_cabinet
    show_cabinet(message)

def handle_cancel(message: Message):
    """Handle /cancel command - cancel current state"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    
    if user_state:
        fsm.clear_state(message.from_user.id, message.chat.id)
        bot.reply_to(message, "❌ Операция отменена")
        logger.info(f"User {message.from_user.id} canceled state: {user_state}")
    else:
        bot.reply_to(message, "Нет активных операций для отмены")

def start_add_client(call: CallbackQuery):
    """Start adding client process"""
    bot.answer_callback_query(call.id)
    fsm.set_state(call.from_user.id, call.message.chat.id, States.CLIENT_PHONE)
    bot.send_message(call.message.chat.id, "📞 Введите телефон клиента (только цифры, 10-15 символов):")

def handle_text_message(message: Message):
    """Обработчик всех текстовых сообщений с проверкой состояния"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    
    if user_state == States.CLIENT_PHONE:
        process_phone(message)
    elif user_state == States.CLIENT_NAME:
        process_name(message)
    elif user_state == States.CLIENT_ORDER_LINK:
        process_order_link(message)
    elif user_state == States.CLIENT_AMOUNT:
        process_amount(message)
    elif user_state == States.CLIENT_RECEIPT:
        skip_receipt(message)
    elif user_state == States.WITHDRAWAL_AMOUNT:
        process_withdrawal_amount(message)

def handle_media_message(message: Message):
    """Обработчик медиа сообщений (фото, документы)"""
    user_state = fsm.get_state(message.from_user.id, message.chat.id)
    
    if user_state == States.CLIENT_RECEIPT:
        process_receipt(message)

def handle_callback_query(call: CallbackQuery):
    """Обработчик всех callback запросов с проверкой состояния"""
    user_state = fsm.get_state(call.from_user.id, call.message.chat.id)
    
    if user_state == States.CLIENT_MESSENGER:
        process_messenger(call)
    elif user_state == States.CLIENT_STATUS:
        process_status(call)
    elif user_state == States.CLIENT_CONFIRM:
        process_confirm(call)
    else:
        # Если callback не связан с состоянием, игнорируем
        bot.answer_callback_query(call.id)

def process_phone(message: Message):
    """Process client phone"""
    # Добавим логирование для отладки
    logger.info(f"Processing phone from user {message.from_user.id}: {message.text}")
    
    phone = message.text.strip()
    
    if not is_phone(phone):
        logger.warning(f"Invalid phone format: {phone}")
        bot.reply_to(message, "❌ Неверный формат телефона. Введите только цифры (10-15 символов):")
        return
    
    logger.info(f"Phone validated successfully: {phone}")
    
    # Save phone to state data
    fsm.set_data(message.from_user.id, message.chat.id, 'phone', phone)
    logger.info(f"Phone saved to state data")
    
    fsm.set_state(message.from_user.id, message.chat.id, States.CLIENT_NAME)
    logger.info(f"State changed to CLIENT_NAME for user {message.from_user.id}")
    bot.reply_to(message, "👤 Введите ФИО клиента:")

def process_name(message: Message):
    """Process client name"""
    name = message.text.strip()
    
    if len(name) < 2:
        bot.reply_to(message, "❌ Слишком короткое имя. Введите ФИО клиента:")
        return
    
    # Save name to state data
    fsm.set_data(message.from_user.id, message.chat.id, 'name', name)
    
    # Show messenger options
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 Telegram", callback_data="messenger_telegram"),
        InlineKeyboardButton("💬 WhatsApp", callback_data="messenger_whatsapp"),
        InlineKeyboardButton("📧 Другое", callback_data="messenger_other")
    )
    
    fsm.set_state(message.from_user.id, message.chat.id, States.CLIENT_MESSENGER)
    bot.reply_to(message, "📨 Выберите мессенджер для связи:", reply_markup=keyboard)

def process_messenger(call: CallbackQuery):
    """Process messenger selection"""
    bot.answer_callback_query(call.id)
    
    messenger_map = {
        "messenger_telegram": "Telegram",
        "messenger_whatsapp": "WhatsApp",
        "messenger_other": "Другое"
    }
    
    messenger = messenger_map.get(call.data, "Другое")
    
    # Save messenger to state data
    fsm.set_data(call.from_user.id, call.message.chat.id, 'messenger', messenger)
    
    fsm.set_state(call.from_user.id, call.message.chat.id, States.CLIENT_ORDER_LINK)
    bot.edit_message_text(
        "🔗 Введите ссылку на товар или описание заказа:",
        call.message.chat.id,
        call.message.message_id
    )

def process_order_link(message: Message):
    """Process order link or description"""
    order_link = message.text.strip()
    
    if len(order_link) < 3:
        bot.reply_to(message, "❌ Слишком короткое описание. Введите ссылку или описание заказа:")
        return
    
    # Save order_link to state data
    fsm.set_data(message.from_user.id, message.chat.id, 'order_link', order_link)
    
    fsm.set_state(message.from_user.id, message.chat.id, States.CLIENT_AMOUNT)
    bot.reply_to(message, "💰 Введите сумму заказа (в рублях):")

def process_amount(message: Message):
    """Process order amount"""
    amount_str = message.text.strip()
    
    if not is_money(amount_str):
        bot.reply_to(message, "❌ Неверный формат суммы. Введите число (например: 1000 или 1000.50):")
        return
    
    amount = float(normalize_money(amount_str))
    
    if amount <= 0:
        bot.reply_to(message, "❌ Сумма должна быть больше нуля:")
        return
    
    # Save amount to state data
    fsm.set_data(message.from_user.id, message.chat.id, 'amount', amount)
    
    # Show status options
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🤔 Хочет купить", callback_data="status_wants"),
        InlineKeyboardButton("⏳ Ждём оплаты", callback_data="status_waiting"),
        InlineKeyboardButton("✅ Оплатил", callback_data="status_paid")
    )
    
    fsm.set_state(message.from_user.id, message.chat.id, States.CLIENT_STATUS)
    bot.reply_to(message, "📋 Выберите статус заказа:", reply_markup=keyboard)

def process_status(call: CallbackQuery):
    """Process status selection"""
    bot.answer_callback_query(call.id)
    
    status_map = {
        "status_wants": "хочет купить",
        "status_waiting": "ждём оплаты",
        "status_paid": "оплатил"
    }
    
    status = status_map.get(call.data, "хочет купить")
    
    # Save status to state data
    fsm.set_data(call.from_user.id, call.message.chat.id, 'status', status)
    
    if status == "оплатил":
        fsm.set_state(call.from_user.id, call.message.chat.id, States.CLIENT_RECEIPT)
        bot.edit_message_text(
            "📄 Прикрепите фото или PDF чека (или отправьте любое сообщение для пропуска):",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        # Skip receipt step
        fsm.set_data(call.from_user.id, call.message.chat.id, 'receipt_url', '')
        show_confirmation(call.message.chat.id, call.from_user.id)

def process_receipt(message: Message):
    """Process receipt file"""
    try:
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id
        
        if file_id:
            # Upload to Google Drive
            receipt_url = receipts.save_receipt(bot, file_id)
            
            fsm.set_data(message.from_user.id, message.chat.id, 'receipt_url', receipt_url)
            
            bot.reply_to(message, "✅ Чек сохранён!")
        else:
            fsm.set_data(message.from_user.id, message.chat.id, 'receipt_url', '')
        
        show_confirmation(message.chat.id, message.from_user.id)
        
    except Exception as e:
        logger.error(f"Error saving receipt: {e}")
        bot.reply_to(message, "❌ Ошибка при сохранении чека. Продолжаем без чека.")
        
        fsm.set_data(message.from_user.id, message.chat.id, 'receipt_url', '')
        
        show_confirmation(message.chat.id, message.from_user.id)

def skip_receipt(message: Message):
    """Skip receipt upload"""
    fsm.set_data(message.from_user.id, message.chat.id, 'receipt_url', '')
    
    show_confirmation(message.chat.id, message.from_user.id)

def show_confirmation(chat_id: int, user_id: int):
    """Show confirmation of client data"""
    data = fsm.get_data(user_id, chat_id)
    
    text = f"""📋 <b>Проверьте данные клиента:</b>

📞 Телефон: {data['phone']}
👤 ФИО: {data['name']}
📨 Мессенджер: {data['messenger']}
🔗 Заказ: {data['order_link']}
💰 Сумма: {data['amount']:.2f} ₽
📋 Статус: {data['status']}
📄 Чек: {"Есть" if data.get('receipt_url') else "Нет"}"""
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Сохранить", callback_data="confirm_save"),
        InlineKeyboardButton("❌ Отменить", callback_data="confirm_cancel")
    )
    
    fsm.set_state(user_id, chat_id, States.CLIENT_CONFIRM)
    bot.send_message(chat_id, text, reply_markup=keyboard)

def process_confirm(call: CallbackQuery):
    """Process confirmation"""
    bot.answer_callback_query(call.id)
    
    if call.data == "confirm_save":
        save_client(call.message.chat.id, call.from_user.id)
    else:
        fsm.clear_state(call.from_user.id, call.message.chat.id)
        bot.edit_message_text("❌ Добавление клиента отменено", call.message.chat.id, call.message.message_id)

def save_client(chat_id: int, user_id: int):
    """Save client to spreadsheet"""
    try:
        data = fsm.get_data(user_id, chat_id)
        
        # Get worker info
        worker = sheets.get_worker(user_id)
        if not worker:
            bot.send_message(chat_id, "❌ Ошибка: работник не найден")
            return
        
        # Calculate commission
        clients_count = worker.get('clients_count', 0)
        amount = data['amount']
        commission_amount = commission.calc(clients_count, amount)
        
        # Prepare client data
        client_data = {
            'worker_tg_id': user_id,
            'worker_username': worker.get('username', ''),
            'phone': data['phone'],
            'name': data['name'],
            'messenger': data['messenger'],
            'order_link': data['order_link'],
            'amount': amount,
            'status': data['status'],
            'receipt_url': data.get('receipt_url', ''),
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save to sheets
        sheets.append_client_row(client_data)
        sheets.inc_clients_count(user_id)
        
        # Add commission to balance only if paid
        if data['status'] == 'оплатил':
            sheets.inc_balance(user_id, commission_amount)
        
        # Notify admins
        notify_admins_new_client(client_data, commission_amount)
        
        bot.send_message(chat_id, f"✅ Клиент добавлен! Комиссия: {commission_amount:.2f} ₽")
        
    except Exception as e:
        logger.error(f"Error saving client: {e}")
        bot.send_message(chat_id, "❌ Ошибка при сохранении клиента")
    
    finally:
        fsm.clear_state(user_id, chat_id)

def notify_admins_new_client(client_data: dict, commission: float):
    """Notify admins about new client"""
    from config import ADMIN_IDS
    
    text = f"""📈 <b>Новый клиент добавлен</b>

👤 Работник: @{client_data['worker_username']}
📞 Клиент: {client_data['name']} ({client_data['phone']})
💰 Сумма: {client_data['amount']:.2f} ₽
💵 Комиссия: {commission:.2f} ₽
📋 Статус: {client_data['status']}"""
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

def start_withdrawal(call: CallbackQuery):
    """Start withdrawal request"""
    bot.answer_callback_query(call.id)
    
    # Check worker balance
    worker = sheets.get_worker(call.from_user.id)
    if not worker:
        bot.send_message(call.message.chat.id, "❌ Работник не найден")
        return
    
    balance = worker.get('balance', 0.0)
    if balance <= 0:
        bot.send_message(call.message.chat.id, "❌ Недостаточно средств для вывода")
        return
    
    fsm.set_state(call.from_user.id, call.message.chat.id, States.WITHDRAWAL_AMOUNT)
    bot.send_message(call.message.chat.id, f"💰 Ваш баланс: {balance:.2f} ₽\n\nВведите сумму для вывода:")

def process_withdrawal_amount(message: Message):
    """Process withdrawal amount"""
    try:
        amount_str = message.text.strip()
        
        if not is_money(amount_str):
            bot.reply_to(message, "❌ Неверный формат суммы. Введите число:")
            return
        
        amount = float(normalize_money(amount_str))
        
        if amount <= 0:
            bot.reply_to(message, "❌ Сумма должна быть больше нуля:")
            return
        
        # Check balance
        worker = sheets.get_worker(message.from_user.id)
        balance = worker.get('balance', 0.0)
        
        if amount > balance:
            bot.reply_to(message, f"❌ Недостаточно средств. Ваш баланс: {balance:.2f} ₽")
            return
        
        # Create withdrawal request
        withdrawal_id = sheets.create_withdrawal(message.from_user.id, amount)
        
        # Deduct from balance immediately
        sheets.inc_balance(message.from_user.id, -amount)
        
        # Notify admins
        notify_admins_withdrawal(message.from_user.id, worker.get('username', ''), amount, withdrawal_id)
        
        bot.reply_to(message, f"✅ Заявка на вывод {amount:.2f} ₽ отправлена администратору")
        
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        bot.reply_to(message, "❌ Ошибка при обработке заявки")
    
    finally:
        fsm.clear_state(message.from_user.id, message.chat.id)

def notify_admins_withdrawal(tg_id: int, username: str, amount: float, withdrawal_id: int):
    """Notify admins about withdrawal request"""
    from config import ADMIN_IDS
    
    text = f"""💸 <b>Заявка на вывод средств</b>

👤 Работник: @{username} (ID: {tg_id})
💰 Сумма: {amount:.2f} ₽
🆔 ID заявки: {withdrawal_id}"""
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Выплатил", callback_data=f"withdraw_approve_{withdrawal_id}"),
        InlineKeyboardButton("❌ Отказ", callback_data=f"withdraw_decline_{withdrawal_id}")
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}") 