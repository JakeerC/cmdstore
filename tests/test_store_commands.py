"""Tests for command CRUD, filtering, sorting, usage increment, and auto-copy."""

from cmdstore.store import CommandStore


def test_add_command_persists_and_sets_fields(store: CommandStore):
    """Adding a command persists it to commands.json with all expected fields."""
    cmd = store.add_command(
        command="git status",
        description="Check git working tree",
        tags=["git", "vcs"],
        tool="git",
    )

    assert cmd["command"] == "git status"
    assert cmd["description"] == "Check git working tree"
    assert cmd["tags"] == ["git", "vcs"]
    assert cmd["tool"] == "git"
    assert cmd["used_count"] == 0
    assert "id" in cmd
    assert "created_at" in cmd

    loaded = store._load_commands()
    assert len(loaded) == 1
    assert loaded[0]["id"] == cmd["id"]


def test_add_command_uses_config_defaults(store: CommandStore):
    """Adding a command without tool/tags uses configured defaults."""
    cfg = store.get_config()
    cfg["defaults"]["tool"] = "default_tool"
    cfg["defaults"]["tags"] = ["default_tag"]
    store._save_config(cfg)

    cmd = store.add_command(command="npm test")
    assert cmd["tool"] == "default_tool"
    assert cmd["tags"] == ["default_tag"]


def test_list_commands_and_filtering(store: CommandStore, capsys):
    """List commands displays items and filters by tool."""
    store.add_command("npm install", tool="npm")
    store.add_command("git pull", tool="git")

    capsys.readouterr()  # clear buffer
    store.list_commands()
    out = capsys.readouterr().out
    assert "npm install" in out
    assert "git pull" in out

    store.list_commands(tool_filter="git")
    out = capsys.readouterr().out
    assert "git pull" in out
    assert "npm install" not in out


def test_list_commands_sorting(store: CommandStore, capsys):
    """List commands respects sort_by configuration."""
    cfg = store.get_config()
    cfg["search"]["sort_by"] = "alphabetical"
    cfg["search"]["sort_order"] = "asc"
    store._save_config(cfg)

    store.add_command("zebra")
    store.add_command("alpha")

    capsys.readouterr()
    store.list_commands()
    out = capsys.readouterr().out
    assert out.index("alpha") < out.index("zebra")


def test_list_commands_group_by_tool(store: CommandStore, capsys):
    """List commands supports group_by_tool."""
    cfg = store.get_config()
    cfg["search"]["group_by_tool"] = True
    store._save_config(cfg)

    store.add_command("git diff", tool="git")
    store.add_command("docker ps", tool="docker")

    capsys.readouterr()
    store.list_commands()
    out = capsys.readouterr().out
    assert "[docker]" in out
    assert "[git]" in out


def test_search_commands_with_fzf_increments_usage_and_copies(
    store: CommandStore, monkeypatch, mock_clipboard
):
    """Search with fzf increments usage count and copies command to clipboard."""
    cmd = store.add_command("python -m unittest")

    # Mock run_fzf_search to return the formatted line
    line = f"{cmd['command']} ║ id: {cmd['id']}"
    monkeypatch.setattr("cmdstore.store.run_fzf_search", lambda *args, **kwargs: line)

    result = store.search_commands()
    assert result == "python -m unittest"
    assert mock_clipboard.copied == ["python -m unittest"]

    loaded = store._load_commands()
    assert loaded[0]["used_count"] == 1


def test_search_commands_auto_copy_disabled(
    store: CommandStore, monkeypatch, mock_clipboard, capsys
):
    """Search does not copy or notify when auto_copy is disabled."""
    cfg = store.get_config()
    cfg["auto_copy"]["enabled"] = False
    store._save_config(cfg)

    cmd = store.add_command("echo hello")
    line = f"{cmd['command']} ║ id: {cmd['id']}"
    monkeypatch.setattr("cmdstore.store.run_fzf_search", lambda *args, **kwargs: line)

    capsys.readouterr()
    result = store.search_commands()
    out = capsys.readouterr().out

    assert result == "echo hello"
    assert mock_clipboard.copied == []
    assert "Copied to clipboard" not in out

    # Usage must still be incremented
    loaded = store._load_commands()
    assert loaded[0]["used_count"] == 1


def test_search_commands_notification_disabled(
    store: CommandStore, monkeypatch, mock_clipboard, capsys
):
    """Search copies to clipboard but suppresses notification when show_notification is False."""
    cfg = store.get_config()
    cfg["auto_copy"]["enabled"] = True
    cfg["auto_copy"]["show_notification"] = False
    store._save_config(cfg)

    cmd = store.add_command("echo test")
    line = f"{cmd['command']} ║ id: {cmd['id']}"
    monkeypatch.setattr("cmdstore.store.run_fzf_search", lambda *args, **kwargs: line)

    capsys.readouterr()
    result = store.search_commands()
    out = capsys.readouterr().out

    assert result == "echo test"
    assert mock_clipboard.copied == ["echo test"]
    assert "Copied to clipboard" not in out


def test_search_commands_clipboard_failure_does_not_discard_command(
    store: CommandStore, monkeypatch, capsys
):
    """If clipboard copy fails, command is still returned and usage incremented."""
    cmd = store.add_command("pytest -q")
    line = f"{cmd['command']} ║ id: {cmd['id']}"
    monkeypatch.setattr("cmdstore.store.run_fzf_search", lambda *args, **kwargs: line)

    def failing_copy(text):
        raise RuntimeError("Pyperclip could not find a copy/paste mechanism")

    monkeypatch.setattr("cmdstore.store.pyperclip.copy", failing_copy)

    capsys.readouterr()
    result = store.search_commands()
    out = capsys.readouterr().out

    assert result == "pytest -q"
    assert "Clipboard unavailable" in out
    assert "pytest -q" in out

    loaded = store._load_commands()
    assert loaded[0]["used_count"] == 1


def test_search_commands_fallback_ui(store: CommandStore, monkeypatch, mock_clipboard):
    """When fzf is missing or disabled, fallback UI is used."""
    store.add_command("ls -la")

    cfg = store.get_config()
    cfg["ui"]["use_fzf"] = False
    store._save_config(cfg)

    monkeypatch.setattr(
        "cmdstore.fallback_ui.select_item",
        lambda items, prompt_text="Search": items[0],
    )

    result = store.search_commands()
    assert result == "ls -la"
    assert mock_clipboard.copied == ["ls -la"]

    loaded = store._load_commands()
    assert loaded[0]["used_count"] == 1


def test_delete_command_with_confirmation(store: CommandStore, monkeypatch):
    """Deleting a command removes it from store when user confirms."""
    cmd1 = store.add_command("cmd 1")
    cmd2 = store.add_command("cmd 2")

    line = f"{cmd1['command']} ║ id: {cmd1['id']}"
    monkeypatch.setattr(
        "cmdstore.store.run_fzf_multi_select_with_preview",
        lambda *args, **kwargs: [line],
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    store.delete_command()

    remaining = store._load_commands()
    assert len(remaining) == 1
    assert remaining[0]["id"] == cmd2["id"]


def test_delete_command_cancelled_by_user(store: CommandStore, monkeypatch):
    """Cancelling delete confirmation preserves all commands."""
    cmd = store.add_command("cmd to keep")
    line = f"{cmd['command']} ║ id: {cmd['id']}"
    monkeypatch.setattr(
        "cmdstore.store.run_fzf_multi_select_with_preview",
        lambda *args, **kwargs: [line],
    )
    monkeypatch.setattr("builtins.input", lambda prompt: "n")

    store.delete_command()

    remaining = store._load_commands()
    assert len(remaining) == 1
    assert remaining[0]["id"] == cmd["id"]
