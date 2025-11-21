# cmdstore - Setup Guide

## Installation

### 1. Install Dependencies

```bash
uv add pyperclip
```

### 2. Setup the Script

```bash
# Make the script executable
chmod +x cmdstore.py

# Create a symlink to use it globally (optional)
sudo ln -s $(pwd)/cmdstore.py /usr/local/bin/cmdstore

# Or add an alias to your .bashrc/.zshrc
echo "alias cmdstore='python3 /path/to/cmdstore.py'" >> ~/.zshrc
```

### 3. Storage Location

By default cmdstore keeps its data under `~/.cmdstore/`.

**Permanently change the default store location:**
```bash
cmdstore --set-store ~/dotfiles/.cmdstore
```

This will set the default for all future invocations. The configuration is saved to `~/.cmdstore_config.json`.

**Override the store location for a single command:**
```bash
cmdstore --store ~/dotfiles/.cmdstore add "npm run build"
```

The `--store` flag takes precedence over the persistent default set by `--set-store`.

## Usage

### Add a Command
```bash
# Basic add
cmdstore add "npm install -D tailwindcss"

# With description and tags
cmdstore add "npm install -D tailwindcss" -d "Install Tailwind as dev dependency" -t npm tailwind setup --tool npm

# Interactive example
cmdstore add "uv venv" -d "Create virtual environment with uv" -t python uv venv --tool uv

# Prompt for everything (no args)
cmdstore add
```

Running `cmdstore add` with no arguments launches an interactive prompt for the command, description, tags, and tool fields.

### Search Commands
```bash
# Search all commands (opens fzf)
cmdstore search

# Filter by tool
cmdstore search --tool npm

# Filter by tag
cmdstore search --tag python
```

### List Commands
```bash
# List all
cmdstore list

# List by tool
cmdstore list --tool npm
```

### Delete Command
```bash
cmdstore delete
# Opens fzf to select a command to delete, then asks for confirmation
```

### Import from History
```bash
# Import from bash history (default last 100 commands)
cmdstore import

# Import from zsh history
cmdstore import --file ~/.zsh_history --limit 200
```

## File Structure

```
~/.cmdstore/
├── commands.json    # All stored commands
└── config.json      # Configuration

~/.cmdstore_config.json  # Global default store path configuration
```

## Example Workflow

```bash
# Add some commands
cmdstore add "npm run dev" -d "Start dev server" -t npm dev --tool npm
cmdstore add "uv pip install -r requirements.txt" -t python uv --tool uv
cmdstore add "nvim ~/.config/nvim/init.lua" -d "Edit neovim config" -t neovim config --tool neovim

# Search and copy to clipboard
cmdstore search --tool npm
# Select with fzf, automatically copies to clipboard

# Paste with Ctrl+V
```

## Tips

- Keep the script in your dotfiles repo for version control
- The `~/.cmdstore/` directory contains your command database (or whichever path you set via `--set-store` or pass via `--store`)
- Use `--set-store` to permanently configure a custom location (e.g., `~/dotfiles/.cmdstore` for version control)
- The persistent store path is saved in `~/.cmdstore_config.json`
- Use `--store` to temporarily override the default for a single command