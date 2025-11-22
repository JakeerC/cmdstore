"""Core command storage operations."""

import json
import uuid
from datetime import datetime
from pathlib import Path

import pyperclip

from cmdstore.colors import Colors, style_error, style_info, style_prompt, style_success
from cmdstore.fzf_integration import (
    extract_command_from_selection,
    extract_command_id,
    format_commands_for_fzf,
    run_fzf_multi_select,
    run_fzf_multi_select_with_preview,
    run_fzf_search,
)


class CommandStore:
    """Manages command storage and retrieval operations."""

    def __init__(self, store_path="~/.cmdstore"):
        self.store_path = Path(store_path).expanduser()
        self.store_file = self.store_path / "commands.json"
        self.config_file = self.store_path / "config.json"
        self._ensure_store_exists()

    def _ensure_store_exists(self):
        """Create store directory and files if they don't exist"""
        self.store_path.mkdir(parents=True, exist_ok=True)
        if not self.store_file.exists():
            self._save_commands([])
        if not self.config_file.exists():
            self._save_config({})

    def _load_commands(self):
        """Load commands from JSON file"""
        try:
            with open(self.store_file) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def _save_commands(self, commands):
        """Save commands to JSON file"""
        with open(self.store_file, "w") as f:
            json.dump(commands, f, indent=2)

    def _load_config(self):
        """Load configuration"""
        try:
            with open(self.config_file) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def _save_config(self, config):
        """Save configuration"""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    def add_command(self, command, description="", tags=None, tool=""):
        """Add a new command to the store"""
        commands = self._load_commands()

        new_cmd = {
            "id": str(uuid.uuid4()),
            "command": command,
            "description": description,
            "tags": tags or [],
            "tool": tool,
            "created_at": datetime.now().isoformat(),
            "used_count": 0,
        }

        commands.append(new_cmd)
        self._save_commands(commands)
        print(style_success(f"✓ Command added: {command}"))
        return new_cmd

    def search_commands(self, tool_filter=None, tag_filter=None):
        """Search commands using fzf"""
        commands = self._load_commands()

        # Filter by tool or tag if specified
        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]
        if tag_filter:
            commands = [c for c in commands if tag_filter in c.get("tags", [])]

        if not commands:
            print(style_error("No commands found."))
            return None

        # Format commands for fzf
        fzf_input = format_commands_for_fzf(commands)

        # Run fzf with preview
        prompt = f"{Colors.BOLD}{Colors.CYAN}Search » {Colors.RESET}"
        selected = run_fzf_search(fzf_input, self.store_file, prompt, preview=True)

        if selected is None:
            print(style_error("Error: fzf not found. Please install fzf first."))
            return None

        # Extract ID from the selected line
        cmd_id = extract_command_id(selected)

        if cmd_id:
            self._increment_usage(cmd_id)
            # Get the full command from store to ensure we have the complete command
            commands = self._load_commands()
            full_cmd = next((c for c in commands if c["id"] == cmd_id), None)
            if full_cmd:  # noqa: SIM108
                command = full_cmd["command"]
            else:
                # Fallback: if command not found, extract from selection
                command = extract_command_from_selection(selected)
        else:
            # Fallback: if no ID found, use the whole selection
            command = selected

        # Copy to clipboard
        pyperclip.copy(command)
        print(style_success(f"✓ Copied to clipboard: {command}"))
        return command

    def _increment_usage(self, cmd_id):
        """Increment the usage count for a command"""
        commands = self._load_commands()
        for cmd in commands:
            if cmd["id"] == cmd_id:
                cmd["used_count"] = cmd.get("used_count", 0) + 1
                break
        self._save_commands(commands)

    def delete_command(self):
        """Delete one or more commands using fzf multi-select"""
        commands = self._load_commands()

        if not commands:
            print(style_error("No commands to delete."))
            return

        # Format commands for fzf (same format as search for preview compatibility)
        fzf_input = format_commands_for_fzf(commands)

        # Run fzf with multi-select and preview
        prompt = f"{Colors.BOLD}{Colors.RED}Delete (Tab to select multiple) » {Colors.RESET}"
        selected_lines = run_fzf_multi_select_with_preview(
            fzf_input, self.store_file, prompt, preview=True
        )

        if selected_lines is None:
            print(style_error("Error: fzf not found."))
            return

        if not selected_lines:
            print(style_info("No commands selected. Deletion cancelled."))
            return

        # Extract command IDs from selected lines
        cmd_ids = []
        for selected in selected_lines:
            cmd_id = extract_command_id(selected)
            if cmd_id:
                cmd_ids.append(cmd_id)

        if not cmd_ids:
            print(style_error("Could not parse command IDs from selection."))
            return

        # Get commands to delete
        commands_to_delete = [c for c in commands if c["id"] in cmd_ids]

        if not commands_to_delete:
            print(style_error("Selected commands not found."))
            return

        # Display summary of commands to be deleted
        print(f"\n{style_info(f'Selected {len(commands_to_delete)} command(s) for deletion:')}")
        for idx, cmd in enumerate(commands_to_delete, 1):
            command = cmd.get("command", "")
            description = cmd.get("description", "")
            tags = ", ".join(cmd.get("tags", []))
            tool = cmd.get("tool", "general")

            print(f"\n  {idx}. {style_prompt('Command:', Colors.CYAN)} {command}")
            if description:
                print(f"     {style_prompt('Description:', Colors.YELLOW)} {description}")
            if tags:
                print(f"     {style_prompt('Tags:', Colors.MAGENTA)} {tags}")
            print(f"     {style_prompt('Tool:', Colors.BLUE)} {tool}")

        prompt_text = style_prompt(
            f"\nDelete {len(commands_to_delete)} command(s)? [Y/n]:", Colors.RED
        )
        confirmation = input(f"{prompt_text} ").strip().lower()
        if confirmation not in ("", "y", "yes"):
            print(style_info("Deletion cancelled."))
            return

        # Remove all selected commands
        commands = [c for c in commands if c["id"] not in cmd_ids]
        self._save_commands(commands)
        print(style_success(f"✓ Deleted {len(commands_to_delete)} command(s)"))

    def list_commands(self, tool_filter=None):
        """List all commands"""
        commands = self._load_commands()

        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]

        if not commands:
            print(style_error("No commands found."))
            return

        for cmd in commands:
            tool = cmd.get("tool", "general")
            tags = ", ".join(cmd.get("tags", []))
            desc = cmd.get("description", "")
            used = cmd.get("used_count", 0)

            print(f"\n[{tool}] {cmd['command']}")
            if desc:
                print(f"  Description: {desc}")
            if tags:
                print(f"  Tags: {tags}")
            print(f"  Used: {used} times")

    def import_from_history(self, history_file="~/.bash_history", limit=100):
        """Import commands from shell history"""
        history_path = Path(history_file).expanduser()

        if not history_path.exists():
            print(style_error(f"History file not found: {history_file}"))
            return

        with open(history_path, errors="ignore") as f:
            lines = f.readlines()

        # Get last N unique commands
        unique_commands = list(dict.fromkeys(lines[-limit:]))

        print(style_info(f"Found {len(unique_commands)} unique commands from history."))
        print(style_info("Select commands to import (use fzf):"))

        selected = run_fzf_multi_select(unique_commands)

        if selected is None:
            print(style_error("Error: fzf not found."))
            return

        for cmd in selected:
            cmd = cmd.strip()
            if cmd:
                self.add_command(cmd, description="Imported from history")
        print(style_success(f"✓ Imported {len(selected)} commands"))
