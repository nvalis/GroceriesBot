"""
Admin command handlers for backup and maintenance.
"""

import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def backup_data(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Create a backup of the bot data."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Simple admin check - only allow in private chats for now
    if chat.type != "private":
        await update.message.reply_text("❌ Backup command only available in private chat.")
        return
    
    logger.info(f"Backup command from user {user.first_name} ({user.id})")
    
    try:
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backups/groceries_backup_{timestamp}.db"
        
        # Ensure backup directory exists
        os.makedirs("backups", exist_ok=True)
        
        success = list_manager.backup_data(backup_path)
        
        if success:
            await update.message.reply_text(f"✅ Backup created successfully!\nFile: `{backup_path}`", parse_mode='Markdown')
            logger.info(f"Backup created by user {user.id}: {backup_path}")
        else:
            await update.message.reply_text("❌ Failed to create backup.")
    
    except Exception as e:
        logger.error(f"Backup command failed: {e}")
        await update.message.reply_text("❌ An error occurred while creating backup.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, list_manager) -> None:
    """Show database statistics."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Simple admin check - only allow in private chats for now
    if chat.type != "private":
        await update.message.reply_text("❌ Stats command only available in private chat.")
        return
    
    logger.info(f"Stats command from user {user.first_name} ({user.id})")
    
    try:
        # Get basic stats from database
        db = list_manager.db
        
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            # Count total chats
            cursor = conn.execute("SELECT COUNT(*) FROM chats")
            total_chats = cursor.fetchone()[0]
            
            # Count total lists
            cursor = conn.execute("SELECT COUNT(*) FROM shopping_lists")
            total_lists = cursor.fetchone()[0]
            
            # Count total items
            cursor = conn.execute("SELECT COUNT(*) FROM shopping_items")
            total_items = cursor.fetchone()[0]
            
            # Count purchased items
            cursor = conn.execute("SELECT COUNT(*) FROM shopping_items WHERE is_purchased = TRUE")
            purchased_items = cursor.fetchone()[0]
        
        stats_text = f"""
📊 *Bot Statistics*

👥 Total Chats: {total_chats}
📋 Total Lists: {total_lists}
📝 Total Items: {total_items}
✅ Purchased Items: {purchased_items}
📍 Pending Items: {total_items - purchased_items}
        """
        
        await update.message.reply_text(stats_text.strip(), parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Stats command failed: {e}")
        await update.message.reply_text("❌ An error occurred while fetching statistics.")