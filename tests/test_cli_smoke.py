"""CLI smoke tests using isolated temporary stores."""

import sys
from pathlib import Path

import pytest

from cmdstore.cli import main


def test_cli_help(capsys):
    """cmdstore --help exits with code 0 and shows usage."""
    with pytest.raises(SystemExit) as exc_info:
        sys_argv = ["cmdstore", "--help"]
        sys.argv = sys_argv
        main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "usage: cmdstore" in out
    assert "Command storage with fuzzy finding" in out


def test_cli_version(capsys):
    """cmdstore --version exits with code 0 and prints version."""
    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["cmdstore", "--version"]
        main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert "cmdstore" in out


def test_cli_add_and_list_smoke(tmp_path: Path, capsys):
    """Smoke test: add a command and list it using --store override."""
    test_store = str(tmp_path / "smoke_store")

    # Add command
    sys.argv = [
        "cmdstore",
        "--store",
        test_store,
        "add",
        "git log --oneline",
        "-d",
        "Compact git log",
        "-t",
        "git",
        "vcs",
        "--tool",
        "git",
    ]
    main()
    out = capsys.readouterr().out
    assert "Command added: git log --oneline" in out

    # List all commands
    sys.argv = ["cmdstore", "--store", test_store, "list"]
    main()
    out = capsys.readouterr().out
    assert "git log --oneline" in out
    assert "[git]" in out

    # List with matching tool filter
    sys.argv = ["cmdstore", "--store", test_store, "list", "--tool", "git"]
    main()
    out = capsys.readouterr().out
    assert "git log --oneline" in out

    # List with non-matching tool filter
    sys.argv = ["cmdstore", "--store", test_store, "list", "--tool", "docker"]
    main()
    out = capsys.readouterr().out
    assert "No commands found." in out


def test_cli_corrupt_store_exits_nonzero(tmp_path: Path, capsys):
    """A corrupt store stops CLI execution with a non-zero exit code."""
    test_store = tmp_path / "corrupt_store"
    test_store.mkdir(parents=True)
    commands_file = test_store / "commands.json"
    commands_file.write_text("{corrupt json", encoding="utf-8")

    sys.argv = ["cmdstore", "--store", str(test_store), "list"]
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    out = capsys.readouterr().out
    assert "Error: Malformed JSON" in out


def test_cli_missing_action_exits_code_2(capsys):
    """Running cmdstore without an action exits with argparse error code 2."""
    sys.argv = ["cmdstore"]
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
