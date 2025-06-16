"""
Handler for custom reply keyboard interactions.
"""

import logging
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# User context tracking for conversational flows
user_contexts = {}

class UserContext:
    """Track user's current conversation state."""
    def __init__(self):
        self.awaiting_item = False
        self.awaiting_list_name = False
        self.awaiting_list_switch = False
        self.awaiting_list_deletion = False
        self.awaiting_item_removal = False
        self.awaiting_item_done = False
        self.in_shopping_mode = False
        self.in_list_mode = False
        self.in_item_mode = False
        self.return_to_shopping = False
        self.return_to_mode = None  # Track which mode to return to
    
    def reset(self):
        """Reset all context flags."""
        self.awaiting_item = False
        self.awaiting_list_name = False
        self.awaiting_list_switch = False
        self.awaiting_list_deletion = False
        self.awaiting_item_removal = False
        self.awaiting_item_done = False
        self.in_shopping_mode = False
        self.in_list_mode = False
        self.in_item_mode = False
        self.return_to_shopping = False
        self.return_to_mode = None

def get_user_context(user_id: int) -> UserContext:
    """Get or create user context."""
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext()
    return user_contexts[user_id]


def get_mode_keyboard(user_context: UserContext, active_list):
    """Get the appropriate keyboard based on current mode."""
    if user_context.in_list_mode:
        return active_list.get_list_management_keyboard()
    elif user_context.in_item_mode:
        return active_list.get_item_management_keyboard()
    else:
        return active_list.get_reply_keyboard()


async def handle_reply_keyboard_text(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Handle text messages from reply keyboard buttons and regular text input."""
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    
    logger.info(f"Reply keyboard text from user {user.first_name} ({user.id}) in chat {chat.id}: {text}")
    
    # Get user context for conversational flows
    user_context = get_user_context(user.id)
    logger.info(f"User context flags: awaiting_list_deletion={user_context.awaiting_list_deletion}, in_list_mode={user_context.in_list_mode}, in_item_mode={user_context.in_item_mode}")
    
    # Handle mode navigation first
    if text == "← Back to Main Menu":
        user_context.reset()  # Reset all modes and return to main menu
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Handle main menu mode selection
    elif text == "📋 List Management":
        user_context.reset()
        user_context.in_list_mode = True
        await enter_list_mode(update, context, list_manager)
    elif text.startswith("✏️ Edit "):
        user_context.reset()
        user_context.in_item_mode = True
        await enter_item_mode(update, context, list_manager)
    elif text == "🛒 Shopping Mode":
        user_context.reset()
        await shopping_mode_action(update, context, list_manager)
    elif text == "ℹ️ Help":
        user_context.reset()
        await show_help_with_keyboard(update, context, list_manager)
    
    # Handle conversational flow responses first (higher priority than mode buttons)
    elif user_context.awaiting_item:
        user_context.reset()
        await add_item_from_text(update, context, list_manager, text)
    elif user_context.awaiting_list_name:
        user_context.reset()
        await create_list_from_text(update, context, list_manager, text)
    elif user_context.awaiting_list_switch:
        user_context.reset()
        await switch_to_list(update, context, list_manager, text)
    elif user_context.awaiting_list_deletion:
        logger.info(f"User context awaiting_list_deletion=True, processing text: {text}")
        user_context.reset()
        await delete_list_from_text(update, context, list_manager, text)
    elif user_context.awaiting_item_done:
        user_context.reset()
        await handle_mark_done_action(update, context, list_manager, text)
    elif user_context.awaiting_item_removal:
        user_context.reset()
        await handle_remove_item_action(update, context, list_manager, text)
    
    # Handle list management mode buttons
    elif user_context.in_list_mode:
        await handle_list_mode_action(update, context, list_manager, text)
    
    # Handle item management mode buttons  
    elif user_context.in_item_mode:
        await handle_item_mode_action(update, context, list_manager, text)
    elif user_context.in_shopping_mode:
        await handle_shopping_mode_action(update, context, list_manager, text)
    
    
    # Handle regular text input - assume it's adding an item
    else:
        await add_item_from_text(update, context, list_manager, text)


async def show_current_list_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show the current shopping list with appropriate keyboard based on current mode."""
    chat = update.effective_chat
    user = update.effective_user
    active_list = list_manager.get_active_list(chat.id)
    user_context = get_user_context(user.id)
    
    # Send list with inline keyboard for item actions
    await update.message.reply_text(
        active_list.get_display_text(),
        parse_mode='Markdown',
        reply_markup=active_list.get_interactive_keyboard()
    )
    
    # Send appropriate mode keyboard based on current context
    if user_context.in_list_mode:
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_list_management_keyboard()
        )
    elif user_context.in_item_mode:
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_item_management_keyboard()
        )
    else:
        # Default to main menu
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_reply_keyboard()
        )


async def add_item_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Prompt user to add an item."""
    user = update.effective_user
    user_context = get_user_context(user.id)
    user_context.awaiting_item = True
    
    # Get current list for keyboard
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    await update.message.reply_text(
        "➕ *Add Item*",
        parse_mode='Markdown',
        reply_markup=ForceReply(input_field_placeholder="Type item name and quantity...")
    )


async def add_item_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Add item from regular text input."""
    chat = update.effective_chat
    user = update.effective_user
    
    # Parse quantity and item name
    parts = text.strip().split(' ', 1)
    if len(parts) == 1:
        quantity = "1"
        item_name = parts[0]
    else:
        # Check if first part is a number
        try:
            int(parts[0])
            quantity = parts[0]
            item_name = parts[1] if len(parts) > 1 else parts[0]
        except ValueError:
            quantity = "1"
            item_name = text
    
    # Add item using list manager
    list_manager.add_item(chat.id, item_name, quantity, user.first_name or "Unknown")
    
    # Get updated list for display
    active_list = list_manager.get_active_list(chat.id)
    logger.info(f"Added item '{item_name}' (qty: {quantity}) to list {active_list.list_id} in chat {chat.id}")
    
    # Check if we should return to a specific mode
    user_context = get_user_context(user.id)
    if user_context.awaiting_item and hasattr(user_context, 'return_to_shopping') and user_context.return_to_shopping:
        # Return to shopping mode after adding item
        user_context.in_shopping_mode = True
        user_context.return_to_shopping = False
        
        pending_items = active_list.items
        await update.message.reply_text(
            f"✅ Added: {quantity} {item_name}",
            parse_mode='Markdown'
        )
        await create_shopping_keyboard(update, list_manager, active_list, pending_items)
    elif user_context.return_to_mode == "item":
        # Return to item management mode
        user_context.return_to_mode = None
        user_context.in_item_mode = True
        await update.message.reply_text(
            f"✅ Added: {quantity} {item_name}",
            parse_mode='Markdown',
            reply_markup=active_list.get_item_management_keyboard()
        )
    elif user_context.return_to_mode == "list":
        # Return to list management mode (unusual case, but handle it)
        user_context.return_to_mode = None
        user_context.in_list_mode = True
        await update.message.reply_text(
            f"✅ Added: {quantity} {item_name}",
            parse_mode='Markdown',
            reply_markup=active_list.get_list_management_keyboard()
        )
    else:
        # Normal add item flow - return to Edit Current List mode
        await update.message.reply_text(
            f"✅ Added: {quantity} {item_name}\n\n{active_list.get_display_text()}",
            parse_mode='Markdown',
            reply_markup=active_list.get_interactive_keyboard()
        )
        
        # Return to Edit Current List mode instead of main menu
        user_context.reset()
        user_context.in_item_mode = True
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_item_management_keyboard()
        )


async def create_list_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Prompt user to create a new list."""
    user = update.effective_user
    user_context = get_user_context(user.id)
    user_context.awaiting_list_name = True
    
    # Get current list for keyboard
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    await update.message.reply_text(
        "📝 *Create New List*",
        parse_mode='Markdown',
        reply_markup=ForceReply(input_field_placeholder="Type list name...")
    )

async def create_list_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Create a new list from text input."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Clean up the list name
    list_name = text.strip()
    list_id = list_name.lower().replace(' ', '-').replace('_', '-')
    
    # Check if list already exists
    existing_lists = list_manager.get_all_lists(chat.id)
    if any(lst.list_id == list_name.lower().replace(' ', '_') for lst in existing_lists):
        active_list = list_manager.get_active_list(chat.id)
        user_context = get_user_context(user.id)
        
        # Return to appropriate mode
        if user_context.return_to_mode == "list":
            user_context.return_to_mode = None
            user_context.in_list_mode = True
            await update.message.reply_text(
                f"❌ List with similar name already exists!\n"
                f"Choose a different name or use the 🔄 button to switch lists.",
                parse_mode='Markdown',
                reply_markup=active_list.get_list_management_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ List with similar name already exists!\n"
                f"Choose a different name or use the 🔄 button to switch lists.",
                parse_mode='Markdown',
                reply_markup=active_list.get_reply_keyboard()
            )
        return
    
    # Create the new list
    list_id = list_manager.create_list(chat.id, list_name)
    new_list = list_manager.get_list(chat.id, list_id)
    list_manager.set_active_list(chat.id, list_id)
    
    logger.info(f"Created list '{list_id}' ({list_name}) in chat {chat.id}")
    
    await update.message.reply_text(
        f"✅ Created and switched to list: *{list_name}* (`{list_id}`)\n\n"
        f"{new_list.get_display_text()}",
        parse_mode='Markdown',
        reply_markup=new_list.get_interactive_keyboard()
    )
    
    # Return to appropriate mode
    user_context = get_user_context(user.id)
    if user_context.return_to_mode == "list":
        user_context.return_to_mode = None
        user_context.in_list_mode = True
        await update.message.reply_text(
            "📋 *List Management Mode*",
            parse_mode='Markdown',
            reply_markup=new_list.get_list_management_keyboard()
        )
    else:
        # Send reply keyboard separately to ensure it stays
        await update.message.reply_text(
            "🔽",
            reply_markup=new_list.get_reply_keyboard()
        )


async def switch_lists_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show list switching options using custom keyboard."""
    user = update.effective_user
    chat = update.effective_chat
    lists = list_manager.get_all_lists(chat.id)
    
    if len(lists) <= 1:
        await update.message.reply_text("You only have one list. Create more lists with the 📝 button!")
        return
    
    # Set context for list switching selection
    user_context = get_user_context(user.id)
    user_context.awaiting_list_switch = True
    
    # Create custom keyboard with list names
    keyboard = []
    active_list = list_manager.get_active_list(chat.id)
    
    for shopping_list in lists:
        item_count = len(shopping_list.items)
        status = "📍" if shopping_list.list_id == active_list.list_id else "🔄"
        button_text = f"{status} {shopping_list.name} ({item_count})"
        
        # Limit button text length for better display
        if len(button_text) > 35:
            button_text = f"{status} {shopping_list.name[:28]}... ({item_count})"
        
        keyboard.append([KeyboardButton(button_text)])
    
    # Add cancel button
    keyboard.append([KeyboardButton("❌ Cancel Switch")])
    
    custom_keyboard = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Tap a list to switch to it..."
    )
    
    text = "🔄 *Switch Lists*\n\n"
    
    for shopping_list in lists:
        status = "📍 (current)" if shopping_list.list_id == active_list.list_id else ""
        item_count = len(shopping_list.items)
        text += f"• *{shopping_list.name}* - {item_count} items {status}\n"
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=custom_keyboard
    )

async def switch_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle list switching from custom keyboard button press."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Handle cancel option
    if text == "❌ Cancel Switch":
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Parse the button text to extract list name
    # Button format: "🔄 List Name (count)" or "📍 List Name (count)"
    if text.startswith("🔄 ") or text.startswith("📍 "):
        # Extract list name from button text
        button_text = text[2:].strip()  # Remove emoji and space
        
        # Remove the count part in parentheses at the end
        if "(" in button_text and button_text.endswith(")"):
            list_name = button_text.rsplit("(", 1)[0].strip()
            # Handle truncated names (remove "...")
            if list_name.endswith("..."):
                list_name = list_name[:-3].strip()
        else:
            list_name = button_text
    else:
        # Fallback: treat the entire text as a list name
        list_name = text.strip()
    
    # Get all lists for this chat
    existing_lists = list_manager.get_all_lists(chat.id)
    
    # Find the target list by name (try exact match first, then partial)
    target_list = None
    
    # Try exact name match first
    for lst in existing_lists:
        if lst.name.lower() == list_name.lower():
            target_list = lst
            break
    
    # If no exact match, try partial match
    if not target_list:
        for lst in existing_lists:
            if list_name.lower() in lst.name.lower():
                target_list = lst
                break
    
    if not target_list:
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            f"❌ Could not find list matching '{list_name}'.",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Check if already on this list
    current_active = list_manager.get_active_list(chat.id)
    if target_list.list_id == current_active.list_id:
        await update.message.reply_text(
            f"📍 You're already using *{target_list.name}*!",
            parse_mode='Markdown',
            reply_markup=target_list.get_reply_keyboard()
        )
        return
    
    # Switch to the list
    list_manager.set_active_list(chat.id, target_list.list_id)
    logger.info(f"User {user.first_name} switched to list '{target_list.list_id}' in chat {chat.id}")
    
    # Get updated user context and return to appropriate mode
    user_context = get_user_context(user.id)
    
    await update.message.reply_text(
        f"✅ Switched to: *{target_list.name}*\n\n"
        f"{target_list.get_display_text()}",
        parse_mode='Markdown',
        reply_markup=target_list.get_interactive_keyboard()
    )
    
    # Return to appropriate mode
    if user_context.return_to_mode == "list":
        user_context.return_to_mode = None
        user_context.in_list_mode = True
        await update.message.reply_text(
            "📋 *List Management Mode*",
            parse_mode='Markdown',
            reply_markup=target_list.get_list_management_keyboard()
        )
    else:
        # Send reply keyboard separately to ensure it stays
        await update.message.reply_text(
            "🔽",
            reply_markup=target_list.get_reply_keyboard()
        )


async def show_all_lists_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show all lists with their contents."""
    chat = update.effective_chat
    user = update.effective_user
    lists = list_manager.get_all_lists(chat.id)
    user_context = get_user_context(user.id)
    
    if not lists:
        await update.message.reply_text("No lists found. Create one with `/new <name>`")
        return
    
    text = "📊 *All Your Lists:*\n\n"
    active_list = list_manager.get_active_list(chat.id)
    
    for shopping_list in lists:
        status = "📍" if shopping_list.list_id == active_list.list_id else "📋"
        item_count = len(shopping_list.items)
        
        text += f"{status} *{shopping_list.name}* (`{shopping_list.list_id}`)\n"
        text += f"   • {item_count} items\n\n"
    
    # Return to appropriate mode
    if user_context.in_list_mode:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=active_list.get_list_management_keyboard())
    elif user_context.in_item_mode:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=active_list.get_item_management_keyboard())
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=active_list.get_reply_keyboard())


async def delete_list_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show list deletion options using custom keyboard."""
    user = update.effective_user
    chat = update.effective_chat
    lists = list_manager.get_all_lists(chat.id)
    
    if len(lists) <= 1:
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            "❌ Cannot delete your only list! Create another list first with the 📝 button.",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Set context for list deletion selection
    user_context = get_user_context(user.id)
    user_context.awaiting_list_deletion = True
    
    # Create custom keyboard with list names
    keyboard = []
    active_list = list_manager.get_active_list(chat.id)
    
    for shopping_list in lists:
        item_count = len(shopping_list.items)
        status = "📍" if shopping_list.list_id == active_list.list_id else "🗑️"
        button_text = f"{status} {shopping_list.name} ({item_count})"
        
        # Limit button text length for better display
        if len(button_text) > 35:
            button_text = f"{status} {shopping_list.name[:28]}... ({item_count})"
        
        keyboard.append([KeyboardButton(button_text)])
    
    # Add cancel button
    keyboard.append([KeyboardButton("❌ Cancel Delete")])
    
    custom_keyboard = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Tap a list to delete it..."
    )
    
    text = "🗑️ *Delete List*\n\n"
    text += "⚠️ This action cannot be undone!\n\n"
    
    for shopping_list in lists:
        status = "📍 (current)" if shopping_list.list_id == active_list.list_id else ""
        item_count = len(shopping_list.items)
        text += f"• *{shopping_list.name}* - {item_count} items {status}\n"
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=custom_keyboard
    )


async def delete_list_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle list deletion from custom keyboard button press."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Handle cancel option
    if text == "❌ Cancel Delete":
        active_list = list_manager.get_active_list(chat.id)
        user_context = get_user_context(user.id)
        
        # Return to appropriate mode
        if user_context.return_to_mode == "list":
            user_context.return_to_mode = None
            user_context.in_list_mode = True
            await update.message.reply_text(
                ".",
                reply_markup=active_list.get_list_management_keyboard()
            )
        else:
            await update.message.reply_text(
                ".",
                reply_markup=active_list.get_reply_keyboard()
            )
        return
    
    # Parse the button text to extract list name
    # Button format: "🗑️ List Name (count)" or "📍 List Name (count)"
    if text.startswith("🗑️ ") or text.startswith("📍 "):
        # Extract list name from button text
        button_text = text[2:].strip()  # Remove emoji and space
        
        # Remove the count part in parentheses at the end
        if "(" in button_text and button_text.endswith(")"):
            list_name = button_text.rsplit("(", 1)[0].strip()
            # Handle truncated names (remove "...")
            if list_name.endswith("..."):
                list_name = list_name[:-3].strip()
        else:
            list_name = button_text
    else:
        # Fallback: treat the entire text as a list name
        list_name = text.strip()
    
    logger.info(f"Parsed list name '{list_name}' from button text '{text}'")
    
    # Get all lists for this chat
    existing_lists = list_manager.get_all_lists(chat.id)
    
    # Can't delete if only one list
    if len(existing_lists) <= 1:
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            "❌ Cannot delete your only list! Create another list first with the 📝 button.",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Find the target list by name (try exact match first, then partial)
    target_list = None
    
    # Try exact name match first
    logger.info(f"Looking for exact match of '{list_name}' among {[lst.name for lst in existing_lists]}")
    for lst in existing_lists:
        if lst.name.lower() == list_name.lower():
            target_list = lst
            logger.info(f"Found exact match: {lst.name}")
            break
    
    # If no exact match, try partial match
    if not target_list:
        logger.info(f"No exact match found, trying partial match")
        for lst in existing_lists:
            if list_name.lower() in lst.name.lower():
                target_list = lst
                logger.info(f"Found partial match: {lst.name}")
                break
    
    if not target_list:
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            f"❌ Could not find list matching '{list_name}'.",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Delete the list
    logger.info(f"Attempting to delete list '{target_list.name}' (ID: {target_list.list_id})")
    if list_manager.delete_list(chat.id, target_list.list_id):
        current_list = list_manager.get_active_list(chat.id)
        logger.info(f"User {user.first_name} successfully deleted list '{target_list.list_id}' in chat {chat.id}")
        
        user_context = get_user_context(user.id)
        
        # Return to appropriate mode
        if user_context.return_to_mode == "list":
            user_context.return_to_mode = None
            user_context.in_list_mode = True
            await update.message.reply_text(
                f"✅ Deleted list: *{target_list.name}*\n"
                f"Now using: *{current_list.name}*",
                parse_mode='Markdown',
                reply_markup=current_list.get_list_management_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✅ Deleted list: *{target_list.name}*\n"
                f"Now using: *{current_list.name}*",
                parse_mode='Markdown',
                reply_markup=current_list.get_reply_keyboard()
            )
    else:
        logger.error(f"Failed to delete list '{target_list.name}' (ID: {target_list.list_id})")
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            f"❌ Could not delete list '{target_list.name}'. Please try again.",
            reply_markup=active_list.get_reply_keyboard()
        )


async def shopping_mode_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Enter shopping mode with custom keyboard for each item."""
    user = update.effective_user
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    # Check if list has items (since we now remove completed items immediately)
    if not active_list.items:
        await update.message.reply_text(
            f"🛒 *{active_list.name}* is empty!\n"
            f"Add some items first with the ➕ button.",
            parse_mode='Markdown',
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Check if we have too many items for efficient display
    if len(active_list.items) > 100:
        await update.message.reply_text(
            f"🛒 Too many items ({len(active_list.items)}) for shopping mode!\n"
            f"Use the interactive list instead or remove some items.",
            parse_mode='Markdown',
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Set shopping mode context
    user_context = get_user_context(user.id)
    user_context.in_shopping_mode = True
    
    # Create keyboard with shopping mode layout
    await create_shopping_keyboard(update, list_manager, active_list, active_list.items)


async def create_shopping_keyboard(update: Update, list_manager, active_list, pending_items) -> None:
    """Create and send the shopping mode keyboard."""
    keyboard = []
    
    # Add item buttons (3 per row for optimal display)
    buttons_per_row = 3
    current_row = []
    
    for i, item in enumerate(pending_items):
        # Create button text with checkmark emoji
        button_text = f"✅ {item.quantity} {item.name}"
        
        # Truncate long item names to fit button (shorter for 3 columns)
        if len(button_text) > 20:
            truncated_name = item.name[:12] + "..."
            button_text = f"✅ {item.quantity} {truncated_name}"
        
        current_row.append(KeyboardButton(button_text))
        
        # Add row when we reach the limit or it's the last item
        if len(current_row) == buttons_per_row or i == len(pending_items) - 1:
            keyboard.append(current_row)
            current_row = []
    
    # Add control buttons
    keyboard.append([KeyboardButton("🔍 Show List"), KeyboardButton("❌ Exit Shopping Mode")])
    
    shopping_keyboard = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Tap items to mark as done..."
    )
    
    text = f"🛒 *Shopping Mode: {active_list.name}*\n\n"
    text += f"📝 {len(pending_items)} items to buy"
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=shopping_keyboard
    )


async def handle_shopping_mode_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle actions in shopping mode."""
    user = update.effective_user
    chat = update.effective_chat
    user_context = get_user_context(user.id)
    
    # Handle exit shopping mode
    if text == "❌ Exit Shopping Mode":
        user_context.in_shopping_mode = False
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_reply_keyboard()
        )
        return
    
    # Handle show list
    if text == "🔍 Show List":
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            active_list.get_display_text(),
            parse_mode='Markdown'
        )
        # Stay in shopping mode - don't change keyboard
        return
    
    
    # Handle item completion (button format: "✅ quantity itemname")
    if text.startswith("✅ "):
        # Parse the button text to find the item
        button_text = text[2:].strip()  # Remove "✅ "
        
        # Extract quantity and item name
        parts = button_text.split(' ', 1)
        if len(parts) >= 2:
            quantity = parts[0]
            item_name = parts[1]
            
            # Handle truncated names (remove "...")
            if item_name.endswith("..."):
                item_name = item_name[:-3].strip()
        else:
            # Fallback if format is unexpected
            quantity = "1"
            item_name = button_text
        
        # Find and mark the item as done
        active_list = list_manager.get_active_list(chat.id)
        item_found = False
        
        for i, item in enumerate(active_list.items):
            if (item.quantity == quantity and 
                (item.name == item_name or item.name.startswith(item_name))):
                
                list_manager.remove_item(chat.id, i)
                item_found = True
                logger.info(f"User {user.first_name} removed item '{item.name}' as done in shopping mode")
                break
        
        if item_found:
            # Refresh the shopping mode keyboard
            updated_list = list_manager.get_active_list(chat.id)
            
            if not updated_list.items:
                # All items done - exit shopping mode
                user_context.in_shopping_mode = False
                await update.message.reply_text(
                    f"🎉 *Shopping Complete!*\n\n"
                    f"✅ All items done for *{updated_list.name}*!\n"
                    f"Great job shopping! 🛒",
                    parse_mode='Markdown',
                    reply_markup=updated_list.get_reply_keyboard()
                )
            else:
                # Update the shopping keyboard with remaining items
                await create_shopping_keyboard(update, list_manager, updated_list, updated_list.items)
        else:
            await update.message.reply_text(
                f"❌ Could not find item matching '{item_name}' with quantity '{quantity}'."
            )
        return
    
    # Handle any other text as potential item addition (fallback)
    await add_item_from_text(update, context, list_manager, text)


async def enter_list_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Enter list management mode with all lists overview."""
    chat = update.effective_chat
    lists = list_manager.get_all_lists(chat.id)
    
    if not lists:
        await update.message.reply_text("No lists found. Create one with the 📝 button!")
        return
    
    text = ""
    active_list = list_manager.get_active_list(chat.id)
    
    for shopping_list in lists:
        status = "📍" if shopping_list.list_id == active_list.list_id else "📋"
        item_count = len(shopping_list.items)
        
        text += f"{status} *{shopping_list.name}* (`{shopping_list.list_id}`)\n"
        text += f"   • {item_count} items\n\n"
    
    await update.message.reply_text(
        text, 
        parse_mode='Markdown', 
        reply_markup=active_list.get_list_management_keyboard()
    )


async def enter_item_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Enter item management mode with current list display."""
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    # Send list with inline keyboard for item actions
    await update.message.reply_text(
        active_list.get_display_text(),
        parse_mode='Markdown',
        reply_markup=active_list.get_interactive_keyboard()
    )
    
    # Send edit mode keyboard
    await update.message.reply_text(
        ".",
        reply_markup=active_list.get_item_management_keyboard()
    )


async def handle_list_mode_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle actions in list management mode."""
    user_context = get_user_context(update.effective_user.id)
    
    if text == "📋 Show Current List":
        await show_current_list_action(update, context, list_manager)
    elif text == "📝 Create New List":
        user_context.return_to_mode = "list"
        await create_list_prompt(update, context, list_manager)
    elif text == "🔄 Switch Lists":
        user_context.return_to_mode = "list"
        await switch_lists_action(update, context, list_manager)
    elif text == "🗑️ Delete List":
        user_context.return_to_mode = "list"
        await delete_list_action(update, context, list_manager)


async def handle_item_mode_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle actions in item management mode."""
    user_context = get_user_context(update.effective_user.id)
    
    if text == "➕ Add Item":
        user_context.return_to_mode = "item"
        await add_item_prompt(update, context, list_manager)
    elif text == "🔍 Show List":
        await show_current_list_in_item_mode(update, context, list_manager)
    elif text == "🗑️ Remove Item":
        await enter_remove_item_mode(update, context, list_manager)
    elif text == "🗑️ Wipe All":
        await wipe_all_items(update, context, list_manager)


async def enter_mark_done_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Enter mark done mode with item buttons."""
    user = update.effective_user
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    # Get pending items (not purchased)
    if not active_list.items:
        await update.message.reply_text(
            f"✅ *{active_list.name}* is empty!",
            parse_mode='Markdown',
            reply_markup=active_list.get_item_management_keyboard()
        )
        return
    
    # Set context for mark done
    user_context = get_user_context(user.id)
    user_context.awaiting_item_done = True
    
    # Create keyboard with item buttons
    keyboard = []
    buttons_per_row = 1  # One item per row for clarity
    
    for item in active_list.items:
        button_text = f"✅ {item.quantity} {item.name}"
        if len(button_text) > 35:
            button_text = f"✅ {item.quantity} {item.name[:25]}..."
        keyboard.append([KeyboardButton(button_text)])
    
    keyboard.append([KeyboardButton("❌ Cancel Mark Done")])
    
    mark_done_keyboard = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Tap an item to mark as done..."
    )
    
    text = f"✅ *Mark Items Done*"
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=mark_done_keyboard
    )


async def enter_remove_item_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Enter remove item mode with item buttons."""
    user = update.effective_user
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    if not active_list.items:
        await update.message.reply_text(
            f"📝 *{active_list.name}* is empty!",
            parse_mode='Markdown',
            reply_markup=active_list.get_item_management_keyboard()
        )
        return
    
    # Set context for item removal
    user_context = get_user_context(user.id)
    user_context.awaiting_item_removal = True
    
    # Create keyboard with all item buttons
    keyboard = []
    
    for item in active_list.items:
        button_text = f"🗑️ {item.quantity} {item.name}"
        if len(button_text) > 35:
            button_text = f"🗑️ {item.quantity} {item.name[:25]}..."
        keyboard.append([KeyboardButton(button_text)])
    
    keyboard.append([KeyboardButton("❌ Cancel Remove")])
    
    remove_keyboard = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Tap an item to remove it..."
    )
    
    text = f"🗑️ *Remove Items*\n\n"
    text += f"⚠️ This action cannot be undone!"
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=remove_keyboard
    )



async def wipe_all_items(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Wipe all items from the current list."""
    chat = update.effective_chat
    user = update.effective_user
    
    active_list = list_manager.get_active_list(chat.id)
    count = len(active_list.items)
    
    if count > 0:
        # Clear all items
        active_list.items = []
        list_manager.save_list(active_list)
        
        await update.message.reply_text(
            f"🗑️ Wiped all {count} items from *{active_list.name}*!",
            parse_mode='Markdown',
            reply_markup=active_list.get_item_management_keyboard()
        )
    else:
        await update.message.reply_text(
            f"*{active_list.name}* is already empty.",
            parse_mode='Markdown',
            reply_markup=active_list.get_item_management_keyboard()
        )


async def show_current_list_in_item_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show the current list contents in item management mode."""
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    await update.message.reply_text(
        active_list.get_display_text(),
        parse_mode='Markdown',
        reply_markup=active_list.get_item_management_keyboard()
    )


async def handle_mark_done_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle marking items as done from custom keyboard."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Handle cancel
    if text == "❌ Cancel Mark Done":
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_item_management_keyboard()
        )
        return
    
    # Parse button text (format: "✅ quantity itemname")
    if text.startswith("✅ "):
        button_text = text[2:].strip()
        
        # Extract quantity and item name
        parts = button_text.split(' ', 1)
        if len(parts) >= 2:
            quantity = parts[0]
            item_name = parts[1]
            if item_name.endswith("..."):
                item_name = item_name[:-3].strip()
        else:
            quantity = "1"
            item_name = button_text
        
        # Find and mark the item as done
        active_list = list_manager.get_active_list(chat.id)
        item_found = False
        
        for i, item in enumerate(active_list.items):
            if (item.quantity == quantity and 
                (item.name == item_name or item.name.startswith(item_name))):
                
                list_manager.remove_item(chat.id, i)
                item_found = True
                logger.info(f"User {user.first_name} removed item '{item.name}' as done")
                break
        
        if item_found:
            await update.message.reply_text(
                f"✅ Done: {quantity} {item_name}",
                reply_markup=active_list.get_item_management_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Could not find item matching '{item_name}' with quantity '{quantity}'.",
                reply_markup=active_list.get_item_management_keyboard()
            )


async def handle_remove_item_action(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager, text: str) -> None:
    """Handle removing items from custom keyboard."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Handle cancel
    if text == "❌ Cancel Remove":
        active_list = list_manager.get_active_list(chat.id)
        await update.message.reply_text(
            ".",
            reply_markup=active_list.get_item_management_keyboard()
        )
        return
    
    # Parse button text (format: "🗑️ status quantity itemname")
    if text.startswith("🗑️ "):
        button_text = text[2:].strip()
        
        # Remove status emoji if present
        if button_text.startswith("✅ ") or button_text.startswith("📝 "):
            button_text = button_text[2:].strip()
        
        # Extract quantity and item name
        parts = button_text.split(' ', 1)
        if len(parts) >= 2:
            quantity = parts[0]
            item_name = parts[1]
            if item_name.endswith("..."):
                item_name = item_name[:-3].strip()
        else:
            quantity = "1"
            item_name = button_text
        
        # Find and remove the item
        active_list = list_manager.get_active_list(chat.id)
        item_found = False
        
        for i, item in enumerate(active_list.items):
            if (item.quantity == quantity and 
                (item.name == item_name or item.name.startswith(item_name))):
                
                list_manager.remove_item(chat.id, i)
                item_found = True
                logger.info(f"User {user.first_name} removed item '{item.name}'")
                break
        
        if item_found:
            await update.message.reply_text(
                f"🗑️ Removed: {quantity} {item_name}",
                reply_markup=active_list.get_item_management_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Could not find item matching '{item_name}' with quantity '{quantity}'.",
                reply_markup=active_list.get_item_management_keyboard()
            )


async def show_help_with_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show help message and ensure reply keyboard is present."""
    chat = update.effective_chat
    active_list = list_manager.get_active_list(chat.id)
    
    help_text = f"""
🛒 *Grocery Bot Help*

*Current List:* {active_list.name} (`{active_list.list_id}`)

*Main Menu Modes:*
📋 List Management - Create, switch, and delete lists
✏️ Edit Current List - Add, remove, and mark items as done
🛒 Shopping Mode - Easy tap-to-complete interface for shopping

*📋 List Management Mode:*
• Show Current List - Display your active list
• Create New List - Make a new shopping list
• Switch Lists - Change between your lists
• Delete List - Remove lists permanently
• All Lists - Overview of all your lists

*✏️ Edit Current List Mode:*
• Add Item - Add new items to your list
• Show List - Display current list items
• Remove Item - Remove items with buttons
• Wipe All - Remove all items from the list

*🛒 Shopping Mode:*
• Tap any item to remove it from the list
• Add items while shopping
• Auto-exits when all items are done

*Commands:*
/add - Add item to current list
/list - Show current list  
/done - Mark item as bought
/remove - Remove item
/new - Create new list
/go - Switch to different list

*Adding Items:*
Just type the item name! Examples:
• `milk` (adds 1 milk)
• `2 bread` (adds 2 bread)
• `3 apples` (adds 3 apples)
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=active_list.get_reply_keyboard()
    )