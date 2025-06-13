# CLAUDE.md

## Project Overview

This is a complete Telegram groceries application. The bot can be invited into group chats to manage multiple shopping lists. Features include interactive item management, multi-list support, persistent SQLite storage, and admin functionality.

## Architecture Notes

This codebase uses Python 3.13 with python-telegram-bot library. Project management is done with uv. The application uses a modular architecture with:

- **SQLite Database**: Persistent storage with proper schema design
- **Modular Handlers**: Organized command handlers in separate files
- **Interactive UI**: Inline keyboards for real-time list management
- **Caching Layer**: Performance optimization with cache invalidation
- **Admin Tools**: Backup and statistics functionality

## Current Implementation Status

The bot is feature-complete with:
- ✅ Multi-list management per chat
- ✅ Interactive inline keyboards for item actions with quantity display
- ✅ SQLite data persistence with backup
- ✅ Modular code architecture
- ✅ Admin commands and logging
- ✅ Error handling and edge cases
- ✅ Fixed callback handler bugs

## Project management

The file tasks.md contains a high-level overview of tasks. All major changes are committed using git.

## Memories

- Dont add new items to the tasks.md file until explicitly told so