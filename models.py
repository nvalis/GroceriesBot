"""
Data models for the Telegram Groceries Bot.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


@dataclass
class ShoppingItem:
    """Represents a single item in a shopping list."""
    name: str
    quantity: str = "1"
    added_by: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"📝 {self.quantity} {self.name}"


@dataclass
class ShoppingList:
    """Represents a shopping list for a chat."""
    chat_id: int
    name: str = "Shopping List"
    list_id: str = "groceries"
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
    
    
    def get_display_text(self) -> str:
        """Get formatted text for displaying the list."""
        if not self.items:
            return f"📝 *{self.name}* is empty."
        
        text = f"📝 *{self.name}*\n\n"
        for i, item in enumerate(self.items, 1):
            text += f"{i}. {item}\n"
        return text
    
    def get_interactive_keyboard(self):
        """Get inline keyboard for list actions - disabled."""
        return None
    
    def get_reply_keyboard(self) -> ReplyKeyboardMarkup:
        """Get main menu reply keyboard."""
        # Truncate list name if too long for button
        display_name = self.name
        if len(display_name) > 15:
            display_name = display_name[:12] + "..."
        
        keyboard = [
            [f"✏️ Edit {display_name}", "🛒 Shopping Mode"],
            ["📋 List Management", "ℹ️ Help"]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            input_field_placeholder="Choose a mode or type item name..."
        )
    
    def get_list_management_keyboard(self) -> ReplyKeyboardMarkup:
        """Get list management mode keyboard."""
        keyboard = [
            ["📋 Show Current List", "📝 Create New List"],
            ["🔄 Switch Lists", "🗑️ Delete List"],
            ["← Back to Main Menu"]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            input_field_placeholder="Manage your lists..."
        )
    
    def get_item_management_keyboard(self) -> ReplyKeyboardMarkup:
        """Get item management mode keyboard."""
        keyboard = [
            ["➕ Add Item", "🔍 Show List"],
            ["🗑️ Remove Item", "🗑️ Wipe All"],
            ["← Back to Main Menu"]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            is_persistent=True,
            input_field_placeholder="Manage your items..."
        )