# Telegram Groceries Bot

A Telegram bot for managing grocery shopping lists in group chats with persistent data storage and interactive features.

## Features

- **Multi-list Management**: Create and manage multiple shopping lists per chat
- **Interactive UI**: Inline keyboards for easy item management (mark done, remove items) with quantity display
- **Persistent Storage**: SQLite database for data persistence across bot restarts
- **Group Chat Support**: Works seamlessly in Telegram group chats
- **Admin Commands**: Backup and statistics functionality
- **Real-time Updates**: Live list updates with refresh functionality
- **Smart Quantity Handling**: Automatically parse quantities from item names

## Commands

### Basic Commands
- `/start` - Start the bot and get welcome message
- `/help` - Show available commands

### Item Management
- `/add <item> [quantity]` - Add item to current list (e.g., `/add milk 2`)
- `/remove <number>` - Remove item by number
- `/done <number>` - Mark item as purchased

### List Management
- `/list` - Show current shopping list with interactive buttons (quantities shown in buttons)
- `/lists` - Show all lists with switching options
- `/new <list_name>` - Create a new shopping list
- `/go <list_name>` - Switch to a different list
- `/delete <list_name>` - Delete a shopping list
- `/clear` - Remove all purchased items
- `/wipe` - Clear entire list

### Admin Commands (Private chat only)
- `/backup` - Create database backup
- `/stats` - Show bot usage statistics

## Development

This project uses `uv` for Python package management and Python 3.13.

### Setup

1. Clone the repository
2. Install dependencies:
```bash
uv sync
```

3. Create a `.env` file with your bot token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### Running

```bash
uv run python main.py
```

### Project Structure

```
telegram_groceries/
├── main.py                     # Bot entry point
├── models.py                   # Data models (ShoppingItem, ShoppingList)
├── database.py                 # SQLite database management
├── persistent_list_manager.py  # Persistent storage manager
├── handlers/                   # Command handlers
│   ├── __init__.py
│   ├── basic_commands.py       # start, help, new_chat_members
│   ├── item_commands.py        # add, remove, mark_done
│   ├── list_commands.py        # list operations
│   ├── callback_handler.py     # interactive button handling
│   └── admin_commands.py       # backup, stats
├── tasks.md                    # Development tasks
└── CLAUDE.md                   # Project instructions
```

## Database Schema

The bot uses SQLite with the following tables:

- **chats**: Store chat information and active list preferences
- **shopping_lists**: Multiple lists per chat with unique identifiers
- **shopping_items**: Items belonging to lists with purchase status

Data is automatically backed up with the `/backup` command and persists across bot restarts.