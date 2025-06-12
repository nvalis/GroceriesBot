import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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

class ShoppingListManager:
    """Manages shopping lists for different chats."""
    
    def __init__(self):
        self.lists: Dict[int, ShoppingList] = {}
    
    def get_list(self, chat_id: int) -> ShoppingList:
        """Get or create a shopping list for a chat."""
        if chat_id not in self.lists:
            self.lists[chat_id] = ShoppingList(chat_id=chat_id)
        return self.lists[chat_id]
    
    def add_item(self, chat_id: int, name: str, quantity: str = "1", added_by: str = "") -> None:
        """Add an item to a chat's shopping list."""
        shopping_list = self.get_list(chat_id)
        shopping_list.add_item(name, quantity, added_by)
    
    def remove_item(self, chat_id: int, index: int) -> bool:
        """Remove an item from a chat's shopping list."""
        shopping_list = self.get_list(chat_id)
        return shopping_list.remove_item(index)
    
    def mark_purchased(self, chat_id: int, index: int) -> bool:
        """Mark an item as purchased in a chat's shopping list."""
        shopping_list = self.get_list(chat_id)
        return shopping_list.mark_purchased(index)
    
    def clear_purchased(self, chat_id: int) -> int:
        """Clear all purchased items from a chat's shopping list."""
        shopping_list = self.get_list(chat_id)
        return shopping_list.clear_purchased()
    
    def get_list_display(self, chat_id: int) -> str:
        """Get formatted display text for a chat's shopping list."""
        shopping_list = self.get_list(chat_id)
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
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/add <item> [quantity] - Add item to shopping list
/list - Show current shopping list
/remove <number> - Remove item by number
/done <number> - Mark item as purchased
/clear - Clear purchased items
/clearall - Clear entire shopping list
    """
    await update.message.reply_text(help_text)

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

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the current shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"List command from user {user.first_name} ({user.id}) in chat {chat.id}")
    list_text = list_manager.get_list_display(chat_id)
    await update.message.reply_text(list_text, parse_mode='Markdown')

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

async def clear_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all purchased items from the shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    
    logger.info(f"Clear purchased items command from user {user.first_name} ({user.id}) in chat {chat.id}")
    count = list_manager.clear_purchased(chat_id)
    
    if count > 0:
        logger.info(f"Cleared {count} purchased items from chat {chat.id}")
        await update.message.reply_text(f"✅ Cleared {count} purchased item(s) from the shopping list!")
    else:
        await update.message.reply_text("No purchased items to clear.")

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the entire shopping list."""
    user = update.effective_user
    chat = update.effective_chat
    chat_id = update.effective_chat.id
    shopping_list = list_manager.get_list(chat_id)
    count = len(shopping_list.items)
    
    logger.info(f"Clear all items command from user {user.first_name} ({user.id}) in chat {chat.id}")
    shopping_list.items.clear()
    
    if count > 0:
        logger.info(f"Cleared entire shopping list ({count} items) from chat {chat.id}")
        await update.message.reply_text(f"✅ Cleared entire shopping list ({count} item(s))!")
    else:
        await update.message.reply_text("Shopping list is already empty.")

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
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("remove", remove_item))
    application.add_handler(CommandHandler("done", mark_done))
    application.add_handler(CommandHandler("clear", clear_done))
    application.add_handler(CommandHandler("clearall", clear_all))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
