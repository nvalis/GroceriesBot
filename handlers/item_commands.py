"""
Item management command handlers.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Add an item to the shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"Add command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        await update.message.reply_text("Please specify an item to add. Usage: /add <item> [quantity]")
        return
    
    chat_id = update.effective_chat.id
    added_by = update.effective_user.first_name or "Unknown"
    
    # Parse arguments
    if len(context.args) == 1:
        item_name = context.args[0]
        quantity = "1"
    else:
        # Check if last argument is a number (quantity)
        try:
            quantity = str(int(context.args[-1]))
            item_name = " ".join(context.args[:-1])
        except ValueError:
            # Last argument is not a number, treat everything as item name
            item_name = " ".join(context.args)
            quantity = "1"
    
    logger.info(f"Adding item '{item_name}' (qty: {quantity}) by {added_by} in chat {chat.id}")
    list_manager.add_item(chat_id, item_name, quantity, added_by)
    await update.message.reply_text(f"✅ Added {quantity} {item_name} to the shopping list!")


async def remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Remove an item from the shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"Remove command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        await update.message.reply_text("Please specify item number to remove. Usage: /remove <number>")
        return
    
    try:
        index = int(context.args[0]) - 1  # Convert to 0-based index
        chat_id = update.effective_chat.id
        
        logger.info(f"Removing item #{context.args[0]} by {user.first_name} in chat {chat.id}")
        if list_manager.remove_item(chat_id, index):
            await update.message.reply_text("✅ Item removed from the shopping list!")
        else:
            logger.warning(f"Invalid item number {context.args[0]} in chat {chat.id}")
            await update.message.reply_text("❌ Invalid item number.")
    except ValueError:
        logger.warning(f"Invalid number format '{context.args[0]}' from user {user.first_name} in chat {chat.id}")
        await update.message.reply_text("❌ Please provide a valid number.")


async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Mark an item as purchased."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"Done command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        await update.message.reply_text("Please specify item number to mark as done. Usage: /done <number>")
        return
    
    try:
        index = int(context.args[0]) - 1  # Convert to 0-based index
        chat_id = update.effective_chat.id
        
        logger.info(f"Marking item #{context.args[0]} as done by {user.first_name} in chat {chat.id}")
        if list_manager.mark_purchased(chat_id, index):
            await update.message.reply_text("✅ Item marked as purchased!")
        else:
            logger.warning(f"Invalid item number {context.args[0]} in chat {chat.id}")
            await update.message.reply_text("❌ Invalid item number.")
    except ValueError:
        logger.warning(f"Invalid number format '{context.args[0]}' from user {user.first_name} in chat {chat.id}")
        await update.message.reply_text("❌ Please provide a valid number.")