"""
Start handler module
Handles /start command and worker registration flow
"""

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

from config import ADMIN_IDS
import sheets

logger = logging.getLogger(__name__)

# Get bot instance from main module
bot: TeleBot = None

def init_bot(bot_instance: TeleBot):
    """Initialize bot instance"""
    global bot
    bot = bot_instance
    register_handlers()

def register_handlers():
    """Register all handlers for this module"""
    bot.message_handler(commands=['start'])(handle_start)
    bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))(handle_approve)
    bot.callback_query_handler(func=lambda call: call.data.startswith('decline_'))(handle_decline)

def handle_start(message: Message):
    """Handle /start command"""
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    # Check if user is admin
    if tg_id in ADMIN_IDS:
        bot.reply_to(message, "🔧 Вы админ, используйте /admin для панели управления")
        return
    
    # Check worker status
    worker = sheets.get_worker(tg_id)
    
    if worker:
        if worker.get("role") == "worker":
            show_cabinet(message)
        elif worker.get("role") == "pending":
            bot.reply_to(message, "⏳ Ваша заявка на рассмотрении. Ожидайте одобрения от администратора.")
        else:
            bot.reply_to(message, "❌ Произошла ошибка. Обратитесь к администратору.")
    else:
        # Add new worker with pending status
        sheets.add_worker(tg_id, username)
        
        # Notify admins
        notify_admins_new_worker(tg_id, username)
        
        bot.reply_to(message, "📝 Заявка на регистрацию отправлена. Ожидайте одобрения от администратора.")

def show_cabinet(message: Message):
    """Show worker cabinet"""
    tg_id = message.from_user.id
    worker = sheets.get_worker(tg_id)
    
    if not worker:
        bot.reply_to(message, "❌ Работник не найден")
        return
    
    clients_count = worker.get("clients_count", 0)
    balance = worker.get("balance", 0.0)
    
    text = f"""👤 <b>Ваш личный кабинет</b>

— Клиентов: {clients_count}
— Баланс: {balance:.2f} ₽"""
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить клиента", callback_data="add_client"),
        InlineKeyboardButton("💸 Запросить выплату", callback_data="request_withdrawal")
    )
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

def notify_admins_new_worker(tg_id: int, username: str):
    """Notify admins about new worker registration"""
    text = f"📋 <b>Новая заявка на регистрацию</b>\n\nПользователь: @{username}\nID: {tg_id}"
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{tg_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{tg_id}")
    )
    
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

def handle_approve(call: CallbackQuery):
    """Handle worker approval"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    tg_id = int(call.data.split('_')[1])
    
    try:
        sheets.approve_worker(tg_id)
        bot.edit_message_text(
            f"✅ Работник {tg_id} одобрен",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify worker
        try:
            bot.send_message(tg_id, "🎉 Поздравляем! Ваша заявка одобрена. Теперь вы можете пользоваться ботом. Нажмите /start для входа в личный кабинет.")
        except Exception as e:
            logger.error(f"Failed to notify worker {tg_id}: {e}")
            
    except Exception as e:
        logger.error(f"Failed to approve worker {tg_id}: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при одобрении")

def handle_decline(call: CallbackQuery):
    """Handle worker decline"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    tg_id = int(call.data.split('_')[1])
    
    bot.edit_message_text(
        f"❌ Заявка работника {tg_id} отклонена",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Note: We don't delete the worker record, just leave it as pending
    # This allows for manual review later if needed 