"""Tests for store initialization and configuration management."""

import json
from pathlib import Path

from cmdstore.config import load_global_store_path, save_global_store_path
from cmdstore.store import DEFAULT_CONFIG, CommandStore


def test_store_initialization_creates_valid_json_files(store_dir: Path):
    """Store creation should create commands.json and config.json with valid JSON content."""
    commands_file = store_dir / "commands.json"
    config_file = store_dir / "config.json"

    assert not commands_file.exists()
    assert not config_file.exists()

    store = CommandStore(store_path=str(store_dir))

    assert commands_file.exists()
    assert config_file.exists()

    with open(commands_file, encoding="utf-8") as f:
        commands_data = json.load(f)
    assert commands_data == []

    with open(config_file, encoding="utf-8") as f:
        config_data = json.load(f)
    assert config_data == DEFAULT_CONFIG
    assert store.get_config() == DEFAULT_CONFIG


def test_nested_config_merge_preserves_defaults_and_applies_overrides(store_dir: Path):
    """User configuration overrides specific nested fields while keeping other defaults."""
    store = CommandStore(store_path=str(store_dir))

    user_config = {
        "auto_copy": {"enabled": False},
        "search": {"sort_by": "alphabetical"},
        "custom_key": "custom_val",
    }
    store._save_config(user_config)

    merged = store.get_config()

    # Overridden values
    assert merged["auto_copy"]["enabled"] is False
    assert merged["search"]["sort_by"] == "alphabetical"
    assert merged["custom_key"] == "custom_val"

    # Preserved defaults
    assert merged["auto_copy"]["show_notification"] is True
    assert merged["search"]["sort_order"] == "desc"
    assert merged["search"]["show_usage_count"] is True
    assert merged["fzf"]["height"] == "50%"
    assert merged["ui"]["use_fzf"] is True


def test_default_config_mutation_does_not_leak_across_instances(tmp_path: Path):
    """Mutating config from one store does not mutate another store or DEFAULT_CONFIG."""
    dir1 = tmp_path / "store1"
    dir2 = tmp_path / "store2"

    store1 = CommandStore(store_path=str(dir1))
    store2 = CommandStore(store_path=str(dir2))

    cfg1 = store1.get_config()
    cfg1["auto_copy"]["enabled"] = False
    cfg1["defaults"]["tags"].append("mutated_tag")

    cfg2 = store2.get_config()
    assert cfg2["auto_copy"]["enabled"] is True
    assert "mutated_tag" not in cfg2["defaults"]["tags"]
    assert DEFAULT_CONFIG["auto_copy"]["enabled"] is True
    assert DEFAULT_CONFIG["defaults"]["tags"] == []


def test_global_config_save_and_load(tmp_path: Path):
    """Global store path configuration should be saved and loaded atomically."""
    config_file = tmp_path / "global_config.json"
    assert load_global_store_path(config_path=config_file) is None

    save_global_store_path("/path/to/custom/store", config_path=config_file)
    assert load_global_store_path(config_path=config_file) == "/path/to/custom/store"
