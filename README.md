<p align="center">
  <img src="https://raw.githubusercontent.com/JakeerC/cmdstore/main/assets/cmdstore_logo.png" alt="cmdstore logo" width="220" />
</p>


# cmdstore

A CLI tool to store and retrieve commands with fuzzy finding using `fzf`. Quickly save, search, and reuse your frequently used commands with rich metadata support.

## Features

- 🎯 **Fuzzy Search**: Interactive command search with `fzf` and live preview
- 📋 **Auto-copy**: Selected commands are automatically copied to clipboard
- 🏷️ **Metadata**: Organize commands with descriptions, tags, and tool categories
- 📊 **Usage Tracking**: Commands track how many times they've been used
- 🗑️ **Multi-select Delete**: Select and delete multiple commands at once
- 📥 **History Import**: Import commands from your shell history
- ⚙️ **Flexible Storage**: Configure custom store locations globally or per-command

## Installation

### Prerequisites

- Python 3.12 or higher
- `fzf` (fuzzy finder) - [Installation guide](https://github.com/junegunn/fzf#installation)

### Install cmdstore

Using `pipx`:
```bash
pipx install cmdstore
```

or using `uv`:
```bash
uv pip install cmdstore
```

Or using `pip`:
```bash
pip install cmdstore
```

Or install from source:
```bash
git clone https://github.com/JakeerC/cmdstore.git
cd cmdstore
uv pip install -e .
```

## Quick Start

```bash
# Add your first command
cmdstore add "npm run dev" -d "Start development server" -t npm dev --tool npm

# Search and use commands
cmdstore search

# List all commands
cmdstore list
```

## Usage

### Add a Command

Add commands with optional metadata:

```bash
# Basic add (interactive prompts for all fields)
cmdstore add

# Add with command only
cmdstore add "npm install -D tailwindcss"

# Add with all metadata
cmdstore add "npm install -D tailwindcss" \
  -d "Install Tailwind as dev dependency" \
  -t npm tailwind setup --tool npm

# Add Python command
cmdstore add "uv venv" \
  -d "Create virtual environment with uv" \
  -t python uv venv --tool uv
```

**Command Options:**
- `-d, --description`: Command description
- `-t, --tags`: Space-separated tags for categorization
- `--tool`: Tool category (npm, uv, node, git, etc.)

### Search Commands

Search commands with `fzf` and preview details:

```bash
# Search all commands (opens fzf with preview)
cmdstore search

# Filter by tool
cmdstore search --tool npm

# Filter by tag
cmdstore search --tag python
```

**Search Features:**
- Interactive fuzzy search with `fzf`
- Live preview showing command details, description, tags, tool, and usage count
- Selected command is automatically copied to clipboard
- Usage count is incremented when a command is selected

### List Commands

Display all commands in a readable format:

```bash
# List all commands
cmdstore list

# List commands by tool
cmdstore list --tool npm
```

### Delete Commands

Delete one or more commands with multi-select:

```bash
cmdstore delete
```

**Delete Features:**
- Opens `fzf` with multi-select mode (use `Tab` to select multiple)
- Preview pane shows full command details
- Confirmation prompt before deletion
- Can delete multiple commands in one operation

### Import from History

Import commands from your shell history:

```bash
# Import from bash history (default: last 100 commands)
cmdstore import

# Import from zsh history
cmdstore import --file ~/.zsh_history --limit 200

# Import from custom history file
cmdstore import --file ~/.fish_history --limit 50
```

**Import Options:**
- `--file`: Path to history file (defaults to config or `~/.bash_history`)
- `--limit`: Number of recent commands to consider (defaults to config or `100`)

**Note:** If `--file` or `--limit` are not provided, cmdstore will use values from `config.json`. If those are not set, it falls back to the defaults shown above.

## Configuration

### Store Location

By default, cmdstore stores data in `~/.cmdstore/`.

**Set a persistent default store location:**
```bash
cmdstore --set-store ~/dotfiles/.cmdstore
```

This saves the configuration to `~/.cmdstore_config.json` and will be used for all future invocations.

**Override store location for a single command:**
```bash
cmdstore --store ~/dotfiles/.cmdstore add "npm run build"
```

The `--store` flag takes precedence over the persistent default.

**Priority order:**
1. `--store` flag (highest priority)
2. Global config from `~/.cmdstore_config.json`
3. Default `~/.cmdstore` (lowest priority)

### Local Configuration (`config.json`)

Each store directory contains a `config.json` file that allows you to customize behavior. This file is automatically created with default values when you first use cmdstore.

**Location:** `~/.cmdstore/config.json` (or your configured store path)

#### Configuration Options

The configuration file supports the following options:

```json
{
  "fzf": {
    "preview_width": "50%",
    "height": "50%",
    "border_style": "rounded"
  },
  "auto_copy": {
    "enabled": true,
    "show_notification": true
  },
  "defaults": {
    "tool": "",
    "tags": [],
    "description_template": "Imported from history"
  },
  "search": {
    "sort_by": "used_count",
    "sort_order": "desc",
    "show_usage_count": true,
    "group_by_tool": false
  },
  "preview": {
    "show_command": true,
    "show_description": true,
    "show_tags": true,
    "show_tool": true,
    "show_usage_count": true,
    "show_created_at": false
  },
  "import": {
    "default_history_file": "~/.bash_history",
    "default_limit": 100,
    "auto_add_tags": [],
    "skip_duplicates": true
  },
  "ui": {
    "colors_enabled": true,
    "emoji_enabled": true,
    "compact_mode": false,
    "confirm_deletion": true
  }
}
```

#### Configuration Sections

**FZF Settings (`fzf`)**
- `preview_width`: Width of the fzf preview pane (e.g., "50%", "60%")
- `height`: Height of the fzf interface (e.g., "50%", "80%")
- `border_style`: Border style for fzf (e.g., "rounded", "sharp")

**Auto-copy Settings (`auto_copy`)**
- `enabled`: Automatically copy selected commands to clipboard (default: `true`)
- `show_notification`: Show notification when command is copied (default: `true`)

**Default Metadata (`defaults`)**
- `tool`: Default tool category for new commands (default: `""`)
- `tags`: Default tags to apply to new commands (default: `[]`)
- `description_template`: Template for imported commands (default: `"Imported from history"`)

**Search Settings (`search`)**
- `sort_by`: Sort commands by `"used_count"`, `"created_at"`, or `"alphabetical"` (default: `"used_count"`)
- `sort_order`: Sort order `"asc"` or `"desc"` (default: `"desc"`)
- `show_usage_count`: Show usage count in list view (default: `true`)
- `group_by_tool`: Group commands by tool in list view (default: `false`)

**Preview Settings (`preview`)**
- `show_command`: Show command in preview pane (default: `true`)
- `show_description`: Show description in preview pane (default: `true`)
- `show_tags`: Show tags in preview pane (default: `true`)
- `show_tool`: Show tool in preview pane (default: `true`)
- `show_usage_count`: Show usage count in preview pane (default: `true`)
- `show_created_at`: Show creation date in preview pane (default: `false`)

**Import Settings (`import`)**
- `default_history_file`: Default history file path (default: `"~/.bash_history"`)
- `default_limit`: Default number of commands to import (default: `100`)
- `auto_add_tags`: Tags to automatically add to imported commands (default: `[]`)
- `skip_duplicates`: Skip commands that already exist in store (default: `true`)

**UI Settings (`ui`)**
- `colors_enabled`: Enable colored output (default: `true`)
- `emoji_enabled`: Enable emoji in output (default: `true`)
- `compact_mode`: Use compact display mode (default: `false`)
- `confirm_deletion`: Require confirmation before deleting (default: `true`)

#### Example Customizations

**Customize search sorting:**
```json
{
  "search": {
    "sort_by": "alphabetical",
    "sort_order": "asc",
    "group_by_tool": true
  }
}
```

**Customize import defaults:**
```json
{
  "import": {
    "default_history_file": "~/.zsh_history",
    "default_limit": 200,
    "auto_add_tags": ["imported", "history"]
  }
}
```

**Customize preview display:**
```json
{
  "preview": {
    "show_created_at": true,
    "show_usage_count": false
  }
}
```

**Disable deletion confirmation:**
```json
{
  "ui": {
    "confirm_deletion": false
  }
}
```

## File Structure

```
~/.cmdstore/
├── commands.json    # All stored commands with metadata
└── config.json      # Local store configuration

~/.cmdstore_config.json  # Global default store path configuration
```

### Command Data Format

Each command is stored with the following structure:

```json
{
  "id": "uuid",
  "command": "npm run dev",
  "description": "Start development server",
  "tags": ["npm", "dev"],
  "tool": "npm",
  "created_at": "2024-01-01T12:00:00",
  "used_count": 5
}
```

## Example Workflow

```bash
# 1. Add some frequently used commands
cmdstore add "npm run dev" -d "Start dev server" -t npm dev --tool npm
cmdstore add "uv pip install -r requirements.txt" -t python uv --tool uv
cmdstore add "nvim ~/.config/nvim/init.lua" -d "Edit neovim config" -t neovim config --tool neovim

# 2. Search and use commands
cmdstore search --tool npm
# Select with fzf, command is automatically copied to clipboard

# 3. Paste with Ctrl+V (or Cmd+V on macOS)

# 4. Import commands from history
cmdstore import --file ~/.zsh_history --limit 200

# 5. Clean up old commands
cmdstore delete
# Use Tab to select multiple, then confirm deletion
```

## Tips

- **Version Control**: Use `--set-store` to point to a directory in your dotfiles repo for version control
- **Organization**: Use consistent tags and tools for better searchability
- **History Import**: Regularly import from your shell history to build your command library
- **Multi-select Delete**: Use `Tab` in fzf to select multiple commands for batch deletion
- **Preview**: The fzf preview pane shows full command details - use it to verify before selecting
- **Configuration**: Customize `config.json` to match your workflow - it's automatically created with sensible defaults
- **Sorting**: Configure search sorting in `config.json` to prioritize frequently used commands or alphabetical order
- **Import Automation**: Set `auto_add_tags` in config to automatically tag imported commands for easier organization

## Requirements

- Python 3.12+
- `fzf` (fuzzy finder)
- `pyperclip` (automatically installed as dependency)

## License

MIT License

Copyright (c) 2025 Jakeer

## Contributing

[Add contribution guidelines here]
