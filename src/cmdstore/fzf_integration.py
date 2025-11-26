"""FZF integration utilities for command selection and preview."""

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

FZF_PREVIEW_DELIMITER = "║"  # ║ , ■ , ¤ , █


def generate_preview_script(config: dict) -> str:
    """Generate the Python script content for fzf preview."""
    preview_config = config.get("preview", {})
    show_command = preview_config.get("show_command", True)
    show_description = preview_config.get("show_description", True)
    show_tags = preview_config.get("show_tags", True)
    show_tool = preview_config.get("show_tool", True)
    show_usage_count = preview_config.get("show_usage_count", True)
    show_created_at = preview_config.get("show_created_at", False)

    script_lines = [
        "#!/usr/bin/env python3",
        "import json",
        "import sys",
        "import os",
        "",
        "try:",
        "    store_path = os.environ.get('CMDSTORE_STORE_FILE')",
        "    if not store_path or not os.path.exists(store_path):",
        "        print('Error: Store file not found')",
        "        sys.exit(1)",
        "",
        "    with open(store_path) as f:",
        "        commands = json.load(f)",
        "",
        "    selected = sys.argv[1] if len(sys.argv) > 1 else ''",
        "    if not selected:",
        "        print('No selection')",
        "        sys.exit(0)",
        "",
        f'    # Parse the selected line: format is "command {FZF_PREVIEW_DELIMITER} id: <id>"',
        f"    delimiter = '{FZF_PREVIEW_DELIMITER}'",
        "    cmd_id = None",
        "",
        "    delimiter_pattern = ' ' + delimiter + ' id: '",
        "    if delimiter_pattern in selected:",
        "        cmd_id = selected.split('id: ')[-1].strip()",
        "    elif 'id: ' in selected:",
        "        cmd_id = selected.split('id: ')[-1].strip()",
        "",
        "    if not cmd_id:",
        "        print('Error: Could not parse command ID')",
        "        sys.exit(1)",
        "",
        "    cmd = next((c for c in commands if c.get('id') == cmd_id), None)",
        "    if not cmd:",
        "        print('Error: Command not found')",
        "        sys.exit(1)",
        "",
        "    # Output formatted command details based on config",
    ]

    if show_command:
        script_lines.extend(
            [
                "    print('\\033[1m\\033[36mCommand:\\033[0m')",
                "    print('  ' + cmd.get('command', ''))",
                "    print()",
            ]
        )

    if show_description:
        script_lines.extend(
            [
                "    desc = cmd.get('description', '')",
                "    if desc:",
                "        print('\\033[1m\\033[33mDescription:\\033[0m')",
                "        print('  ' + desc)",
                "        print()",
            ]
        )

    if show_tags:
        script_lines.extend(
            [
                "    tags = cmd.get('tags', [])",
                "    if tags:",
                "        print('\\033[1m\\033[35mTags:\\033[0m')",
                "        print('  ' + ', '.join(tags))",
                "        print()",
            ]
        )

    if show_tool:
        script_lines.extend(
            [
                "    tool = cmd.get('tool', 'general')",
                "    if tool:",
                "        print('\\033[1m\\033[34mTool:\\033[0m')",
                "        print('  ' + tool)",
                "        print()",
            ]
        )

    if show_usage_count:
        script_lines.extend(
            [
                "    print('\\033[1m\\033[37mUsed:\\033[0m')",
                "    print('  ' + str(cmd.get('used_count', 0)) + ' times')",
            ]
        )

    if show_created_at:
        script_lines.extend(
            [
                "    created_at = cmd.get('created_at', '')",
                "    if created_at:",
                "        print('\\033[1m\\033[37mCreated:\\033[0m')",
                "        print('  ' + created_at)",
            ]
        )

    script_lines.extend(
        [
            "",
            "except Exception as e:",
            "    print('Error: ' + str(e))",
            "    sys.exit(1)",
        ]
    )

    return "\n".join(script_lines)


def create_preview_script(config: dict) -> str:
    """Create a temporary preview script file and return its path."""
    preview_script_content = generate_preview_script(config)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(preview_script_content)
        preview_script_path = f.name

    # Make it executable
    os.chmod(preview_script_path, 0o755)
    return preview_script_path


def format_commands_for_fzf(commands: list) -> list[str]:
    """Format commands for fzf input with delimiter and ID."""
    fzf_input = []
    for cmd in commands:
        # Include ID at the end so preview script can find the command
        # Use a delimiter that's unlikely to appear in commands
        line = f"{cmd['command']} {FZF_PREVIEW_DELIMITER} id: {cmd['id']}"
        fzf_input.append(line)
    return fzf_input


def run_fzf_search(
    fzf_input: list[str],
    store_file: Path,
    prompt: str,
    config: dict,
    preview: bool = True,
) -> str | None:
    """Run fzf with the given input and return the selected line."""
    preview_script_path = None
    try:
        fzf_config = config.get("fzf", {})
        preview_width = fzf_config.get("preview_width", "50%")
        height = fzf_config.get("height", "50%")

        if preview:
            preview_script_path = create_preview_script(config)
            preview_script = f"python3 {shlex.quote(preview_script_path)} {{}}"
        else:
            preview_script = None

        # Prepare fzf command
        fzf_cmd = [
            "fzf",
            "--height",
            height,
            "--reverse",
            "--border",
            "--prompt",
            prompt,
        ]

        if preview and preview_script:
            fzf_cmd.extend(
                [
                    "--preview",
                    preview_script,
                    "--preview-window",
                    f"right:{preview_width}:border-left",
                ]
            )

        # Pass store file path via environment variable
        env = os.environ.copy()
        env["CMDSTORE_STORE_FILE"] = str(store_file)

        result = subprocess.run(
            fzf_cmd,
            input="\n".join(fzf_input),
            text=True,
            capture_output=True,
            env=env,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None
    finally:
        # Clean up temporary preview script file
        if preview_script_path:
            try:
                if os.path.exists(preview_script_path):
                    os.unlink(preview_script_path)
            except Exception:
                pass  # Ignore cleanup errors


def run_fzf_multi_select(fzf_input: list[str], config: dict) -> list[str] | None:
    """Run fzf with multi-select and return selected lines."""
    fzf_config = config.get("fzf", {})
    height = fzf_config.get("height", "50%")

    result = subprocess.run(
        ["fzf", "--multi", "--height", height, "--reverse"],
        input="".join(fzf_input),
        text=True,
        capture_output=True,
    )

    if result.returncode == 0:
        return result.stdout.strip().split("\n")
    return None


def run_fzf_multi_select_with_preview(
    fzf_input: list[str],
    store_file: Path,
    prompt: str,
    config: dict,
    preview: bool = True,
) -> list[str] | None:
    """Run fzf with multi-select and preview, returning selected lines."""
    preview_script_path = None
    try:
        fzf_config = config.get("fzf", {})
        preview_width = fzf_config.get("preview_width", "50%")
        height = fzf_config.get("height", "50%")

        if preview:
            preview_script_path = create_preview_script(config)
            preview_script = f"python3 {shlex.quote(preview_script_path)} {{}}"
        else:
            preview_script = None

        # Prepare fzf command with multi-select
        fzf_cmd = [
            "fzf",
            "--multi",
            "--height",
            height,
            "--reverse",
            "--border",
            "--prompt",
            prompt,
        ]

        if preview and preview_script:
            fzf_cmd.extend(
                [
                    "--preview",
                    preview_script,
                    "--preview-window",
                    f"right:{preview_width}:border-left",
                ]
            )

        # Pass store file path via environment variable
        env = os.environ.copy()
        env["CMDSTORE_STORE_FILE"] = str(store_file)

        result = subprocess.run(
            fzf_cmd,
            input="\n".join(fzf_input),
            text=True,
            capture_output=True,
            env=env,
        )

        if result.returncode == 0:
            selected_lines = result.stdout.strip()
            if selected_lines:
                return selected_lines.split("\n")
            return []
        return None

    finally:
        # Clean up temporary preview script file
        if preview_script_path:
            try:
                if os.path.exists(preview_script_path):
                    os.unlink(preview_script_path)
            except Exception:
                pass  # Ignore cleanup errors


def extract_command_id(selected_line: str) -> str | None:
    """Extract command ID from fzf selected line."""
    if "id: " in selected_line:
        return selected_line.split("id: ")[-1].strip()
    return None


def extract_command_from_selection(selected_line: str) -> str:
    """Extract command text from fzf selected line."""
    if f" {FZF_PREVIEW_DELIMITER} id: " in selected_line:
        return selected_line.rsplit(f" {FZF_PREVIEW_DELIMITER} id: ", 1)[0].strip()
    return selected_line
