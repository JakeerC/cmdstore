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

Using `uv` (recommended):
```bash
uv pip install cmdstore
```

Or using `pip`:
```bash
pip install cmdstore
```

Or install from source:
```bash
git clone <repository-url>
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
- `--file`: Path to history file (default: `~/.bash_history`)
- `--limit`: Number of recent commands to consider (default: 100)

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

## Requirements

- Python 3.12+
- `fzf` (fuzzy finder)
- `pyperclip` (automatically installed as dependency)

## License

MIT License

Copyright (c) 2025 Jakeer

## Contributing

[Add contribution guidelines here]
