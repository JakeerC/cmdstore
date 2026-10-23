"""Pytest fixtures and configuration for cmdstore test suite."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cmdstore.store import CommandStore


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    """Return an isolated temporary directory for store data."""
    path = tmp_path / "test_store"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def store(store_dir: Path) -> CommandStore:
    """Provide a fresh CommandStore instance pointing to an isolated directory."""
    return CommandStore(store_path=str(store_dir))


@pytest.fixture
def mock_clipboard(monkeypatch):
    """Mock pyperclip clipboard functions to avoid touching system clipboard."""
    copied_content = []

    def mock_copy(text: str):
        copied_content.append(text)

    def mock_paste():
        return copied_content[-1] if copied_content else ""

    mock = MagicMock()
    mock.copy.side_effect = mock_copy
    mock.paste.side_effect = mock_paste
    mock.copied = copied_content

    monkeypatch.setattr("cmdstore.store.pyperclip.copy", mock.copy)
    monkeypatch.setattr("cmdstore.store.pyperclip.paste", mock.paste)
    return mock
