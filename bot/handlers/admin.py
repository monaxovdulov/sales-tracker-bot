"""
Admin handler module
Handles admin functionality: /admin panel, withdrawal approvals, exports
"""

import csv
import tempfile
import os
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

from config import ADMIN_IDS
import sheets

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
    bot.message_handler(commands=['admin'])(handle_admin)
    bot.callback_query_handler(func=lambda call: call.data == 'admin_top_workers')(show_top_workers)
    bot.callback_query_handler(func=lambda call: call.data == 'admin_withdrawals')(show_withdrawals)
    bot.callback_query_handler(func=lambda call: call.data == 'admin_export_csv')(export_csv)
    bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))(approve_withdrawal)
    bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_decline_'))(decline_withdrawal)
    bot.callback_query_handler(func=lambda call: call.data == 'admin_back')(handle_admin_back)

def handle_admin(message: Message):
    """Handle /admin command"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Недостаточно прав")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📊 Топ работников", callback_data="admin_top_workers"),
        InlineKeyboardButton("💸 Заявки на вывод", callback_data="admin_withdrawals"),
        InlineKeyboardButton("📄 Экспорт CSV", callback_data="admin_export_csv")
    )
    
    bot.reply_to(message, "🔧 <b>Панель администратора</b>", reply_markup=keyboard)

def show_top_workers(call: CallbackQuery):
    """Show top workers by balance"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    bot.answer_callback_query(call.id)
    
    try:
        ws = sheets.workers_ws()
        records = ws.get_all_records()
        
        # Filter only workers (not pending)
        workers = [r for r in records if r.get('role') == 'worker']
        
        # Sort by balance descending
        workers.sort(key=lambda x: float(x.get('balance', 0)), reverse=True)
        
        if not workers:
            bot.edit_message_text(
                "📊 <b>Топ работников</b>\n\nРаботников пока нет",
                call.message.chat.id,
                call.message.message_id
            )
            return
        
        text = "📊 <b>Топ работников по балансу:</b>\n\n"
        
        for i, worker in enumerate(workers[:10], 1):  # Top 10
            username = worker.get('username', 'unknown')
            balance = float(worker.get('balance', 0))
            clients_count = int(worker.get('clients_count', 0))
            
            text += f"{i}. @{username}\n"
            text += f"   💰 Баланс: {balance:.2f} ₽\n"
            text += f"   👥 Клиентов: {clients_count}\n\n"
        
        # Add back button
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing top workers: {e}")
        bot.edit_message_text("❌ Ошибка при получении данных", call.message.chat.id, call.message.message_id)

def show_withdrawals(call: CallbackQuery):
    """Show pending withdrawal requests"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    bot.answer_callback_query(call.id)
    
    try:
        ws = sheets.withdrawals_ws()
        records = ws.get_all_records()
        
        # Filter pending withdrawals
        pending = [r for r in records if r.get('status') == 'PENDING']
        
        if not pending:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_back"))
            
            bot.edit_message_text(
                "💸 <b>Заявки на вывод</b>\n\nНет заявок на рассмотрении",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
            return
        
        text = "💸 <b>Заявки на вывод:</b>\n\n"
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        for withdrawal in pending:
            withdrawal_id = int(withdrawal.get('id', 0))
            tg_id = int(withdrawal.get('tg_id', 0))
            amount = float(withdrawal.get('amount', 0))
            
            # Get worker username
            worker = sheets.get_worker(tg_id)
            username = worker.get('username', 'unknown') if worker else 'unknown'
            
            text += f"🆔 ID: {withdrawal_id}\n"
            text += f"👤 @{username} (ID: {tg_id})\n"
            text += f"💰 Сумма: {amount:.2f} ₽\n\n"
            
            keyboard.add(
                InlineKeyboardButton(f"✅ {withdrawal_id}", callback_data=f"withdraw_approve_{withdrawal_id}"),
                InlineKeyboardButton(f"❌ {withdrawal_id}", callback_data=f"withdraw_decline_{withdrawal_id}")
            )
        
        keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="admin_back"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error showing withdrawals: {e}")
        bot.edit_message_text("❌ Ошибка при получении данных", call.message.chat.id, call.message.message_id)

def approve_withdrawal(call: CallbackQuery):
    """Approve withdrawal request"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    withdrawal_id = int(call.data.split('_')[2])
    
    try:
        # Get withdrawal details
        ws = sheets.withdrawals_ws()
        records = ws.get_all_records()
        
        withdrawal = None
        for record in records:
            if int(record.get('id', 0)) == withdrawal_id:
                withdrawal = record
                break
        
        if not withdrawal:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена")
            return
        
        tg_id = int(withdrawal.get('tg_id', 0))
        amount = float(withdrawal.get('amount', 0))
        
        # Update status to DONE
        sheets.update_withdrawal(withdrawal_id, "DONE")
        
        # Notify worker
        try:
            bot.send_message(tg_id, f"✅ Выплата {amount:.2f} ₽ подтверждена и выполнена!")
        except Exception as e:
            logger.error(f"Failed to notify worker {tg_id}: {e}")
        
        bot.answer_callback_query(call.id, f"✅ Выплата {withdrawal_id} подтверждена")
        
        # Refresh the withdrawals list
        show_withdrawals(call)
        
    except Exception as e:
        logger.error(f"Error approving withdrawal {withdrawal_id}: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при подтверждении")

def decline_withdrawal(call: CallbackQuery):
    """Decline withdrawal request"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    withdrawal_id = int(call.data.split('_')[2])
    
    try:
        # Get withdrawal details
        ws = sheets.withdrawals_ws()
        records = ws.get_all_records()
        
        withdrawal = None
        for record in records:
            if int(record.get('id', 0)) == withdrawal_id:
                withdrawal = record
                break
        
        if not withdrawal:
            bot.answer_callback_query(call.id, "❌ Заявка не найдена")
            return
        
        tg_id = int(withdrawal.get('tg_id', 0))
        amount = float(withdrawal.get('amount', 0))
        
        # Update status to DECLINED
        sheets.update_withdrawal(withdrawal_id, "DECLINED")
        
        # Return money to worker balance
        sheets.inc_balance(tg_id, amount)
        
        # Notify worker
        try:
            bot.send_message(tg_id, f"❌ Заявка на выплату {amount:.2f} ₽ отклонена. Средства возвращены на баланс.")
        except Exception as e:
            logger.error(f"Failed to notify worker {tg_id}: {e}")
        
        bot.answer_callback_query(call.id, f"❌ Выплата {withdrawal_id} отклонена")
        
        # Refresh the withdrawals list
        show_withdrawals(call)
        
    except Exception as e:
        logger.error(f"Error declining withdrawal {withdrawal_id}: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка при отклонении")

def export_csv(call: CallbackQuery):
    """Export withdrawals to CSV"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    bot.answer_callback_query(call.id)
    
    try:
        ws = sheets.withdrawals_ws()
        records = ws.get_all_records()
        
        # Filter only DONE withdrawals
        done_withdrawals = [r for r in records if r.get('status') == 'DONE']
        
        if not done_withdrawals:
            bot.send_message(call.message.chat.id, "📄 Нет выполненных выплат для экспорта")
            return
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'TG_ID', 'Username', 'Amount', 'Status', 'Date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for withdrawal in done_withdrawals:
                tg_id = int(withdrawal.get('tg_id', 0))
                
                # Get worker username
                worker = sheets.get_worker(tg_id)
                username = worker.get('username', 'unknown') if worker else 'unknown'
                
                writer.writerow({
                    'ID': withdrawal.get('id', ''),
                    'TG_ID': tg_id,
                    'Username': username,
                    'Amount': withdrawal.get('amount', ''),
                    'Status': withdrawal.get('status', ''),
                    'Date': withdrawal.get('created_at', '')
                })
            
            temp_path = csvfile.name
        
        # Send CSV file
        with open(temp_path, 'rb') as csvfile:
            bot.send_document(
                call.message.chat.id,
                csvfile,
                caption="📄 Экспорт выполненных выплат"
            )
        
        # Clean up temporary file
        os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        bot.send_message(call.message.chat.id, "❌ Ошибка при экспорте данных")

# Register callback for back button
def handle_admin_back(call: CallbackQuery):
    """Handle back button in admin panel"""
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "❌ Недостаточно прав")
        return
    
    bot.answer_callback_query(call.id)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📊 Топ работников", callback_data="admin_top_workers"),
        InlineKeyboardButton("💸 Заявки на вывод", callback_data="admin_withdrawals"),
        InlineKeyboardButton("📄 Экспорт CSV", callback_data="admin_export_csv")
    )
    
    bot.edit_message_text("🔧 <b>Панель администратора</b>", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# Register the back button handler separately
def register_back_handler(bot_instance):
    """Register back button handler"""
    bot_instance.callback_query_handler(func=lambda call: call.data == 'admin_back')(handle_admin_back) 