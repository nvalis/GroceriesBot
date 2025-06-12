import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reduce httpx logging spam
logging.getLogger('httpx').setLevel(logging.WARNING)

@dataclass
class ShoppingItem:
    """Represents a single item in a shopping list."""
    name: str
    quantity: str = "1"
    added_by: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    is_purchased: bool = False
    
    def __str__(self) -> str:
        status = "✅" if self.is_purchased else "📝"
        return f"{status} {self.quantity} {self.name}"

@dataclass
class ShoppingList:
    """Represents a shopping list for a chat."""
    chat_id: int
    name: str = "Shopping List"
    list_id: str = "default"
    items: List[ShoppingItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_item(self, name: str, quantity: str = "1", added_by: str = "") -> None:
        """Add an item to the shopping list."""
        item = ShoppingItem(name=name, quantity=quantity, added_by=added_by)
        self.items.append(item)
    
    def remove_item(self, index: int) -> bool:
        """Remove an item by index. Returns True if successful."""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            return True
        return False
    
    def mark_purchased(self, index: int) -> bool:
        """Mark an item as purchased. Returns True if successful."""
        if 0 <= index < len(self.items):
            self.items[index].is_purchased = True
            return True
        return False
    
    def clear_purchased(self) -> int:
        """Remove all purchased items. Returns count of removed items."""
        initial_count = len(self.items)
        self.items = [item for item in self.items if not item.is_purchased]
        return initial_count - len(self.items)
    
    def get_display_text(self) -> str:
        """Get formatted text for displaying the list."""
        if not self.items:
            return f"📝 *{self.name}* is empty."
        
        text = f"📝 *{self.name}*\n\n"
        for i, item in enumerate(self.items, 1):
            text += f"{i}. {item}\n"
        return text
    
    def get_interactive_keyboard(self) -> InlineKeyboardMarkup:
        """Get inline keyboard for list actions."""
        keyboard = []
        
        # Add buttons for each item
        for i, item in enumerate(self.items):
            if not item.is_purchased:
                keyboard.append([
                    InlineKeyboardButton(f"✅ Done: {item.name[:20]}", callback_data=f"done_{i}"),
                    InlineKeyboardButton(f"🗑️ Remove: {item.name[:15]}", callback_data=f"remove_{i}")
                ])
        
        # Add list management buttons
        if keyboard:  # Only show if there are items
            keyboard.append([
                InlineKeyboardButton("🧹 Clear Bought Items", callback_data="clear_bought"),
                InlineKeyboardButton("🗑️ Wipe All", callback_data="wipe_all")
            ])
        
        # Add list switching buttons
        keyboard.append([
            InlineKeyboardButton("📋 All Lists", callback_data="show_lists"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
        ])
        
        return InlineKeyboardMarkup(keyboard)

class ShoppingListManager:
    """Manages shopping lists for different chats."""
    
    def __init__(self):
        # Structure: {chat_id: {list_id: ShoppingList}}
        self.lists: Dict[int, Dict[str, ShoppingList]] = {}
        # Track active list per chat: {chat_id: list_id}
        self.active_lists: Dict[int, str] = {}
    
    def get_list(self, chat_id: int, list_id: str = "groceries") -> ShoppingList:
        """Get or create a shopping list for a chat."""
        if chat_id not in self.lists:
            self.lists[chat_id] = {}
        
        if list_id not in self.lists[chat_id]:
            list_name = "Groceries" if list_id == "groceries" else list_id.replace("_", " ").title()
            self.lists[chat_id][list_id] = ShoppingList(chat_id=chat_id, name=list_name, list_id=list_id)
        
        return self.lists[chat_id][list_id]
    
    def get_active_list(self, chat_id: int) -> ShoppingList:
        """Get the currently active list for a chat."""
        # If no lists exist, create default groceries list
        if chat_id not in self.lists or not self.lists[chat_id]:
            self.get_list(chat_id, "groceries")
            self.active_lists[chat_id] = "groceries"
        
        active_list_id = self.active_lists.get(chat_id, "groceries")
        return self.get_list(chat_id, active_list_id)
    
    def set_active_list(self, chat_id: int, list_id: str) -> bool:
        """Set the active list for a chat. Returns True if successful."""
        # Create the list if it doesn't exist
        self.get_list(chat_id, list_id)
        self.active_lists[chat_id] = list_id
        return True
    
    def create_list(self, chat_id: int, list_name: str) -> str:
        """Create a new list and return its ID."""
        list_id = list_name.lower().replace(" ", "_")
        # Ensure unique list ID
        counter = 1
        original_id = list_id
        while chat_id in self.lists and list_id in self.lists[chat_id]:
            list_id = f"{original_id}_{counter}"
            counter += 1
        
        self.get_list(chat_id, list_id).name = list_name
        return list_id
    
    def delete_list(self, chat_id: int, list_id: str) -> bool:
        """Delete a list. Returns True if successful."""
        if chat_id in self.lists and list_id in self.lists[chat_id]:
            # Must have at least one list
            if len(self.lists[chat_id]) <= 1:
                return False
            
            del self.lists[chat_id][list_id]
            
            # If this was the active list, switch to first available
            if self.active_lists.get(chat_id) == list_id:
                remaining_lists = list(self.lists[chat_id].keys())
                self.active_lists[chat_id] = remaining_lists[0] if remaining_lists else "groceries"
            
            return True
        return False
    
    def get_all_lists(self, chat_id: int) -> List[ShoppingList]:
        """Get all lists for a chat."""
        if chat_id not in self.lists:
            return []
        return list(self.lists[chat_id].values())
    
    def get_lists_summary(self, chat_id: int) -> str:
        """Get a summary of all lists for a chat."""
        lists = self.get_all_lists(chat_id)
        if not lists:
            return "No lists found."
        
        active_list_id = self.active_lists.get(chat_id, "groceries")
        text = "📋 *Shopping Lists:*\n\n"
        
        for shopping_list in sorted(lists, key=lambda x: x.list_id):
            active_marker = "🔹" if shopping_list.list_id == active_list_id else "▫️"
            item_count = len(shopping_list.items)
            purchased_count = sum(1 for item in shopping_list.items if item.is_purchased)
            pending_count = item_count - purchased_count
            
            text += f"{active_marker} *{shopping_list.name}* (`{shopping_list.list_id}`)\n"
            text += f"   📝 {pending_count} pending, ✅ {purchased_count} done\n\n"
        
        text += f"💡 Active list: *{self.get_active_list(chat_id).name}*"
        return text
    
    def get_lists_keyboard(self, chat_id: int) -> InlineKeyboardMarkup:
        """Get inline keyboard for list switching."""
        lists = self.get_all_lists(chat_id)
        active_list_id = self.active_lists.get(chat_id, "groceries")
        
        keyboard = []
        
        # Add switch buttons for each list
        for shopping_list in sorted(lists, key=lambda x: x.list_id):
            if shopping_list.list_id != active_list_id:  # Don't show current active list
                button_text = f"🛒 {shopping_list.name}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"switch_{shopping_list.list_id}")])
        
        # Add management buttons
        keyboard.append([
            InlineKeyboardButton("➕ New List", callback_data="new_list_prompt"),
            InlineKeyboardButton("🗑️ Delete List", callback_data="delete_list_prompt")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Current List", callback_data="back_to_list")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def add_item(self, chat_id: int, name: str, quantity: str = "1", added_by: str = "") -> None:
        """Add an item to a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        shopping_list.add_item(name, quantity, added_by)
    
    def remove_item(self, chat_id: int, index: int) -> bool:
        """Remove an item from a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        return shopping_list.remove_item(index)
    
    def mark_purchased(self, chat_id: int, index: int) -> bool:
        """Mark an item as purchased in a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        return shopping_list.mark_purchased(index)
    
    def clear_purchased(self, chat_id: int) -> int:
        """Clear all purchased items from a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        return shopping_list.clear_purchased()
    
    def get_list_display(self, chat_id: int) -> str:
        """Get formatted display text for a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        return shopping_list.get_display_text()

# Global shopping list manager
list_manager = ShoppingListManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    chat = update.effective_chat
    logger.info(f"Start command from user {user.first_name} ({user.id}) in chat {chat.id}")
    await update.message.reply_text('Hi! I\'m your grocery list bot. Add me to a group to get started!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def show_current_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current active shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"List command from user {user.first_name} ({user.id}) in chat {chat.id}")
    list_text = list_manager.get_list_display(chat_id)
    await update.message.reply_text(list_text, parse_mode='Markdown')

async def clear_done_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def show_current_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current active shopping list with interactive buttons."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"List command from user {user.first_name} ({user.id}) in chat {chat.id}")
    shopping_list = list_manager.get_active_list(chat_id)
    list_text = shopping_list.get_display_text()
    keyboard = shopping_list.get_interactive_keyboard()
    
    await update.message.reply_text(list_text, parse_mode='Markdown', reply_markup=keyboard)

async def show_all_lists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all shopping lists for the chat with interactive buttons."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"Lists command from user {user.first_name} ({user.id}) in chat {chat.id}")
    lists_text = list_manager.get_lists_summary(chat_id)
    keyboard = list_manager.get_lists_keyboard(chat_id)
    
    await update.message.reply_text(lists_text, parse_mode='Markdown', reply_markup=keyboard)

async def create_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def switch_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def wipe_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            active_list_id = list_manager.active_lists.get(chat_id, "groceries")
            
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

def main() -> None:
    """Start the bot."""
    # Create the Application
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_item))
    application.add_handler(CommandHandler("list", show_current_list))
    application.add_handler(CommandHandler("remove", remove_item))
    application.add_handler(CommandHandler("done", mark_done))
    application.add_handler(CommandHandler("clear", clear_done_items))
    
    # Multi-list handlers
    application.add_handler(CommandHandler("lists", show_all_lists))
    application.add_handler(CommandHandler("new", create_list))
    application.add_handler(CommandHandler("go", switch_list))
    application.add_handler(CommandHandler("delete", delete_list))
    application.add_handler(CommandHandler("wipe", wipe_list))
    
    # Callback query handler for interactive buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
