"""
Shopping list management functionality.
"""

from typing import Dict, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import ShoppingList


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