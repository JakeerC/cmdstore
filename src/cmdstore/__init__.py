"""
cmdstore - A CLI tool to store and retrieve commands with fuzzy finding
"""

import argparse
import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import pyperclip

GLOBAL_CONFIG_PATH = Path("~/.cmdstore_config.json").expanduser()


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
        print(f"✓ Command added: {command}")
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
            print("No commands found.")
            return None

        # Format commands for fzf
        fzf_input = []
        for cmd in commands:
            tags_str = ", ".join(cmd.get("tags", []))
            tool_str = f"[{cmd.get('tool', 'general')}]"
            desc = cmd.get("description", "")
            line = f"{cmd['command']} | {tool_str} {desc} | tags: {tags_str} | id: {cmd['id']}"
            fzf_input.append(line)

        # Run fzf
        try:
            result = subprocess.run(
                ["fzf", "--height", "40%", "--reverse", "--preview", "echo {1}"],
                input="\n".join(fzf_input),
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()
                # Extract command (before first |)
                command = selected.split("|")[0].strip()

                # Extract ID and increment usage count
                cmd_id = selected.split("id: ")[-1].strip()
                self._increment_usage(cmd_id)

                # Copy to clipboard
                pyperclip.copy(command)
                print(f"✓ Copied to clipboard: {command}")
                return command
        except FileNotFoundError:
            print("Error: fzf not found. Please install fzf first.")
            return None

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
            print("No commands to delete.")
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
                ["fzf", "--height", "40%", "--reverse", "--prompt", "Delete > "],
                input="\n".join(fzf_input),
                text=True,
                capture_output=True,
            )

            if result.returncode == 0:
                selected = result.stdout.strip()
                cmd_id = selected.split("id: ")[-1].strip()
                cmd_to_delete = next((c for c in commands if c["id"] == cmd_id), None)
                if not cmd_to_delete:
                    print("Selected command not found.")
                    return

                command = cmd_to_delete.get("command", "")
                description = cmd_to_delete.get("description", "")
                tags = ", ".join(cmd_to_delete.get("tags", []))
                tool = cmd_to_delete.get("tool", "general")

                print("\nSelected command for deletion:")
                print(f"  Command: {command}")
                if description:
                    print(f"  Description: {description}")
                if tags:
                    print(f"  Tags: {tags}")
                print(f"  Tool: {tool}")

                confirmation = input("Delete this command? [Y/n]: ").strip().lower()
                if confirmation not in ("", "y", "yes"):
                    print("Deletion cancelled.")
                    return

                # Remove command
                commands = [c for c in commands if c["id"] != cmd_id]
                self._save_commands(commands)
                print("✓ Command deleted")
        except FileNotFoundError:
            print("Error: fzf not found.")

    def list_commands(self, tool_filter=None):
        """List all commands"""
        commands = self._load_commands()

        if tool_filter:
            commands = [c for c in commands if c.get("tool") == tool_filter]

        if not commands:
            print("No commands found.")
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
            print(f"History file not found: {history_file}")
            return

        with open(history_path, errors="ignore") as f:
            lines = f.readlines()

        # Get last N unique commands
        unique_commands = list(dict.fromkeys(lines[-limit:]))

        print(f"Found {len(unique_commands)} unique commands from history.")
        print("Select commands to import (use fzf):")

        try:
            result = subprocess.run(
                ["fzf", "--multi", "--height", "40%", "--reverse"],
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
                print(f"✓ Imported {len(selected)} commands")
        except FileNotFoundError:
            print("Error: fzf not found.")


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
        print(f"✓ Default store path set to: {args.set_store}")
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
            print("Enter command details (leave blank to skip optional fields):")
            while True:
                command = input("Command: ").strip()
                if command:
                    break
                print("Command is required.")
            if not description:
                description = input("Description: ").strip()
            if not tags:
                tags_input = input("Tags (comma-separated): ").strip()
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if not tool:
                tool = input("Tool: ").strip()

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
