"""
Callback query handler for interactive buttons.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Handle button clicks from inline keyboards."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    user = query.from_user
    chat = query.message.chat
    chat_id = chat.id
    data = query.data
    
    logger.info(f"Callback query '{data}' from user {user.first_name} ({user.id}) in chat {chat.id}")
    
    try:
        if data.startswith("done_"):
            # Mark item as done
            item_index = int(data.split("_")[1])
            if list_manager.mark_purchased(chat_id, item_index):
                shopping_list = list_manager.get_active_list(chat_id)
                new_text = shopping_list.get_display_text()
                new_keyboard = shopping_list.get_interactive_keyboard()
                await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
            else:
                await query.edit_message_text("❌ Item not found. List may have changed.")
        
        elif data.startswith("remove_"):
            # Remove item
            item_index = int(data.split("_")[1])
            if list_manager.remove_item(chat_id, item_index):
                shopping_list = list_manager.get_active_list(chat_id)
                new_text = shopping_list.get_display_text()
                new_keyboard = shopping_list.get_interactive_keyboard()
                await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
            else:
                await query.edit_message_text("❌ Item not found. List may have changed.")
        
        elif data == "clear_bought":
            # Clear purchased items
            count = list_manager.clear_purchased(chat_id)
            shopping_list = list_manager.get_active_list(chat_id)
            
            if count > 0:
                new_text = f"🧹 Cleared {count} bought items!\n\n" + shopping_list.get_display_text()
                new_keyboard = shopping_list.get_interactive_keyboard()
                await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
            else:
                await query.edit_message_text(f"No bought items to clear.\n\n{shopping_list.get_display_text()}", 
                                             parse_mode='Markdown', reply_markup=shopping_list.get_interactive_keyboard())
        
        elif data == "wipe_all":
            # Wipe entire list
            shopping_list = list_manager.get_active_list(chat_id)
            count = len(shopping_list.items)
            shopping_list.items.clear()
            
            new_text = f"🧹 Wiped *{shopping_list.name}* clean! ({count} items removed)\n\n" + shopping_list.get_display_text()
            new_keyboard = shopping_list.get_interactive_keyboard()
            await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
        
        elif data == "refresh":
            # Refresh the current list view
            shopping_list = list_manager.get_active_list(chat_id)
            new_text = shopping_list.get_display_text()
            new_keyboard = shopping_list.get_interactive_keyboard()
            
            # Add timestamp to prevent "message not modified" error
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            new_text += f"\n\n🔄 *Refreshed at {timestamp}*"
            
            await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
        
        elif data == "show_lists":
            # Show lists overview
            lists_text = list_manager.get_lists_summary(chat_id)
            keyboard = list_manager.get_lists_keyboard(chat_id)
            await query.edit_message_text(lists_text, parse_mode='Markdown', reply_markup=keyboard)
        
        elif data.startswith("switch_"):
            # Switch to different list
            list_id = data.split("_", 1)[1]
            if list_manager.set_active_list(chat_id, list_id):
                shopping_list = list_manager.get_active_list(chat_id)
                new_text = f"🛒 Switched to *{shopping_list.name}*!\n\n" + shopping_list.get_display_text()
                new_keyboard = shopping_list.get_interactive_keyboard()
                await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
            else:
                await query.edit_message_text("❌ List not found.")
        
        elif data == "back_to_list":
            # Go back to current list view
            shopping_list = list_manager.get_active_list(chat_id)
            new_text = shopping_list.get_display_text()
            new_keyboard = shopping_list.get_interactive_keyboard()
            await query.edit_message_text(new_text, parse_mode='Markdown', reply_markup=new_keyboard)
        
        elif data == "new_list_prompt":
            # Prompt for new list creation
            await query.edit_message_text(
                "To create a new list, use:\n/new <list name>\n\nExample: /new Costco",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Lists", callback_data="show_lists")
                ]])
            )
        
        elif data == "delete_list_prompt":
            # Prompt for list deletion
            lists = list_manager.get_all_lists(chat_id)
            active_list_id = list_manager.db.get_active_list_id(chat_id)
            
            keyboard = []
            for shopping_list in sorted(lists, key=lambda x: x.list_id):
                if len(lists) > 1:  # Can't delete if only one list
                    button_text = f"🗑️ Delete {shopping_list.name}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"confirm_delete_{shopping_list.list_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Lists", callback_data="show_lists")])
            
            if len(lists) <= 1:
                text = "❌ Cannot delete your only list! Create another list first."
            else:
                text = "⚠️ Select a list to delete:"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith("confirm_delete_"):
            # Confirm list deletion
            list_id = data.split("_", 2)[2]
            if list_manager.delete_list(chat_id, list_id):
                current_list = list_manager.get_active_list(chat_id)
                await query.edit_message_text(
                    f"✅ Deleted list `{list_id}`!\nNow using *{current_list.name}*",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 Show Lists", callback_data="show_lists"),
                        InlineKeyboardButton("🔙 Back to Current List", callback_data="back_to_list")
                    ]])
                )
            else:
                await query.edit_message_text("❌ Could not delete list.")
        
        else:
            await query.edit_message_text("❌ Unknown action.")
    
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")