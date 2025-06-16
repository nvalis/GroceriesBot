"""
Persistent shopping list manager that uses SQLite for data storage.
"""

from typing import Dict, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models import ShoppingItem, ShoppingList
from database import DatabaseManager
import logging

logger = logging.getLogger(__name__)


class PersistentShoppingListManager:
    """Manages shopping lists with SQLite persistence."""
    
    def __init__(self, db_path: str = "groceries.db"):
        self.db = DatabaseManager(db_path)
        # Cache for frequently accessed data
        self._list_cache: Dict[str, ShoppingList] = {}
    
    def _get_cache_key(self, chat_id: int, list_id: str) -> str:
        """Generate cache key for a list."""
        return f"{chat_id}:{list_id}"
    
    def _load_list_from_db(self, chat_id: int, list_id: str) -> ShoppingList:
        """Load a shopping list from database."""
        # Get list info
        lists = self.db.get_lists(chat_id)
        list_info = next((l for l in lists if l['list_id'] == list_id), None)
        
        if not list_info:
            # Create the list if it doesn't exist
            list_name = "Groceries" if list_id == "groceries" else list_id.replace("_", " ").title()
            self.db.create_list(chat_id, list_id, list_name)
            shopping_list = ShoppingList(chat_id=chat_id, name=list_name, list_id=list_id)
        else:
            shopping_list = ShoppingList(
                chat_id=chat_id,
                name=list_info['name'],
                list_id=list_info['list_id']
            )
        
        # Load items
        items_data = self.db.get_items(chat_id, list_id)
        shopping_list.items = []
        
        for item_data in items_data:
            item = ShoppingItem(
                name=item_data['name'],
                quantity=item_data['quantity'],
                added_by=item_data['added_by']
            )
            shopping_list.items.append(item)
        
        return shopping_list
    
    def _invalidate_cache(self, chat_id: int, list_id: str = None) -> None:
        """Invalidate cache for a specific list or all lists for a chat."""
        if list_id:
            cache_key = self._get_cache_key(chat_id, list_id)
            self._list_cache.pop(cache_key, None)
        else:
            # Remove all cached lists for this chat
            keys_to_remove = [k for k in self._list_cache.keys() if k.startswith(f"{chat_id}:")]
            for key in keys_to_remove:
                self._list_cache.pop(key, None)
    
    def get_list(self, chat_id: int, list_id: str = "groceries") -> ShoppingList:
        """Get or create a shopping list for a chat."""
        cache_key = self._get_cache_key(chat_id, list_id)
        
        # Check cache first
        if cache_key in self._list_cache:
            return self._list_cache[cache_key]
        
        # Load from database
        shopping_list = self._load_list_from_db(chat_id, list_id)
        
        # Cache the result
        self._list_cache[cache_key] = shopping_list
        
        return shopping_list
    
    def get_active_list(self, chat_id: int) -> ShoppingList:
        """Get the currently active list for a chat."""
        # Ensure chat exists
        self.db.get_or_create_chat(chat_id)
        
        active_list_id = self.db.get_active_list_id(chat_id)
        return self.get_list(chat_id, active_list_id)
    
    def set_active_list(self, chat_id: int, list_id: str) -> bool:
        """Set the active list for a chat. Returns True if successful."""
        # Ensure the list exists
        self.get_list(chat_id, list_id)
        
        # Update in database
        success = self.db.set_active_list_id(chat_id, list_id)
        
        if success:
            logger.info(f"Set active list to {list_id} for chat {chat_id}")
        
        return success
    
    def create_list(self, chat_id: int, list_name: str) -> str:
        """Create a new list and return its ID."""
        list_id = list_name.lower().replace(" ", "_")
        
        # Ensure unique list ID
        existing_lists = self.db.get_lists(chat_id)
        existing_ids = {l['list_id'] for l in existing_lists}
        
        counter = 1
        original_id = list_id
        while list_id in existing_ids:
            list_id = f"{original_id}_{counter}"
            counter += 1
        
        # Create in database
        success = self.db.create_list(chat_id, list_id, list_name)
        
        if success:
            # Invalidate cache for this chat
            self._invalidate_cache(chat_id)
            logger.info(f"Created list '{list_name}' ({list_id}) for chat {chat_id}")
        
        return list_id
    
    def delete_list(self, chat_id: int, list_id: str) -> bool:
        """Delete a list. Returns True if successful."""
        # Check if there's more than one list
        existing_lists = self.db.get_lists(chat_id)
        if len(existing_lists) <= 1:
            return False
        
        # Delete from database
        success = self.db.delete_list(chat_id, list_id)
        
        if success:
            # Invalidate cache
            self._invalidate_cache(chat_id, list_id)
            
            # If this was the active list, switch to first available
            active_list_id = self.db.get_active_list_id(chat_id)
            if active_list_id == list_id:
                remaining_lists = self.db.get_lists(chat_id)
                if remaining_lists:
                    new_active = remaining_lists[0]['list_id']
                    self.db.set_active_list_id(chat_id, new_active)
                    logger.info(f"Switched active list to {new_active} after deleting {list_id}")
        
        return success
    
    def get_all_lists(self, chat_id: int) -> List[ShoppingList]:
        """Get all lists for a chat."""
        lists_data = self.db.get_lists(chat_id)
        shopping_lists = []
        
        for list_data in lists_data:
            shopping_list = self.get_list(chat_id, list_data['list_id'])
            shopping_lists.append(shopping_list)
        
        return shopping_lists
    
    def get_lists_summary(self, chat_id: int) -> str:
        """Get a summary of all lists for a chat."""
        lists = self.get_all_lists(chat_id)
        if not lists:
            return "No lists found."
        
        active_list_id = self.db.get_active_list_id(chat_id)
        text = "📋 *Shopping Lists:*\n\n"
        
        for shopping_list in sorted(lists, key=lambda x: x.list_id):
            active_marker = "🔹" if shopping_list.list_id == active_list_id else "▫️"
            item_count = len(shopping_list.items)
            
            # Escape special characters in names and IDs for Markdown
            safe_name = shopping_list.name.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            safe_id = shopping_list.list_id.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
            
            text += f"{active_marker} *{safe_name}* (`{safe_id}`)\n"
            text += f"   📝 {item_count} items\n\n"
        
        active_list = self.get_active_list(chat_id)
        safe_active_name = active_list.name.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
        text += f"💡 Active list: *{safe_active_name}*"
        return text
    
    def get_lists_keyboard(self, chat_id: int):
        """Get inline keyboard for list switching - disabled."""
        return None
    
    def add_item(self, chat_id: int, name: str, quantity: str = "1", added_by: str = "") -> None:
        """Add an item to a chat's active shopping list."""
        active_list_id = self.db.get_active_list_id(chat_id)
        
        # Add to database
        success = self.db.add_item(chat_id, active_list_id, name, quantity, added_by)
        
        if success:
            # Invalidate cache to force reload
            self._invalidate_cache(chat_id, active_list_id)
    
    def remove_item(self, chat_id: int, index: int) -> bool:
        """Remove an item from a chat's active shopping list."""
        active_list_id = self.db.get_active_list_id(chat_id)
        
        # Remove from database
        success = self.db.remove_item(chat_id, active_list_id, index)
        
        if success:
            # Invalidate cache
            self._invalidate_cache(chat_id, active_list_id)
        
        return success
    
    
    def get_list_display(self, chat_id: int) -> str:
        """Get formatted display text for a chat's active shopping list."""
        shopping_list = self.get_active_list(chat_id)
        return shopping_list.get_display_text()
    
    def wipe_list(self, chat_id: int) -> int:
        """Clear all items from active shopping list. Returns count of removed items."""
        active_list_id = self.db.get_active_list_id(chat_id)
        
        # Clear from database
        count = self.db.clear_all_items(chat_id, active_list_id)
        
        if count > 0:
            # Invalidate cache
            self._invalidate_cache(chat_id, active_list_id)
        
        return count
    
    def backup_data(self, backup_path: str) -> bool:
        """Create a backup of all data."""
        return self.db.backup_database(backup_path)