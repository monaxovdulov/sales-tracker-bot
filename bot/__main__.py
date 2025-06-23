#!/usr/bin/env python3
"""
Sales Tracker Bot - Main Entry Point
"""

import logging
from telebot import TeleBot

from config import BOT_TOKEN, REPLY_TIMEOUT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Initialize and start the bot"""
    # Initialize bot without FSM storage (using our own FSM)
    bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
    
    # Import and initialize handlers
    from handlers import start, worker, admin
    
    # Initialize all handlers with bot instance
    start.init_bot(bot)
    worker.init_bot(bot)
    admin.init_bot(bot)
    
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