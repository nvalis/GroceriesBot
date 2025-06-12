# Project Structure

The Telegram Groceries Bot has been refactored into a modular structure:

## Core Files

- **main.py** - Entry point and application setup
- **models.py** - Data models (ShoppingItem, ShoppingList)
- **list_manager.py** - Business logic for list management

## Handlers Package

- **handlers/__init__.py** - Handler exports
- **handlers/basic_commands.py** - Basic bot commands (start, help)
- **handlers/item_commands.py** - Item operations (add, remove, done)
- **handlers/list_commands.py** - List operations (list, lists, new, switch, etc.)
- **handlers/callback_handler.py** - Interactive button handling

## Benefits

- **Separation of Concerns**: Each module has a clear responsibility
- **Maintainability**: Easy to find and modify specific functionality
- **Testability**: Individual components can be unit tested
- **Scalability**: Easy to add new features without bloating single files
- **Code Reuse**: Modular components can be reused

## Module Dependencies

```
main.py
├── list_manager.py
│   └── models.py
└── handlers/
    ├── basic_commands.py
    ├── item_commands.py
    ├── list_commands.py
    └── callback_handler.py
```

All handlers receive the `list_manager` instance through dependency injection via the wrapper function.