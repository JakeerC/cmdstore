"""Tests for history import functionality."""

from pathlib import Path

from cmdstore.store import CommandStore


def test_import_from_history_basic(store: CommandStore, tmp_path: Path, monkeypatch, capsys):
    """Import reads commands, prompts via fzf, and stores new commands."""
    history_file = tmp_path / ".bash_history"
    history_file.write_text("git status\nls -la\npytest\n", encoding="utf-8")

    # Mock fzf multi-select to return selected items
    monkeypatch.setattr(
        "cmdstore.store.run_fzf_multi_select",
        lambda lines, config: ["git status", "pytest"],
    )

    capsys.readouterr()
    store.import_from_history(history_file=str(history_file))
    out = capsys.readouterr().out

    assert "✓ Imported 2 commands" in out
    # Verify no duplicate prompt
    assert out.count("Select commands to import (use fzf):") == 1

    loaded = store._load_commands()
    assert len(loaded) == 2
    commands = [c["command"] for c in loaded]
    assert "git status" in commands
    assert "pytest" in commands


def test_import_removes_exact_duplicates_and_skips_existing(
    store: CommandStore, tmp_path: Path, monkeypatch, capsys
):
    """Import ignores exact duplicates in history and skips existing store commands."""
    store.add_command("git pull")  # Existing command

    history_file = tmp_path / ".bash_history"
    # File has duplicate "git status" and existing "git pull"
    history_file.write_text(
        "git status\ngit status\ngit pull\nnpm test\n", encoding="utf-8"
    )

    # In fzf multi-select, user selects all unique items passed
    received_candidates = []

    def mock_fzf(candidates, config):
        received_candidates.extend(candidates)
        return candidates

    monkeypatch.setattr("cmdstore.store.run_fzf_multi_select", mock_fzf)

    capsys.readouterr()
    store.import_from_history(history_file=str(history_file))
    out = capsys.readouterr().out

    # Unique candidates fed to fzf should have only one "git status\n"
    assert len([c for c in received_candidates if c.strip() == "git status"]) == 1

    # git pull was skipped because it already existed in store
    assert "Skipped 1 duplicate command(s)." in out
    assert "✓ Imported 2 commands" in out  # git status and npm test


def test_import_auto_add_tags_and_description(
    store: CommandStore, tmp_path: Path, monkeypatch
):
    """Import applies auto_add_tags and description_template."""
    cfg = store.get_config()
    cfg["import"]["auto_add_tags"] = ["imported", "shell"]
    cfg["defaults"]["description_template"] = "From zsh history"
    store._save_config(cfg)

    history_file = tmp_path / ".zsh_history"
    history_file.write_text("cargo build\n", encoding="utf-8")

    monkeypatch.setattr(
        "cmdstore.store.run_fzf_multi_select",
        lambda lines, config: ["cargo build"],
    )

    store.import_from_history(history_file=str(history_file))

    loaded = store._load_commands()
    assert len(loaded) == 1
    assert loaded[0]["command"] == "cargo build"
    assert loaded[0]["tags"] == ["imported", "shell"]
    assert loaded[0]["description"] == "From zsh history"


def test_import_cancelled(store: CommandStore, tmp_path: Path, monkeypatch, capsys):
    """User cancelling fzf selection imports nothing."""
    history_file = tmp_path / ".history"
    history_file.write_text("echo hi\n", encoding="utf-8")

    monkeypatch.setattr("cmdstore.store.run_fzf_multi_select", lambda lines, config: None)

    capsys.readouterr()
    store.import_from_history(history_file=str(history_file))

    loaded = store._load_commands()
    assert len(loaded) == 0


def test_import_missing_history_file(store: CommandStore, capsys):
    """Non-existent history file reports error and exits cleanly."""
    capsys.readouterr()
    store.import_from_history(history_file="/nonexistent/history/path.txt")
    out = capsys.readouterr().out
    assert "History file not found" in out
