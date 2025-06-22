"""
Worker handler module
Handles worker functionality: cabinet, adding clients, withdrawal requests
"""

import datetime
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import logging

import sheets
from services import commission, receipts
from utils.validators import is_phone, is_money, normalize_money, is_url

logger = logging.getLogger(__name__)

# FSM States
class ClientForm(StatesGroup):
    phone = State()
    name = State()
    messenger = State()
    order_link = State()
    amount = State()
    status = State()
    receipt = State()
    confirm = State()

class WithdrawalForm(StatesGroup):
    amount = State()

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
    
    # FSM handlers for adding client
    bot.message_handler(state=ClientForm.phone)(process_phone)
    bot.message_handler(state=ClientForm.name)(process_name)
    bot.callback_query_handler(state=ClientForm.messenger)(process_messenger)
    bot.message_handler(state=ClientForm.order_link)(process_order_link)
    bot.message_handler(state=ClientForm.amount)(process_amount)
    bot.callback_query_handler(state=ClientForm.status)(process_status)
    bot.message_handler(state=ClientForm.receipt, content_types=['photo', 'document'])(process_receipt)
    bot.message_handler(state=ClientForm.receipt)(skip_receipt)
    bot.callback_query_handler(state=ClientForm.confirm)(process_confirm)
    
    # FSM handlers for withdrawal
    bot.message_handler(state=WithdrawalForm.amount)(process_withdrawal_amount)

def handle_cabinet(message: Message):
    """Handle /cabinet command"""
    from handlers.start import show_cabinet
    show_cabinet(message)

def start_add_client(call: CallbackQuery):
    """Start adding client process"""
    bot.answer_callback_query(call.id)
    bot.set_state(call.from_user.id, ClientForm.phone, call.message.chat.id)
    bot.send_message(call.message.chat.id, "📞 Введите телефон клиента (только цифры, 10-15 символов):")

def process_phone(message: Message):
    """Process client phone"""
    phone = message.text.strip()
    
    if not is_phone(phone):
        bot.reply_to(message, "❌ Неверный формат телефона. Введите только цифры (10-15 символов):")
        return
    
    # Save phone to state data
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['phone'] = phone
    
    bot.set_state(message.from_user.id, ClientForm.name, message.chat.id)
    bot.reply_to(message, "👤 Введите ФИО клиента:")

def process_name(message: Message):
    """Process client name"""
    name = message.text.strip()
    
    if len(name) < 2:
        bot.reply_to(message, "❌ Слишком короткое имя. Введите ФИО клиента:")
        return
    
    # Save name to state data
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name
    
    # Show messenger options
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 Telegram", callback_data="messenger_telegram"),
        InlineKeyboardButton("💬 WhatsApp", callback_data="messenger_whatsapp"),
        InlineKeyboardButton("📧 Другое", callback_data="messenger_other")
    )
    
    bot.set_state(message.from_user.id, ClientForm.messenger, message.chat.id)
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
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['messenger'] = messenger
    
    bot.set_state(call.from_user.id, ClientForm.order_link, call.message.chat.id)
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
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['order_link'] = order_link
    
    bot.set_state(message.from_user.id, ClientForm.amount, message.chat.id)
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
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['amount'] = amount
    
    # Show status options
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🤔 Хочет купить", callback_data="status_wants"),
        InlineKeyboardButton("⏳ Ждём оплаты", callback_data="status_waiting"),
        InlineKeyboardButton("✅ Оплатил", callback_data="status_paid")
    )
    
    bot.set_state(message.from_user.id, ClientForm.status, message.chat.id)
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
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['status'] = status
    
    if status == "оплатил":
        bot.set_state(call.from_user.id, ClientForm.receipt, call.message.chat.id)
        bot.edit_message_text(
            "📄 Прикрепите фото или PDF чека (или отправьте любое сообщение для пропуска):",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        # Skip receipt step
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data['receipt_url'] = ""
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
            
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['receipt_url'] = receipt_url
            
            bot.reply_to(message, "✅ Чек сохранён!")
        else:
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['receipt_url'] = ""
        
        show_confirmation(message.chat.id, message.from_user.id)
        
    except Exception as e:
        logger.error(f"Error saving receipt: {e}")
        bot.reply_to(message, "❌ Ошибка при сохранении чека. Продолжаем без чека.")
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['receipt_url'] = ""
        
        show_confirmation(message.chat.id, message.from_user.id)

def skip_receipt(message: Message):
    """Skip receipt upload"""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['receipt_url'] = ""
    
    show_confirmation(message.chat.id, message.from_user.id)

def show_confirmation(chat_id: int, user_id: int):
    """Show confirmation of client data"""
    with bot.retrieve_data(user_id, chat_id) as data:
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
    
    bot.set_state(user_id, ClientForm.confirm, chat_id)
    bot.send_message(chat_id, text, reply_markup=keyboard)

def process_confirm(call: CallbackQuery):
    """Process confirmation"""
    bot.answer_callback_query(call.id)
    
    if call.data == "confirm_save":
        save_client(call.message.chat.id, call.from_user.id)
    else:
        bot.delete_state(call.from_user.id, call.message.chat.id)
        bot.edit_message_text("❌ Добавление клиента отменено", call.message.chat.id, call.message.message_id)

def save_client(chat_id: int, user_id: int):
    """Save client to spreadsheet"""
    try:
        with bot.retrieve_data(user_id, chat_id) as data:
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
        bot.delete_state(user_id, chat_id)

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
    
    bot.set_state(call.from_user.id, WithdrawalForm.amount, call.message.chat.id)
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
        bot.delete_state(message.from_user.id, message.chat.id)

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