"""
Data models for the Telegram Groceries Bot.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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
        purchased_items = sum(1 for item in self.items if item.is_purchased)
        if purchased_items > 0:
            keyboard.append([
                InlineKeyboardButton("🧹 Clear Bought Items", callback_data="clear_bought"),
                InlineKeyboardButton("🗑️ Wipe All", callback_data="wipe_all")
            ])
        elif len(self.items) > 0:  # Only wipe if there are items
            keyboard.append([
                InlineKeyboardButton("🗑️ Wipe All", callback_data="wipe_all")
            ])
        
        # Add list switching buttons
        keyboard.append([
            InlineKeyboardButton("📋 All Lists", callback_data="show_lists"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
        ])
        
        return InlineKeyboardMarkup(keyboard)