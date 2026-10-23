"""Tests for malformed store data, shape validation, and atomic-write safety."""

import json
import os
import stat
from pathlib import Path

import pytest

from cmdstore.errors import MalformedStoreError, StoreWriteError
from cmdstore.storage import atomic_save_json, load_json_file, validate_commands
from cmdstore.store import CommandStore


def test_malformed_json_in_commands_file_raises_error_and_preserves_file(store_dir: Path):
    """Corrupt JSON in commands.json must raise MalformedStoreError and remain untouched."""
    commands_file = store_dir / "commands.json"
    corrupt_content = '{"unclosed": json, syntax'
    commands_file.write_text(corrupt_content, encoding="utf-8")

    # Creating store or loading commands must fail loudly
    with pytest.raises(MalformedStoreError) as exc_info:
        CommandStore(store_path=str(store_dir))

    assert str(commands_file) in str(exc_info.value)
    # File content must remain untouched for manual recovery
    assert commands_file.read_text(encoding="utf-8") == corrupt_content


def test_malformed_json_in_config_file_raises_error_and_preserves_file(store_dir: Path):
    """Corrupt JSON in config.json must raise MalformedStoreError and remain untouched."""
    # Create valid commands.json first
    commands_file = store_dir / "commands.json"
    commands_file.write_text("[]", encoding="utf-8")

    config_file = store_dir / "config.json"
    corrupt_content = "{invalid json content"
    config_file.write_text(corrupt_content, encoding="utf-8")

    with pytest.raises(MalformedStoreError) as exc_info:
        CommandStore(store_path=str(store_dir))

    assert str(config_file) in str(exc_info.value)
    assert config_file.read_text(encoding="utf-8") == corrupt_content


def test_invalid_top_level_shape_raises_error(store_dir: Path):
    """Non-list commands.json or non-dict config.json must raise MalformedStoreError."""
    commands_file = store_dir / "commands.json"
    commands_file.write_text('{"command": "foo"}', encoding="utf-8")  # Dict instead of list

    with pytest.raises(MalformedStoreError) as exc_info:
        load_json_file(commands_file, expected_type=list)
    assert "expected list, got dict" in str(exc_info.value)

    config_file = store_dir / "config.json"
    config_file.write_text('["item1", "item2"]', encoding="utf-8")  # List instead of dict

    with pytest.raises(MalformedStoreError) as exc_info:
        load_json_file(config_file, expected_type=dict)
    assert "expected dict, got list" in str(exc_info.value)


def test_invalid_command_record_fields_raise_error(store_dir: Path):
    """Records missing required 'id' or 'command' fields fail validation."""
    commands_file = store_dir / "commands.json"

    # Missing 'id'
    records = [{"command": "git pull"}]
    with pytest.raises(MalformedStoreError) as exc_info:
        validate_commands(records, path=commands_file)
    assert "Missing or invalid 'id'" in str(exc_info.value)

    # Missing 'command'
    records = [{"id": "uuid-123"}]
    with pytest.raises(MalformedStoreError) as exc_info:
        validate_commands(records, path=commands_file)
    assert "Missing or invalid 'command'" in str(exc_info.value)

    # Element is not a dict
    records = ["not a dict"]
    with pytest.raises(MalformedStoreError) as exc_info:
        validate_commands(records, path=commands_file)
    assert "expected object" in str(exc_info.value)


def test_valid_records_with_missing_optional_fields_get_defaults():
    """Existing records with missing optional fields remain readable with applied defaults."""
    raw_records = [
        {"id": "1", "command": "echo hi"},
        {
            "id": "2",
            "command": "git push",
            "description": "push commits",
            "tags": ["git"],
            "tool": "git",
            "created_at": "2026-01-01T00:00:00",
            "used_count": 5,
        },
    ]
    validated = validate_commands(raw_records)
    assert len(validated) == 2

    # Defaults applied to record 1
    assert validated[0]["description"] == ""
    assert validated[0]["tags"] == []
    assert validated[0]["tool"] == ""
    assert validated[0]["created_at"] == ""
    assert validated[0]["used_count"] == 0

    # Values preserved for record 2
    assert validated[1]["used_count"] == 5
    assert validated[1]["tags"] == ["git"]


def test_atomic_write_failure_preserves_valid_file_and_cleans_up_temp(tmp_path: Path, monkeypatch):
    """An interrupted or failed write preserves prior file and removes temporary files."""
    target_file = tmp_path / "data.json"
    original_data = [{"id": "orig", "command": "echo original"}]
    atomic_save_json(target_file, original_data)

    # Force os.replace to fail, simulating write/replace error
    def failing_replace(src, dst):
        raise OSError("Simulated disk replacement failure")

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(StoreWriteError):
        atomic_save_json(target_file, [{"id": "new", "command": "echo new"}])

    # Original file is intact
    with open(target_file, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == original_data

    # No leftover .tmp files
    tmp_files = list(tmp_path.glob(".*.tmp"))
    assert len(tmp_files) == 0


def test_atomic_write_preserves_file_permissions(tmp_path: Path):
    """Atomic write preserves existing file permissions."""
    target_file = tmp_path / "secure_store.json"
    atomic_save_json(target_file, {"initial": "value"})

    # Set mode to 0o600 (owner read/write only)
    os.chmod(target_file, 0o600)
    current_mode = stat.S_IMODE(os.stat(target_file).st_mode)

    # Write new content
    atomic_save_json(target_file, {"updated": "value"})

    new_mode = stat.S_IMODE(os.stat(target_file).st_mode)
    assert new_mode == current_mode
