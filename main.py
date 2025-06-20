"""
Main entry point for the Telegram Groceries Bot.
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from persistent_list_manager import PersistentShoppingListManager
from handlers import (
    start, help_command, new_chat_members,
    add_item, remove_item, mark_done,
    show_current_list, show_all_lists, create_list, switch_list,
    delete_list, wipe_list,
    handle_callback_query, handle_reply_keyboard_text,
    backup_data, stats_command
)

# Load environment variables from .env file
load_dotenv()

# Enable logging to both console and file
import datetime
log_filename = f"bot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Create handlers
file_handler = logging.FileHandler(log_filename)
console_handler = logging.StreamHandler()

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Reduce httpx logging spam
logging.getLogger('httpx').setLevel(logging.WARNING)

# Global shopping list manager with SQLite persistence
list_manager = PersistentShoppingListManager()


def create_handler_with_list_manager(handler_func):
    """Create a wrapper that passes list_manager to handlers that need it."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await handler_func(update, context, list_manager)
    return wrapper


def main() -> None:
    """Start the bot."""
    # Create the Application
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    application = Application.builder().token(token).build()

    # Basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", create_handler_with_list_manager(help_command)))
    
    # Item management handlers
    application.add_handler(CommandHandler("add", create_handler_with_list_manager(add_item)))
    application.add_handler(CommandHandler("remove", create_handler_with_list_manager(remove_item)))
    application.add_handler(CommandHandler("done", create_handler_with_list_manager(mark_done)))
    
    # List management handlers
    application.add_handler(CommandHandler("list", create_handler_with_list_manager(show_current_list)))
    application.add_handler(CommandHandler("lists", create_handler_with_list_manager(show_all_lists)))
    application.add_handler(CommandHandler("new", create_handler_with_list_manager(create_list)))
    application.add_handler(CommandHandler("go", create_handler_with_list_manager(switch_list)))
    application.add_handler(CommandHandler("delete", create_handler_with_list_manager(delete_list)))
    application.add_handler(CommandHandler("wipe", create_handler_with_list_manager(wipe_list)))
    
    # Callback query handler for interactive buttons
    application.add_handler(CallbackQueryHandler(create_handler_with_list_manager(handle_callback_query)))
    
    # Text message handler for reply keyboard and general text input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, create_handler_with_list_manager(handle_reply_keyboard_text)))
    
    # Admin handlers
    application.add_handler(CommandHandler("backup", create_handler_with_list_manager(backup_data)))
    application.add_handler(CommandHandler("stats", create_handler_with_list_manager(stats_command)))
    
    
    # Group management handler
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))

    # Run the bot until the user presses Ctrl-C
    logger.info(f"Starting bot... Log file: {log_filename}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()