"""Tests for fzf integration, line formatting, and subprocess outcomes."""

import subprocess
from pathlib import Path

import pytest

from cmdstore.errors import FzfError
from cmdstore.fzf_integration import (
    FZF_PREVIEW_DELIMITER,
    extract_command_from_selection,
    extract_command_id,
    format_commands_for_fzf,
    run_fzf_multi_select,
    run_fzf_multi_select_with_preview,
    run_fzf_search,
)


def test_format_commands_and_extract_handles_delimiter_content():
    """Commands containing delimiter-like text are formatted and parsed accurately."""
    expected_cmd1 = "docker run --label id: 9999 my-image:latest"
    expected_cmd2 = f"echo 'special symbol {FZF_PREVIEW_DELIMITER}'"
    commands = [
        {
            "id": "abc-123",
            "command": expected_cmd1,
        },
        {
            "id": "xyz-789",
            "command": expected_cmd2,
        },
    ]

    formatted = format_commands_for_fzf(commands)
    assert len(formatted) == 2

    # Check command 1
    assert extract_command_id(formatted[0]) == "abc-123"
    assert extract_command_from_selection(formatted[0]) == expected_cmd1

    # Check command 2
    assert extract_command_id(formatted[1]) == "xyz-789"
    assert extract_command_from_selection(formatted[1]) == expected_cmd2


def test_multi_select_joins_input_with_newlines(monkeypatch):
    """Multi-select passes items joined by newline, not empty string."""
    received_input = None

    def mock_run(cmd, input, text, capture_output, **kwargs):
        nonlocal received_input
        received_input = input
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="alpha\n")

    monkeypatch.setattr(subprocess, "run", mock_run)

    items = ["alpha", "beta", "gamma"]
    result = run_fzf_multi_select(items, config={})

    assert received_input == "alpha\nbeta\ngamma"
    assert received_input != "alphabetagamma"
    assert result == ["alpha"]


def test_multi_select_empty_selection_returns_empty_list(monkeypatch):
    """When fzf exits 0 with empty stdout, multi_select returns an empty list."""

    def mock_run(cmd, input, text, capture_output, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = run_fzf_multi_select(["item1", "item2"], config={})
    assert result == []


def test_multi_select_cancellation_returns_none(monkeypatch):
    """When fzf exits with 1 (no match) or 130 (interrupted), None is returned."""

    def mock_run_1(cmd, input, text, capture_output, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run_1)
    assert run_fzf_multi_select(["item1"], config={}) is None

    def mock_run_130(cmd, input, text, capture_output, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=130, stdout="")

    monkeypatch.setattr(subprocess, "run", mock_run_130)
    assert run_fzf_multi_select(["item1"], config={}) is None


def test_multi_select_unexpected_error_code_raises_fzf_error(monkeypatch):
    """When fzf exits with an error code like 2, FzfError is raised."""

    def mock_run_2(cmd, input, text, capture_output, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd, returncode=2, stdout="", stderr="fzf: syntax error"
        )

    monkeypatch.setattr(subprocess, "run", mock_run_2)

    with pytest.raises(FzfError) as exc_info:
        run_fzf_multi_select(["item1"], config={})

    assert exc_info.value.returncode == 2
    assert "fzf: syntax error" in str(exc_info.value)


def test_missing_fzf_binary_raises_file_not_found(monkeypatch):
    """When fzf binary is missing, FileNotFoundError is propagated for fallback handling."""

    def mock_missing_run(*args, **kwargs):
        raise FileNotFoundError("fzf: No such file or directory")

    monkeypatch.setattr(subprocess, "run", mock_missing_run)

    with pytest.raises(FileNotFoundError):
        run_fzf_multi_select(["item1"], config={})


def test_search_and_preview_cleans_up_preview_script(tmp_path: Path, monkeypatch):
    """The temporary preview script is always cleaned up in finally block."""
    temp_scripts_created = []

    def mock_run_failing(cmd, **kwargs):
        # Locate preview script from command args
        for arg in cmd:
            if "python3" in arg:
                # Find script name
                parts = arg.split()
                for p in parts:
                    if p.endswith(".py"):
                        temp_scripts_created.append(Path(p))
        raise RuntimeError("Subprocess execution crash")

    monkeypatch.setattr(subprocess, "run", mock_run_failing)

    store_file = tmp_path / "commands.json"
    store_file.write_text("[]", encoding="utf-8")

    with pytest.raises(RuntimeError):
        run_fzf_search(["item1"], store_file=store_file, prompt="> ", config={}, preview=True)

    assert len(temp_scripts_created) == 1
    # Check that the script file was deleted by the finally block
    assert not temp_scripts_created[0].exists()


def test_multi_select_with_preview_stdout_splitlines(tmp_path: Path, monkeypatch):
    """run_fzf_multi_select_with_preview uses splitlines and preserves formatting."""

    def mock_run_success(cmd, input, text, capture_output, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="line1\nline2\n"
        )

    monkeypatch.setattr(subprocess, "run", mock_run_success)

    store_file = tmp_path / "commands.json"
    store_file.write_text("[]", encoding="utf-8")

    result = run_fzf_multi_select_with_preview(
        ["line1", "line2"], store_file=store_file, prompt="> ", config={}, preview=False
    )
    assert result == ["line1", "line2"]
