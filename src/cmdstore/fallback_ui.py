"""Fallback UI for command selection when fzf is not available."""

from cmdstore.colors import Colors, style_error, style_info, style_prompt


def print_item_list(items: list, show_details: bool = True):
    """Print a numbered list of items."""
    for idx, item in enumerate(items, 1):
        if isinstance(item, dict):
            command = item.get("command", "")
            description = item.get("description", "")
            tags = ", ".join(item.get("tags", []))
            tool = item.get("tool", "")

            print(f"{Colors.BOLD}{idx}. {command}{Colors.RESET}")
            if show_details:
                if description:
                    print(f"   {Colors.YELLOW}Description:{Colors.RESET} {description}")
                if tags:
                    print(f"   {Colors.MAGENTA}Tags:{Colors.RESET} {tags}")
                if tool:
                    print(f"   {Colors.BLUE}Tool:{Colors.RESET} {tool}")
            print()
        else:
            # Simple string item (e.g. for history import)
            print(f"{Colors.BOLD}{idx}. {item}{Colors.RESET}")


def select_item(items: list, prompt_text: str = "Select item") -> dict | str | None:
    """
    Interactive selection fallback.
    Returns the selected item (dict or string) or None if cancelled.
    """
    if not items:
        print(style_info("No items to select."))
        return None

    print(style_info("\nFZF not found. Using fallback selection mode.\n"))
    print_item_list(items)

    while True:
        try:
            selection = input(
                f"{style_prompt(f'{prompt_text} (1-{len(items)}, q to quit):', Colors.CYAN)} "
            ).strip()

            if selection.lower() in ("q", "quit", "exit"):
                return None

            if not selection:
                continue

            try:
                idx = int(selection)
                if 1 <= idx <= len(items):
                    return items[idx - 1]
                else:
                    print(style_error(f"Please enter a number between 1 and {len(items)}"))
            except ValueError:
                print(style_error("Invalid input. Please enter a number."))

        except KeyboardInterrupt:
            print()
            return None


def multi_select_items(items: list, prompt_text: str = "Select items") -> list | None:
    """
    Interactive multi-selection fallback.
    Returns list of selected items or None if cancelled.
    """
    if not items:
        print(style_info("No items to select."))
        return None

    print(style_info("\nFZF not found. Using fallback selection mode.\n"))
    print_item_list(items)

    print(style_info("Enter comma-separated numbers (e.g. 1, 3, 5) or 'all'"))

    while True:
        try:
            selection = input(
                f"{style_prompt(f'{prompt_text} (q to quit):', Colors.CYAN)} "
            ).strip()

            if selection.lower() in ("q", "quit", "exit"):
                return None

            if not selection:
                continue

            if selection.lower() == "all":
                return items

            selected_items = []
            parts = selection.split(",")
            valid = True

            for part in parts:
                part = part.strip()
                if not part:
                    continue
                try:
                    idx = int(part)
                    if 1 <= idx <= len(items):
                        selected_items.append(items[idx - 1])
                    else:
                        print(style_error(f"Number {idx} is out of range (1-{len(items)})"))
                        valid = False
                        break
                except ValueError:
                    print(style_error(f"Invalid input '{part}'. Please enter numbers."))
                    valid = False
                    break

            if valid and selected_items:
                return selected_items
            if valid and not selected_items:
                print(style_error("No valid items selected."))

        except KeyboardInterrupt:
            print()
            return None
