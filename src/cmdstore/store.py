"""Core command storage operations."""

import json
import uuid
from datetime import datetime
from pathlib import Path

import pyperclip

import cmdstore.fallback_ui as fallback_ui
from cmdstore.colors import Colors, style_error, style_info, style_prompt, style_success
from cmdstore.fzf_integration import (
    extract_command_from_selection,
    extract_command_id,
    format_commands_for_fzf,
    run_fzf_multi_select,
    run_fzf_multi_select_with_preview,
    run_fzf_search,
)

DEFAULT_CONFIG = {
    "fzf": {
        "preview_width": "50%",
        "height": "50%",
        "border_style": "rounded",
    },
    "auto_copy": {
        "enabled": True,
        "show_notification": True,
    },
    "defaults": {
        "tool": "",
        "tags": [],
        "description_template": "Imported from history",
    },
    "search": {
        "sort_by": "used_count",
        "sort_order": "desc",
        "show_usage_count": True,
        "group_by_tool": False,
    },
    "preview": {
        "show_command": True,
        "show_description": True,
        "show_tags": True,
        "show_tool": True,
        "show_usage_count": True,
        "show_created_at": False,
    },
    "import": {
        "default_history_file": "~/.bash_history",
        "default_limit": 100,
        "auto_add_tags": [],
        "skip_duplicates": True,
    },
    "ui": {
        "colors_enabled": True,
        "emoji_enabled": True,
        "compact_mode": False,
        "confirm_deletion": True,
        "use_fzf": True,
    },
}


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
            self._save_config(DEFAULT_CONFIG.copy())

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

    def _deep_merge(self, default, user):
        """Deep merge user config into default config"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self):
        """Get merged configuration with defaults"""
        user_config = self._load_config()
        return self._deep_merge(DEFAULT_CONFIG.copy(), user_config)

    def add_command(self, command, description="", tags=None, tool=""):
        """Add a new command to the store"""
        commands = self._load_commands()
        config = self.get_config()

        defaults_config = config.get("defaults", {})

        # Use defaults if values are empty
        if not tool:
            tool = defaults_config.get("tool", "")
        if not tags:
            tags = defaults_config.get("tags", [])

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
        config = self.get_config()

        # Filter by tool or tag if specified
        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]
        if tag_filter:
            commands = [c for c in commands if tag_filter in c.get("tags", [])]

        if not commands:
            print(style_error("No commands found."))
            return None

        # Apply sorting based on config
        search_config = config.get("search", {})
        sort_by = search_config.get("sort_by", "used_count")
        sort_order = search_config.get("sort_order", "desc")

        if sort_by == "used_count":
            commands.sort(key=lambda x: x.get("used_count", 0), reverse=(sort_order == "desc"))
        elif sort_by == "created_at":
            commands.sort(key=lambda x: x.get("created_at", ""), reverse=(sort_order == "desc"))
        elif sort_by == "alphabetical":
            commands.sort(
                key=lambda x: x.get("command", "").lower(), reverse=(sort_order == "desc")
            )

        # Format commands for fzf
        fzf_input = format_commands_for_fzf(commands)

        # Run fzf with preview
        prompt = f"{Colors.BOLD}{Colors.CYAN}Search » {Colors.RESET}"

        # Check if fzf is enabled
        ui_config = config.get("ui", {})
        use_fzf = ui_config.get("use_fzf", True)

        if use_fzf:
            try:
                selected = run_fzf_search(fzf_input, self.store_file, prompt, config, preview=True)

                if selected is None:
                    # User cancelled fzf
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

            except FileNotFoundError:
                # FZF not found, fall through to fallback UI
                pass

        # Fallback UI
        selected_item = fallback_ui.select_item(commands, prompt_text="Search")
        if not selected_item:
            return None

        command = selected_item["command"]
        self._increment_usage(selected_item["id"])

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
        config = self.get_config()

        if not commands:
            print(style_error("No commands to delete."))
            return

        # Format commands for fzf (same format as search for preview compatibility)
        fzf_input = format_commands_for_fzf(commands)

        # Run fzf with multi-select and preview
        prompt = f"{Colors.BOLD}{Colors.RED}Delete (Tab to select multiple) » {Colors.RESET}"

        # Check if fzf is enabled
        ui_config = config.get("ui", {})
        use_fzf = ui_config.get("use_fzf", True)

        cmd_ids = []

        if use_fzf:
            try:
                selected_lines = run_fzf_multi_select_with_preview(
                    fzf_input, self.store_file, prompt, config, preview=True
                )

                if selected_lines is None:
                    # User cancelled or fzf failed (but not missing)
                    return

                if not selected_lines:
                    print(style_info("No commands selected. Deletion cancelled."))
                    return

                # Extract command IDs from selected lines
                for selected in selected_lines:
                    cmd_id = extract_command_id(selected)
                    if cmd_id:
                        cmd_ids.append(cmd_id)

                if not cmd_ids:
                    print(style_error("Could not parse command IDs from selection."))
                    return

            except FileNotFoundError:
                # FZF not found, fall through to fallback UI
                use_fzf = False

        if not use_fzf:
            # Fallback UI
            selected_items = fallback_ui.multi_select_items(
                commands, prompt_text="Select commands to delete"
            )
            if not selected_items:
                return

            cmd_ids = [item["id"] for item in selected_items]

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

        ui_config = config.get("ui", {})
        confirm_deletion = ui_config.get("confirm_deletion", True)

        if confirm_deletion:
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
        config = self.get_config()

        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]

        if not commands:
            print(style_error("No commands found."))
            return

        # Apply sorting based on config
        search_config = config.get("search", {})
        sort_by = search_config.get("sort_by", "used_count")
        sort_order = search_config.get("sort_order", "desc")

        if sort_by == "used_count":
            commands.sort(key=lambda x: x.get("used_count", 0), reverse=(sort_order == "desc"))
        elif sort_by == "created_at":
            commands.sort(key=lambda x: x.get("created_at", ""), reverse=(sort_order == "desc"))
        elif sort_by == "alphabetical":
            commands.sort(
                key=lambda x: x.get("command", "").lower(), reverse=(sort_order == "desc")
            )

        # Group by tool if enabled
        group_by_tool = search_config.get("group_by_tool", False)
        show_usage_count = search_config.get("show_usage_count", True)

        if group_by_tool:
            # Group commands by tool
            grouped = {}
            for cmd in commands:
                tool = cmd.get("tool", "general")
                if tool not in grouped:
                    grouped[tool] = []
                grouped[tool].append(cmd)

            for tool in sorted(grouped.keys()):
                print(f"\n{style_prompt(f'[{tool}]', Colors.BLUE)}")
                for cmd in grouped[tool]:
                    tags = ", ".join(cmd.get("tags", []))
                    desc = cmd.get("description", "")
                    used = cmd.get("used_count", 0)

                    print(f"  {cmd['command']}")
                    if desc:
                        print(f"    Description: {desc}")
                    if tags:
                        print(f"    Tags: {tags}")
                    if show_usage_count:
                        print(f"    Used: {used} times")
        else:
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
                if show_usage_count:
                    print(f"  Used: {used} times")

    def import_from_history(self, history_file=None, limit=None):
        """Import commands from shell history"""
        config = self.get_config()
        import_config = config.get("import", {})

        # Use config defaults if not provided
        if history_file is None:
            history_file = import_config.get("default_history_file", "~/.bash_history")
        if limit is None:
            limit = import_config.get("default_limit", 100)

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

        print(style_info("Select commands to import (use fzf):"))

        try:
            selected = run_fzf_multi_select(unique_commands, config)
            if selected is None:
                # User cancelled
                return
        except FileNotFoundError:
            # FZF not found, use fallback UI
            selected = fallback_ui.multi_select_items(
                unique_commands, prompt_text="Select commands to import"
            )
            if not selected:
                return

        # Get existing commands to check for duplicates
        existing_commands = self._load_commands()
        existing_command_texts = {c.get("command", "").strip() for c in existing_commands}

        defaults_config = config.get("defaults", {})
        description_template = defaults_config.get("description_template", "Imported from history")
        auto_add_tags = import_config.get("auto_add_tags", [])
        skip_duplicates = import_config.get("skip_duplicates", True)

        imported_count = 0
        skipped_count = 0

        for cmd in selected:
            cmd = cmd.strip()
            if cmd:
                if skip_duplicates and cmd in existing_command_texts:
                    skipped_count += 1
                    continue

                # Use auto_add_tags if configured
                tags = auto_add_tags.copy() if auto_add_tags else []
                self.add_command(cmd, description=description_template, tags=tags)
                imported_count += 1

        if skipped_count > 0:
            print(style_info(f"Skipped {skipped_count} duplicate command(s)."))
        print(style_success(f"✓ Imported {imported_count} commands"))
