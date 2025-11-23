"""Command-line interface for cmdstore."""

import argparse
from importlib.metadata import PackageNotFoundError, version

from cmdstore.colors import Colors, style_error, style_info, style_prompt, style_success
from cmdstore.config import load_global_store_path, save_global_store_path
from cmdstore.store import CommandStore

try:
    __version__ = version("cmdstore")
except PackageNotFoundError:
    # Fallback to __init__.py version if package not installed
    try:
        from cmdstore import __version__
    except ImportError:
        __version__ = "unknown"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Command storage with fuzzy finding")
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )
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
    import_parser.add_argument(
        "--file", default=None, help="History file path (defaults to config or ~/.bash_history)"
    )
    import_parser.add_argument(
        "--limit", type=int, default=None, help="Number of recent commands (defaults to config or 100)"
    )

    args = parser.parse_args()

    # Handle --set-store as a special case that doesn't require an action
    if args.set_store:
        save_global_store_path(args.set_store)
        print(style_success(f"✓ Default store path set to: {args.set_store}"))
        return  # Exit early after setting the store path

    # If no action provided and --set-store wasn't used, show error
    if not args.action:
        parser.error("the following arguments are required: action")

    # Determine effective store path
    effective_store = args.store or load_global_store_path() or "~/.cmdstore"

    store = CommandStore(store_path=effective_store)

    if args.action == "add":
        command = args.cmd
        description = args.description
        tags = args.tags
        tool = args.tool

        if not command:
            print(style_info("Enter command details (leave blank to skip optional fields):"))
            while True:
                command = input(f"{style_prompt('Command:', Colors.CYAN)} ").strip()
                if command:
                    break
                print(style_error("Command is required."))
            if not description:
                description = input(f"{style_prompt('Description:', Colors.YELLOW)} ").strip()
            if not tags:
                prompt_text = style_prompt("Tags (comma-separated):", Colors.MAGENTA)
                tags_input = input(f"{prompt_text} ").strip()
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if not tool:
                tool = input(f"{style_prompt('Tool:', Colors.BLUE)} ").strip()

        store.add_command(command, description, tags, tool)
    elif args.action == "search":
        store.search_commands(tool_filter=args.tool, tag_filter=args.tag)
    elif args.action == "delete":
        store.delete_command()
    elif args.action == "list":
        store.list_commands(tool_filter=args.tool)
    elif args.action == "import":
        # Pass None to use config defaults, or use provided values
        store.import_from_history(args.file, args.limit)
