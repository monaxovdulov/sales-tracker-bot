#!/usr/bin/env python3
"""
Sales Tracker Bot - Main Entry Point
"""

import logging
from telebot import TeleBot
from telebot.storage import StateMemoryStorage

from config import BOT_TOKEN, REPLY_TIMEOUT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Initialize and start the bot"""
    # Initialize bot with FSM storage
    state_storage = StateMemoryStorage()
    bot = TeleBot(BOT_TOKEN, parse_mode="HTML", state_storage=state_storage)
    
    # Import and initialize handlers
    from handlers import start, worker, admin
    
    # Initialize all handlers with bot instance
    start.init_bot(bot)
    worker.init_bot(bot)
    admin.init_bot(bot)
    admin.register_back_handler(bot)  # Register admin back button handler
    
    logger.info("Bot started successfully")
    
    # Start polling
    try:
        bot.infinity_polling(timeout=REPLY_TIMEOUT)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    main() 