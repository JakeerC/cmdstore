"""
cmdstore - A CLI tool to store and retrieve commands with fuzzy finding
"""

import argparse
import json
import os
import shlex
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pyperclip

GLOBAL_CONFIG_PATH = Path("~/.cmdstore_config.json").expanduser()
FZF_PREVIEW_WIDTH = "50%"
FZF_PREVIEW_DELIMITER = "■"


# ANSI color codes for terminal styling
class Colors:
    """ANSI escape codes for terminal colors and styles"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Text colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def _style_prompt(text: str, color: str = Colors.CYAN, bold: bool = True) -> str:
    """Style a prompt text with ANSI codes"""
    style = Colors.BOLD if bold else ""
    return f"{style}{color}{text}{Colors.RESET}"


def _style_success(text: str) -> str:
    """Style success messages"""
    return f"{Colors.BOLD}{Colors.GREEN}{text}{Colors.RESET}"


def _style_error(text: str) -> str:
    """Style error messages"""
    return f"{Colors.BOLD}{Colors.RED}{text}{Colors.RESET}"


def _style_info(text: str) -> str:
    """Style info messages"""
    return f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}"


class CommandStore:
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
        print(_style_success(f"✓ Command added: {command}"))
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
            print(_style_error("No commands found."))
            return None

        # Format commands for fzf
        # Include ID at the end for robust parsing (avoids issues with pipes in commands)
        fzf_input = []
        for cmd in commands:
            # Include ID at the end so preview script can find the command
            # Use a delimiter that's unlikely to appear in commands {FZF_PREVIEW_DELIMITER}
            line = f"{cmd['command']} {FZF_PREVIEW_DELIMITER} id: {cmd['id']}"
            fzf_input.append(line)

        # Create preview script that shows description and tags
        # fzf replaces {} with the selected line
        # We pass the store file path via environment variable to avoid escaping issues
        # Write to a temporary Python script to avoid quoting issues
        preview_script_content = f"""#!/usr/bin/env python3
import json
import sys
import os

try:
    store_path = os.environ.get('CMDSTORE_STORE_FILE')
    if not store_path or not os.path.exists(store_path):
        print('Error: Store file not found')
        sys.exit(1)

    with open(store_path) as f:
        commands = json.load(f)

    selected = sys.argv[1] if len(sys.argv) > 1 else ''
    if not selected:
        print('No selection')
        sys.exit(0)

    # Parse the selected line: format is "command {FZF_PREVIEW_DELIMITER} id: <id>"
    delimiter = '{FZF_PREVIEW_DELIMITER}'
    cmd_id = None

    delimiter_pattern = ' ' + delimiter + ' id: '
    if delimiter_pattern in selected:
        cmd_id = selected.split('id: ')[-1].strip()
    elif 'id: ' in selected:
        cmd_id = selected.split('id: ')[-1].strip()

    if not cmd_id:
        print('Error: Could not parse command ID')
        sys.exit(1)

    cmd = next((c for c in commands if c.get('id') == cmd_id), None)
    if not cmd:
        print('Error: Command not found')
        sys.exit(1)

    # Output formatted command details
    print('\\033[1m\\033[36mCommand:\\033[0m')
    print('  ' + cmd.get('command', ''))
    print()

    desc = cmd.get('description', '')
    if desc:
        print('\\033[1m\\033[33mDescription:\\033[0m')
        print('  ' + desc)
        print()

    tags = cmd.get('tags', [])
    if tags:
        print('\\033[1m\\033[35mTags:\\033[0m')
        print('  ' + ', '.join(tags))
        print()

    tool = cmd.get('tool', 'general')
    if tool:
        print('\\033[1m\\033[34mTool:\\033[0m')
        print('  ' + tool)
        print()

    print('\\033[1m\\033[37mUsed:\\033[0m')
    print('  ' + str(cmd.get('used_count', 0)) + ' times')

except Exception as e:
    print('Error: ' + str(e))
    sys.exit(1)
"""
        # Create temporary script file
        preview_script_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(preview_script_content)
                preview_script_path = f.name

            # Make it executable and create the preview command
            os.chmod(preview_script_path, 0o755)
            # Quote the script path, but leave {} unquoted so fzf can replace it
            preview_script = f"python3 {shlex.quote(preview_script_path)} {{}}"

            # Run fzf with preview window on the right side
            # Pass store file path via environment variable to avoid escaping issues
            env = os.environ.copy()
            env["CMDSTORE_STORE_FILE"] = str(self.store_file)
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    FZF_PREVIEW_WIDTH,
                    "--reverse",
                    "--preview",
                    preview_script,
                    "--preview-window",
                    f"right:{FZF_PREVIEW_WIDTH}:border-left",
                    "--border",
                    "--prompt",
                    f"{Colors.BOLD}{Colors.CYAN}Search » {Colors.RESET}",
                ],
                input="\n".join(fzf_input),
                text=True,
                capture_output=True,
                env=env,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()

                # Extract ID from the end (format: "command {FZF_PREVIEW_DELIMITER} id: {id}")
                # This approach is robust against commands containing pipe characters
                cmd_id = None
                if "id: " in selected:
                    cmd_id = selected.split("id: ")[-1].strip()

                if cmd_id:
                    self._increment_usage(cmd_id)
                    # Get the full command from store to ensure we have the complete command
                    # This is more reliable than parsing from the fzf output
                    commands = self._load_commands()
                    full_cmd = next((c for c in commands if c["id"] == cmd_id), None)
                    if full_cmd:
                        command = full_cmd["command"]
                    else:
                        # Fallback: if command not found, extract from selection
                        if f" {FZF_PREVIEW_DELIMITER} id: " in selected:
                            command = selected.rsplit(f" {FZF_PREVIEW_DELIMITER} id: ", 1)[
                                0
                            ].strip()
                        else:
                            command = selected
                else:
                    # Fallback: if no ID found, use the whole selection {FZF_PREVIEW_DELIMITER}
                    command = selected

                # Copy to clipboard
                pyperclip.copy(command)
                print(_style_success(f"✓ Copied to clipboard: {command}"))
                return command
        except FileNotFoundError:
            print(_style_error("Error: fzf not found. Please install fzf first."))
            return None
        finally:
            # Clean up temporary preview script file
            if preview_script_path:
                try:
                    if os.path.exists(preview_script_path):
                        os.unlink(preview_script_path)
                except Exception:
                    pass  # Ignore cleanup errors

    def _increment_usage(self, cmd_id):
        """Increment the usage count for a command"""
        commands = self._load_commands()
        for cmd in commands:
            if cmd["id"] == cmd_id:
                cmd["used_count"] = cmd.get("used_count", 0) + 1
                break
        self._save_commands(commands)

    def delete_command(self):
        """Delete a command using fzf selection"""
        commands = self._load_commands()

        if not commands:
            print(_style_error("No commands to delete."))
            return

        # Format commands for fzf
        fzf_input = []
        for cmd in commands:
            tags_str = ", ".join(cmd.get("tags", []))
            tool_str = f"[{cmd.get('tool', 'general')}]"
            line = f"{cmd['command']} | {tool_str} | tags: {tags_str} | id: {cmd['id']}"
            fzf_input.append(line)

        # Run fzf
        try:
            result = subprocess.run(
                [
                    "fzf",
                    "--height",
                    FZF_PREVIEW_WIDTH,
                    "--reverse",
                    "--prompt",
                    f"{Colors.BOLD}{Colors.RED}Delete » {Colors.RESET}",
                    "--border",
                ],
                input="\n".join(fzf_input),
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()
                cmd_id = selected.split("id: ")[-1].strip()
                cmd_to_delete = next((c for c in commands if c["id"] == cmd_id), None)
                if not cmd_to_delete:
                    print(_style_error("Selected command not found."))
                    return

                command = cmd_to_delete.get("command", "")
                description = cmd_to_delete.get("description", "")
                tags = ", ".join(cmd_to_delete.get("tags", []))
                tool = cmd_to_delete.get("tool", "general")

                print(f"\n{_style_info('Selected command for deletion:')}")
                print(f"  {_style_prompt('Command:', Colors.CYAN)} {command}")
                if description:
                    print(f"  {_style_prompt('Description:', Colors.YELLOW)} {description}")
                if tags:
                    print(f"  {_style_prompt('Tags:', Colors.MAGENTA)} {tags}")
                print(f"  {_style_prompt('Tool:', Colors.BLUE)} {tool}")

                prompt_text = _style_prompt("Delete this command? [Y/n]:", Colors.RED)
                confirmation = input(f"{prompt_text} ").strip().lower()
                if confirmation not in ("", "y", "yes"):
                    print(_style_info("Deletion cancelled."))
                    return

                # Remove command
                commands = [c for c in commands if c["id"] != cmd_id]
                self._save_commands(commands)
                print(_style_success("✓ Command deleted"))
        except FileNotFoundError:
            print("Error: fzf not found.")

    def list_commands(self, tool_filter=None):
        """List all commands"""
        commands = self._load_commands()

        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]

        if not commands:
            print(_style_error("No commands found."))
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
            print(_style_error(f"History file not found: {history_file}"))
            return

        with open(history_path, errors="ignore") as f:
            lines = f.readlines()

        # Get last N unique commands
        unique_commands = list(dict.fromkeys(lines[-limit:]))

        print(_style_info(f"Found {len(unique_commands)} unique commands from history."))
        print(_style_info("Select commands to import (use fzf):"))

        try:
            result = subprocess.run(
                ["fzf", "--multi", "--height", FZF_PREVIEW_WIDTH, "--reverse"],
                input="".join(unique_commands),
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip().split("\n")
                for cmd in selected:
                    cmd = cmd.strip()
                    if cmd:
                        self.add_command(cmd, description="Imported from history")
                print(_style_success(f"✓ Imported {len(selected)} commands"))
        except FileNotFoundError:
            print(_style_error("Error: fzf not found."))


def _load_global_store_path():
    """Load the globally configured default store path, if any."""
    if GLOBAL_CONFIG_PATH.exists():
        try:
            with open(GLOBAL_CONFIG_PATH) as f:
                cfg = json.load(f)
            store = cfg.get("store")
            if isinstance(store, str) and store.strip():
                return store
        except json.JSONDecodeError:
            return None
    return None


def _save_global_store_path(path: str):
    """Persistently set the global default store path."""
    GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_CONFIG_PATH, "w") as f:
        json.dump({"store": path}, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Command storage with fuzzy finding")
    parser.add_argument(
        "--store",
        default=None,
        help="Override store directory for this invocation",
    )
    parser.add_argument(
        "--set-store",
        dest="set_store",
        default=None,
        help="Persistently set the default store directory",
    )
    subparsers = parser.add_subparsers(dest="action", help="Commands")
    # Make subparsers optional - we'll handle --set-store case separately
    subparsers.required = False

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new command")
    add_parser.add_argument("cmd", nargs="?", help="The command to store")
    add_parser.add_argument("-d", "--description", default="", help="Command description")
    add_parser.add_argument("-t", "--tags", nargs="+", default=[], help="Tags for the command")
    add_parser.add_argument("--tool", default="", help="Tool category (npm, uv, node, etc.)")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search commands with fzf")
    search_parser.add_argument("--tool", help="Filter by tool")
    search_parser.add_argument("--tag", help="Filter by tag")

    # Delete command
    subparsers.add_parser("delete", help="Delete a command")

    # List commands
    list_parser = subparsers.add_parser("list", help="List all commands")
    list_parser.add_argument("--tool", help="Filter by tool")

    # Import from history
    import_parser = subparsers.add_parser("import", help="Import from shell history")
    import_parser.add_argument("--file", default="~/.bash_history", help="History file path")
    import_parser.add_argument("--limit", type=int, default=100, help="Number of recent commands")

    args = parser.parse_args()

    # Handle --set-store as a special case that doesn't require an action
    if args.set_store:
        _save_global_store_path(args.set_store)
        print(_style_success(f"✓ Default store path set to: {args.set_store}"))
        return  # Exit early after setting the store path

    # If no action provided and --set-store wasn't used, show error
    if not args.action:
        parser.error("the following arguments are required: action")

    # Determine effective store path
    effective_store = args.store or _load_global_store_path() or "~/.cmdstore"

    store = CommandStore(store_path=effective_store)

    if args.action == "add":
        command = args.cmd
        description = args.description
        tags = args.tags
        tool = args.tool

        if not command:
            print(_style_info("Enter command details (leave blank to skip optional fields):"))
            while True:
                command = input(f"{_style_prompt('Command:', Colors.CYAN)} ").strip()
                if command:
                    break
                print(_style_error("Command is required."))
            if not description:
                description = input(f"{_style_prompt('Description:', Colors.YELLOW)} ").strip()
            if not tags:
                prompt_text = _style_prompt("Tags (comma-separated):", Colors.MAGENTA)
                tags_input = input(f"{prompt_text} ").strip()
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if not tool:
                tool = input(f"{_style_prompt('Tool:', Colors.BLUE)} ").strip()

        store.add_command(command, description, tags, tool)
    elif args.action == "search":
        store.search_commands(tool_filter=args.tool, tag_filter=args.tag)
    elif args.action == "delete":
        store.delete_command()
    elif args.action == "list":
        store.list_commands(tool_filter=args.tool)
    elif args.action == "import":
        store.import_from_history(args.file, args.limit)


__all__ = ["CommandStore", "main"]
