"""
List management command handlers.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def show_current_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show the current active shopping list with interactive buttons."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"List command from user {user.first_name} ({user.id}) in chat {chat.id}")
    shopping_list = list_manager.get_active_list(chat_id)
    list_text = shopping_list.get_display_text()
    keyboard = shopping_list.get_interactive_keyboard()
    
    await update.message.reply_text(list_text, parse_mode='Markdown', reply_markup=keyboard)


async def show_all_lists(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show all shopping lists for the chat with interactive buttons."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"Lists command from user {user.first_name} ({user.id}) in chat {chat.id}")
    lists_text = list_manager.get_lists_summary(chat_id)
    keyboard = list_manager.get_lists_keyboard(chat_id)
    
    await update.message.reply_text(lists_text, parse_mode='Markdown', reply_markup=keyboard)


async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Create a new shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"New list command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        await update.message.reply_text("Please specify a name for the new list. Usage: /new <name>\n\nExamples:\n/new Costco\n/new Whole Foods\n/new Pharmacy")
        return
    
    chat_id = update.effective_chat.id
    list_name = " ".join(context.args)
    
    logger.info(f"Creating new list '{list_name}' by {user.first_name} in chat {chat.id}")
    list_id = list_manager.create_list(chat_id, list_name)
    list_manager.set_active_list(chat_id, list_id)  # Auto-switch to new list
    
    await update.message.reply_text(f"✅ Created and switched to *{list_name}*!\nStart adding items with /add", parse_mode='Markdown')


async def switch_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Switch to a different shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"Go command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        
        # Show available lists for easy switching
        lists_text = list_manager.get_lists_summary(chat.id)
        await update.message.reply_text(f"{lists_text}\n\nUsage: /go <list_id>\nExample: /go costco", parse_mode='Markdown')
        return
    
    chat_id = update.effective_chat.id
    list_id = context.args[0].lower().replace(" ", "_")
    
    logger.info(f"Switching to list '{list_id}' by {user.first_name} in chat {chat.id}")
    
    # Check if list exists
    if chat_id in list_manager.lists and list_id in list_manager.lists[chat_id]:
        list_manager.set_active_list(chat_id, list_id)
        list_name = list_manager.get_active_list(chat_id).name
        await update.message.reply_text(f"🛒 Now shopping at *{list_name}*!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ List `{list_id}` not found.\nUse /lists to see your lists or /new to create one.", parse_mode='Markdown')


async def delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Delete a shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    
    if not context.args:
        logger.info(f"Delete command without args from user {user.first_name} ({user.id}) in chat {chat.id}")
        await update.message.reply_text("Please specify a list ID to delete. Usage: /delete <list_id>\nUse /lists to see available lists.")
        return
    
    chat_id = update.effective_chat.id
    list_id = context.args[0].lower().replace(" ", "_")
    
    logger.info(f"Deleting list '{list_id}' by {user.first_name} in chat {chat.id}")
    
    if list_manager.delete_list(chat_id, list_id):
        current_list = list_manager.get_active_list(chat_id)
        await update.message.reply_text(f"✅ Deleted list `{list_id}`!\nNow using *{current_list.name}*", parse_mode='Markdown')
    else:
        lists = list_manager.get_all_lists(chat_id)
        if len(lists) <= 1:
            await update.message.reply_text("❌ Cannot delete your only list! Create another list first.")
        else:
            await update.message.reply_text(f"❌ List `{list_id}` not found. Use /lists to see your lists.", parse_mode='Markdown')


async def clear_done_items(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Clear purchased items from the shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"Clear purchased items command from user {user.first_name} ({user.id}) in chat {chat.id}")
    count = list_manager.clear_purchased(chat_id)
    shopping_list = list_manager.get_active_list(chat_id)
    
    if count > 0:
        logger.info(f"Cleared {count} purchased items from chat {chat.id}")
        await update.message.reply_text(f"🧹 Cleared {count} bought items from *{shopping_list.name}*!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"No bought items to clear in *{shopping_list.name}*.", parse_mode='Markdown')


async def wipe_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Completely clear the active shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    shopping_list = list_manager.get_active_list(chat_id)
    count = len(shopping_list.items)
    
    logger.info(f"Wipe command from user {user.first_name} ({user.id}) in chat {chat.id}")
    shopping_list.items.clear()
    
    if count > 0:
        logger.info(f"Wiped entire shopping list ({count} items) from chat {chat.id}")
        await update.message.reply_text(f"🧹 Wiped *{shopping_list.name}* clean! ({count} items removed)", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"*{shopping_list.name}* is already empty.", parse_mode='Markdown')