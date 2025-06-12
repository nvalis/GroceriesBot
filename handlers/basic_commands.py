"""
Basic bot command handlers.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat = update.effective_chat
    logger.info(f"Start command from user {user.first_name} ({user.id}) in chat {chat.id}")
    await update.message.reply_text('Hi! I\'m your grocery list bot. Add me to a group to get started!')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Send a message when the command /help is issued."""
    user = update.effective_user
    chat = update.effective_chat
    logger.info(f"Help command from user {user.first_name} ({user.id}) in chat {chat.id}")
    
    # Show current active list
    active_list = list_manager.get_active_list(chat.id)
    
    help_text = f"""
🛒 *Grocery Bot Help*

*Current List:* {active_list.name} (`{active_list.list_id}`)

*Basic Commands:*
/add - Add item to current list
/list - Show current list
/done - Mark item as bought
/remove - Remove item
/clear - Remove bought items

*List Management:*
/lists - Show all your lists
/new - Create new list
/go - Switch to different list
/delete - Delete a list
/wipe - Clear entire current list
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle new members joining the chat."""
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.is_bot and member.username == context.bot.username:
            logger.info(f"Bot added to chat {chat.id} ({chat.title or 'Private'})")
            await update.message.reply_text(
                "Hello! I'm your grocery list bot. Use /help to see available commands."
            )