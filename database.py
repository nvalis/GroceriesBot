"""
SQLite database management for the Telegram Groceries Bot.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for shopping lists."""
    
    def __init__(self, db_path: str = "groceries.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                self._create_tables(conn)
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create the database tables."""
        # Chats table - stores chat information
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                active_list_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Shopping lists table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                list_id TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats (chat_id) ON DELETE CASCADE,
                UNIQUE(chat_id, list_id)
            )
        """)
        
        # Shopping items table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_pk INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity TEXT DEFAULT '1',
                added_by TEXT DEFAULT '',
                is_purchased BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (list_pk) REFERENCES shopping_lists (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_lists ON shopping_lists (chat_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_list_items ON shopping_items (list_pk)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_active_list ON chats (chat_id, active_list_id)")
        
        conn.commit()
    
    def get_or_create_chat(self, chat_id: int, chat_title: str = None) -> None:
        """Ensure chat exists in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Check if chat exists
                cursor = conn.execute("SELECT chat_id FROM chats WHERE chat_id = ?", (chat_id,))
                if not cursor.fetchone():
                    # Create new chat record
                    conn.execute("""
                        INSERT INTO chats (chat_id, chat_title, active_list_id)
                        VALUES (?, ?, 'groceries')
                    """, (chat_id, chat_title))
                    
                    # Create default groceries list
                    self.create_list(chat_id, "groceries", "Groceries")
                    logger.info(f"Created new chat {chat_id} with default list")
        except Exception as e:
            logger.error(f"Failed to create chat {chat_id}: {e}")
            raise
    
    def create_list(self, chat_id: int, list_id: str, name: str) -> bool:
        """Create a new shopping list."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Ensure chat exists
                self.get_or_create_chat(chat_id)
                
                conn.execute("""
                    INSERT INTO shopping_lists (chat_id, list_id, name)
                    VALUES (?, ?, ?)
                """, (chat_id, list_id, name))
                
                conn.commit()
                logger.info(f"Created list '{name}' ({list_id}) for chat {chat_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"List {list_id} already exists for chat {chat_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to create list {list_id} for chat {chat_id}: {e}")
            return False
    
    def get_lists(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get all lists for a chat."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT id, list_id, name, created_at
                    FROM shopping_lists
                    WHERE chat_id = ?
                    ORDER BY created_at
                """, (chat_id,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get lists for chat {chat_id}: {e}")
            return []
    
    def delete_list(self, chat_id: int, list_id: str) -> bool:
        """Delete a shopping list."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                cursor = conn.execute("""
                    DELETE FROM shopping_lists
                    WHERE chat_id = ? AND list_id = ?
                """, (chat_id, list_id))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.info(f"Deleted list {list_id} for chat {chat_id}")
                
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete list {list_id} for chat {chat_id}: {e}")
            return False
    
    def get_active_list_id(self, chat_id: int) -> str:
        """Get the active list ID for a chat."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT active_list_id FROM chats WHERE chat_id = ?
                """, (chat_id,))
                
                result = cursor.fetchone()
                return result[0] if result else "groceries"
        except Exception as e:
            logger.error(f"Failed to get active list for chat {chat_id}: {e}")
            return "groceries"
    
    def set_active_list_id(self, chat_id: int, list_id: str) -> bool:
        """Set the active list for a chat."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE chats
                    SET active_list_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                """, (list_id, chat_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set active list {list_id} for chat {chat_id}: {e}")
            return False
    
    def add_item(self, chat_id: int, list_id: str, name: str, quantity: str = "1", added_by: str = "") -> bool:
        """Add an item to a shopping list."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get list primary key
                cursor = conn.execute("""
                    SELECT id FROM shopping_lists
                    WHERE chat_id = ? AND list_id = ?
                """, (chat_id, list_id))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"List {list_id} not found for chat {chat_id}")
                    return False
                
                list_pk = result[0]
                
                conn.execute("""
                    INSERT INTO shopping_items (list_pk, name, quantity, added_by)
                    VALUES (?, ?, ?, ?)
                """, (list_pk, name, quantity, added_by))
                
                conn.commit()
                logger.info(f"Added item '{name}' to list {list_id} for chat {chat_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to add item '{name}' to list {list_id} for chat {chat_id}: {e}")
            return False
    
    def get_items(self, chat_id: int, list_id: str) -> List[Dict[str, Any]]:
        """Get all items from a shopping list."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT si.id, si.name, si.quantity, si.added_by, si.is_purchased, si.created_at
                    FROM shopping_items si
                    JOIN shopping_lists sl ON si.list_pk = sl.id
                    WHERE sl.chat_id = ? AND sl.list_id = ?
                    ORDER BY si.created_at
                """, (chat_id, list_id))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get items from list {list_id} for chat {chat_id}: {e}")
            return []
    
    def update_item_purchased(self, chat_id: int, list_id: str, item_index: int, is_purchased: bool) -> bool:
        """Update the purchased status of an item by index."""
        try:
            items = self.get_items(chat_id, list_id)
            if 0 <= item_index < len(items):
                item_id = items[item_index]['id']
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE shopping_items
                        SET is_purchased = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (is_purchased, item_id))
                    
                    conn.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update item {item_index} in list {list_id} for chat {chat_id}: {e}")
            return False
    
    def remove_item(self, chat_id: int, list_id: str, item_index: int) -> bool:
        """Remove an item by index."""
        try:
            items = self.get_items(chat_id, list_id)
            if 0 <= item_index < len(items):
                item_id = items[item_index]['id']
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM shopping_items WHERE id = ?", (item_id,))
                    conn.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove item {item_index} from list {list_id} for chat {chat_id}: {e}")
            return False
    
    def clear_purchased_items(self, chat_id: int, list_id: str) -> int:
        """Remove all purchased items from a list. Returns count of removed items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM shopping_items
                    WHERE id IN (
                        SELECT si.id
                        FROM shopping_items si
                        JOIN shopping_lists sl ON si.list_pk = sl.id
                        WHERE sl.chat_id = ? AND sl.list_id = ? AND si.is_purchased = TRUE
                    )
                """, (chat_id, list_id))
                
                count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared {count} purchased items from list {list_id} for chat {chat_id}")
                return count
        except Exception as e:
            logger.error(f"Failed to clear purchased items from list {list_id} for chat {chat_id}: {e}")
            return 0
    
    def clear_all_items(self, chat_id: int, list_id: str) -> int:
        """Remove all items from a list. Returns count of removed items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM shopping_items
                    WHERE id IN (
                        SELECT si.id
                        FROM shopping_items si
                        JOIN shopping_lists sl ON si.list_pk = sl.id
                        WHERE sl.chat_id = ? AND sl.list_id = ?
                    )
                """, (chat_id, list_id))
                
                count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleared all {count} items from list {list_id} for chat {chat_id}")
                return count
        except Exception as e:
            logger.error(f"Failed to clear all items from list {list_id} for chat {chat_id}: {e}")
            return 0
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            import shutil
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Database backed up to {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False